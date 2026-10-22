"""Benchmark hook cleanup is testable without Apple MLX or model weights."""
import pytest

from scripts.benchmark_mlx import RuntimeMethods


@pytest.mark.parametrize("failed", [False, True])
def test_runtime_methods_restore_on_success_and_failure(failed):
    class Model:
        def generate(self):
            return "original generation"

    generate = Model.generate
    methods = RuntimeMethods(Model)
    try:
        Model.generate = lambda self: "capture"
        if failed:
            raise RuntimeError("quality gate")
    except RuntimeError:
        pass
    finally:
        methods.restore()
    assert Model.generate is generate
    methods.restore()
    assert Model().generate() == "original generation"


def test_instrumentation_observes_only_first_completed_token():
    from scripts.benchmark_mlx import instrument_generate
    source = '''
def generate(self, values):
    result = []
    for step in range(len(values)):
        token_id = values[step]
        result.append(token_id)
    return result
'''
    calls = []
    generate = instrument_generate(source, {}, lambda: calls.append("first"))
    assert generate(None, [1, 8, 9]) == [1, 8, 9]
    assert calls == ["first"]
    calls.clear()
    assert generate(None, []) == []
    assert calls == []
