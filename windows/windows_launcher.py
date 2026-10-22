"""Native-looking Windows launcher for the bundled local OCR services.

This module intentionally uses only the Python standard library. In particular,
it avoids PowerShell-backed shortcuts, which are commonly flagged by heuristic
antivirus rules even when the target script is benign.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import json
import os
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path


CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
CREATE_NEW_PROCESS_GROUP = getattr(
    subprocess,
    "CREATE_NEW_PROCESS_GROUP",
    0x00000200,
)
ERROR_ALREADY_EXISTS = 183
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
APP_URL = "http://127.0.0.1:3000/"
READY_URL = "http://127.0.0.1:18765/api/readyz"
CLIENT_STATUS_URL = "http://127.0.0.1:18765/api/client/status"
UNLOAD_URL = "http://127.0.0.1:18765/api/model/unload"


def _message(text: str, *, error: bool = False) -> None:
    flags = 0x10 if error else 0x40
    ctypes.windll.user32.MessageBoxW(
        None,
        text,
        "墨析 OCR 工作台",
        flags,
    )


def _http_open(request: str | urllib.request.Request, timeout: int = 2):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    return opener.open(request, timeout=timeout)


def _wait_until_ready(url: str, attempts: int = 120) -> bool:
    for _ in range(attempts):
        try:
            with _http_open(url, timeout=2):
                return True
        except Exception:
            time.sleep(0.5)
    return False


def _client_connected() -> bool:
    try:
        with _http_open(CLIENT_STATUS_URL, timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return bool(payload.get("connected"))
    except Exception:
        return False


def _wait_for_client_session(
    *,
    connect_timeout_seconds: float = 60,
    disconnect_grace_seconds: float = 5,
    poll_seconds: float = 0.5,
) -> bool:
    deadline = time.monotonic() + connect_timeout_seconds
    while time.monotonic() < deadline:
        if _client_connected():
            break
        time.sleep(poll_seconds)
    else:
        return False

    disconnected_since: float | None = None
    while True:
        if _client_connected():
            disconnected_since = None
        elif disconnected_since is None:
            disconnected_since = time.monotonic()
        elif time.monotonic() - disconnected_since >= disconnect_grace_seconds:
            return True
        time.sleep(poll_seconds)


def _process_image_path(pid: int) -> Path | None:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [
        ctypes.wintypes.DWORD,
        ctypes.wintypes.BOOL,
        ctypes.wintypes.DWORD,
    ]
    kernel32.OpenProcess.restype = ctypes.wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [
        ctypes.wintypes.HANDLE,
        ctypes.wintypes.DWORD,
        ctypes.wintypes.LPWSTR,
        ctypes.POINTER(ctypes.wintypes.DWORD),
    ]
    kernel32.QueryFullProcessImageNameW.restype = ctypes.wintypes.BOOL
    kernel32.CloseHandle.argtypes = [ctypes.wintypes.HANDLE]
    kernel32.CloseHandle.restype = ctypes.wintypes.BOOL
    handle = kernel32.OpenProcess(
        PROCESS_QUERY_LIMITED_INFORMATION,
        False,
        pid,
    )
    if not handle:
        return None
    try:
        capacity = ctypes.wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(capacity.value)
        if not kernel32.QueryFullProcessImageNameW(
            handle,
            0,
            buffer,
            ctypes.byref(capacity),
        ):
            return None
        return Path(buffer.value)
    finally:
        kernel32.CloseHandle(handle)


def _belongs_to_install(pid: int, install_root: Path) -> bool:
    image_path = _process_image_path(pid)
    if image_path is None:
        return False
    executable = os.path.normcase(os.path.abspath(image_path))
    root = os.path.normcase(os.path.abspath(install_root))
    try:
        return os.path.commonpath([executable, root]) == root
    except ValueError:
        return False


def _stop_saved_process(pid_file: Path, install_root: Path) -> None:
    if not pid_file.exists():
        return
    try:
        pid = int(pid_file.read_text(encoding="utf-8").strip())
        if _belongs_to_install(pid, install_root):
            subprocess.run(
                ["taskkill.exe", "/PID", str(pid), "/T", "/F"],
                creationflags=CREATE_NO_WINDOW,
                check=False,
                capture_output=True,
            )
    except (OSError, ValueError):
        pass
    finally:
        pid_file.unlink(missing_ok=True)


def _stop_services(install_root: Path, state_root: Path) -> None:
    try:
        request = urllib.request.Request(UNLOAD_URL, method="POST")
        with _http_open(request, timeout=5):
            pass
    except Exception:
        pass
    _stop_saved_process(state_root / "frontend.pid", install_root)
    _stop_saved_process(state_root / "backend.pid", install_root)


def _find_edge() -> Path | None:
    candidates: list[Path] = []
    for env_name in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA"):
        base = os.environ.get(env_name)
        if base:
            candidates.append(
                Path(base) / "Microsoft" / "Edge" / "Application" / "msedge.exe"
            )
    return next((candidate for candidate in candidates if candidate.exists()), None)


def _start_process(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    stdout_path: Path,
    stderr_path: Path,
) -> subprocess.Popen[bytes]:
    with stdout_path.open("ab") as stdout, stderr_path.open("ab") as stderr:
        return subprocess.Popen(
            command,
            cwd=cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            creationflags=CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP,
            close_fds=True,
        )


def _acquire_mutex():
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = [
        ctypes.wintypes.LPVOID,
        ctypes.wintypes.BOOL,
        ctypes.wintypes.LPCWSTR,
    ]
    kernel32.CreateMutexW.restype = ctypes.wintypes.HANDLE
    kernel32.ReleaseMutex.argtypes = [ctypes.wintypes.HANDLE]
    kernel32.ReleaseMutex.restype = ctypes.wintypes.BOOL
    kernel32.CloseHandle.argtypes = [ctypes.wintypes.HANDLE]
    kernel32.CloseHandle.restype = ctypes.wintypes.BOOL
    handle = kernel32.CreateMutexW(
        None,
        True,
        "Local\\MoxiOCRStudioLauncher",
    )
    if not handle:
        raise OSError(ctypes.get_last_error(), "无法创建应用互斥锁")
    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(handle)
        return None
    return kernel32, handle


def _run_application() -> int:
    install_root = Path(__file__).resolve().parents[2]
    local_app_data = Path(os.environ["LOCALAPPDATA"])
    support_root = local_app_data / "MoxiOCRStudio"
    state_root = support_root / "runtime"
    log_root = support_root / "logs"
    data_root = support_root / "data"
    model_root = support_root / "models" / "Unlimited-OCR"
    ai_packages = support_root / "ai-packages"
    app_root = install_root / "app"
    python_root = install_root / "runtime" / "python"
    python_exe = python_root / "python.exe"
    backend_bootstrap = python_root / "backend_bootstrap.py"
    node_exe = install_root / "runtime" / "node" / "node.exe"
    frontend_root = app_root / "frontend"

    for directory in (
        support_root,
        state_root,
        log_root,
        data_root,
        model_root,
        ai_packages,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    mutex = _acquire_mutex()
    if mutex is None:
        return 0
    kernel32, mutex_handle = mutex

    try:
        _stop_services(install_root, state_root)
        required = (python_exe, backend_bootstrap, node_exe, frontend_root / "server.js")
        if not all(path.exists() for path in required):
            raise RuntimeError("程序运行文件不完整，请重新安装墨析 OCR 工作台。")

        env = dict(os.environ)
        env.update(
            {
                "OCR_STUDIO_DATA_DIR": str(data_root),
                "UNLIMITED_OCR_MODEL_DIR": str(model_root),
                "OCR_STUDIO_AI_PACKAGES_DIR": str(ai_packages),
                "OCR_STUDIO_UV_EXE": str(
                    support_root / "runtime-tools" / "uv.exe"
                ),
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONUTF8": "1",
                "OCR_STUDIO_BACKEND_HOST": "127.0.0.1",
                "OCR_STUDIO_BACKEND_PORT": "18765",
                "OCR_STUDIO_CLIENT_TIMEOUT_SECONDS": "90",
                "PORT": "3000",
                "HOST": "127.0.0.1",
            }
        )

        backend = _start_process(
            [str(python_exe), str(backend_bootstrap)],
            cwd=python_root,
            env=env,
            stdout_path=log_root / "backend.log",
            stderr_path=log_root / "backend-error.log",
        )
        (state_root / "backend.pid").write_text(
            str(backend.pid),
            encoding="utf-8",
        )
        if not _wait_until_ready(READY_URL):
            raise RuntimeError(
                "OCR 后端没有成功启动。请重新安装，或检查 "
                f"{log_root / 'backend-error.log'}。"
            )

        frontend = _start_process(
            [str(node_exe), "server.js"],
            cwd=frontend_root,
            env=env,
            stdout_path=log_root / "frontend.log",
            stderr_path=log_root / "frontend-error.log",
        )
        (state_root / "frontend.pid").write_text(
            str(frontend.pid),
            encoding="utf-8",
        )
        if not _wait_until_ready(APP_URL):
            raise RuntimeError(
                "OCR 界面没有成功启动。请重新安装，或检查 "
                f"{log_root / 'frontend-error.log'}。"
            )

        edge = _find_edge()
        if edge:
            profile = support_root / "edge-profile"
            subprocess.Popen(
                [
                    str(edge),
                    f"--app={APP_URL}",
                    f"--user-data-dir={profile}",
                    "--no-first-run",
                    "--disable-background-mode",
                    "--disable-features=msEdgeSidebarV2",
                ],
                creationflags=CREATE_NEW_PROCESS_GROUP,
                close_fds=True,
            )
        else:
            webbrowser.open(APP_URL)
        if not _wait_for_client_session():
            raise RuntimeError(
                "浏览器已经打开，但网页未能连接本机 OCR 服务。"
                "请重新启动应用；如果仍然失败，请查看日志目录。"
            )
        return 0
    except Exception as exc:
        _message(str(exc), error=True)
        return 1
    finally:
        _stop_services(install_root, state_root)
        kernel32.ReleaseMutex(mutex_handle)
        kernel32.CloseHandle(mutex_handle)


def main() -> int:
    if os.name != "nt":
        raise RuntimeError("Windows launcher can only run on Windows")
    install_root = Path(__file__).resolve().parents[2]
    support_root = Path(os.environ["LOCALAPPDATA"]) / "MoxiOCRStudio"
    if "--stop" in sys.argv[1:]:
        _stop_services(install_root, support_root / "runtime")
        return 0
    return _run_application()


if __name__ == "__main__":
    raise SystemExit(main())
