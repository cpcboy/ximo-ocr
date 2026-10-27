from __future__ import annotations

import importlib
import json
import sys
import types
import zipfile
from pathlib import Path
from typing import Any

import pytest
from fastapi import HTTPException


class _FakeEngine:
    def __init__(self, *_args: Any) -> None:
        self.busy = False

    def status(self) -> dict[str, Any]:
        return {"loaded": False}

    def unload(self) -> None:
        return None


class _FakeModelDownloadManager:
    def __init__(self, *_args: Any) -> None:
        pass

    def status(self) -> dict[str, Any]:
        return {}


def test_v2_export_preserves_original_layout_and_truncation(reader_app):
    job = reader_app.store.create(filename="v2.pdf", content_type="application/pdf", options={})
    raw = '<PAGE><BLOCK>text[0,0,100,100]<FORK>Recognized text'
    reader_app.store.update(job['id'], status='completed', pages=[{
        'index': 0, 'text': 'Recognized text', 'raw_model_output': raw,
        'model_id': 'mlx-community/Unlimited-OCR-2-bf16', 'truncated': True,
        'partial_result': True, 'stop_reason': 'length',
    }])
    reader_app._write_exports(job['id'])
    exported = json.loads((reader_app.store.job_dir(job['id']) / 'exports/v2.json').read_text())
    page = exported['pages'][0]
    assert page['text'] == 'Recognized text' and page['raw_model_output'] == raw
    assert page['model_id'] == 'mlx-community/Unlimited-OCR-2-bf16' and page['truncated'] is True
    assert page['partial_result'] and page['stop_reason'] == 'length'


@pytest.mark.parametrize('long_template', [False, True])
def test_v2_reader_and_export_keep_all_numbered_records(reader_app, long_template):
    text = '\n\n'.join(f'Entry {i:03d}: shipment ID MX-{2000+i}; units {i+3}.' for i in range(1, 121))
    if long_template:
        text = '\n'.join(f'Entry {i:03d}: This shipment contains the following items and must be delivered '
                         f'to the designated address before the scheduled collection time. Quantity {i+3}.'
                         for i in range(1, 121))
    job = reader_app.store.create(filename='unique-records.png', content_type='image/png', options={})
    reader_app.store.update(job['id'], status='completed', pages=[{
        'index': 0, 'text': text, 'model_id': 'mlx-community/Unlimited-OCR-2-bf16',
    }])
    reader_app.prepare_reader(job['id'])
    page = reader_app.store.get(job['id'])['pages'][0]
    assert page['text'] == text and page.get('reading_text', text) == text
    exported = json.loads((reader_app.store.job_dir(job['id']) / 'exports/unique-records.json').read_text())
    assert exported['pages'][0]['text'] == text


@pytest.fixture()
def reader_app(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Any:
    engine_module = types.ModuleType("backend.engine")
    engine_module.ModelEngine = _FakeEngine
    download_module = types.ModuleType("backend.model_download")
    download_module.ModelDownloadManager = _FakeModelDownloadManager
    documents_module = types.ModuleType("backend.documents")
    documents_module.DocumentPreparer = object
    documents_module.converter_status = lambda: {}
    monkeypatch.setitem(sys.modules, "backend.engine", engine_module)
    monkeypatch.setitem(sys.modules, "backend.model_download", download_module)
    monkeypatch.setitem(sys.modules, "backend.documents", documents_module)

    config_module = importlib.import_module("backend.config")
    store_module = importlib.import_module("backend.store")
    jobs_root = tmp_path / "data" / "jobs"
    monkeypatch.setattr(config_module, "DATA_ROOT", tmp_path / "data")
    monkeypatch.setattr(config_module, "JOBS_ROOT", jobs_root)
    monkeypatch.setattr(store_module, "JOBS_ROOT", jobs_root)

    app_module = importlib.import_module("backend.app")
    isolated_store = store_module.JobStore()
    monkeypatch.setattr(app_module, "store", isolated_store)
    return app_module


def test_reader_state_defaults_and_partial_merge(reader_app: Any) -> None:
    defaults = reader_app._validate_reader_state({}, page_count=4)
    assert defaults == {
        "last_page": 0,
        "bookmarks": [],
        "notes": {},
        "view_mode": "split",
        "theme": "system",
        "font_size": 16,
        "line_height": 1.7,
        "split_percent": 50,
        "spread": False,
        "show_raw": False,
        "zoom": 100,
        "rotation": 0,
        "sidebar_tab": "pages",
    }

    merged = reader_app._validate_reader_state(
        {
            "last_page": 3,
            "bookmarks": [3, 1],
            "notes": {"3": "结尾"},
            "theme": "sepia",
        },
        page_count=4,
        current={
            **defaults,
            "view_mode": "text",
            "font_size": 20,
        },
    )
    assert merged["last_page"] == 3
    assert merged["bookmarks"] == [1, 3]
    assert merged["notes"] == {"3": "结尾"}
    assert merged["theme"] == "sepia"
    assert merged["view_mode"] == "text"
    assert merged["font_size"] == 20


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"unknown": True}, "不支持的字段"),
        ({"last_page": 4}, "last_page"),
        ({"bookmarks": [1, 1]}, "不能包含重复页码"),
        ({"notes": []}, "notes 必须"),
        ({"notes": {"not-a-page": "内容"}}, "notes 的键"),
        ({"notes": {"1": 123}}, "notes 的内容"),
    ],
)
def test_reader_state_rejects_invalid_payloads(
    reader_app: Any,
    payload: dict[str, Any],
    message: str,
) -> None:
    with pytest.raises(HTTPException) as captured:
        reader_app._validate_reader_state(payload, page_count=4)
    assert captured.value.status_code == 422
    assert message in captured.value.detail


def test_prepare_reader_preserves_source_and_is_idempotent(
    reader_app: Any,
) -> None:
    repeated_sentence = (
        "Everyone enjoyed the movie even though the ending was sad and "
        "the class discussed the final scene together. "
    )
    original = (
        "A normal page contains useful material. " * 45
        + repeated_sentence * 14
    )
    clean = "This short page has no repetitive tail."
    job = reader_app.store.create(
        filename="reader-test.pdf",
        content_type="application/pdf",
        options={},
    )
    reader_app.store.update(
        job["id"],
        status="completed",
        pages=[
            {
                "index": 0,
                "label": "第 1 页",
                "source_name": "reader-test.pdf",
                "image_file": None,
                "status": "completed",
                "text": original,
                "error": None,
                "elapsed_seconds": 1.0,
            },
            {
                "index": 1,
                "label": "第 2 页",
                "source_name": "reader-test.pdf",
                "image_file": None,
                "status": "completed",
                "text": clean,
                "error": None,
                "elapsed_seconds": 1.0,
            },
        ],
        stats={
            "total_pages": 2,
            "completed_pages": 2,
            "failed_pages": 0,
            "elapsed_seconds": 2.0,
        },
    )

    first = reader_app.prepare_reader(job["id"])
    assert first["changed_pages"] == 1
    assert first["removed_chars"] > 0
    repaired_page, clean_page = first["job"]["pages"]
    assert repaired_page["text"] == original
    assert len(repaired_page["reading_text"]) < len(original)
    assert repaired_page["reading_repair"]["removed_chars"] > 0
    assert "reading_text" not in clean_page
    assert "reading_repair" not in clean_page

    second = reader_app.prepare_reader(job["id"])
    assert second["changed_pages"] == first["changed_pages"]
    assert second["removed_chars"] == first["removed_chars"]
    assert second["job"]["updated_at"] == first["job"]["updated_at"]
    assert second["job"]["pages"][0]["text"] == original
    assert (
        second["job"]["pages"][0]["reading_text"]
        == repaired_page["reading_text"]
    )

    export_path = (
        reader_app.store.job_dir(job["id"])
        / "exports"
        / "reader-test.json"
    )
    exported = json.loads(export_path.read_text(encoding="utf-8"))
    assert exported["pages"][0]["text"] == original.strip()
    assert exported["pages"][0]["reading_text"] == repaired_page["reading_text"]
    assert exported["pages"][0]["reading_repair"]["removed_chars"] > 0

    updated = reader_app.update_page(job["id"], 0, {"text": "人工校对后的结果"})
    assert updated["pages"][0]["text"] == "人工校对后的结果"
    assert "reading_text" not in updated["pages"][0]
    assert "reading_repair" not in updated["pages"][0]


def test_complete_package_is_a_valid_attachment(reader_app: Any) -> None:
    job = reader_app.store.create(
        filename="测试图片.jpg",
        content_type="image/jpeg",
        options={},
    )
    directory = reader_app.store.job_dir(job["id"])
    reader_app.store.source_path(job["id"]).write_bytes(b"original-image")
    pages = directory / "pages"
    pages.mkdir(exist_ok=True)
    (pages / "page-0001.png").write_bytes(b"preview-image")
    reader_app.store.update(
        job["id"],
        status="completed",
        pages=[
            {
                "index": 0,
                "label": "第 1 页",
                "source_name": "测试图片.jpg",
                "status": "completed",
                "text": "识别结果",
                "error": None,
            }
        ],
    )

    response = reader_app.download_package(job["id"])
    assert response.media_type == "application/zip"
    disposition = response.headers["content-disposition"]
    assert disposition.startswith("attachment; filename*=UTF-8''")
    assert disposition.endswith("-%E5%AE%8C%E6%95%B4%E7%BB%93%E6%9E%9C.zip")

    archive_path = Path(response.path)
    assert archive_path.is_file()
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == {
            "原始文件/测试图片.jpg",
            "识别结果/测试图片.txt",
            "识别结果/测试图片.md",
            "识别结果/测试图片.json",
            "页面预览/page-0001.png",
        }
