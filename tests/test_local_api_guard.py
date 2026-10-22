"""Browser-origin checks using a synthetic downloader; no model/data writes."""
from __future__ import annotations

import importlib
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def guarded_api(monkeypatch, tmp_path):
    config = importlib.import_module("backend.config")
    store_module = importlib.import_module("backend.store")
    monkeypatch.setattr(config, "DATA_ROOT", tmp_path)
    monkeypatch.setattr(config, "JOBS_ROOT", tmp_path / "jobs")
    monkeypatch.setattr(store_module, "JOBS_ROOT", tmp_path / "jobs")
    api = importlib.import_module("backend.app")
    calls = []
    monkeypatch.setattr(api, "engine", SimpleNamespace(busy=False, status=lambda: {"loaded": False}))
    monkeypatch.setattr(api, "model_loader_thread", None)
    monkeypatch.setattr(api, "model_download", SimpleNamespace(
        start=lambda: calls.append("start") or {"state": "checking"},
    ))
    # No lifespan/startup: never process a real or synthetic job queue.
    return TestClient(api.app, base_url="http://127.0.0.1:18765"), calls


@pytest.mark.parametrize("headers", [
    {"Origin": "https://example-attacker.invalid", "Content-Type": "text/plain"},
    {"Origin": "null"},
    {"Origin": "http://127.0.0.1:3000.example-attacker.invalid"},
    {"Origin": "http://127.0.0.1:4173"},
    {"Referer": "https://example-attacker.invalid/form"},
    {"Sec-Fetch-Site": "cross-site"},
    {"Host": "example-attacker.invalid:18765"},
])
def test_cross_site_cannot_start_download(guarded_api, headers):
    client, calls = guarded_api
    response = client.post("/api/model/download", headers=headers)
    assert response.status_code == 403
    assert calls == []


@pytest.mark.parametrize("headers", [
    {},  # Native shell / CLI
    {"Origin": "http://127.0.0.1:3000"},
    {"Origin": "http://localhost:3000", "Sec-Fetch-Site": "cross-site"},
    {"Referer": "http://127.0.0.1:3000/", "Sec-Fetch-Site": "same-site"},
])
def test_local_ui_and_native_calls_still_work(guarded_api, headers):
    client, calls = guarded_api
    response = client.post("/api/model/download", headers=headers)
    assert response.status_code == 202
    assert calls == ["start"]


def test_cors_preflight_is_not_broadened(guarded_api):
    client, calls = guarded_api
    response = client.options("/api/model/download", headers={
        "Origin": "http://127.0.0.1:3000", "Access-Control-Request-Method": "POST",
    })
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"
    assert calls == []
