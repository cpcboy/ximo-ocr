from __future__ import annotations

import contextlib
import gc
import importlib.util
import io
import logging
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import resolve_model_dir


logger = logging.getLogger("ocr-studio.engine")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class LegacyMLXEngine:
    """Loads the custom Unlimited-OCR MLX implementation once per process."""

    def __init__(self, model_dir: Path):
        self._model_dir = model_dir
        self._runner: Any | None = None
        self._lock = threading.RLock()
        self._state_lock = threading.Lock()
        self._state = "not_loaded"
        self._message = "模型尚未加载，将在首个 OCR 任务开始时自动加载"
        self._busy = False
        self._last_loaded_at: str | None = None
        self._last_log = ""
        self._last_scan_diagnostics: dict[str, Any] = {}

    @property
    def model_dir(self) -> Path:
        return resolve_model_dir(self._model_dir)

    @property
    def busy(self) -> bool:
        with self._state_lock:
            return self._busy

    def status(self) -> dict[str, Any]:
        weights = self.model_dir / "model.safetensors"
        size_bytes = weights.stat().st_size if weights.exists() else 0
        with self._state_lock:
            return {
                "path": str(self.model_dir),
                "exists": self.model_dir.exists(),
                "weights_found": weights.exists(),
                "size_bytes": size_bytes,
                "size_gb": round(size_bytes / 1024**3, 2) if size_bytes else 0,
                "loaded": self._runner is not None,
                "state": self._state,
                "message": self._message,
                "busy": self._busy,
                "last_loaded_at": self._last_loaded_at,
            }

    def _set_state(
        self,
        state: str,
        message: str,
        *,
        busy: bool | None = None,
    ) -> None:
        with self._state_lock:
            self._state = state
            self._message = message
            if busy is not None:
                self._busy = busy

    def last_scan_diagnostics(self) -> dict[str, Any]:
        with self._state_lock:
            return dict(self._last_scan_diagnostics)

    def _import_runtime(self) -> Any:
        # Keep first launch usable even when inference components are missing.
        from .model_compat import apply_runtime_compatibility

        init_file = self.model_dir / "__init__.py"
        if not init_file.exists():
            raise FileNotFoundError(f"找不到模型运行文件：{init_file}")

        import hashlib

        package_name = "unlimited_ocr_runtime_" + hashlib.sha256(
            str(self.model_dir.resolve()).encode()
        ).hexdigest()[:16]
        package = sys.modules.get(package_name)
        if package is None:
            spec = importlib.util.spec_from_file_location(
                package_name,
                init_file,
                submodule_search_locations=[str(self.model_dir)],
            )
            if spec is None or spec.loader is None:
                raise RuntimeError("无法载入 Unlimited-OCR 的 Python 运行模块")
            package = importlib.util.module_from_spec(spec)
            sys.modules[package_name] = package
            spec.loader.exec_module(package)
            apply_runtime_compatibility(package_name, package)
        return package

    def load(self) -> None:
        with self._lock:
            if self._runner is not None:
                self._set_state("ready", "模型已加载，可以开始识别", busy=False)
                return

            weights = self.model_dir / "model.safetensors"
            if not weights.exists():
                self._set_state(
                    "error",
                    "没有找到模型权重，请在设置中下载模型",
                    busy=False,
                )
                raise FileNotFoundError(f"找不到模型权重：{weights}")

            self._set_state(
                "loading",
                "正在把 6.7 GB 模型载入统一内存，通常需要一小会儿",
                busy=True,
            )
            capture = io.StringIO()
            try:
                with contextlib.redirect_stdout(capture):
                    package = self._import_runtime()
                    runner_cls = getattr(package, "UnlimitedOCRInference")
                    runner = runner_cls(str(self.model_dir))
                    runner.load()
                self._runner = runner
                self._last_loaded_at = utc_now()
                self._last_log = capture.getvalue()[-4000:]
                self._set_state("ready", "模型已加载，可以开始识别", busy=False)
            except Exception as exc:
                self._runner = None
                self._last_log = capture.getvalue()[-4000:]
                logger.exception("Unable to load Unlimited-OCR")
                self._set_state(
                    "error",
                    f"模型加载失败：{type(exc).__name__}: {exc}",
                    busy=False,
                )
                raise

    @staticmethod
    def _clean_result(text: str) -> str:
        cleaned = text.replace("\x00", "").strip()
        if "Assistant:" in cleaned:
            cleaned = cleaned.rsplit("Assistant:", 1)[-1].strip()
        return cleaned

    def scan(
        self,
        image_path: Path,
        *,
        prompt: str,
        mode: str,
        max_length: int,
    ) -> str:
        with self._lock:
            self.load()
            assert self._runner is not None
            self._set_state("running", f"正在识别 {image_path.name}", busy=True)
            with self._state_lock:
                self._last_scan_diagnostics = {}
            capture = io.StringIO()
            try:
                precise = mode != "fast"
                with contextlib.redirect_stdout(capture):
                    result = self._runner.infer_single(
                        image_path=str(image_path),
                        prompt=prompt or "document parsing.",
                        output_dir=None,
                        max_length=max(2048, min(int(max_length), 32768)),
                        temperature=0.0,
                        base_size=1024,
                        image_size=640 if precise else 1024,
                        crop_mode=precise,
                    )
                self._last_log = capture.getvalue()[-4000:]
                repetition = getattr(self._runner, "last_repetition", None)
                with self._state_lock:
                    self._last_scan_diagnostics = {
                        "repetition": repetition,
                    }
                self._set_state("ready", "模型已加载，可以继续识别", busy=False)
                return self._clean_result(str(result))
            except Exception as exc:
                self._last_log = capture.getvalue()[-4000:]
                logger.exception("OCR inference failed for %s", image_path)
                self._set_state(
                    "error",
                    f"本页识别失败：{type(exc).__name__}: {exc}",
                    busy=False,
                )
                raise

    def unload(self) -> None:
        if self.busy:
            raise RuntimeError("模型正在处理任务，暂时不能卸载")
        with self._lock:
            self._runner = None
            gc.collect()
            try:
                import mlx.core as mx

                clear_cache = getattr(mx, "clear_cache", None)
                if callable(clear_cache):
                    clear_cache()
            except Exception:
                logger.debug("MLX cache cleanup was unavailable", exc_info=True)
            gc.collect()
            self._set_state(
                "not_loaded",
                "模型已从内存卸载，将在下次任务时自动加载",
                busy=False,
            )


