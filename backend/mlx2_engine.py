"""Local, unquantized Unlimited-OCR-2. No network/model-supplied Python execution."""
from __future__ import annotations

import gc
import json
from pathlib import Path
from typing import Any

from .legacy_mlx_engine import LegacyMLXEngine, logger, utc_now
from .mlx2_runtime import MLX_VLM_REVISION, runtime_ready
from .mlx2_vision import patch_model_vision
from .model_catalog import model_spec, model_verified
from .ocr2_text import readable_ocr2_text
from .repetition import find_exact_token_loop, trim_repetitive_tail


class MLX2Engine(LegacyMLXEngine):
    """Keep the existing serial/lifecycle contract; one image per job page."""

    def status(self) -> dict[str, Any]:
        spec = model_spec("mlx")
        weights = [self.model_dir / item["path"] for item in spec["files"]
                   if item["path"].endswith(".safetensors")]
        found = all(path.is_file() and not path.is_symlink() for path in weights)
        size = sum(path.stat().st_size for path in weights if path.is_file())
        with self._state_lock:
            return {
                "path": str(self.model_dir), "exists": self.model_dir.exists(),
                "weights_found": found, "size_bytes": size, "size_gb": round(size / 1024**3, 2),
                "loaded": self._runner is not None, "state": self._state,
                "message": self._message, "busy": self._busy, "last_loaded_at": self._last_loaded_at,
                "platform": "mlx", "framework": "MLX / BF16（2.0 适配预览）",
                "model_id": spec["id"], "model_revision": spec["revision"],
                "adapter_revision": MLX_VLM_REVISION,
            }

    def load(self) -> None:
        with self._lock:
            if self._runner is not None:
                return
            self._set_state("loading", "正在加载 Unlimited-OCR 2.0 BF16（约 6.7 GB）", busy=True)
            try:
                if not model_verified(self.model_dir, model_spec("mlx")):
                    raise RuntimeError("2.0 模型未完成校验，请在设置中下载或校验；不会使用或覆盖 1.0 模型")
                if not runtime_ready():
                    raise RuntimeError("缺少已校验的 2.0 MLX 适配组件，请安装匹配版本的墨析")
                config = json.loads((self.model_dir / "config.json").read_text(encoding="utf-8"))
                if config.get("sparse_attention_config", {}).get("training_stage") != "dash" or config.get("quantization"):
                    raise RuntimeError("此入口只接受已固定版本的 Unlimited-OCR 2.0 BF16 模型")
                from mlx_vlm import load

                # Directory exists and receipt covers every shard/config. The
                # processor is bundled in mlx-vlm, not imported from HF files.
                self._runner = load(str(self.model_dir), strict=True, trust_remote_code=False)
                patch_model_vision(self._runner[0])
                self._last_loaded_at = utc_now()
                self._set_state("ready", "Unlimited-OCR 2.0 BF16 已加载", busy=False)
            except BaseException as exc:
                self._runner = None
                self._set_state("error", f"2.0 模型加载失败：{type(exc).__name__}: {exc}", busy=False)
                gc.collect()
                try:
                    import mlx.core as mx
                    mx.clear_cache()
                except Exception:
                    logger.debug("MLX cache cleanup unavailable after failed load", exc_info=True)
                logger.exception("Unable to load Unlimited-OCR 2")
                raise

    def scan(self, image_path: Path, *, prompt: str, mode: str, max_length: int) -> str:
        with self._lock:
            self.load()
            self._set_state("running", f"Unlimited-OCR 2.0 正在识别 {image_path.name}", busy=True)
            with self._state_lock:
                self._last_scan_diagnostics = {}
            stream = None
            try:
                from mlx_vlm import stream_generate
                from mlx_vlm.prompt_utils import apply_chat_template

                model, processor = self._runner
                task = (prompt or "").strip()
                if not task or task == "document parsing.":
                    task = "Multi page parsing."
                formatted = apply_chat_template(processor, model.config, task, num_images=1)
                limit = max(2048, min(int(max_length), 32768))
                stream = stream_generate(
                    model, processor, formatted, image=str(image_path),
                    max_tokens=limit, temperature=0.0, skip_special_tokens=False,
                    cropping=mode != "fast", base_size=1024,
                    image_size=640 if mode != "fast" else 1024,
                )
                pieces, tokens = [], []
                repetition = None
                finish_reason = None
                last = None
                for chunk in stream:
                    last = chunk
                    pieces.append(chunk.text)
                    finish_reason = getattr(chunk, "finish_reason", None)
                    # Final chunk repeats the last token; do not count it twice.
                    if chunk.token is not None and finish_reason is None:
                        tokens.append(int(chunk.token))
                    if len(tokens) >= 192 and len(tokens) % 32 == 0:
                        loop = find_exact_token_loop(tokens)
                        if loop:
                            repetition = {"detected": True, "generation_stop": loop}
                            finish_reason = "repetition"
                            break
                raw = "".join(pieces)
                result = trim_repetitive_tail(readable_ocr2_text(raw), preserve_numbers=True)
                if result.finding.detected:
                    repetition = {**(repetition or {}), "detected": True,
                                  "cleanup": result.finding.as_dict()}
                with self._state_lock:
                    self._last_scan_diagnostics = {
                        "model_id": model_spec("mlx")["id"], "adapter_revision": MLX_VLM_REVISION,
                        "repetition": repetition, "finish_reason": finish_reason,
                        "truncated": finish_reason == "length",
                        "partial_result": finish_reason in {"length", "repetition"} or result.finding.detected,
                        "stop_reason": finish_reason,
                        "raw_model_output": raw,
                        "generation_tokens": getattr(last, "generation_tokens", len(tokens)),
                        "peak_memory_gb": getattr(last, "peak_memory", None),
                    }
                if not result.text:
                    raise RuntimeError("2.0 未返回可用文字，请检查页面或重试")
                self._set_state("ready", "Unlimited-OCR 2.0 BF16 已加载", busy=False)
                return result.text
            except Exception as exc:
                self._set_state("error", f"本页识别失败：{type(exc).__name__}: {exc}", busy=False)
                logger.exception("Unlimited-OCR 2 inference failed")
                raise
            finally:
                try:
                    if stream is not None:
                        stream.close()
                finally:
                    # Also release lifecycle state for KeyboardInterrupt or
                    # GeneratorExit; the application can then unload safely.
                    if self.busy:
                        self._set_state("error", "本页识别已中断，请重试", busy=False)
