"""Start the bundled backend with paths that stay writable after installation."""

from __future__ import annotations

import os
import sys
from pathlib import Path


INSTALL_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = INSTALL_ROOT / "app"
AI_PACKAGES = Path(
    os.environ.get(
        "OCR_STUDIO_AI_PACKAGES_DIR",
        Path(os.environ["LOCALAPPDATA"]) / "MoxiOCRStudio" / "ai-packages",
    )
)

for search_path in (APP_ROOT, AI_PACKAGES):
    resolved = str(search_path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "backend.app:app",
        host=os.environ.get("OCR_STUDIO_BACKEND_HOST", "127.0.0.1"),
        port=int(os.environ.get("OCR_STUDIO_BACKEND_PORT", "18765")),
    )
