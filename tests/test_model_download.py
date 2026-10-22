from __future__ import annotations

import hashlib
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.model_catalog import RECEIPT, model_verified
from backend.model_download import ModelDownloadManager


@pytest.fixture
def model_server():
    payload = b"test-model-content\n" * 1000
    state = SimpleNamespace(mode="range", ranges=[], payload=payload)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requested = self.headers.get("Range")
            state.ranges.append(requested)
            start = int(requested.split("=")[1].split("-")[0]) if requested else 0
            if state.mode == "ignore":
                start = 0
            body = state.payload[start:]
            self.send_response(206 if start else 200)
            if start:
                offset = start + 1 if state.mode == "wrong-range" else start
                self.send_header("Content-Range", f"bytes {offset}-{len(state.payload)-1}/{len(state.payload)}")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if state.mode == "truncated":
                body = body[: len(body) // 2]
            self.wfile.write(body)

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    state.url = f"http://127.0.0.1:{server.server_port}/model"
    yield state
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


@pytest.fixture
def downloader(tmp_path, model_server, monkeypatch):
    manager = ModelDownloadManager(tmp_path / "models", kind="mlx")
    item = {"path": "model.safetensors", "size": len(model_server.payload),
            "algorithm": "sha256", "digest": hashlib.sha256(model_server.payload).hexdigest()}
    manager.spec = {"id": "test/local", "revision": "pinned-test", "weights": item["path"], "files": [item]}
    manager._bytes_total = item["size"]
    manager.model_dir.mkdir()
    monkeypatch.setattr(manager, "_file_url", lambda _name: model_server.url)
    monkeypatch.setattr(manager, "_runtime_ready", lambda: True)
    return manager


def finish(manager):
    manager.start()
    manager._thread.join(timeout=8)
    assert not manager._thread.is_alive()
    return manager.status()


def test_first_download_and_receipt_invalidation(downloader, model_server):
    state = finish(downloader)
    assert state["model_ready"] and state["state"] == "completed"
    assert state["progress"] == 100
    assert (downloader.model_dir / "model.safetensors").read_bytes() == model_server.payload
    assert model_verified(downloader.model_dir, downloader.spec)
    # A same-size corrupt replacement must not retain a ready status.
    (downloader.model_dir / "model.safetensors").write_bytes(b"x" * len(model_server.payload))
    assert not downloader.status()["model_ready"]
    assert finish(downloader)["model_ready"]


@pytest.mark.parametrize("mode", ["range", "ignore"])
def test_resume_or_server_ignoring_range_never_duplicates(downloader, model_server, mode):
    model_server.mode = mode
    (downloader.model_dir / "model.safetensors.part").write_bytes(model_server.payload[:100])
    assert downloader.status()["state"] == "cancelled"
    assert finish(downloader)["model_ready"]
    assert model_server.ranges == ["bytes=100-"]
    assert (downloader.model_dir / "model.safetensors").read_bytes() == model_server.payload


def test_wrong_content_range_rejected_without_changing_partial(downloader, model_server):
    model_server.mode = "wrong-range"
    partial = downloader.model_dir / "model.safetensors.part"
    partial.write_bytes(model_server.payload[:100])
    assert finish(downloader)["state"] == "error"
    assert partial.read_bytes() == model_server.payload[:100]
    assert not (downloader.model_dir / RECEIPT).exists()


@pytest.mark.parametrize("mode", ["truncated", "bad-hash"])
def test_incomplete_or_corrupt_model_is_never_enabled(downloader, model_server, mode):
    model_server.mode = mode
    if mode == "bad-hash":
        model_server.payload = b"x" * len(model_server.payload)
    state = finish(downloader)
    assert not state["model_ready"]
    assert state["state"] == "error"
    assert not (downloader.model_dir / "model.safetensors").exists()


def test_complete_partial_is_validated_without_416_request(downloader, model_server):
    (downloader.model_dir / "model.safetensors.part").write_bytes(model_server.payload)
    assert finish(downloader)["model_ready"]
    assert model_server.ranges == []


def test_cancel_then_resume_preserves_partial(downloader, model_server, monkeypatch):
    # Cancel immediately after the first network read, while saving that chunk.
    original = downloader._set

    def cancel_after_bytes(**values):
        original(**values)
        if values.get("bytes_downloaded", 0) > 0:
            downloader._cancel.set()

    monkeypatch.setattr(downloader, "_set", cancel_after_bytes)
    assert finish(downloader)["state"] == "cancelled"
    assert (downloader.model_dir / "model.safetensors.part").exists()
    assert not (downloader.model_dir / RECEIPT).exists()
    monkeypatch.setattr(downloader, "_set", original)
    assert finish(downloader)["model_ready"]


def test_insufficient_disk_never_starts_network(downloader, model_server, monkeypatch):
    monkeypatch.setattr("backend.model_download.shutil.disk_usage", lambda _path: SimpleNamespace(free=1))
    assert "磁盘空间不足" in finish(downloader)["message"]
    assert model_server.ranges == []


def test_concurrent_start_only_creates_one_worker(downloader, monkeypatch):
    began, release = threading.Event(), threading.Event()
    calls = []

    def work():
        calls.append(True)
        began.set()
        release.wait(timeout=5)

    monkeypatch.setattr(downloader, "_run", work)
    threads = [threading.Thread(target=downloader.start) for _ in range(8)]
    for thread in threads:
        thread.start()
    assert began.wait(timeout=3)
    for thread in threads:
        thread.join(timeout=2)
    release.set()
    downloader._thread.join(timeout=2)
    assert len(calls) == 1


def test_missing_runtime_does_not_publish_receipt(downloader, monkeypatch):
    monkeypatch.setattr(downloader, "_runtime_ready", lambda: False)
    state = finish(downloader)
    assert state["state"] == "error" and not state["model_ready"]
    assert not (downloader.model_dir / RECEIPT).exists()


def test_idle_cancel_and_runtime_subprocess_cancellation(downloader):
    assert downloader.cancel()["state"] == "idle"
    import sys

    done = threading.Event()

    def work():
        with pytest.raises(InterruptedError):
            downloader._run_command([sys.executable, "-c", "import time; time.sleep(30)"], "test")
        done.set()

    thread = threading.Thread(target=work)
    thread.start()
    time.sleep(0.2)
    downloader._cancel.set()
    assert done.wait(timeout=5)
    thread.join(timeout=1)


def test_symlink_target_not_overwritten(downloader, model_server, tmp_path):
    protected = tmp_path / "protected"
    protected.write_bytes(b"user file")
    try:
        (downloader.model_dir / "model.safetensors").symlink_to(protected)
    except OSError:
        pytest.skip("Windows account cannot create symlinks")
    assert finish(downloader)["state"] == "error"
    assert protected.read_bytes() == b"user file"


def test_pinned_manifests_include_runtime_and_hashes():
    from backend.model_catalog import model_spec

    for kind in ("mlx", "windows"):
        spec = model_spec(kind)
        assert len(spec["revision"]) == 40
        assert spec["weights"] in {f["path"] for f in spec["files"]}
        assert "tokenizer.json" in {f["path"] for f in spec["files"]}
        for item in spec["files"]:
            assert item["size"] > 0
            assert len(item["digest"]) == (64 if item["algorithm"] == "sha256" else 40)
            assert not Path(item["path"]).is_absolute() and ".." not in Path(item["path"]).parts


@pytest.mark.parametrize("receipt", [[], None, "invalid", 1, {"files": None}])
def test_malformed_receipt_is_not_ready(downloader, receipt):
    (downloader.model_dir / RECEIPT).write_text(json.dumps(receipt))
    assert not model_verified(downloader.model_dir, downloader.spec)
    assert not downloader.status()["model_ready"]


def test_windows_runtime_needs_versioned_receipt_and_real_probe(tmp_path, monkeypatch):
    import sys
    from backend.model_download import WINDOWS_RUNTIME_IMPORTS, WINDOWS_RUNTIME_VERSION

    manager = ModelDownloadManager(tmp_path / "models" / "test", kind="windows")
    for name in WINDOWS_RUNTIME_IMPORTS:
        directory = manager._runtime_root() / name
        directory.mkdir(parents=True)
        (directory / "__init__.py").write_text("")
    marker = manager._runtime_marker()
    marker.write_text("{}")
    assert not manager._runtime_ready()
    marker.write_text(json.dumps({"version": WINDOWS_RUNTIME_VERSION, "python": list(sys.version_info[:2])}))
    calls = []
    monkeypatch.setattr(manager, "_probe_windows_runtime", lambda: calls.append(True) or False)
    assert not manager._runtime_ready()
    assert not manager._runtime_ready()
    assert len(calls) == 1  # health checks cache the probe
    manager._runtime_probe_cache = None
    monkeypatch.setattr(manager, "_probe_windows_runtime", lambda: calls.append(True) or True)
    assert manager._runtime_ready()
    manager._install_runtime()  # repair bypasses the cache
    assert len(calls) == 3


def test_windows_runtime_repair_reinstalls_after_failed_probe(tmp_path, monkeypatch):
    manager = ModelDownloadManager(tmp_path / "models" / "test", kind="windows")
    monkeypatch.setattr(manager, "_runtime_ready", lambda: False)
    monkeypatch.setattr(manager, "_ensure_uv", lambda: Path("unused-test-uv"))
    commands = []
    monkeypatch.setattr(manager, "_run_command", lambda cmd, _message: commands.append(cmd))
    monkeypatch.setattr(manager, "_probe_windows_runtime", lambda: False)
    with pytest.raises(RuntimeError, match="导入或版本校验失败"):
        manager._install_runtime()
    assert len(commands) == 2 and all("--reinstall" in command for command in commands)
    assert not manager._runtime_marker().exists()
