"""远程视觉接口：请求构造、结果清洗、错误分类与重试。"""
from __future__ import annotations

import io
import json
import urllib.error

import pytest

from backend import remote_engine
from backend.remote_engine import (
    DEFAULT_OCR_PROMPT,
    STRUCTURED_OCR_PROMPT,
    RemoteEngine,
    RemoteEngineError,
    build_prompt,
    probe_models,
)


class FakeResponse:
    def __init__(self, payload: dict):
        self._raw = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._raw

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_: object) -> bool:
        return False


class FakeOpener:
    def __init__(self, results: list[object]):
        self.results = list(results)
        self.requests: list[object] = []

    def open(self, request, timeout=None):  # noqa: ANN001, ARG002
        self.requests.append(request)
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return FakeResponse(result)  # type: ignore[arg-type]


def make_endpoint(**overrides):
    endpoint = {
        "id": "ep-test",
        "name": "测试接口",
        "base_url": "http://127.0.0.1:18091/v1",
        "model": "qwen3.8-flash-next-iq3_s",
        "api_key": "sk-test",
        "max_concurrency": 1,
        "timeout_seconds": 60,
        "max_output_tokens": 4096,
    }
    endpoint.update(overrides)
    return endpoint


def patch_opener(monkeypatch, opener: FakeOpener):
    monkeypatch.setattr(remote_engine, "_opener", lambda url: opener)
    monkeypatch.setattr(remote_engine.time, "sleep", lambda _seconds: None)
    return opener


def completion(content: str, **extra):
    payload = {
        "choices": [
            {
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }
    payload.update(extra)
    return payload


def test_build_prompt_replaces_native_default():
    assert build_prompt(DEFAULT_OCR_PROMPT) == STRUCTURED_OCR_PROMPT
    assert build_prompt("document parsing") == STRUCTURED_OCR_PROMPT
    assert build_prompt("") == STRUCTURED_OCR_PROMPT
    assert build_prompt("只输出表格") == "只输出表格"


def test_scan_sends_multimodal_payload(tmp_path, monkeypatch):
    image = tmp_path / "page.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    opener = patch_opener(monkeypatch, FakeOpener([completion("识别结果")]))

    text, usage = RemoteEngine(make_endpoint()).scan(
        image,
        prompt=DEFAULT_OCR_PROMPT,
        max_length=8192,
    )

    assert text == "识别结果"
    assert usage["total_tokens"] == 15
    request = opener.requests[0]
    assert request.full_url == "http://127.0.0.1:18091/v1/chat/completions"
    assert request.get_header("Authorization") == "Bearer sk-test"
    body = json.loads(request.data.decode("utf-8"))
    assert body["model"] == "qwen3.8-flash-next-iq3_s"
    assert body["temperature"] == 0.0
    assert body["max_tokens"] == 4096  # 受接口 max_output_tokens 限制
    content = body["messages"][0]["content"]
    assert content[0]["text"] == STRUCTURED_OCR_PROMPT
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")


def test_max_length_is_capped_by_endpoint_budget(tmp_path, monkeypatch):
    image = tmp_path / "page.png"
    image.write_bytes(b"png")
    opener = patch_opener(monkeypatch, FakeOpener([completion("ok")]))
    RemoteEngine(make_endpoint(max_output_tokens=2048)).scan(
        image,
        prompt="x",
        max_length=16384,
    )
    body = json.loads(opener.requests[0].data.decode("utf-8"))
    assert body["max_tokens"] == 2048


def test_fenced_output_is_unwrapped(tmp_path, monkeypatch):
    image = tmp_path / "page.png"
    image.write_bytes(b"png")
    patch_opener(
        monkeypatch,
        FakeOpener([completion("```html\n<table><tr><td>a</td></tr></table>\n```")]),
    )
    text, _ = RemoteEngine(make_endpoint()).scan(image, prompt="x", max_length=4096)
    assert text == "<table><tr><td>a</td></tr></table>"


def test_list_content_parts_are_joined(tmp_path, monkeypatch):
    image = tmp_path / "page.png"
    image.write_bytes(b"png")
    payload = {
        "choices": [
            {
                "message": {
                    "content": [
                        {"type": "text", "text": "第一段"},
                        {"type": "text", "text": "第二段"},
                    ]
                }
            }
        ]
    }
    patch_opener(monkeypatch, FakeOpener([payload]))
    text, _ = RemoteEngine(make_endpoint()).scan(image, prompt="x", max_length=4096)
    assert text == "第一段第二段"


def test_empty_content_with_length_finish_explains_budget(tmp_path, monkeypatch):
    image = tmp_path / "page.png"
    image.write_bytes(b"png")
    payload = {
        "choices": [{"message": {"content": ""}, "finish_reason": "length"}]
    }
    patch_opener(monkeypatch, FakeOpener([payload]))
    with pytest.raises(RemoteEngineError) as excinfo:
        RemoteEngine(make_endpoint()).scan(image, prompt="x", max_length=4096)
    assert "输出长度" in str(excinfo.value)


def test_auth_error_is_not_retried(tmp_path, monkeypatch):
    image = tmp_path / "page.png"
    image.write_bytes(b"png")
    error = urllib.error.HTTPError(
        "http://127.0.0.1:18091/v1/chat/completions",
        401,
        "Unauthorized",
        {},
        io.BytesIO(json.dumps({"error": {"message": "Invalid API key."}}).encode()),
    )
    opener = patch_opener(monkeypatch, FakeOpener([error]))

    with pytest.raises(RemoteEngineError) as excinfo:
        RemoteEngine(make_endpoint()).scan(image, prompt="x", max_length=4096)

    assert "密钥" in str(excinfo.value)
    assert "Invalid API key." in str(excinfo.value)
    assert len(opener.requests) == 1


def test_server_error_is_retried_then_succeeds(tmp_path, monkeypatch):
    image = tmp_path / "page.png"
    image.write_bytes(b"png")
    error = urllib.error.HTTPError(
        "http://127.0.0.1:18091/v1/chat/completions",
        503,
        "Unavailable",
        {},
        io.BytesIO(b""),
    )
    opener = patch_opener(
        monkeypatch,
        FakeOpener([error, completion("重试成功")]),
    )
    text, _ = RemoteEngine(make_endpoint()).scan(image, prompt="x", max_length=4096)
    assert text == "重试成功"
    assert len(opener.requests) == 2


def test_list_models_uses_models_endpoint(monkeypatch):
    opener = patch_opener(
        monkeypatch,
        FakeOpener([{"data": [{"id": "a"}, {"id": "b"}]}]),
    )
    models = RemoteEngine(make_endpoint()).list_models()
    assert models == ["a", "b"]
    assert opener.requests[0].full_url.endswith("/v1/models")


def test_probe_models_uses_supplied_key(monkeypatch):
    opener = patch_opener(monkeypatch, FakeOpener([{"data": [{"id": "m"}]}]))
    assert probe_models("http://127.0.0.1:18081/v1", "sk-probe") == ["m"]
    assert opener.requests[0].get_header("Authorization") == "Bearer sk-probe"


def test_missing_choices_is_reported(tmp_path, monkeypatch):
    image = tmp_path / "page.png"
    image.write_bytes(b"png")
    patch_opener(monkeypatch, FakeOpener([{"choices": []}]))
    with pytest.raises(RemoteEngineError) as excinfo:
        RemoteEngine(make_endpoint()).scan(image, prompt="x", max_length=4096)
    assert "choices" in str(excinfo.value)
