import json
import shutil
from pathlib import Path

import pytest

from scripts import deploy_macos as deploy


def test_manifest_detects_changed_app_files(tmp_path):
    app = tmp_path / "test.app"
    app.mkdir()
    file = app / "program"
    file.write_bytes(b"original")
    before = deploy.manifest(app)
    file.write_bytes(b"changed!")
    assert deploy.manifest(app) != before


def test_deploy_refuses_drift_before_any_mutation(tmp_path, monkeypatch):
    app = tmp_path / "installed.app"
    app.mkdir()
    (app / "code").write_text("current")
    monkeypatch.setattr(deploy, "INSTALLED", app)
    expected = tmp_path / "expected.json"
    expected.write_text("{}")
    backup = tmp_path / "backup"
    with pytest.raises(RuntimeError, match="漂移"):
        deploy.replace_app(tmp_path / "candidate.app", expected, backup, rollback=True)
    assert not backup.exists()
    assert (app / "code").read_text() == "current"


def test_atomic_replacement_retains_exact_previous_app(tmp_path, monkeypatch):
    app = tmp_path / "installed.app"
    candidate = tmp_path / "candidate.app"
    app.mkdir()
    candidate.mkdir()
    (app / "code").write_text("old")
    (candidate / "code").write_text("new")
    monkeypatch.setattr(deploy, "INSTALLED", app)
    expected = tmp_path / "expected.json"
    expected.write_text(json.dumps(deploy.manifest(app)))

    class OfflineSocket:
        def __enter__(self): return self
        def __exit__(self, *_args): pass
        def settimeout(self, _timeout): pass
        def connect_ex(self, _address): return 1

    monkeypatch.setattr(deploy.socket, "socket", OfflineSocket)

    def commands(command, **_kwargs):
        if command[0] == "ditto":
            shutil.copytree(command[1], command[2])
        else:
            assert command[0] == "codesign"

    monkeypatch.setattr(deploy.subprocess, "run", commands)
    backup = tmp_path / "backup"
    deploy.replace_app(candidate, expected, backup, rollback=True)
    assert (app / "code").read_text() == "new"
    assert (backup / "previous.app" / "code").read_text() == "old"
    assert (candidate / "code").read_text() == "new"
    audit = json.loads((backup / "deployment.json").read_text())
    assert audit["installed_manifest"] == deploy.manifest(app)
