from __future__ import annotations

import json
import math
import re
import sys
import time
from pathlib import Path
from types import ModuleType
from typing import Any

import mlx.core as mx
import mlx.nn as nn
import numpy as np
from PIL import Image, ImageOps

from .repetition import (
    analyze_repetitive_tail,
    find_exact_token_loop,
    trim_repetitive_tail,
)


CONV_WEIGHT_KEYS = {
    "sam_model.patch_embed.proj.weight",
    "sam_model.neck.0.weight",
    "sam_model.neck.2.weight",
    "sam_model.net_2.weight",
    "sam_model.net_3.weight",
    "vision_model.embeddings.patch_embedding.weight",
}


def _resize_spatial(
    value: mx.array,
    target_height: int,
    target_width: int,
) -> mx.array:
    if value.shape[1] == target_height and value.shape[2] == target_width:
        return value
    scale = (
        target_height / value.shape[1],
        target_width / value.shape[2],
    )
    resized = nn.Upsample(
        scale_factor=scale,
        mode="cubic",
        align_corners=False,
    )(value.astype(mx.float32))
    return resized.astype(value.dtype)


def _resize_rel_pos(value: mx.array, target_length: int) -> mx.array:
    if value.shape[0] == target_length:
        return value
    resized = nn.Upsample(
        scale_factor=target_length / value.shape[0],
        mode="linear",
        align_corners=False,
    )(value[None, :, :].astype(mx.float32))[0]
    if resized.shape[0] > target_length:
        resized = resized[:target_length]
    elif resized.shape[0] < target_length:
        resized = mx.pad(
            resized,
            [(0, target_length - resized.shape[0]), (0, 0)],
        )
    return resized.astype(value.dtype)


def _relative_attention_bias(
    q: mx.array,
    rel_pos_h: mx.array,
    rel_pos_w: mx.array,
    height: int,
    width: int,
) -> mx.array:
    """Port of SAM decomposed relative positional attention."""

    rel_h = _resize_rel_pos(rel_pos_h, 2 * height - 1)
    rel_w = _resize_rel_pos(rel_pos_w, 2 * width - 1)

    h_coords = (
        mx.arange(height, dtype=mx.int32)[:, None]
        - mx.arange(height, dtype=mx.int32)[None, :]
        + height
        - 1
    )
    w_coords = (
        mx.arange(width, dtype=mx.int32)[:, None]
        - mx.arange(width, dtype=mx.int32)[None, :]
        + width
        - 1
    )
    rh = rel_h[h_coords]
    rw = rel_w[w_coords]

    batch, heads, _, dim = q.shape
    q_spatial = q.reshape(batch, heads, height, width, dim)
    bias_h = mx.einsum("bhyxc,ykc->bhyxk", q_spatial, rh)
    bias_w = mx.einsum("bhyxc,xkc->bhyxk", q_spatial, rw)
    return (
        bias_h[..., :, None] + bias_w[..., None, :]
    ).reshape(batch, heads, height * width, height * width)


def _patch_model_module(model_module: ModuleType) -> None:
    def rms_norm_call(self: Any, value: mx.array) -> mx.array:
        return mx.fast.rms_norm(value, self.weight, self.eps)

    def rotary_call(
        self: Any,
        value: mx.array,
        position_ids: mx.array | None = None,
        seq_len: int | None = None,
    ) -> tuple[mx.array, mx.array]:
        self._ensure_freqs()
        cos, sin = self.cos_cached, self.sin_cached
        if position_ids is not None:
            cos = cos[position_ids]
            sin = sin[position_ids]
        elif seq_len is not None:
            cos = cos[:seq_len]
            sin = sin[:seq_len]
        return cos, sin

    def interpolate_sam_pos(
        position_embedding: mx.array,
        target_size: int,
    ) -> mx.array:
        return _resize_spatial(
            position_embedding,
            target_size,
            target_size,
        )

    def clip_embeddings_call(
        self: Any,
        pixel_values: mx.array,
        patch_embeds: mx.array | None = None,
    ) -> mx.array:
        batch_size = pixel_values.shape[0]
        if patch_embeds is None:
            patch_embeds = self.patch_embedding(pixel_values)
        batch, height, width, channels = patch_embeds.shape
        flattened = patch_embeds.reshape(batch, height * width, channels)
        class_tokens = mx.tile(
            self.class_embedding.reshape(1, 1, -1),
            (batch_size, 1, 1),
        )
        embeddings = mx.concatenate([class_tokens, flattened], axis=1)

        position_weights = self.position_embedding.weight
        class_position = position_weights[:1][None, :, :]
        source_grid = int(math.sqrt(position_weights.shape[0] - 1))
        patch_positions = position_weights[1:].reshape(
            1,
            source_grid,
            source_grid,
            channels,
        )
        patch_positions = _resize_spatial(patch_positions, height, width)
        patch_positions = patch_positions.reshape(1, height * width, channels)
        positions = mx.concatenate([class_position, patch_positions], axis=1)
        return embeddings + positions

    def sam_attention_call(self: Any, value: mx.array) -> mx.array:
        batch, token_count, channels = value.shape
        height = width = int(math.sqrt(token_count))
        if height * width != token_count:
            raise ValueError(
                f"SAM attention expected a square token grid, got {token_count}"
            )

        qkv = self.qkv(value).reshape(
            batch,
            token_count,
            3,
            self.num_heads,
            self.head_dim,
        )
        q = qkv[:, :, 0].transpose(0, 2, 1, 3)
        k = qkv[:, :, 1].transpose(0, 2, 1, 3)
        v = qkv[:, :, 2].transpose(0, 2, 1, 3)
        scores = (q @ k.transpose(0, 1, 3, 2)) * self.scale
        if self.use_rel_pos:
            scores = scores + _relative_attention_bias(
                q,
                self.rel_pos_h,
                self.rel_pos_w,
                height,
                width,
            )
        attention = mx.softmax(scores.astype(mx.float32), axis=-1).astype(q.dtype)
        output = attention @ v
        output = output.transpose(0, 2, 1, 3).reshape(
            batch,
            token_count,
            channels,
        )
        return self.proj(output)

    def sam_block_call(self: Any, value: mx.array) -> mx.array:
        shortcut = value
        normalized = self.norm1(value)
        batch, token_count, channels = normalized.shape
        height = width = int(math.sqrt(token_count))
        window_size = self.attn.window_size

        if window_size > 0:
            grid = normalized.reshape(batch, height, width, channels)
            pad_h = (window_size - height % window_size) % window_size
            pad_w = (window_size - width % window_size) % window_size
            if pad_h or pad_w:
                grid = mx.pad(
                    grid,
                    [(0, 0), (0, pad_h), (0, pad_w), (0, 0)],
                )
            padded_h, padded_w = height + pad_h, width + pad_w
            rows, columns = padded_h // window_size, padded_w // window_size
            windows = grid.reshape(
                batch,
                rows,
                window_size,
                columns,
                window_size,
                channels,
            )
            windows = windows.transpose(0, 1, 3, 2, 4, 5).reshape(
                batch * rows * columns,
                window_size * window_size,
                channels,
            )
            attended = self.attn(windows)
            attended = attended.reshape(
                batch,
                rows,
                columns,
                window_size,
                window_size,
                channels,
            )
            attended = attended.transpose(0, 1, 3, 2, 4, 5).reshape(
                batch,
                padded_h,
                padded_w,
                channels,
            )
            attended = attended[:, :height, :width, :].reshape(
                batch,
                token_count,
                channels,
            )
        else:
            attended = self.attn(normalized)

        value = shortcut + attended
        return value + self.mlp(self.norm2(value))

    def multimodal_call(
        self: Any,
        input_ids: mx.array | None = None,
        attention_mask: mx.array | None = None,
        position_ids: mx.array | None = None,
        past_key_values: Any | None = None,
        inputs_embeds: mx.array | None = None,
        images: Any | None = None,
        images_seq_mask: mx.array | None = None,
        images_spatial_crop: Any | None = None,
        use_cache: bool = False,
    ) -> Any:
        if inputs_embeds is None:
            inputs_embeds = self.language_model.embed_tokens(input_ids)

        if images is not None and images_seq_mask is not None:
            image_features = self.encode_images(images, images_spatial_crop)
            for batch_index, features in enumerate(image_features):
                if features is None or features.shape[0] == 0:
                    continue
                mask = np.asarray(images_seq_mask[batch_index], dtype=bool)
                positions = np.flatnonzero(mask)
                if len(positions) != features.shape[0]:
                    raise ValueError(
                        "Image token count does not match encoded features: "
                        f"{len(positions)} placeholders vs {features.shape[0]} features"
                    )
                position_ids_array = mx.array(positions, dtype=mx.int32)
                current_features = inputs_embeds[
                    batch_index,
                    position_ids_array,
                ]
                inputs_embeds = inputs_embeds.at[
                    batch_index,
                    position_ids_array,
                ].add(features - current_features)

        hidden_states, new_cache = self.language_model(
            input_ids=None,
            inputs_embeds=inputs_embeds,
            attention_mask=attention_mask,
            position_ids=position_ids,
            past_key_values=past_key_values,
            use_cache=use_cache,
        )
        logits = self.lm_head(hidden_states)
        return model_module.ModelOutput(
            logits=logits,
            past_key_values=new_cache,
        )

    def generate(
        self: Any,
        input_ids: mx.array,
        images: Any | None = None,
        images_seq_mask: mx.array | None = None,
        images_spatial_crop: Any | None = None,
        max_length: int = 32768,
        temperature: float = 0.0,
        eos_token_id: int = 1,
    ) -> mx.array:
        prompt_length = int(input_ids.shape[1])
        max_new_tokens = max(1, int(max_length) - prompt_length)
        chunks = [input_ids]
        cache = None
        current = input_ids
        output_history: list[int] = []
        ngram_size = 35
        ngram_window = 128
        self._ocr_stop_reason = None

        for step in range(max_new_tokens):
            if step == 0:
                output = self(
                    input_ids=current,
                    images=images,
                    images_seq_mask=images_seq_mask,
                    images_spatial_crop=images_spatial_crop,
                    use_cache=True,
                )
            else:
                output = self(
                    input_ids=current[:, -1:],
                    past_key_values=cache,
                    use_cache=True,
                )
            cache = output.past_key_values
            logits = output.logits[:, -1, :]

            if len(output_history) >= ngram_size - 1:
                prefix = tuple(output_history[-(ngram_size - 1) :])
                search_start = max(
                    0,
                    len(output_history) - ngram_window - ngram_size,
                )
                banned: set[int] = set()
                for index in range(
                    search_start,
                    len(output_history) - ngram_size + 1,
                ):
                    candidate = output_history[index : index + ngram_size]
                    if tuple(candidate[:-1]) == prefix:
                        banned.add(candidate[-1])
                if banned:
                    logits = logits.at[
                        0,
                        mx.array(sorted(banned), dtype=mx.int32),
                    ].add(float("-inf"))

            if temperature > 0:
                probabilities = mx.softmax(
                    (logits / temperature).astype(mx.float32),
                    axis=-1,
                )
                next_token = mx.random.categorical(
                    mx.log(probabilities),
                    axis=-1,
                ).reshape(1, 1)
            else:
                next_token = mx.argmax(logits, axis=-1, keepdims=True)

            token_id = int(next_token.item())
            chunks.append(next_token)
            output_history.append(token_id)
            current = next_token
            if token_id == eos_token_id:
                break

            if len(output_history) >= 128 and len(output_history) % 16 == 0:
                exact_loop = find_exact_token_loop(output_history)
                if exact_loop:
                    keep_tokens = exact_loop["start"] + exact_loop["period"]
                    output_history = output_history[:keep_tokens]
                    chunks = chunks[: keep_tokens + 1]
                    reason = {"kind": "exact_token_loop"}
                    reason.update(exact_loop)
                    self._ocr_stop_reason = reason
                    break

            tokenizer = getattr(self, "_ocr_tokenizer", None)
            if (
                tokenizer is not None
                and len(output_history) >= 256
                and len(output_history) % 32 == 0
            ):
                preview = tokenizer.decode(
                    output_history,
                    skip_special_tokens=False,
                )
                preview = _clean_generated_text(
                    preview,
                    tokenizer.decode(
                        [eos_token_id],
                        skip_special_tokens=False,
                    ),
                )
                finding = analyze_repetitive_tail(preview)
                if finding.detected:
                    reason = {"kind": "repetitive_text_tail"}
                    reason.update(finding.as_dict())
                    self._ocr_stop_reason = reason
                    break
        return mx.concatenate(chunks, axis=1)

    model_module.RMSNorm.__call__ = rms_norm_call
    model_module.RotaryEmbedding.__call__ = rotary_call
    model_module._interpolate_pos_embed = interpolate_sam_pos
    model_module.CLIPVisionEmbeddings.__call__ = clip_embeddings_call
    model_module.SAMAttention.__call__ = sam_attention_call
    model_module.SAMBlock.__call__ = sam_block_call
    model_module.UnlimitedOCRModel.__call__ = multimodal_call
    model_module.UnlimitedOCRModel.generate = generate


def _load_model_compatible(
    model_module: ModuleType,
    config_module: ModuleType,
    model_dir: str,
) -> Any:
    directory = Path(model_dir)
    with (directory / "config.json").open("r", encoding="utf-8") as handle:
        config_data = json.load(handle)
    config = config_module.UnlimitedOCRConfig.from_original_config(config_data)
    model = model_module.UnlimitedOCRModel(config)

    weights = mx.load(str(directory / "model.safetensors"))
    compatible: dict[str, mx.array] = {}
    for original_name, value in weights.items():
        name = original_name
        rel_position = re.fullmatch(
            r"sam_model\.blocks\.(\d+)\.attn\.(rel_pos_[hw])",
            original_name,
        )
        if rel_position:
            block_index = int(rel_position.group(1))
            attribute = rel_position.group(2)
            setattr(
                model.sam_model.blocks[block_index].attn,
                attribute,
                mx.zeros(value.shape, dtype=value.dtype),
            )
        if name.startswith("sam_model.neck."):
            suffix = name.removeprefix("sam_model.neck.")
            name = f"sam_model.neck.layers.{suffix}"
        if original_name in CONV_WEIGHT_KEYS:
            value = value.transpose(0, 2, 3, 1)
        compatible[name] = value

    # PyTorch keeps this deterministic position index as a non-persistent
    # buffer, while MLX exposes it as a loadable array.
    compatible["vision_model.embeddings.position_ids"] = (
        model.vision_model.embeddings.position_ids
    )

    model.load_weights(list(compatible.items()), strict=True)
    mx.eval(model.parameters())
    return model


def _dynamic_patches(
    image: Image.Image,
    image_processing_module: ModuleType,
    image_size: int,
) -> tuple[list[Image.Image], tuple[int, int]]:
    return image_processing_module.dynamic_preprocess(
        image,
        min_num=2,
        max_num=32,
        image_size=image_size,
        use_thumbnail=False,
    )


def _image_tensor(image: Image.Image) -> np.ndarray:
    array = np.asarray(image, dtype=np.float32) / 255.0
    array = (array - 0.5) / 0.5
    return array.transpose(2, 0, 1)


def _clean_generated_text(value: str, eos_text: str) -> str:
    cleaned = value.replace(eos_text, "").replace("\x00", "").strip()
    # Grounded output wraps recognized text in ref tags and coordinates in det
    # tags. Preserve the text while removing geometry metadata.
    cleaned = cleaned.replace("<|ref|>", "").replace("<|/ref|>", "")
    cleaned = re.sub(
        r"<\|det\|>.*?<\|/det\|>",
        "",
        cleaned,
        flags=re.DOTALL,
    )
    cleaned = cleaned.replace("<|det|>", "").replace("<|/det|>", "")
    cleaned = cleaned.replace("\\coloneqq", ":=").replace("\\eqqcolon", "=:")
    return cleaned.strip()


def _patch_inference_module(
    inference_module: ModuleType,
    model_module: ModuleType,
    config_module: ModuleType,
    image_processing_module: ModuleType,
) -> None:
    def compatible_loader(model_dir: str) -> Any:
        return _load_model_compatible(
            model_module,
            config_module,
            model_dir,
        )

    def compatible_tokenizer(model_dir: str) -> Any:
        from transformers import PreTrainedTokenizerFast

        # The bundled tokenizer config selects the Llama wrapper even though
        # tokenizer.json uses byte-level BPE. The generic fast backend preserves
        # its decoder, avoiding visible artifacts such as "Ġ" and "Ċ".
        return PreTrainedTokenizerFast(
            tokenizer_file=str(Path(model_dir) / "tokenizer.json"),
            bos_token="<｜begin▁of▁sentence｜>",
            eos_token="<｜end▁of▁sentence｜>",
            pad_token="<｜▁pad▁｜>",
            additional_special_tokens=["<|User|>", "<|Assistant|>"],
        )

    def infer_single(
        self: Any,
        image_path: str,
        prompt: str = "document parsing.",
        output_dir: str | None = None,
        max_length: int = 32768,
        temperature: float = 0.0,
        base_size: int = 1024,
        image_size: int = 640,
        crop_mode: bool = True,
    ) -> str:
        if self.model is None:
            self.load()

        source = image_processing_module.load_image(image_path)
        if source is None:
            raise ValueError(f"无法读取图片：{image_path}")
        source = source.convert("RGB")
        full_prompt = prompt.strip() or "document parsing."
        if "<image>" not in full_prompt:
            full_prompt = f"<image>{full_prompt}"
        before_image, after_image = full_prompt.split("<image>", 1)

        before_tokens = self.tokenizer.encode(
            before_image,
            add_special_tokens=False,
        )
        after_tokens = self.tokenizer.encode(
            after_image,
            add_special_tokens=False,
        )
        image_token_id = 128815
        patch_size = 16
        downsample_ratio = 4

        patches: list[Image.Image] = []
        crop_shape = (1, 1)
        if crop_mode and (
            source.width > image_size or source.height > image_size
        ):
            patches, crop_shape = _dynamic_patches(
                source,
                image_processing_module,
                image_size,
            )

        global_dimension = base_size if crop_mode else image_size
        global_view = ImageOps.pad(
            source,
            (global_dimension, global_dimension),
            method=Image.Resampling.BICUBIC,
            color=(128, 128, 128),
        )
        original_array = _image_tensor(global_view)[None, ...]

        if patches:
            patches_array = np.stack(
                [_image_tensor(patch) for patch in patches],
                axis=0,
            )
            local_grid = math.ceil(
                (image_size // patch_size) / downsample_ratio
            )
            width_crops, height_crops = crop_shape
            local_tokens = (
                local_grid * width_crops + 1
            ) * (local_grid * height_crops)
        else:
            patches_array = np.zeros(
                (0, 3, image_size, image_size),
                dtype=np.float32,
            )
            local_tokens = 0

        global_grid = math.ceil(
            (global_dimension // patch_size) / downsample_ratio
        )
        global_tokens = global_grid * (global_grid + 1) + 1
        image_token_count = global_tokens + local_tokens

        token_ids = (
            [self.tokenizer.bos_token_id]
            + before_tokens
            + [image_token_id] * image_token_count
            + after_tokens
        )
        mask = (
            [False] * (1 + len(before_tokens))
            + [True] * image_token_count
            + [False] * len(after_tokens)
        )
        input_ids = mx.array([token_ids], dtype=mx.int32)
        image_mask = mx.array([mask], dtype=mx.bool_)
        images = [
            [
                mx.array(patches_array),
                mx.array(original_array),
            ]
        ]

        self.last_repetition = None
        self.model._ocr_tokenizer = self.tokenizer
        started = time.monotonic()
        output_ids = self.model.generate(
            input_ids=input_ids,
            images=images,
            images_seq_mask=image_mask,
            images_spatial_crop=[crop_shape],
            max_length=max_length,
            temperature=temperature,
            eos_token_id=self.tokenizer.eos_token_id,
        )
        generated_ids = output_ids[0, len(token_ids) :].tolist()
        text = self.tokenizer.decode(
            generated_ids,
            skip_special_tokens=False,
        )
        eos_text = self.tokenizer.decode(
            [self.tokenizer.eos_token_id],
            skip_special_tokens=False,
        )
        result = _clean_generated_text(text, eos_text)
        trimmed = trim_repetitive_tail(result)
        stop_reason = getattr(self.model, "_ocr_stop_reason", None)
        if stop_reason or trimmed.finding.detected:
            self.last_repetition = {
                "detected": True,
                "generation_stop": stop_reason,
                "cleanup": trimmed.finding.as_dict(),
            }
        result = trimmed.text

        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            (output_path / "result.txt").write_text(result, encoding="utf-8")

        elapsed = time.monotonic() - started
        print(
            f"OCR complete: {len(generated_ids)} tokens in {elapsed:.1f}s"
        )
        if self.last_repetition:
            print("OCR repetition loop detected and trimmed")
        return result

    inference_module.load_model = compatible_loader
    inference_module.load_tokenizer = compatible_tokenizer
    inference_module.UnlimitedOCRInference.infer_single = infer_single


def apply_runtime_compatibility(
    package_name: str,
    package: ModuleType,
) -> None:
    """Repair the incomplete third-party MLX port without modifying model files."""

    model_module = sys.modules[f"{package_name}.model"]
    config_module = sys.modules[f"{package_name}.config"]
    inference_module = sys.modules[f"{package_name}.inference"]
    image_processing_module = sys.modules[f"{package_name}.image_processing"]

    _patch_model_module(model_module)
    _patch_inference_module(
        inference_module,
        model_module,
        config_module,
        image_processing_module,
    )
    package.UnlimitedOCRInference = inference_module.UnlimitedOCRInference
