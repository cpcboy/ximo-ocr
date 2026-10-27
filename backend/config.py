from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if os.name == "nt":
    DEFAULT_DATA_ROOT = (
        Path(os.getenv("LOCALAPPDATA", str(Path.home())))
        / "MoxiOCRStudio"
        / "data"
    )
    DEFAULT_MODEL_DIR = (
        Path(os.getenv("LOCALAPPDATA", str(Path.home())))
        / "MoxiOCRStudio"
        / "models"
        / "Unlimited-OCR"
    )
else:
    DEFAULT_DATA_ROOT = PROJECT_ROOT / "data"
    DEFAULT_MODEL_DIR = Path(os.getenv(
        "OCR_STUDIO_SUPPORT_DIR",
        str(Path.home() / "Library/Application Support/墨析 OCR 工作台"),
    )) / "models" / "Unlimited-OCR-2-bf16"

DATA_ROOT = Path(
    os.getenv("OCR_STUDIO_DATA_DIR", str(DEFAULT_DATA_ROOT))
).expanduser()
JOBS_ROOT = DATA_ROOT / "jobs"
# 模型接口配置（含本机密钥）只保存在数据目录，权限 0600，不进入 Git。
MODEL_CONFIG_PATH = Path(
    os.getenv("OCR_STUDIO_MODEL_CONFIG", str(DATA_ROOT / "config" / "models.json"))
).expanduser()

MODEL_DIR = Path(
    os.getenv(
        "UNLIMITED_OCR_MODEL_DIR",
        str(DEFAULT_MODEL_DIR),
    )
).expanduser()


def resolve_model_dir(directory: Path) -> Path:
    """V2 has a separate directory; never mistake or overwrite v1/LM Studio files."""
    return directory

MAX_UPLOAD_BYTES = int(os.getenv("OCR_STUDIO_MAX_UPLOAD_BYTES", 1024**3))
MAX_PAGES = int(os.getenv("OCR_STUDIO_MAX_PAGES", "300"))

IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
    ".gif",
    ".heic",
    ".heif",
}
PDF_EXTENSIONS = {".pdf"}
OFFICE_EXTENSIONS = {
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".odt",
    ".ods",
    ".odp",
}
TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".csv",
    ".tsv",
    ".json",
    ".jsonl",
    ".xml",
    ".yaml",
    ".yml",
    ".html",
    ".htm",
    ".log",
    ".rtf",
    ".eml",
}
ARCHIVE_EXTENSIONS = {".zip"}
SUPPORTED_EXTENSIONS = (
    IMAGE_EXTENSIONS
    | PDF_EXTENSIONS
    | OFFICE_EXTENSIONS
    | TEXT_EXTENSIONS
    | ARCHIVE_EXTENSIONS
)


def ensure_data_dirs() -> None:
    JOBS_ROOT.mkdir(parents=True, exist_ok=True)
