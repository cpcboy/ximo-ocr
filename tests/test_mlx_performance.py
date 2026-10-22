"""Lossless scheduling contract; numeric inference is an opt-in benchmark."""
import ast
import hashlib
from pathlib import Path

import pytest


def test_generation_keeps_full_logits_and_quality_settings():
    source = Path(__file__).resolve().parents[1] / "backend/model_compat.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    generate = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "generate")
    call = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "multimodal_call")
    assert "last_logits_only" not in [arg.arg for arg in call.args.args]
    assert "logits = self.lm_head(hidden_states)" in source.read_text(encoding="utf-8")
    assert "single_token_moe" not in source.read_text(encoding="utf-8")
    engine = source.with_name("engine.py").read_text(encoding="utf-8")
    for setting in ("temperature=0.0", "base_size=1024", "image_size=640 if precise else 1024", "crop_mode=precise"):
        assert setting in engine
    loop = next(n for n in ast.walk(generate) if isinstance(n, ast.For) and isinstance(n.target, ast.Name) and n.target.id == "step")
    item_index = next(i for i, n in enumerate(loop.body) if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "token_id")
    cleanup = loop.body[item_index + 1]
    assert isinstance(cleanup, ast.Delete)
    assert [n.id for n in cleanup.targets] == ["output", "logits"]
    assert ast.unparse(loop.body[item_index + 2]) == "release_inference_cache()"
    calls = [n for n in ast.walk(generate) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "release_inference_cache"]
    assert len(calls) == 1

    # Removing only our scheduling lines must restore the complete baseline
    # generation algorithm, including repetition/length/sampling safeguards.
    # Baseline: ce8b0392f72a282071a6b451612ffe709924c51f, Python AST unparse.
    del loop.body[item_index + 1:item_index + 3]
    assert hashlib.sha256(ast.unparse(generate).encode()).hexdigest() == "d8b00ca3bfec4566c16a082eaea2f13191538bad56991a40839fa0250c2ca020"


@pytest.mark.parametrize("idle,expected", [(0, False), (1024**3 - 1, False), (1024**3, False), (1024**3 + 1, True)])
def test_release_only_clears_idle_cache(idle, expected):
    # Compile only this helper with a fake MLX so Windows CI exercises it.
    from types import SimpleNamespace
    path = Path(__file__).resolve().parents[1] / "backend/mlx_performance.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    helper = next(n for n in tree.body if isinstance(n, ast.FunctionDef))
    calls = []
    namespace = {"mx": SimpleNamespace(clear_cache=lambda: calls.append("clear"), get_cache_memory=lambda: idle), "IDLE_CACHE_BUDGET": 1024**3}
    exec(compile(ast.Module(body=[helper], type_ignores=[]), str(path), "exec"), namespace)
    assert namespace["release_inference_cache"]() is expected
    assert calls == (["clear"] if expected else [])
    # No persistent state: crossing the threshold again must trigger again.
    assert namespace["release_inference_cache"]() is expected
    assert calls == (["clear", "clear"] if expected else [])


@pytest.mark.parametrize("sequence,max_length", [([1], 10), ([17, 18, 1], 10), ([17, 18, 19], 4)])
def test_first_token_eos_and_length_limit_preserve_output(sequence, max_length):
    from types import SimpleNamespace
    from typing import Any
    from scripts.benchmark_mlx import instrument_generate

    class Array:
        def __init__(self, rows):
            self.rows = rows
            self.shape = (1, len(rows[0]))

        def __getitem__(self, index):
            return Array([self.rows[0][index[1]]])

        def item(self):
            return self.rows[0][0]

        def tolist(self):
            return self.rows

    class Logits:
        def __init__(self, token):
            self.token = token

        def __getitem__(self, index):
            return self

    def concatenate(chunks, axis):
        assert axis == 1
        return Array([[token for chunk in chunks for token in chunk.rows[0]]])

    source = (Path(__file__).resolve().parents[1] / "backend/model_compat.py").read_text(encoding="utf-8")
    clears = []
    namespace = {"Any": Any, "mx": SimpleNamespace(array=Array, argmax=lambda logits, **kw: Array([[logits.token]]), concatenate=concatenate),
                 "release_inference_cache": lambda: clears.append("check")}
    generate = instrument_generate(source, namespace, lambda: None)

    class Model:
        def __init__(self):
            self.calls = 0
            self.cache = object()

        def __call__(self, **kwargs):
            if self.calls:
                assert kwargs["past_key_values"] is self.cache
                assert kwargs["input_ids"].shape == (1, 1)
            logits = Logits(sequence[self.calls])
            self.calls += 1
            return SimpleNamespace(logits=logits, past_key_values=self.cache)

    model = Model()
    actual = generate(model, Array([[7]]), max_length=max_length, eos_token_id=1)
    assert actual.tolist() == [[7] + sequence]
    assert clears == ["check"] * len(sequence)
    assert model._ocr_stop_reason is None
