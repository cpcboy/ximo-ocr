"""模型接口配置：预设、持久化、校验与密钥遮蔽。"""
from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from backend.model_registry import (
    KEEP_KEY_SENTINEL,
    LOCAL_ENGINE_ID,
    EndpointValidationError,
    ModelEndpointRegistry,
    normalize_base_url,
    public_endpoint,
)


def make_registry(tmp_path: Path) -> ModelEndpointRegistry:
    return ModelEndpointRegistry(tmp_path / "config" / "models.json")


def test_presets_are_available_without_writing_files(tmp_path):
    registry = make_registry(tmp_path)
    endpoints = registry.list()
    assert [endpoint["id"] for endpoint in endpoints] == [
        "preset-3090ti",
        "preset-4090",
    ]
    assert {endpoint["max_concurrency"] for endpoint in endpoints} == {1}
    assert all(endpoint["enabled"] for endpoint in endpoints)
    assert not (tmp_path / "config" / "models.json").exists()


def test_preset_ports_match_documented_bridges(tmp_path):
    registry = make_registry(tmp_path)
    ports = {
        endpoint["id"]: endpoint["base_url"] for endpoint in registry.list()
    }
    assert ports["preset-3090ti"] == "http://127.0.0.1:18081/v1"
    assert ports["preset-4090"] == "http://127.0.0.1:18091/v1"


def test_create_persists_private_file_and_masks_key(tmp_path):
    registry = make_registry(tmp_path)
    created = registry.create(
        {
            "name": "自定义 vLLM",
            "base_url": "http://10.0.0.9:8000/v1/",
            "model": "qwen-vl",
            "api_key": "sk-local-secret",
            "max_concurrency": 3,
        }
    )
    assert created["base_url"] == "http://10.0.0.9:8000/v1"
    assert created["max_concurrency"] == 3

    path = registry.path
    assert path.exists()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    raw = json.loads(path.read_text("utf-8"))
    assert raw["endpoints"][-1]["api_key"] == "sk-local-secret"

    public = public_endpoint(created)
    assert "api_key" not in public
    assert public["api_key_set"] is True
    assert "sk-local-secret" not in json.dumps(public)

    reloaded = ModelEndpointRegistry(path)
    assert reloaded.get(created["id"])["api_key"] == "sk-local-secret"


def test_update_without_key_keeps_existing_secret(tmp_path):
    registry = make_registry(tmp_path)
    created = registry.create(
        {
            "name": "接口 A",
            "base_url": "http://127.0.0.1:9000/v1",
            "model": "m1",
            "api_key": "sk-keep",
        }
    )
    updated = registry.update(created["id"], {"name": "接口 A2"})
    assert updated["name"] == "接口 A2"
    assert updated["api_key"] == "sk-keep"

    kept = registry.update(created["id"], {"api_key": KEEP_KEY_SENTINEL})
    assert kept["api_key"] == "sk-keep"

    cleared = registry.update(created["id"], {"api_key": ""})
    assert cleared["api_key"] == ""


def test_delete_removes_endpoint(tmp_path):
    registry = make_registry(tmp_path)
    registry.delete("preset-4090")
    assert [endpoint["id"] for endpoint in registry.list()] == ["preset-3090ti"]
    with pytest.raises(KeyError):
        registry.delete("preset-4090")


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"base_url": "ftp://127.0.0.1/v1"}, "http"),
        ({"base_url": "http:///v1"}, "主机名"),
        ({"base_url": "http://127.0.0.1:1/v1?x=1"}, "查询参数"),
        ({"name": ""}, "名称"),
        ({"model": ""}, "模型"),
        ({"max_concurrency": 0}, "并发数"),
        ({"max_concurrency": 10}, "并发数"),
        ({"timeout_seconds": 5}, "超时时间"),
    ],
)
def test_invalid_fields_are_rejected(tmp_path, payload, expected):
    registry = make_registry(tmp_path)
    base = {
        "name": "接口",
        "base_url": "http://127.0.0.1:18081/v1",
        "model": "m",
    }
    with pytest.raises(EndpointValidationError) as excinfo:
        registry.create({**base, **payload})
    assert expected in str(excinfo.value)


def test_duplicate_names_are_rejected(tmp_path):
    registry = make_registry(tmp_path)
    with pytest.raises(EndpointValidationError):
        registry.create(
            {
                "name": "3090 Ti · Qwen3.8 Flash",
                "base_url": "http://127.0.0.1:18082/v1",
                "model": "m",
            }
        )


def test_corrupt_file_does_not_crash(tmp_path):
    config = tmp_path / "config" / "models.json"
    config.parent.mkdir(parents=True)
    config.write_text("{not json", encoding="utf-8")
    registry = ModelEndpointRegistry(config)
    assert registry.list() == []
    # 原文件保持原样，等待用户重新添加而不是被静默覆盖。
    assert config.read_text("utf-8") == "{not json"


def test_normalize_base_url_trims_trailing_slash():
    assert (
        normalize_base_url(" https://example.test/v1/ ")
        == "https://example.test/v1"
    )


def test_local_engine_id_is_reserved_name():
    assert LOCAL_ENGINE_ID == "local"
