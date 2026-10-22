from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

from .config import resolve_model_dir
from .model_catalog import RECEIPT, current_platform, file_stats, model_spec, model_verified

UV_VERSION = "0.12.0"
UV_WINDOWS_SHA256 = "68200e25de594df92387186bbfb9d9df606ec1d87efaa0ae0c7f690970e53db6"
UV_WINDOWS_URL = (
    "https://github.com/astral-sh/uv/releases/download/"
    f"{UV_VERSION}/uv-x86_64-pc-windows-msvc.zip"
)
WINDOWS_RUNTIME_VERSION = 2
WINDOWS_RUNTIME_IMPORTS = {
    "torch": "2.10.0", "torchvision": "0.25.0", "transformers": "4.57.1",
    "numpy": "2.4.6", "PIL": "12.1.1", "safetensors": "0.7.0",
    "einops": "0.8.2", "psutil": "7.2.2", "requests": "2.32.5",
    "tqdm": "4.67.1", "matplotlib": "3.10.8",
}


class ModelDownloadManager:
    """One worker; pinned files become usable only after content validation."""

    def __init__(self, model_dir: Path, *, kind: str | None = None):
        self.model_dir = model_dir
        self.kind = kind or current_platform()
        self.available = self.kind in {"mlx", "windows"}
        self.spec = model_spec(self.kind or "mlx")
        self._lock = threading.RLock()
        self._cancel = threading.Event()
        self._thread: threading.Thread | None = None
        self._state = "idle"
        self._message = "等待下载"
        self._progress = 0
        self._bytes_downloaded = 0
        self._bytes_total = sum(item["size"] for item in self.spec["files"])
        self._runtime_variant = "Apple MLX" if self.kind == "mlx" else "NVIDIA CUDA 12.8"
        self._error: str | None = None
        self._runtime_probe_cache: tuple[Any, bool] | None = None

    def _set(self, **values: Any) -> None:
        with self._lock:
            for key, value in values.items():
                setattr(self, f"_{key}", value)

    def _check_cancel(self) -> None:
        if self._cancel.is_set():
            raise InterruptedError("下载已暂停")

    def _runtime_root(self) -> Path:
        return Path(os.getenv("OCR_STUDIO_AI_PACKAGES_DIR", self.model_dir.parents[1] / "ai-packages"))

    def _runtime_marker(self) -> Path:
        return self._runtime_root() / ".unlimited-ocr-cu128-ready"

    def _probe_windows_runtime(self) -> bool:
        # Embedded Python ignores PYTHONPATH. Add only the app-managed target
        # explicitly; do not accept packages found in the builder/user's Python.
        code = (
            "import sys, importlib; from pathlib import Path; "
            f"root=Path({str(self._runtime_root())!r}).resolve(); sys.path.insert(0, str(root)); "
            f"expected={WINDOWS_RUNTIME_IMPORTS!r}; "
            "modules={name: importlib.import_module(name) for name in expected}; "
            "assert all(Path(module.__file__).resolve().is_relative_to(root) for module in modules.values()); "
            "assert all(str(getattr(modules[name], '__version__', '')).split('+')[0] == version "
            "for name, version in expected.items()); import addict, easydict"
        )
        try:
            result = subprocess.run([sys.executable, "-c", code],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), check=False)
            return result.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False

    def _runtime_ready(self) -> bool:
        if self.kind == "windows":
            try:
                marker = self._runtime_marker()
                receipt = json.loads(marker.read_text(encoding="utf-8"))
                if not isinstance(receipt, dict) or receipt.get("version") != WINDOWS_RUNTIME_VERSION:
                    return False
                if receipt.get("python") != list(sys.version_info[:2]):
                    return False
                files = [marker] + [self._runtime_root() / name / "__init__.py"
                                   for name in WINDOWS_RUNTIME_IMPORTS]
                fingerprint = tuple((p.stat().st_size, p.stat().st_mtime_ns) for p in files)
            except (OSError, ValueError, TypeError):
                return False
            if self._runtime_probe_cache is None or self._runtime_probe_cache[0] != fingerprint:
                self._runtime_probe_cache = (fingerprint, self._probe_windows_runtime())
            return self._runtime_probe_cache[1]
        if self.kind == "mlx":
            return all(importlib.util.find_spec(name) is not None for name in
                       ("mlx", "transformers", "safetensors", "numpy", "PIL"))
        return False

    def status(self) -> dict[str, Any]:
        with self._lock:
            running = bool(self._thread and self._thread.is_alive())
            external = self.kind == "mlx" and resolve_model_dir(self.model_dir) != self.model_dir
            ready = not running and (external or model_verified(self.model_dir, self.spec))
            runtime_ready = self._runtime_ready()
            state, message, progress = self._state, self._message, self._progress
            if state in {"idle", "completed"}:
                if ready and runtime_ready:
                    state, progress = "completed", 100
                    message = "正在使用已有的 LM Studio 模型" if external else "模型与推理组件已就绪"
                else:
                    state, progress = "idle", 0
                    message = "尚未就绪，请下载或校验模型"
                    if any(self.model_dir.glob("*.part")):
                        state, message = "cancelled", "发现上次未完成的下载，点击继续下载即可续传"
            if not self.available:
                message = "MLX 需要 Apple Silicon 与 macOS 14+；Windows 版使用 NVIDIA/PyTorch。"
            return {
                "available": self.available, "platform": self.kind,
                "model_id": self.spec["id"],
                "model_url": f"https://huggingface.co/{self.spec['id']}",
                "model_revision": self.spec["revision"],
                "download_path": str(self.model_dir),
                "using_external_model": external, "model_ready": ready,
                "state": state, "message": message, "progress": progress,
                "bytes_downloaded": self._bytes_total if ready else self._bytes_downloaded,
                "bytes_total": self._bytes_total,
                "runtime_variant": self._runtime_variant, "runtime_ready": runtime_ready,
                "error": self._error, "running": running,
            }

    def start(self) -> dict[str, Any]:
        if not self.available:
            raise RuntimeError("当前平台不支持该模型，请使用 Apple Silicon macOS 14+ 或 Windows NVIDIA 版本")
        with self._lock:
            if self._thread and self._thread.is_alive():
                return self.status()
            self._cancel.clear()
            self._set(state="checking", message="正在检查模型文件与磁盘空间", progress=0,
                      bytes_downloaded=0, error=None)
            self._thread = threading.Thread(target=self._run, name="model-download", daemon=True)
            self._thread.start()
        return self.status()

    def cancel(self) -> dict[str, Any]:
        with self._lock:
            if self._thread and self._thread.is_alive():
                self._cancel.set()
                self._set(state="canceling", message="正在暂停下载，未完成文件会保留用于续传")
        return self.status()

    def _valid_file(self, path: Path, item: dict[str, Any]) -> bool:
        if path.is_symlink() or not path.is_file() or path.stat().st_size != item["size"]:
            return False
        digest = hashlib.sha256() if item["algorithm"] == "sha256" else hashlib.sha1()
        if item["algorithm"] == "git-sha1":
            digest.update(f"blob {item['size']}\0".encode())
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                self._check_cancel()
                digest.update(chunk)
        return digest.hexdigest() == item["digest"]

    def _file_url(self, relative_path: str) -> str:
        quoted = urllib.parse.quote(relative_path, safe="/")
        return f"https://huggingface.co/{self.spec['id']}/resolve/{self.spec['revision']}/{quoted}?download=true"

    def _download_file(self, item: dict[str, Any], completed: int) -> int:
        name, size = item["path"], item["size"]
        if Path(name).is_absolute() or ".." in Path(name).parts:
            raise RuntimeError("无效的模型文件清单")
        destination = self.model_dir / name
        partial = destination.with_name(destination.name + ".part")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.is_symlink() or partial.is_symlink():
            raise RuntimeError("模型下载目录包含符号链接，请选择独立应用目录")
        existing = partial.stat().st_size if partial.exists() else 0
        if existing == size and self._valid_file(partial, item):
            partial.replace(destination)
            return size
        if existing >= size:
            partial.unlink()
            existing = 0
        headers = {"User-Agent": "MoxiOCRStudio/1.3", "Accept-Encoding": "identity"}
        if existing:
            headers["Range"] = f"bytes={existing}-"
        request = urllib.request.Request(self._file_url(name), headers=headers)
        with urllib.request.urlopen(request, timeout=20) as response:
            if response.status == 206:
                match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", response.headers.get("Content-Range", ""))
                if not match or tuple(map(int, match.groups())) != (existing, size - 1, size):
                    raise RuntimeError("服务器返回了不匹配的续传区间；保留断点，请重试")
            elif response.status == 200:
                existing = 0
            else:
                raise RuntimeError(f"模型服务器返回 HTTP {response.status}")
            self._check_cancel()
            with partial.open("ab" if existing else "wb") as output:
                current = existing
                while True:
                    self._check_cancel()
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    if current + len(chunk) > size:
                        raise RuntimeError(f"{name} 超过清单大小，已停止下载")
                    output.write(chunk)
                    current += len(chunk)
                    done = completed + current
                    self._set(state="downloading", message=f"正在下载 {name}",
                              progress=min(98, int(98 * done / self._bytes_total)), bytes_downloaded=done)
        self._set(state="verifying", message=f"正在校验 {name}")
        if not self._valid_file(partial, item):
            if partial.stat().st_size == size:
                partial.unlink()
            raise RuntimeError(f"{name} 不完整或校验不符，未启用该文件；可点击继续下载")
        self._check_cancel()
        partial.replace(destination)
        return size

    def _download_model(self) -> None:
        self.model_dir.mkdir(parents=True, exist_ok=True)
        (self.model_dir / RECEIPT).unlink(missing_ok=True)
        pending = []
        completed = 0
        for item in self.spec["files"]:
            self._check_cancel()
            self._set(message=f"正在校验已有文件 {item['path']}")
            if self._valid_file(self.model_dir / item["path"], item):
                completed += item["size"]
            else:
                pending.append(item)
        remaining = 0
        for item in pending:
            part = self.model_dir / (item["path"] + ".part")
            partial_size = part.stat().st_size if part.is_file() and not part.is_symlink() else 0
            if partial_size >= item["size"]:
                remaining += 0 if self._valid_file(part, item) else item["size"]
            else:
                remaining += item["size"] - partial_size
        reserve = 512 * 1024**2
        if self.kind == "windows" and not self._runtime_ready():
            reserve += 10 * 1024**3
        if shutil.disk_usage(self.model_dir).free < remaining + reserve:
            raise RuntimeError(f"磁盘空间不足，至少还需 {(remaining + reserve) / 1024**3:.1f} GB 可用空间")
        self._set(bytes_downloaded=completed)
        for item in sorted(pending, key=lambda f: f["path"] == self.spec["weights"]):
            self._check_cancel()
            for attempt in range(3):
                try:
                    completed += self._download_file(item, completed)
                    break
                except (urllib.error.URLError, TimeoutError, ConnectionError):
                    self._check_cancel()
                    if attempt == 2:
                        raise RuntimeError("模型下载网络中断；已保留断点，请检查网络后继续") from None
                    self._set(message="网络中断，正在重试；断点已保留")
                    if self._cancel.wait(attempt + 1):
                        self._check_cancel()
        self._set(bytes_downloaded=completed)

    def _ensure_uv(self) -> Path:
        tools_dir = self._runtime_root().parent / "runtime-tools"
        tools_dir.mkdir(parents=True, exist_ok=True)
        uv_exe = tools_dir / "uv.exe"
        receipt = tools_dir / "uv.sha256"
        if uv_exe.is_file() and receipt.is_file():
            if hashlib.sha256(uv_exe.read_bytes()).hexdigest() == receipt.read_text().strip():
                return uv_exe
        self._set(state="installing", message="正在下载 Windows 环境管理组件")
        with tempfile.TemporaryFile() as archive:
            with urllib.request.urlopen(UV_WINDOWS_URL, timeout=20) as response:
                for chunk in iter(lambda: response.read(1024 * 1024), b""):
                    self._check_cancel()
                    archive.write(chunk)
            archive.seek(0)
            if hashlib.file_digest(archive, "sha256").hexdigest() != UV_WINDOWS_SHA256:
                raise RuntimeError("Windows 环境管理组件校验失败")
            archive.seek(0)
            with zipfile.ZipFile(archive) as package:
                names = [n for n in package.namelist() if Path(n).name == "uv.exe"]
                if len(names) != 1:
                    raise RuntimeError("Windows 环境管理组件包不完整")
                data = package.read(names[0])
        temp = uv_exe.with_suffix(".part")
        temp.write_bytes(data)
        temp.replace(uv_exe)
        receipt.write_text(hashlib.sha256(data).hexdigest())
        return uv_exe

    def _run_command(self, command: list[str], message: str) -> None:
        self._set(state="installing", message=message)
        # Package-manager output can contain proxy credentials: never expose it in UI/logs.
        with tempfile.TemporaryFile() as output:
            process = subprocess.Popen(command, stdout=output, stderr=output,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            try:
                while process.poll() is None:
                    if self._cancel.wait(0.2):
                        raise InterruptedError("组件安装已暂停")
                if process.returncode:
                    raise RuntimeError(f"{message}失败（退出代码 {process.returncode}），请检查网络后重试")
            finally:
                if process.poll() is None:
                    if os.name == "nt":
                        subprocess.run(["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            creationflags=subprocess.CREATE_NO_WINDOW, timeout=5, check=False)
                    else:
                        process.terminate()
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()

    def _install_runtime(self) -> None:
        # Explicit repair must really probe imports again, even if health cached
        # success earlier in this process (e.g. a subsequently damaged DLL).
        if self.kind == "windows":
            self._runtime_probe_cache = None
        if self._runtime_ready():
            return
        if self.kind == "mlx":
            raise RuntimeError("安装包中的 MLX 推理组件不完整，请重新安装最新版墨析")
        target = self._runtime_root()
        target.mkdir(parents=True, exist_ok=True)
        self._runtime_marker().unlink(missing_ok=True)
        common = [str(self._ensure_uv()), "pip", "install", "--target", str(target),
                  "--python", sys.executable, "--upgrade", "--reinstall", "--only-binary", ":all:"]
        self._run_command(common + ["--index-url", "https://download.pytorch.org/whl/cu128",
            "torch==2.10.0", "torchvision==0.25.0"], "正在安装 PyTorch 与 CUDA（首次较慢）")
        self._run_command(common + ["transformers==4.57.1", "Pillow==12.1.1", "einops==0.8.2",
            "addict==2.4.0", "easydict==1.13", "psutil==7.2.2", "requests==2.32.5",
            "tqdm==4.67.1", "numpy==2.4.6", "safetensors==0.7.0", "matplotlib==3.10.8"],
            "正在安装模型运行组件")
        self._set(state="installing", message="正在验证 Windows 推理组件")
        if not self._probe_windows_runtime():
            raise RuntimeError("Windows 推理组件导入或版本校验失败，请点击校验/修复重试")
        self._check_cancel()
        self._runtime_marker().write_text(json.dumps({
            "version": WINDOWS_RUNTIME_VERSION, "python": list(sys.version_info[:2]),
            "cuda": "12.8", "model": self.spec["id"],
        }), encoding="utf-8")
        self._runtime_probe_cache = None

    def _run(self) -> None:
        try:
            self._download_model()
            self._install_runtime()
            self._check_cancel()
            stats = file_stats(self.model_dir, self.spec)
            if stats is None:
                raise RuntimeError("模型文件发生变化，请重新校验")
            receipt = self.model_dir / RECEIPT
            temporary = receipt.with_suffix(".tmp")
            temporary.write_text(json.dumps({"revision": self.spec["revision"], "files": stats}), encoding="utf-8")
            temporary.replace(receipt)
            self._set(state="completed", message="模型下载与校验完成，可以开始识别", progress=100, error=None)
        except InterruptedError:
            self._set(state="cancelled", message="下载已暂停，下次会从断点继续", error=None)
        except Exception as exc:
            message = str(exc) if isinstance(exc, RuntimeError) else f"下载失败（{type(exc).__name__}），断点已保留，请重试"
            self._set(state="error", message=message, error=message)
