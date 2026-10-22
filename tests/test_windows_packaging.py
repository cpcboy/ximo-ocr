"""Compile the real NSIS scripts with host-native, non-ASCII fixture paths."""

import os
from pathlib import Path
import shutil
import subprocess

import pytest


def _compiler() -> str:
    located = shutil.which("makensis")
    if located:
        return located
    if os.name == "nt":
        for variable in ("ProgramFiles(x86)", "ProgramFiles"):
            base = os.environ.get(variable)
            if base:
                candidate = Path(base) / "NSIS" / "makensis.exe"
                if candidate.is_file():
                    return str(candidate)
    pytest.skip("NSIS not installed; Windows CI repeats these tests after installation")


@pytest.mark.parametrize("script", ["launcher.nsi", "installer.nsi"])
def test_nsis_compiles_unicode_paths_and_product_name(tmp_path: Path, script: str) -> None:
    compiler = _compiler()
    root = Path(__file__).resolve().parents[1]
    stage = tmp_path / "待打包 files"
    nested = stage / "nested files"
    nested.mkdir(parents=True)
    (stage / "SOURCE_COMMIT").write_text("synthetic-fixture\n", encoding="ascii")
    (nested / "示例.txt").write_text("synthetic fixture\n", encoding="utf-8")
    output = tmp_path / "候选 installer.exe"
    prefix = "/" if os.name == "nt" else "-"
    result = subprocess.run(
        [
            compiler,
            f"{prefix}INPUTCHARSET", "UTF8",
            f"{prefix}DSTAGE_FILES={stage / '*'}",
            f"{prefix}DOUTPUT_FILE={output}",
            f"{prefix}DICON_FILE={root / 'windows' / 'AppIcon.ico'}",
            str(root / "windows" / script),
        ],
        capture_output=True,
        timeout=60,
    )
    assert result.returncode == 0, (result.stdout + result.stderr).decode("utf-8", "replace")
    data = output.read_bytes()
    assert data.startswith(b"MZ")
    # Version resource must preserve Chinese, not the host ACP's mojibake.
    assert "墨析 OCR 工作台".encode("utf-16le") in data
