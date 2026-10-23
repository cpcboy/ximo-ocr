"""任务绑定识别引擎：校验、默认值与健康检查清单。"""
from __future__ import annotations

import importlib
from types import SimpleNamespace
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from backend.model_registry import ModelEndpointRegistry


@pytest.fixture()
def api_client(tmp_path, monkeypatch):
    config = importlib.import_module("backend.config")
    store_module = importlib.import_module("backend.store")
    monkeypatch.setattr(config, "DATA_ROOT", tmp_path)
    monkeypatch.setattr(config, "JOBS_ROOT", tmp_path / "jobs")
    monkeypatch.setattr(store_module, "JOBS_ROOT", tmp_path / "jobs")
    api = importlib.import_module("backend.app")
    monkeypatch.setattr(
        api,
        "registry",
        ModelEndpointRegistry(tmp_path / "config" / "models.json"),
    )
    monkeypatch.setattr(
        api,
        "model_download",
        SimpleNamespace(
            status=lambda: {
                "running": False,
                "model_ready": False,
                "runtime_ready": False,
            }
        ),
    )
    monkeypatch.setattr(api, "engine", SimpleNamespace(busy=False, status=lambda: {
        "loaded": False, "state": "not_loaded", "message": "未加载", "path": "x",
    }))
    # 不启动 lifespan：任务只入队，不会真的推理。
    return TestClient(api.app, base_url="http://127.0.0.1:18765")


def upload(client, *, engine: str | None = None, name: str = "合成.txt"):
    headers = {
        "Content-Type": "application/octet-stream",
        "X-File-Name": quote(name),
        "X-File-Type": "text/plain",
        "X-OCR-Options": "%7B%7D",
    }
    if engine is not None:
        headers["X-OCR-Engine"] = engine
    return client.post("/api/jobs", headers=headers, content=b"hello")


def test_remote_engine_job_binds_endpoint(api_client):
    response = upload(api_client, engine="preset-4090")
    assert response.status_code == 201, response.text
    job = response.json()
    assert job["engine_id"] == "preset-4090"
    assert job["engine_label"] == "4090 · Qwen3.8 Flash"
    assert job["status"] == "queued"


def test_unknown_engine_is_rejected(api_client):
    response = upload(api_client, engine="ep-does-not-exist")
    assert response.status_code == 422


def test_local_engine_requires_ready_model(api_client):
    response = upload(api_client, engine="local")
    assert response.status_code == 409
    assert "模型" in response.json()["detail"]


def test_local_engine_is_default(api_client):
    response = upload(api_client)
    assert response.status_code == 409  # 默认本地，模型未就绪
    assert "模型" in response.json()["detail"]


def test_engine_catalog_lists_local_and_remote(api_client):
    response = api_client.get("/api/models")
    assert response.status_code == 200
    payload = response.json()
    ids = [engine["id"] for engine in payload["engines"]]
    assert ids[0] == "local"
    assert "preset-3090ti" in ids and "preset-4090" in ids
    assert payload["max_parallel"] == 9
    remote = [e for e in payload["engines"] if e["kind"] == "remote"]
    assert all(e["max_concurrency"] == 1 for e in remote)
    assert all(e["api_key_set"] is False for e in remote)


def test_endpoint_crud_and_key_masking(api_client):
    created = api_client.post(
        "/api/models/endpoints",
        json={
            "name": "自建接口",
            "base_url": "http://127.0.0.1:9000/v1",
            "model": "m1",
            "api_key": "sk-secret-value",
            "max_concurrency": 3,
        },
    )
    assert created.status_code == 201, created.text
    endpoint = created.json()
    assert endpoint["api_key_set"] is True
    assert "sk-secret-value" not in created.text

    listed = api_client.get("/api/models/endpoints").json()["endpoints"]
    assert any(item["id"] == endpoint["id"] for item in listed)
    assert "sk-secret-value" not in api_client.get("/api/models/endpoints").text

    updated = api_client.put(
        f"/api/models/endpoints/{endpoint['id']}",
        json={"name": "自建接口 2"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "自建接口 2"
    assert updated.json()["api_key_set"] is True

    deleted = api_client.delete(f"/api/models/endpoints/{endpoint['id']}")
    assert deleted.status_code == 204
    assert all(
        item["id"] != endpoint["id"]
        for item in api_client.get("/api/models/endpoints").json()["endpoints"]
    )


def test_invalid_endpoint_payload_is_422(api_client):
    response = api_client.post(
        "/api/models/endpoints",
        json={"name": "坏地址", "base_url": "ftp://x/v1", "model": "m"},
    )
    assert response.status_code == 422


def test_discover_requires_valid_url(api_client):
    response = api_client.post(
        "/api/models/discover",
        json={"base_url": "not-a-url"},
    )
    assert response.status_code == 422
