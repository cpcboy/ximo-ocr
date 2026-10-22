from __future__ import annotations

import email
import html
import logging
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass, field
from email import policy
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable

import fitz
from PIL import Image, ImageOps, ImageSequence

from .config import (
    ARCHIVE_EXTENSIONS,
    IMAGE_EXTENSIONS,
    MAX_PAGES,
    OFFICE_EXTENSIONS,
    PDF_EXTENSIONS,
    SUPPORTED_EXTENSIONS,
    TEXT_EXTENSIONS,
)


logger = logging.getLogger("ocr-studio.documents")


@dataclass
class PreparedPage:
    index: int
    label: str
    source_name: str
    image_path: Path | None = None
    extracted_text: str | None = None


@dataclass
class PreparedDocument:
    pages: list[PreparedPage] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.parts.append(text)

    def text(self) -> str:
        return "\n".join(self.parts)


def _tool_candidates(name: str) -> Iterable[Path]:
    located = shutil.which(name)
    if located:
        yield Path(located)
    if name == "soffice":
        if os.name == "nt":
            for env_name in ("PROGRAMFILES", "PROGRAMFILES(X86)"):
                program_files = os.getenv(env_name)
                if program_files:
                    yield (
                        Path(program_files)
                        / "LibreOffice"
                        / "program"
                        / "soffice.exe"
                    )
        yield Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")
        yield Path("/opt/homebrew/bin/soffice")
        yield Path("/usr/local/bin/soffice")
        runtime_root = Path.home() / ".cache/codex-runtimes"
        if runtime_root.exists():
            yield from runtime_root.glob(
                "*/dependencies/bin/override/soffice"
            )


def find_tool(name: str) -> Path | None:
    for candidate in _tool_candidates(name):
        if candidate.exists() and os.access(candidate, os.X_OK):
            return candidate
    return None


def converter_status() -> dict[str, object]:
    soffice = find_tool("soffice")
    return {
        "pdf": True,
        "images": True,
        "office": bool(soffice),
        "office_tool": str(soffice) if soffice else None,
        "archives": True,
        "plain_text": True,
    }


def parse_page_range(value: str, total: int) -> list[int]:
    if total <= 0:
        return []
    value = (value or "").strip()
    if not value:
        return list(range(total))

    selected: set[int] = set()
    for raw_part in value.replace("，", ",").split(","):
        part = raw_part.strip()
        if not part:
            continue
        if "-" in part:
            left, right = part.split("-", 1)
            try:
                start = max(1, int(left.strip()))
                end = min(total, int(right.strip()))
            except ValueError as exc:
                raise ValueError(f"页码范围格式不正确：{part}") from exc
            if start > end:
                start, end = end, start
            selected.update(range(start - 1, end))
        else:
            try:
                page = int(part)
            except ValueError as exc:
                raise ValueError(f"页码格式不正确：{part}") from exc
            if 1 <= page <= total:
                selected.add(page - 1)
    if not selected:
        raise ValueError("指定的页码范围没有可处理页面")
    return sorted(selected)


class DocumentPreparer:
    def __init__(
        self,
        pages_dir: Path,
        *,
        dpi: int = 160,
        page_range: str = "",
        max_pages: int = MAX_PAGES,
    ):
        self.pages_dir = pages_dir
        self.pages_dir.mkdir(parents=True, exist_ok=True)
        self.dpi = max(96, min(int(dpi), 300))
        self.page_range = page_range
        self.max_pages = max(1, min(int(max_pages), MAX_PAGES))
        self.result = PreparedDocument()
        self._page_counter = 0

    def prepare(
        self,
        source: Path,
        *,
        display_name: str | None = None,
    ) -> PreparedDocument:
        self._prepare_path(
            source,
            display_name=display_name or source.name,
            depth=0,
        )
        if not self.result.pages:
            details = "；".join(self.result.warnings)
            raise ValueError(details or "文件中没有找到可以处理的内容")
        return self.result

    def _ensure_capacity(self) -> None:
        if len(self.result.pages) >= self.max_pages:
            raise ValueError(f"单个任务最多处理 {self.max_pages} 页")

    def _new_image_path(self) -> Path:
        self._page_counter += 1
        return self.pages_dir / f"page-{self._page_counter:04d}.png"

    def _add_page(
        self,
        *,
        label: str,
        source_name: str,
        image_path: Path | None = None,
        extracted_text: str | None = None,
    ) -> None:
        self._ensure_capacity()
        self.result.pages.append(
            PreparedPage(
                index=len(self.result.pages),
                label=label,
                source_name=source_name,
                image_path=image_path,
                extracted_text=extracted_text,
            )
        )

    def _prepare_path(self, source: Path, *, display_name: str, depth: int) -> None:
        suffix = source.suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            self.result.warnings.append(f"{display_name}：暂不支持 {suffix or '未知'} 格式")
            return
        if suffix in PDF_EXTENSIONS:
            self._render_pdf(source, display_name)
        elif suffix in IMAGE_EXTENSIONS:
            self._render_image(source, display_name)
        elif suffix in OFFICE_EXTENSIONS:
            self._render_office(source, display_name)
        elif suffix in TEXT_EXTENSIONS:
            self._read_text_document(source, display_name)
        elif suffix in ARCHIVE_EXTENSIONS:
            self._extract_archive(source, display_name, depth)

    def _render_pdf(self, source: Path, display_name: str) -> None:
        with fitz.open(source) as document:
            if document.needs_pass:
                raise ValueError(f"{display_name} 是加密 PDF，请先解除密码")
            selected = parse_page_range(self.page_range, document.page_count)
            zoom = self.dpi / 72.0
            matrix = fitz.Matrix(zoom, zoom)
            for page_index in selected:
                self._ensure_capacity()
                page = document.load_page(page_index)
                pixmap = page.get_pixmap(matrix=matrix, alpha=False)
                target = self._new_image_path()
                pixmap.save(target)
                self._add_page(
                    label=f"{display_name} · 第 {page_index + 1} 页",
                    source_name=display_name,
                    image_path=target,
                )

    def _render_image(self, source: Path, display_name: str) -> None:
        try:
            with Image.open(source) as image:
                frames = [
                    frame.copy()
                    for frame in ImageSequence.Iterator(image)
                ]
                selected = parse_page_range(self.page_range, len(frames))
                for frame_index in selected:
                    self._ensure_capacity()
                    frame = ImageOps.exif_transpose(frames[frame_index].copy())
                    if frame.mode not in {"RGB", "RGBA"}:
                        frame = frame.convert("RGB")
                    if frame.mode == "RGBA":
                        background = Image.new("RGB", frame.size, "white")
                        background.paste(frame, mask=frame.getchannel("A"))
                        frame = background
                    target = self._new_image_path()
                    frame.save(target, "PNG", optimize=True)
                    label = display_name
                    if len(frames) > 1:
                        label = f"{display_name} · 第 {frame_index + 1} 帧"
                    self._add_page(
                        label=label,
                        source_name=display_name,
                        image_path=target,
                    )
                return
        except Exception as pil_error:
            if source.suffix.lower() not in {".heic", ".heif"}:
                raise ValueError(f"无法读取图片 {display_name}：{pil_error}") from pil_error

        sips = find_tool("sips")
        if not sips:
            raise ValueError(f"无法读取 HEIC 图片 {display_name}")
        target = self._new_image_path()
        completed = subprocess.run(
            [str(sips), "-s", "format", "png", str(source), "--out", str(target)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if completed.returncode != 0 or not target.exists():
            raise ValueError(
                f"HEIC 转换失败：{completed.stderr.strip() or completed.stdout.strip()}"
            )
        self._add_page(
            label=display_name,
            source_name=display_name,
            image_path=target,
        )

    def _render_office(self, source: Path, display_name: str) -> None:
        soffice = find_tool("soffice")
        if not soffice:
            raise ValueError(
                "没有找到 LibreOffice，暂时无法转换 Word、Excel 或 PPT 文件"
            )
        with tempfile.TemporaryDirectory(prefix="ocr-office-") as temp_dir_raw:
            temp_dir = Path(temp_dir_raw)
            profile_dir = temp_dir / "profile"
            output_dir = temp_dir / "output"
            output_dir.mkdir()
            completed = subprocess.run(
                [
                    str(soffice),
                    f"-env:UserInstallation={profile_dir.resolve().as_uri()}",
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(output_dir),
                    str(source),
                ],
                capture_output=True,
                text=True,
                timeout=240,
            )
            pdfs = sorted(output_dir.glob("*.pdf"))
            if completed.returncode != 0 or not pdfs:
                message = completed.stderr.strip() or completed.stdout.strip()
                raise ValueError(f"{display_name} 转换失败：{message or '未生成 PDF'}")
            self._render_pdf(pdfs[0], display_name)

    @staticmethod
    def _decode_bytes(raw: bytes) -> str:
        for encoding in ("utf-8-sig", "utf-16", "gb18030", "big5", "latin-1"):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="replace")

    def _read_text_document(self, source: Path, display_name: str) -> None:
        suffix = source.suffix.lower()
        if suffix == ".rtf":
            textutil = find_tool("textutil")
            if not textutil:
                raise ValueError("没有找到 RTF 文本转换工具，无法读取这个文件")
            completed = subprocess.run(
                [str(textutil), "-convert", "txt", "-stdout", str(source)],
                capture_output=True,
                timeout=60,
            )
            if completed.returncode != 0:
                raise ValueError(f"无法读取 RTF 文件 {display_name}")
            text = self._decode_bytes(completed.stdout)
        elif suffix == ".eml":
            message = email.message_from_bytes(source.read_bytes(), policy=policy.default)
            parts: list[str] = []
            for key in ("subject", "from", "to", "date"):
                value = message.get(key)
                if value:
                    parts.append(f"{key.title()}: {value}")
            body = message.get_body(preferencelist=("plain", "html"))
            if body:
                content = body.get_content()
                if body.get_content_type() == "text/html":
                    parser = _HTMLTextExtractor()
                    parser.feed(content)
                    content = parser.text()
                parts.append(content)
            text = "\n\n".join(parts)
        else:
            text = self._decode_bytes(source.read_bytes())
            if suffix in {".html", ".htm"}:
                parser = _HTMLTextExtractor()
                parser.feed(text)
                text = html.unescape(parser.text())

        self._add_page(
            label=f"{display_name} · 直接读取",
            source_name=display_name,
            extracted_text=text.strip(),
        )

    def _extract_archive(self, source: Path, display_name: str, depth: int) -> None:
        if depth >= 2:
            self.result.warnings.append(f"{display_name}：压缩包嵌套层级过深，已跳过")
            return
        with tempfile.TemporaryDirectory(prefix="ocr-archive-") as temp_dir_raw:
            temp_dir = Path(temp_dir_raw)
            with zipfile.ZipFile(source) as archive:
                members = [item for item in archive.infolist() if not item.is_dir()]
                if len(members) > 200:
                    raise ValueError("压缩包文件数量超过 200 个，已停止处理")
                total_size = sum(item.file_size for item in members)
                if total_size > 1024**3:
                    raise ValueError("压缩包解压后超过 1 GB，已停止处理")
                for item in members:
                    member_path = Path(item.filename)
                    if (
                        member_path.is_absolute()
                        or ".." in member_path.parts
                        or item.file_size > 512 * 1024**2
                    ):
                        self.result.warnings.append(
                            f"{display_name}/{item.filename}：路径或大小不安全，已跳过"
                        )
                        continue
                    suffix = member_path.suffix.lower()
                    if suffix not in SUPPORTED_EXTENSIONS:
                        self.result.warnings.append(
                            f"{display_name}/{item.filename}：格式不支持，已跳过"
                        )
                        continue
                    safe_name = re.sub(r"[^0-9A-Za-z._-]+", "_", member_path.name)
                    target = temp_dir / f"{len(self.result.pages):04d}-{safe_name}"
                    with archive.open(item) as reader, target.open("wb") as writer:
                        shutil.copyfileobj(reader, writer)
                    self._prepare_path(
                        target,
                        display_name=f"{display_name}/{member_path.name}",
                        depth=depth + 1,
                    )
