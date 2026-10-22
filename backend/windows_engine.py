from __future__ import annotations

import contextlib
import gc
import io
import logging
import subprocess
import threading
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


logger = logging.getLogger("ocr-studio.windows-engine")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def detect_nvidia_gpu() -> dict[str, Any]:
    command = [
        "nvidia-smi",
        "--query-gpu=name,memory.total,driver_version",
        "--format=csv,noheader,nounits",
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        first_line = completed.stdout.strip().splitlines()[0]
        name, memory_mb, driver = [part.strip() for part in first_line.split(",", 2)]
        return {
            "compatible": completed.returncode == 0,
            "name": name,
            "memory_gb": round(int(memory_mb) / 1024, 1),
            "driver": driver,
            "message": f"{name} · {round(int(memory_mb) / 1024, 1)} GB 显存",
        }
    except Exception:
        return {
            "compatible": False,
            "name": None,
            "memory_gb": 0,
            "driver": None,
            "message": "未检测到 NVIDIA CUDA 显卡",
        }


class WindowsModelEngine:
    """Runs the official PyTorch Unlimited-OCR model on Windows and CUDA."""

    def __init__(self, model_dir: Path):
        self.model_dir = model_dir
        self._model: Any | None = None
        self._tokenizer: Any | None = None
        self._lock = threading.RLock()
        self._state_lock = threading.Lock()
        self._state = "not_loaded"
        self._message = "模型尚未下载，请在本机引擎中点击下载"
        self._busy = False
        self._last_loaded_at: str | None = None
        self._last_log = ""
        self._last_scan_diagnostics: dict[str, Any] = {}
        self._hardware = detect_nvidia_gpu()

    @property
    def busy(self) -> bool:
        with self._state_lock:
            return self._busy

    def _weights_path(self) -> Path:
        return self.model_dir / "model-00001-of-000001.safetensors"

    def status(self) -> dict[str, Any]:
        weights = self._weights_path()
        size_bytes = weights.stat().st_size if weights.exists() else 0
        with self._state_lock:
            message = self._message
            if not weights.exists() and self._state != "error":
                message = "模型尚未下载，请点击“下载 Windows 模型”"
            return {
                "path": str(self.model_dir),
                "exists": self.model_dir.exists(),
                "weights_found": weights.exists(),
                "size_bytes": size_bytes,
                "size_gb": round(size_bytes / 1024**3, 2) if size_bytes else 0,
                "loaded": self._model is not None,
                "state": self._state,
                "message": message,
                "busy": self._busy,
                "last_loaded_at": self._last_loaded_at,
                "platform": "windows",
                "framework": "PyTorch + CUDA",
                "hardware": dict(self._hardware),
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

    def load(self) -> None:
        with self._lock:
            if self._model is not None:
                self._set_state("ready", "模型已加载，可以开始识别", busy=False)
                return
            if not self._weights_path().exists():
                self._set_state("error", "请先下载 Windows 模型", busy=False)
                raise FileNotFoundError(f"找不到模型权重：{self._weights_path()}")

            self._set_state(
                "loading",
                "正在把模型载入 NVIDIA 显卡",
                busy=True,
            )
            capture = io.StringIO()
            try:
                with contextlib.redirect_stdout(capture):
                    import torch
                    from transformers import AutoModel, AutoTokenizer

                    if not torch.cuda.is_available():
                        raise RuntimeError(
                            "这个 Windows 版本需要 NVIDIA CUDA 显卡；"
                            "请安装最新版显卡驱动后重试"
                        )
                    tokenizer = AutoTokenizer.from_pretrained(
                        str(self.model_dir),
                        trust_remote_code=True,
                        local_files_only=True,
                    )
                    model = AutoModel.from_pretrained(
                        str(self.model_dir),
                        trust_remote_code=True,
                        use_safetensors=True,
                        torch_dtype=torch.bfloat16,
                        local_files_only=True,
                    )
                    model = model.eval().cuda()
                self._model = model
                self._tokenizer = tokenizer
                self._last_loaded_at = utc_now()
                self._last_log = capture.getvalue()[-4000:]
                self._hardware = {
                    **self._hardware,
                    "compatible": True,
                    "name": torch.cuda.get_device_name(0),
                }
                self._set_state("ready", "模型已加载，可以开始识别", busy=False)
            except Exception as exc:
                self._model = None
                self._tokenizer = None
                self._last_log = capture.getvalue()[-4000:]
                logger.exception("Unable to load Unlimited-OCR on Windows")
                self._set_state(
                    "error",
                    f"模型加载失败：{type(exc).__name__}: {exc}",
                    busy=False,
                )
                raise

    @staticmethod
    def _clean_result(text: str) -> str:
        cleaned = text.replace("\x00", "").strip()
        stop = "<｜end▁of▁sentence｜>"
        if cleaned.endswith(stop):
            cleaned = cleaned[: -len(stop)].strip()
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
            assert self._model is not None and self._tokenizer is not None
            self._set_state("running", f"正在识别 {image_path.name}", busy=True)
            capture = io.StringIO()
            try:
                precise = mode != "fast"
                model_prompt = prompt or "document parsing."
                if "<image>" not in model_prompt:
                    model_prompt = f"<image>{model_prompt}"
                with tempfile.TemporaryDirectory(prefix="moxi-ocr-") as output_dir:
                    with contextlib.redirect_stdout(capture):
                        result = self._model.infer(
                            self._tokenizer,
                            prompt=model_prompt,
                            image_file=str(image_path),
                            output_path=output_dir,
                            max_length=max(2048, min(int(max_length), 32768)),
                            temperature=0.0,
                            base_size=1024,
                            image_size=640 if precise else 1024,
                            crop_mode=precise,
                            eval_mode=True,
                            no_repeat_ngram_size=35,
                            ngram_window=128,
                            save_results=False,
                        )
                self._last_log = capture.getvalue()[-4000:]
                with self._state_lock:
                    self._last_scan_diagnostics = {
                        "repetition": None,
                        "platform": "windows",
                    }
                self._set_state("ready", "模型已加载，可以继续识别", busy=False)
                return self._clean_result(str(result))
            except Exception as exc:
                self._last_log = capture.getvalue()[-4000:]
                logger.exception("Windows OCR inference failed for %s", image_path)
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
            self._model = None
            self._tokenizer = None
            gc.collect()
            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.ipc_collect()
            except Exception:
                logger.debug("CUDA cache cleanup was unavailable", exc_info=True)
            gc.collect()
            self._set_state(
                "not_loaded",
                "模型已从显存卸载，将在下次任务时自动加载",
                busy=False,
            )
