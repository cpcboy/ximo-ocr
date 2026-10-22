"""Pinned public model manifests. Never discover or execute floating remote code."""
from __future__ import annotations

import json
import platform
import sys
from pathlib import Path
from typing import Any

CATALOG_DIR = Path(__file__).with_name("models")
RECEIPT = ".moxi-model-complete.json"


def model_spec(kind: str) -> dict[str, Any]:
    if kind not in {"mlx", "windows"}:
        raise ValueError("Unsupported model platform")
    return json.loads((CATALOG_DIR / f"{kind}.json").read_text(encoding="utf-8"))


def current_platform() -> str | None:
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin" and platform.machine().lower() in {"arm64", "aarch64"}:
        version = platform.mac_ver()[0].split(".")[0]
        if version.isdigit() and int(version) >= 14:
            return "mlx"
    return None


def file_stats(directory: Path, spec: dict[str, Any]) -> dict[str, list[int]] | None:
    result = {}
    try:
        for item in spec["files"]:
            path = directory / item["path"]
            if path.is_symlink() or not path.is_file():
                return None
            stat = path.stat()
            if stat.st_size != item["size"]:
                return None
            result[item["path"]] = [stat.st_size, stat.st_mtime_ns]
    except OSError:
        return None
    return result


def model_verified(directory: Path, spec: dict[str, Any]) -> bool:
    """Cheap health probe; receipt is written only after full content verification."""
    try:
        receipt = json.loads((directory / RECEIPT).read_text(encoding="utf-8"))
        return (
            isinstance(receipt, dict)
            and receipt.get("revision") == spec["revision"]
            and receipt.get("files") == file_stats(directory, spec)
            and receipt.get("files") is not None
        )
    except (OSError, ValueError, TypeError):
        return False
