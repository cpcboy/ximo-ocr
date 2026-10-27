"""Verify the exact reviewed v2 adapter without importing MLX in health probes."""
from __future__ import annotations

import hashlib
import importlib.metadata
import importlib.util
from functools import lru_cache
from pathlib import Path

MLX_VLM_REVISION = "c3ae82e2e79ee553c534c7b4efea73bc85122ab2"
RUNTIME_VERSIONS = {"mlx": "0.32.4", "mlx-metal": "0.32.4", "mlx-vlm": "0.7.11", "transformers": "5.14.0"}
ADAPTER_HASHES = {
    "dash.py": "aa26c89bac3e57be0247b8deb287a54b089548ee88f21c833cbf4f104cf43820",
    "language.py": "4cc0e87a1558d0e330dd5a03d8ad59e6277872157f52c89cd3d615a8916451d9",
    "processing_unlimitedocr.py": "3f6c8b78c7c269e410f79c89fdd384e6f90c8a8d8a0843f27b5e663de2c82222",
    "config.py": "39f0c26dc2268b9f6c297cd1b01de1f0ebf0e3bd216c3ed51cd24cb305729a5c",
    "unlimitedocr.py": "675fbfd54501fa7f2925869427e0562320cfdb5d08c5d61242a39acd9aaa39c8",
    "../deepseekocr/vision.py": "da7722cd6cd2b653ed3f485579766197cd8d6caab9abd36e4adb83dd80e1e535",
    "../deepseekocr/sam.py": "84325d5f831f6206e7a3249055c40b065a8e1293b410b8d94a91916d1f2ede97",
    "../deepseekocr/config.py": "ef40ebd5fab0b3c2e5a7bad0aebe3a719ec177e9d578215ed3c8ccefa0da2f34",
    "../kernels.py": "00929a3acc11d1930894a0cf7e784a6623c0e88d1c80039def97058a6bee74f0",
}


@lru_cache(maxsize=2)
def _hashes_match(fingerprint: tuple) -> bool:
    return all(hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected
               for path, _size, _mtime, expected in fingerprint)


def runtime_ready() -> bool:
    try:
        if any(importlib.metadata.version(name) != version for name, version in RUNTIME_VERSIONS.items()):
            return False
        spec = importlib.util.find_spec("mlx_vlm")
        if spec is None or not spec.origin:
            return False
        root = Path(spec.origin).parent / "models/unlimited_ocr"
        fingerprint = []
        for name, expected in ADAPTER_HASHES.items():
            path = root / name
            stat = path.stat()
            fingerprint.append((str(path), stat.st_size, stat.st_mtime_ns, expected))
        return _hashes_match(tuple(fingerprint))
    except (OSError, ValueError, ImportError, importlib.metadata.PackageNotFoundError):
        return False
