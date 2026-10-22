from pathlib import Path

from windows import windows_launcher


def test_process_guard_only_accepts_bundled_executables(
    monkeypatch,
    tmp_path: Path,
) -> None:
    install_root = tmp_path / "MoxiOCRStudio"
    bundled_python = install_root / "runtime" / "python" / "python.exe"
    monkeypatch.setattr(
        windows_launcher,
        "_process_image_path",
        lambda _pid: bundled_python,
    )
    assert windows_launcher._belongs_to_install(1234, install_root)

    unrelated = tmp_path / "Unrelated" / "python.exe"
    monkeypatch.setattr(
        windows_launcher,
        "_process_image_path",
        lambda _pid: unrelated,
    )
    assert not windows_launcher._belongs_to_install(1234, install_root)


def test_installer_does_not_launch_hidden_powershell() -> None:
    root = Path(__file__).resolve().parents[1]
    scripts = "\n".join(
        (root / "windows" / name).read_text(encoding="utf-8")
        for name in ("installer.nsi", "launcher.nsi")
    )
    assert "WindowsPowerShell" not in scripts
    assert "ExecutionPolicy" not in scripts
    assert "CreateShortcut" in scripts
    assert "停止后台服务.lnk" in scripts  # Removed during an in-place upgrade.


def test_launcher_waits_for_browser_heartbeat(
    monkeypatch,
) -> None:
    states = iter([False, True, True, False, False])
    moments = iter([0.0, 0.0, 1.0, 2.0, 8.0])
    monkeypatch.setattr(
        windows_launcher,
        "_client_connected",
        lambda: next(states),
    )
    monkeypatch.setattr(
        windows_launcher.time,
        "monotonic",
        lambda: next(moments),
    )
    monkeypatch.setattr(
        windows_launcher.time,
        "sleep",
        lambda _seconds: None,
    )
    assert windows_launcher._wait_for_client_session()
