"""Optional Apple Silicon numerical gate; torch is validation-only, not bundled.

Reference operation matches official baidu/Unlimited-OCR-2 deepencoder.py
at 9cf077c4b206e0e2a31879df937b0b0bcba3661c, get_abs_pos/get_abs_pos_sam.
Linux/Windows CI skips this gate; a Mac deployment requires it to pass locally.
"""
from types import SimpleNamespace

import numpy as np
import pytest

mx = pytest.importorskip('mlx.core')
torch = pytest.importorskip('torch')
pytest.importorskip('mlx_vlm')

from backend.mlx2_vision import patch_model_vision, quick_gelu, sam_relative_positions
from mlx_vlm.models.deepseekocr.vision import VisionEmbeddings, VisionModel
from mlx_vlm.models.deepseekocr.config import VisionConfig
from mlx_vlm.models.deepseekocr.sam import get_abs_pos_sam


def assert_numerically_equal(actual, expected, dtype='float32'):
    actual = np.array(actual.astype(mx.float32))
    expected = expected.float().numpy()
    if dtype == 'bfloat16':
        # FP32 interpolation can straddle a BF16 rounding boundary. Permit at
        # most one BF16 ULP, not a broad relative-error/quality relaxation.
        def ordered_bf16(values):
            bits = (values.view(np.uint32) >> 16).astype(np.int32)
            return np.where(bits & 0x8000, 0x8000 - (bits & 0x7fff), 0x8000 + bits)
        assert np.all(np.abs(ordered_bf16(actual) - ordered_bf16(expected)) <= 1)
        assert np.count_nonzero(actual != expected) / expected.size < 0.01
    else:
        np.testing.assert_allclose(actual, expected, atol=1e-5, rtol=2e-5)


def test_bf16_gate_rejects_more_than_one_ulp_even_at_small_values():
    reference = torch.full((1000,), 0.0001, dtype=torch.bfloat16)
    # Exactly two adjacent BF16 values apart; only 0.1% of the sample differs.
    altered = reference.float().numpy().copy()
    bits = altered.view(np.uint32)
    bits[0] += 2 << 16
    with pytest.raises(AssertionError):
        assert_numerically_equal(mx.array(altered).astype(mx.bfloat16), reference, 'bfloat16')


@pytest.mark.parametrize('target', [10, 16, 20])
@pytest.mark.parametrize('dtype', ['float32', 'bfloat16'])
def test_clip_positions_match_official_torch_antialias(target, dtype):
    data = np.random.default_rng(41).standard_normal((1, 257, 32)).astype(np.float32)
    positions = mx.array(data).astype(getattr(mx, dtype))
    reference = torch.from_numpy(data).to(getattr(torch, dtype))
    embeddings = VisionEmbeddings(SimpleNamespace(hidden_size=32, patch_size=14, num_channels=3))
    unaffected = VisionEmbeddings(SimpleNamespace(hidden_size=32, patch_size=14, num_channels=3))
    import mlx.nn as nn
    patch_model_vision(SimpleNamespace(vision_model=SimpleNamespace(
        embeddings=embeddings, pre_layrnorm=nn.LayerNorm(32), transformer=SimpleNamespace(layers=[]))))
    assert unaffected._get_abs_pos.__func__ is VisionEmbeddings._get_abs_pos
    actual = embeddings._get_abs_pos(positions, target * target + 1)
    if target == 16:
        assert actual is positions
        expected = reference
    else:
        grid = reference[:, 1:].reshape(1, 16, 16, 32).permute(0, 3, 1, 2).float()
        resized = torch.nn.functional.interpolate(grid, size=(target, target), mode='bicubic',
                                                   antialias=True, align_corners=False).to(reference.dtype)
        expected = torch.cat((reference[:, :1], resized.permute(0, 2, 3, 1).reshape(1, target * target, 32)), dim=1)
    assert actual.dtype == getattr(mx, dtype)
    assert_numerically_equal(actual, expected, dtype)


@pytest.mark.parametrize('target', [40, 64])
def test_existing_sam_positions_match_official_torch(target):
    data = np.random.default_rng(42).standard_normal((1, 64, 64, 16)).astype(np.float32)
    actual = get_abs_pos_sam(mx.array(data), target)
    reference = torch.from_numpy(data).permute(0, 3, 1, 2)
    expected = torch.nn.functional.interpolate(reference, size=(target, target), mode='bicubic',
                                               antialias=True, align_corners=False).permute(0, 2, 3, 1)
    assert_numerically_equal(actual, expected)


@pytest.mark.parametrize('query,key', [(40, 40), (64, 64), (40, 64), (80, 80)])
def test_sam_relative_positions_match_official_half_pixel(query, key):
    data = np.random.default_rng(43).standard_normal((127, 32)).astype(np.float32)
    length = 2 * max(query, key) - 1
    reference = torch.from_numpy(data)
    if length != 127:
        reference = torch.nn.functional.interpolate(reference.T[None], size=length, mode='linear')[0].T
    q = torch.arange(query)[:, None] * max(key / query, 1.0)
    k = torch.arange(key)[None, :] * max(query / key, 1.0)
    indices = (q - k + (key - 1) * max(query / key, 1.0)).long()
    actual = sam_relative_positions(query, key, mx.array(data))
    assert_numerically_equal(actual, reference[indices])


def test_clip_activation_and_layernorm_match_official_without_changing_weights():
    from mlx_vlm.models.deepseekocr import sam
    config = VisionConfig(model_type='vision', hidden_size=32, intermediate_size=64,
                          num_attention_heads=4, layers=2, layer_norm_eps=1e-6)
    model = VisionModel(config)
    weight = model.transformer.layers[0].mlp.fc1.weight
    patch_model_vision(SimpleNamespace(vision_model=model))
    assert model.transformer.layers[0].mlp.fc1.weight is weight
    assert sam.get_rel_pos is sam_relative_positions
    data = np.random.default_rng(44).standard_normal((1, 17, 32)).astype(np.float32) * 0.01
    reference = torch.from_numpy(data)
    expected_activation = reference * torch.sigmoid(1.702 * reference)
    expected_norm = torch.nn.functional.layer_norm(reference, (32,), eps=1e-5)
    for layer in model.transformer.layers:
        assert layer.mlp.activation_fn is quick_gelu
        assert_numerically_equal(layer.mlp.activation_fn(mx.array(data)), expected_activation)
        for norm in (model.pre_layrnorm, layer.layer_norm1, layer.layer_norm2):
            assert norm.eps == 1e-5
            assert_numerically_equal(norm(mx.array(data)), expected_norm)
