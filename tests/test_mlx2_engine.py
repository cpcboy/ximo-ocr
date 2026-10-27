from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.mlx2_engine import MLX2Engine
from backend.model_catalog import model_spec
from backend.ocr2_text import readable_ocr2_text


def test_v2_manifest_is_bf16_sharded_and_contains_no_remote_code():
    spec = model_spec("mlx")
    assert spec["version"] == 2 and spec["precision"] == "BF16"
    assert spec["id"] == "mlx-community/Unlimited-OCR-2-bf16"
    assert spec["revision"] == "850d1e483f5a82a0597f0a45aac31b07ba840df2"
    names = [item["path"] for item in spec["files"]]
    assert len([name for name in names if name.endswith(".safetensors")]) == 2
    assert "model.safetensors.index.json" in names
    assert not any(name.endswith(".py") for name in names)
    assert model_spec("windows")["id"] == "baidu/Unlimited-OCR"


def test_no_legacy_auto_fallback(tmp_path, monkeypatch):
    from backend.config import resolve_model_dir
    legacy = tmp_path / ".lmstudio/models/LoJexLLM/Unlimited-OCR-MLX"
    legacy.mkdir(parents=True)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    new = tmp_path / "models/Unlimited-OCR-2-bf16"
    assert resolve_model_dir(new) == new


def test_layout_conversion_keeps_all_text_and_table_html():
    table = '<table><tr><td>A &amp; B</td><td>120.00</td></tr></table>'
    raw = ('<PAGE><BLOCK>title<LEVEL1>[0,1,999,100]<FORK>合同 2026'
           '<BLOCK>text[10,20,900,60]<FORK>保留正文。'
           '<BLOCK>table[10,100,999,900]<FORK>' + table +
           '<BLOCK>footer[1,950,900,999]<FORK>第 1 页<｜end▁of▁sentence｜>')
    text = readable_ocr2_text(raw)
    assert all(part in text for part in ('合同 2026', '保留正文。', table, '第 1 页'))
    assert not any(token in text for token in ('<PAGE>', '<BLOCK>', '<FORK>', '<LEVEL1>'))


@pytest.mark.parametrize("label", ["cross_text", "append_text", "image_caption", "equation", "unknown_label"])
def test_block_bodies_are_never_dropped(label):
    raw = f'<BLOCK>{label}[-1, 1.5, 800, 900]<LEVEL2><FORK>x = 123'
    assert readable_ocr2_text(raw) == "x = 123"


def test_malformed_headers_do_not_silently_delete_text():
    raw = '<BLOCK>text[broken]<FORK>Important content'
    assert readable_ocr2_text(raw) == raw
    assert readable_ocr2_text('plain text <table><tr><td>1</td></tr></table>') == 'plain text <table><tr><td>1</td></tr></table>'
    assert readable_ocr2_text('<BLOCK>title<LEVEL0><FORK>Title') == 'Title'
    assert readable_ocr2_text('<BLOCK>text[0，1，2，3]<FORK>Body') == 'Body'


def test_unverified_model_is_refused_before_import(tmp_path):
    engine = MLX2Engine(tmp_path)
    with pytest.raises(RuntimeError, match="未完成校验"):
        engine.load()
    assert not engine.busy and not engine.status()["loaded"]


def test_status_requires_both_shards(tmp_path):
    engine = MLX2Engine(tmp_path)
    (tmp_path / "model-00001-of-00002.safetensors").write_bytes(b"one")
    assert not engine.status()["weights_found"]
    (tmp_path / "model-00002-of-00002.safetensors").write_bytes(b"two")
    assert engine.status()["weights_found"] and engine.status()["size_bytes"] == 6


@pytest.fixture
def fake_engine(tmp_path, monkeypatch):
    engine = MLX2Engine(tmp_path)
    engine._runner = (SimpleNamespace(config={}), object())
    monkeypatch.setattr(engine, "load", lambda: None)
    calls, closed = [], []
    state = {"chunks": [('<PAGE><BLOCK>text[0,0,100,100]<FORK>Hello 2.0', 12, None), ('', 1, 'stop')]}

    def stream(*args, **kwargs):
        calls.append((args, kwargs))
        try:
            for text, token, reason in state["chunks"]:
                if isinstance(text, BaseException):
                    raise text
                yield SimpleNamespace(text=text, token=token, finish_reason=reason,
                                      generation_tokens=2, peak_memory=7.0)
        finally:
            closed.append(True)

    monkeypatch.setitem(sys.modules, "mlx_vlm", SimpleNamespace(stream_generate=stream))
    monkeypatch.setitem(sys.modules, "mlx_vlm.prompt_utils", SimpleNamespace(
        apply_chat_template=lambda _processor, _config, task, num_images: "<image>" + task))
    return engine, state, calls, closed


def test_scan_keeps_quality_settings_and_raw_result(fake_engine, tmp_path):
    engine, state, calls, closed = fake_engine
    assert engine.scan(tmp_path / 'page.png', prompt='document parsing.', mode='precise', max_length=12000) == 'Hello 2.0'
    args, kwargs = calls[0]
    assert args[2] == '<image>Multi page parsing.'
    assert kwargs['temperature'] == 0.0 and kwargs['cropping'] is True
    assert kwargs['base_size'] == 1024 and kwargs['image_size'] == 640
    assert kwargs['max_tokens'] == 12000 and 'kv_bits' not in kwargs
    diag = engine.last_scan_diagnostics()
    assert diag['raw_model_output'] == state['chunks'][0][0]
    assert diag['finish_reason'] == 'stop' and not diag['truncated']
    assert closed == [True] and not engine.busy


def test_fast_mode_and_custom_prompt_remain_explicit(fake_engine, tmp_path):
    engine, state, calls, closed = fake_engine
    engine.scan(tmp_path / 'page.png', prompt='Read this page.', mode='fast', max_length=32768)
    assert calls[0][0][2] == '<image>Read this page.'
    assert calls[0][1]['cropping'] is False and calls[0][1]['image_size'] == 1024


def test_length_limit_keeps_partial_text_and_marks_truncation(fake_engine, tmp_path):
    engine, state, calls, closed = fake_engine
    state['chunks'][-1] = ('', 12, 'length')
    assert engine.scan(tmp_path / 'page.png', prompt='', mode='precise', max_length=2048) == 'Hello 2.0'
    assert engine.last_scan_diagnostics()['truncated'] is True


def test_scan_error_closes_stream_and_releases_busy_flag(fake_engine, tmp_path):
    engine, state, calls, closed = fake_engine
    state['chunks'] = [(RuntimeError('test error'), 0, None)]
    with pytest.raises(RuntimeError, match='test error'):
        engine.scan(tmp_path / 'page.png', prompt='', mode='precise', max_length=2048)
    assert closed == [True] and not engine.busy and engine.status()['state'] == 'error'


def test_generation_interrupt_can_unload(fake_engine, tmp_path):
    engine, state, calls, closed = fake_engine
    state['chunks'] = [(KeyboardInterrupt(), 0, None)]
    with pytest.raises(KeyboardInterrupt):
        engine.scan(tmp_path / 'page.png', prompt='', mode='precise', max_length=2048)
    assert closed == [True] and not engine.busy
    engine.unload()
    assert not engine.status()['loaded']


def test_first_load_interrupt_releases_busy_flag(tmp_path, monkeypatch):
    from backend import mlx2_engine
    (tmp_path / 'config.json').write_text('{"sparse_attention_config":{"training_stage":"dash"}}')
    monkeypatch.setattr(mlx2_engine, 'model_verified', lambda *_args: True)
    monkeypatch.setattr(mlx2_engine, 'runtime_ready', lambda: True)
    def interrupt(*_args, **_kwargs):
        raise KeyboardInterrupt()
    monkeypatch.setitem(sys.modules, 'mlx_vlm', SimpleNamespace(load=interrupt))
    engine = MLX2Engine(tmp_path)
    with pytest.raises(KeyboardInterrupt):
        engine.scan(tmp_path / 'page.png', prompt='', mode='precise', max_length=2048)
    assert not engine.busy
    engine.unload()
    assert not engine.status()['loaded']


def test_exact_loop_stops_with_diagnostic(fake_engine, tmp_path):
    engine, state, calls, closed = fake_engine
    state['chunks'] = [('word ', 42, None)] * 300
    engine.scan(tmp_path / 'page.png', prompt='', mode='precise', max_length=2048)
    assert engine.last_scan_diagnostics()['repetition']['detected']
    diag = engine.last_scan_diagnostics()
    assert 'generation_stop' in diag['repetition']
    assert diag['partial_result'] and diag['stop_reason'] == 'repetition'
    assert not diag['truncated']
    assert closed == [True]


@pytest.mark.parametrize('long_template', [False, True])
def test_v2_scan_keeps_120_distinct_numbered_entries(fake_engine, tmp_path, long_template):
    engine, state, calls, closed = fake_engine
    bodies = [f'Entry {i:03d}: shipment ID MX-{2000+i}; units {i+3}.' for i in range(1, 121)]
    if long_template:
        bodies = [f'Entry {i:03d}: This shipment contains the following items and must be delivered '
                  f'to the designated address before the scheduled collection time. Quantity {i+3}.'
                  for i in range(1, 121)]
    state['chunks'] = [('<PAGE>' + ''.join('<BLOCK>text[0,0,100,100]<FORK>' + body for body in bodies), 42, None), ('', 1, 'stop')]
    text = engine.scan(tmp_path / 'page.png', prompt='', mode='precise', max_length=16384)
    assert all(body in text for body in bodies)
    assert not engine.last_scan_diagnostics()['partial_result']


@pytest.mark.parametrize('legacy_config', [None, {"model_type": "unlimited-ocr"}])
def test_download_never_overwrites_v1_directory(tmp_path, legacy_config):
    from backend.model_download import ModelDownloadManager
    if legacy_config is None:
        old_file = tmp_path / 'model.safetensors'
        old_file.write_bytes(b'old model')
    else:
        old_file = tmp_path / 'config.json'
        old_file.write_text(json.dumps(legacy_config))
    before = old_file.read_bytes()
    manager = ModelDownloadManager(tmp_path, kind='mlx')
    with pytest.raises(RuntimeError, match='旧模型|其它模型'):
        manager._download_model()
    assert old_file.read_bytes() == before


def test_runtime_missing_or_wrong_version_is_not_ready(monkeypatch):
    from backend import mlx2_runtime
    monkeypatch.setattr(mlx2_runtime.importlib.metadata, 'version', lambda _name: '0.0.0')
    assert not mlx2_runtime.runtime_ready()


@pytest.mark.parametrize('identity', ['verified', 'missing-receipt', 'wrong-weights', 'v1'])
def test_corrupt_v2_config_repair_requires_pinned_weights(tmp_path, monkeypatch, identity):
    import hashlib
    from backend.model_catalog import RECEIPT, file_stats
    from backend.model_download import ModelDownloadManager

    payloads = {'config.json': b'{"sparse_attention_config":{"training_stage":"dash"}}',
                'one.safetensors': b'weight one', 'two.safetensors': b'weight two'}
    manager = ModelDownloadManager(tmp_path, kind='mlx')
    manager.spec = {"version": 2, "revision": "test-v2", "weights": "one.safetensors",
                    "files": [{"path": name, "size": len(data), "algorithm": "sha256",
                               "digest": hashlib.sha256(data).hexdigest()} for name, data in payloads.items()]}
    for name, data in payloads.items():
        (tmp_path / name).write_bytes(data)
    (tmp_path / RECEIPT).write_text(json.dumps({'revision': 'test-v2', 'files': file_stats(tmp_path, manager.spec)}))
    (tmp_path / 'config.json').write_bytes(b'{broken')
    if identity == 'missing-receipt':
        (tmp_path / RECEIPT).unlink()
    elif identity == 'wrong-weights':
        (tmp_path / 'one.safetensors').write_bytes(b'not our model')
    elif identity == 'v1':
        (tmp_path / 'config.json').write_text('{"model_type":"unlimited-ocr"}')
    calls = []

    def download(item, _completed):
        calls.append(item['path'])
        (tmp_path / item['path']).write_bytes(payloads[item['path']])
        return item['size']

    monkeypatch.setattr(manager, '_download_file', download)
    if identity == 'verified':
        def interrupt_download(_item, _completed):
            raise InterruptedError('test pause during repair')
        monkeypatch.setattr(manager, '_download_file', interrupt_download)
        with pytest.raises(InterruptedError):
            manager._download_model()
        assert (tmp_path / RECEIPT).exists()
        second = ModelDownloadManager(tmp_path, kind='mlx')
        second.spec = manager.spec
        monkeypatch.setattr(second, '_download_file', download)
        second._download_model()
        assert calls == ['config.json']
        # A paused identity check must propagate cancellation, not become a
        # misleading foreign-model rejection.
        (tmp_path / 'config.json').write_bytes(b'{broken')
        monkeypatch.setattr(second, '_valid_file', lambda *_args: (_ for _ in ()).throw(InterruptedError()))
        with pytest.raises(InterruptedError):
            second._has_v2_repair_identity()
    else:
        with pytest.raises(RuntimeError, match='其它模型'):
            manager._download_model()
        assert not calls
