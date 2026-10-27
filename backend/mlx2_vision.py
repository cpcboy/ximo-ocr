"""Scoped CLIP position fix for the pinned preview adapter.

Official Unlimited-OCR-2 deepencoder.py uses float32 bicubic, antialias=True,
align_corners=False, then restores the weight dtype. MLX Upsample uses NHWC.
CLIP changes are instance-scoped. SAM's shared relative-position helper is
corrected in this MLX engine process only. No dependency file/weight is edited.
"""
from __future__ import annotations

from math import isqrt
from types import MethodType


def clip_abs_pos(_self, positions, target_tokens):
    import mlx.core as mx
    import mlx.nn as nn

    source = isqrt(positions.shape[1] - 1)
    target = isqrt(target_tokens)
    if source == target:
        return positions
    channels = positions.shape[-1]
    grid = positions[:, 1:].reshape(1, source, source, channels).astype(mx.float32)
    resized = nn.Upsample(
        scale_factor=(target / source, target / source), mode="cubic",
        align_corners=False, antialias=True,
    )(grid).astype(positions.dtype)
    return mx.concatenate((positions[:, :1], resized.reshape(1, target * target, channels)), axis=1)


def patch_model_vision(model):
    from mlx_vlm.models.deepseekocr import sam

    embeddings = model.vision_model.embeddings
    embeddings._get_abs_pos = MethodType(clip_abs_pos, embeddings)
    model.vision_model.pre_layrnorm.eps = 1e-5
    for layer in model.vision_model.transformer.layers:
        layer.mlp.activation_fn = quick_gelu
        layer.layer_norm1.eps = 1e-5
        layer.layer_norm2.eps = 1e-5
    sam.get_rel_pos = sam_relative_positions


def quick_gelu(value):
    import mlx.core as mx
    return value * mx.sigmoid(1.702 * value)


def sam_relative_positions(q_size, k_size, positions):
    """Official half-pixel linear interpolation, not the port's i * scale."""
    import mlx.core as mx

    length = 2 * max(q_size, k_size) - 1
    if positions.shape[0] != length:
        source = positions.astype(mx.float32)
        coordinates = (mx.arange(length, dtype=mx.float32) + 0.5) * (source.shape[0] / length) - 0.5
        coordinates = mx.clip(coordinates, 0, source.shape[0] - 1)
        lower = mx.floor(coordinates).astype(mx.int32)
        upper = mx.minimum(lower + 1, source.shape[0] - 1)
        weight = (coordinates - lower.astype(mx.float32))[:, None]
        positions = (source[lower] * (1 - weight) + source[upper] * weight).astype(positions.dtype)
    q = mx.arange(q_size, dtype=mx.float32)[:, None] * max(k_size / q_size, 1.0)
    k = mx.arange(k_size, dtype=mx.float32)[None, :] * max(q_size / k_size, 1.0)
    relative = q - k + (k_size - 1) * max(q_size / k_size, 1.0)
    return positions[relative.astype(mx.int32)]
