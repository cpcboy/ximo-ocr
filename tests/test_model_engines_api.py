"""任务绑定识别引擎：校验、默认值与健康检查清单。"""
from __future__ import annotations

import importlib
from types import SimpleNamespace
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from backend.model_registry import ModelEndpointRegistry


@pytest.fixture()
def api_client(tmp_path, monkeypatch):
    config = importlib.import_module("backend.config")
    store_module = importlib.import_module("backend.store")
    monkeypatch.setattr(config, "DATA_ROOT", tmp_path)
    monkeypatch.setattr(config, "JOBS_ROOT", tmp_path / "jobs")
    monkeypatch.setattr(store_module, "JOBS_ROOT", tmp_path / "jobs")
    api = importlib.import_module("backend.app")
    monkeypatch.setattr(
        api,
        "registry",
        ModelEndpointRegistry(tmp_path / "config" / "models.json"),
    )
    monkeypatch.setattr(
        api,
        "model_download",
        SimpleNamespace(
            status=lambda: {
                "running": False,
                "model_ready": False,
                "runtime_ready": False,
            }
        ),
    )
    monkeypatch.setattr(api, "engine", SimpleNamespace(busy=False, status=lambda: {
        "loaded": False, "state": "not_loaded", "message": "未加载", "path": "x",
    }))
    # 不启动 lifespan：任务只入队，不会真的推理。
    return TestClient(api.app, base_url="http://127.0.0.1:18765")


def upload(client, *, engine: str | None = None, name: str = "合成.txt"):
    headers = {
        "Content-Type": "application/octet-stream",
        "X-File-Name": quote(name),
        "X-File-Type": "text/plain",
        "X-OCR-Options": "%7B%7D",
    }
    if engine is not None:
        headers["X-OCR-Engine"] = engine
    return client.post("/api/jobs", headers=headers, content=b"hello")


def test_remote_engine_job_binds_endpoint(api_client):
    response = upload(api_client, engine="preset-4090")
    assert response.status_code == 201, response.text
    job = response.json()
    assert job["engine_id"] == "preset-4090"
    assert job["engine_label"] == "4090 · Qwen3.8 Flash"
    assert job["status"] == "queued"


def test_unknown_engine_is_rejected(api_client):
    response = upload(api_client, engine="ep-does-not-exist")
    assert response.status_code == 422


def test_local_engine_requires_ready_model(api_client):
    response = upload(api_client, engine="local")
    assert response.status_code == 409
    assert "模型" in response.json()["detail"]


def test_local_engine_is_default(api_client):
    response = upload(api_client)
    assert response.status_code == 409  # 默认本地，模型未就绪
    assert "模型" in response.json()["detail"]


def test_engine_catalog_lists_local_and_remote(api_client):
    response = api_client.get("/api/models")
    assert response.status_code == 200
    payload = response.json()
    ids = [engine["id"] for engine in payload["engines"]]
    assert ids[0] == "local"
    assert "preset-3090ti" in ids and "preset-4090" in ids
    assert payload["max_parallel"] == 9
    remote = [e for e in payload["engines"] if e["kind"] == "remote"]
    assert all(e["max_concurrency"] == 1 for e in remote)
    assert all(e["api_key_set"] is False for e in remote)


def test_endpoint_crud_and_key_masking(api_client):
    created = api_client.post(
        "/api/models/endpoints",
        json={
            "name": "自建接口",
            "base_url": "http://127.0.0.1:9000/v1",
            "model": "m1",
            "api_key": "sk-secret-value",
            "max_concurrency": 3,
        },
    )
    assert created.status_code == 201, created.text
    endpoint = created.json()
    assert endpoint["api_key_set"] is True
    assert "sk-secret-value" not in created.text

    listed = api_client.get("/api/models/endpoints").json()["endpoints"]
    assert any(item["id"] == endpoint["id"] for item in listed)
    assert "sk-secret-value" not in api_client.get("/api/models/endpoints").text

    updated = api_client.put(
        f"/api/models/endpoints/{endpoint['id']}",
        json={"name": "自建接口 2"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "自建接口 2"
    assert updated.json()["api_key_set"] is True

    deleted = api_client.delete(f"/api/models/endpoints/{endpoint['id']}")
    assert deleted.status_code == 204
    assert all(
        item["id"] != endpoint["id"]
        for item in api_client.get("/api/models/endpoints").json()["endpoints"]
    )


def test_invalid_endpoint_payload_is_422(api_client):
    response = api_client.post(
        "/api/models/endpoints",
        json={"name": "坏地址", "base_url": "ftp://x/v1", "model": "m"},
    )
    assert response.status_code == 422


def test_discover_requires_valid_url(api_client):
    response = api_client.post(
        "/api/models/discover",
        json={"base_url": "not-a-url"},
    )
    assert response.status_code == 422


def test_scan_page_image_rejects_deleted_and_disabled_endpoints(api_client, tmp_path):
    api = importlib.import_module("backend.app")
    image = tmp_path / "page.png"
    image.write_bytes(b"png")
    options = {"prompt": "x", "mode": "precision", "max_length": 4096}

    with pytest.raises(RuntimeError) as deleted:
        api._scan_page_image("ep-missing", image, options)
    assert "已被删除" in str(deleted.value)

    api.registry.update("preset-4090", {"enabled": False})
    with pytest.raises(RuntimeError) as disabled:
        api._scan_page_image("preset-4090", image, options)
    assert "已停用" in str(disabled.value)


def test_test_endpoint_does_not_reuse_stored_key_for_new_url(api_client, monkeypatch):
    api = importlib.import_module("backend.app")
    captured = {}

    class FakeRemote:
        def __init__(self, endpoint):
            captured.update(endpoint)

        def list_models(self, timeout=15.0):
            return ["m"]

    seen = []
    monkeypatch.setattr(api, "RemoteEngine", FakeRemote)
    api.registry.update("preset-4090", {"api_key": "sk-stored-secret"})
    response = api_client.post(
        "/api/models/endpoints/preset-4090/test",
        json={"base_url": "http://127.0.0.1:9999/v1"},
    )
    seen.append(captured.get("api_key"))
    assert response.status_code == 200
    assert seen == [""], "改为其它地址时不得携带已保存的密钥"


def test_canceling_job_is_not_restarted(api_client):
    api = importlib.import_module("backend.app")
    job = api.store.create(
        filename="合成.txt",
        content_type="text/plain",
        options={},
        engine_id="preset-4090",
        engine_label="4090",
    )
    api.store.update(
        job["id"],
        status="canceling",
        cancel_requested=True,
        pages=[],
    )
    api._process_job(job["id"])
    latest = api.store.get(job["id"])
    assert latest["status"] == "canceling"
    assert latest["pages"] == []


def test_queued_job_canceled_before_start_is_finalized(api_client):
    """上传期间被取消、却仍写成 queued 的任务必须收尾，不能反复调度。"""
    api = importlib.import_module("backend.app")
    job = api.store.create(
        filename="合成.txt",
        content_type="text/plain",
        options={},
        engine_id="preset-4090",
        engine_label="4090",
    )
    api.store.update(
        job["id"],
        status="queued",
        cancel_requested=True,
    )
    assert api._job_was_requeued(job["id"]) is False
    assert api._resolve_job_engine(job["id"]) is None

    api._process_job(job["id"])

    latest = api.store.get(job["id"])
    assert latest["status"] == "canceled"


def test_orphan_canceling_job_can_be_deleted(api_client):
    api = importlib.import_module("backend.app")
    job = api.store.create(
        filename="合成.txt",
        content_type="text/plain",
        options={},
        engine_id="preset-4090",
        engine_label="4090",
    )
    api.store.update(job["id"], status="canceling", cancel_requested=True)
    response = api_client.delete(f"/api/jobs/{job['id']}")
    assert response.status_code == 204


def test_changing_base_url_with_blank_key_drops_stored_key(api_client):
    api = importlib.import_module("backend.app")
    api.registry.update("preset-4090", {"api_key": "sk-stored"})
    response = api_client.put(
        "/api/models/endpoints/preset-4090",
        json={"base_url": "http://127.0.0.1:9999/v1", "api_key": ""},
    )
    assert response.status_code == 200
    assert api.registry.get("preset-4090")["api_key"] == ""
    assert response.json()["api_key_set"] is False


def test_direct_text_job_runs_to_completion(api_client):
    """文本文件不依赖模型，用来覆盖 queued→preparing→running→completed 全链路。"""
    api = importlib.import_module("backend.app")
    job = api.store.create(
        filename="合成.txt",
        content_type="text/plain",
        options={},
        engine_id="preset-4090",
        engine_label="4090",
    )
    source = api.store.job_dir(job["id"]) / job["source_file"]
    source.write_text("第一行内容\n第二行内容", encoding="utf-8")
    api.store.update(job["id"], status="queued", size=source.stat().st_size)

    api._process_job(job["id"])

    latest = api.store.get(job["id"])
    assert latest["status"] == "completed"
    assert "第一行内容" in latest["pages"][0]["text"]
    assert latest["stats"]["elapsed_seconds"] >= 0
