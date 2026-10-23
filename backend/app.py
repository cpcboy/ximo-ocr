from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import shutil
import threading
import time
import urllib.parse
import zipfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response

from .config import (
    MAX_PAGES,
    MAX_UPLOAD_BYTES,
    MODEL_CONFIG_PATH,
    MODEL_DIR,
    SUPPORTED_EXTENSIONS,
    ensure_data_dirs,
)
from .dispatcher import JobDispatcher
from .documents import DocumentPreparer, converter_status
from .engine import ModelEngine
from .model_download import ModelDownloadManager
from .model_registry import (
    DEFAULT_ENDPOINT_CONCURRENCY,
    GLOBAL_MAX_PARALLEL,
    KEEP_KEY_SENTINEL,
    LOCAL_ENGINE_ID,
    LOCAL_ENGINE_LABEL,
    LOCAL_MAX_CONCURRENCY,
    EndpointValidationError,
    ModelEndpointRegistry,
    normalize_base_url,
    public_endpoint,
)
from .remote_engine import RemoteEngine, RemoteEngineError, probe_models
from .repetition import trim_repetitive_tail
from .store import JobStore, safe_filename, utc_now


logging.basicConfig(
    level=os.getenv("OCR_STUDIO_LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("ocr-studio")

ensure_data_dirs()
store = JobStore()
engine = ModelEngine(MODEL_DIR)
model_download = ModelDownloadManager(MODEL_DIR)
registry = ModelEndpointRegistry(MODEL_CONFIG_PATH)
model_operation_lock = threading.RLock()
dispatcher = JobDispatcher(
    resolve_engine=lambda job_id: _resolve_job_engine(job_id),
    slots_for=lambda engine_id: _engine_slots(engine_id),
    process=lambda job_id: _run_job(job_id),
    max_parallel=GLOBAL_MAX_PARALLEL,
    requeue_if=lambda job_id: _job_was_requeued(job_id),
)
model_loader_thread: threading.Thread | None = None
client_monitor_stop = threading.Event()
client_monitor_thread: threading.Thread | None = None
client_activity_lock = threading.Lock()
last_client_seen = 0.0

try:
    CLIENT_TIMEOUT_SECONDS = max(
        5,
        int(os.getenv("OCR_STUDIO_CLIENT_TIMEOUT_SECONDS", "12")),
    )
except ValueError:
    CLIENT_TIMEOUT_SECONDS = 12


def _mark_client_seen() -> None:
    global last_client_seen
    with client_activity_lock:
        last_client_seen = time.monotonic()


def _mark_client_disconnected() -> None:
    global last_client_seen
    with client_activity_lock:
        last_client_seen = 0.0


def _client_is_connected() -> bool:
    with client_activity_lock:
        seen = last_client_seen
    return bool(
        seen
        and time.monotonic() - seen <= CLIENT_TIMEOUT_SECONDS
    )


def _engine_slots(engine_id: str) -> int:
    if engine_id == LOCAL_ENGINE_ID:
        return LOCAL_MAX_CONCURRENCY
    endpoint = registry.get(engine_id)
    if endpoint is None:
        return 1
    return int(endpoint.get("max_concurrency") or DEFAULT_ENDPOINT_CONCURRENCY)


def _resolve_job_engine(job_id: str) -> str | None:
    """调度器取任务时确认它仍在排队；被取消或删除的任务直接丢弃。"""
    try:
        job = store.get(job_id)
    except KeyError:
        return None
    if job.get("status") != "queued":
        return None
    return str(job.get("engine_id") or LOCAL_ENGINE_ID)


def _job_was_requeued(job_id: str) -> bool:
    """任务收尾窗口里被“重试”回队列时，调度器需要重新接手。"""
    try:
        return store.get(job_id).get("status") == "queued"
    except KeyError:
        return False


def _local_jobs_active() -> bool:
    """只有本机 MLX 的任务才影响内存释放与模型下载，远程任务不应挡住它们。"""
    if dispatcher.running_by_engine().get(LOCAL_ENGINE_ID):
        return True
    return LOCAL_ENGINE_ID in dispatcher.pending_engines()


def _engine_catalog() -> list[dict[str, Any]]:
    running = dispatcher.running_by_engine()
    local_status = engine.status()
    catalog: list[dict[str, Any]] = [
        {
            "id": LOCAL_ENGINE_ID,
            "label": LOCAL_ENGINE_LABEL,
            "kind": "local",
            "enabled": True,
            "max_concurrency": LOCAL_MAX_CONCURRENCY,
            "running": running.get(LOCAL_ENGINE_ID, 0),
            "state": local_status.get("state"),
            "detail": local_status.get("message"),
            "model": local_status.get("path"),
            "platform": local_status.get("platform"),
            "api_key_set": True,
        }
    ]
    for endpoint in registry.list():
        enabled = bool(endpoint.get("enabled"))
        catalog.append(
            {
                "id": endpoint["id"],
                "label": endpoint["name"],
                "kind": "remote",
                "enabled": enabled,
                "max_concurrency": int(endpoint["max_concurrency"]),
                "running": running.get(endpoint["id"], 0),
                "state": "ready" if enabled else "disabled",
                "detail": f"{endpoint['model']} · {endpoint['base_url']}",
                "model": endpoint["model"],
                "base_url": endpoint["base_url"],
                "api_key_set": bool(endpoint.get("api_key")),
                "preset": bool(endpoint.get("preset")),
            }
        )
    return catalog


def _engine_label(engine_id: str) -> str:
    if engine_id == LOCAL_ENGINE_ID:
        return LOCAL_ENGINE_LABEL
    endpoint = registry.get(engine_id)
    return str(endpoint["name"]) if endpoint else engine_id


def _scan_page_image(
    engine_id: str,
    image_path: Path,
    options: dict[str, Any],
    should_cancel: Any = None,
) -> tuple[str, dict[str, Any], str]:
    """按任务绑定的引擎识别一页；返回文字、诊断和引擎标识。"""
    if engine_id == LOCAL_ENGINE_ID:
        download_status = model_download.status()
        if not download_status.get("model_ready") or not download_status.get("runtime_ready"):
            raise RuntimeError("请先在设置中完成模型下载与校验，再重试此任务")
        text = engine.scan(
            image_path,
            prompt=options["prompt"],
            mode=options["mode"],
            max_length=options["max_length"],
        )
        return text, engine.last_scan_diagnostics(), engine_id

    endpoint = registry.get(engine_id)
    if endpoint is None:
        raise RuntimeError("这个模型接口已被删除，请重新选择识别引擎后重试")
    if not endpoint.get("enabled"):
        raise RuntimeError("这个模型接口已停用，请启用后重试")
    text, usage = RemoteEngine(endpoint).scan(
        image_path,
        prompt=options["prompt"],
        max_length=options["max_length"],
        mode=options["mode"],
        should_cancel=should_cancel,
    )
    return text, {"usage": usage, "truncated": bool(usage.get("truncated"))}, engine_id


def _unload_model_if_idle(reason: str) -> bool:
    if engine.busy or _local_jobs_active():
        return False
    if not engine.status()["loaded"]:
        return False
    try:
        engine.unload()
    except RuntimeError:
        return False
    logger.info("Model automatically unloaded: %s", reason)
    return True


def _client_monitor_loop() -> None:
    while not client_monitor_stop.wait(2):
        if not _client_is_connected():
            _unload_model_if_idle("网页已关闭或连接已超时")


def _start_client_monitor() -> None:
    global client_monitor_thread
    if client_monitor_thread and client_monitor_thread.is_alive():
        return
    client_monitor_stop.clear()
    client_monitor_thread = threading.Thread(
        target=_client_monitor_loop,
        name="ocr-client-monitor",
        daemon=True,
    )
    client_monitor_thread.start()


def _default_options(raw: dict[str, Any] | None = None) -> dict[str, Any]:
    raw = raw or {}
    return {
        "mode": "fast" if raw.get("mode") == "fast" else "precision",
        "prompt": str(raw.get("prompt") or "document parsing.")[:1000],
        "page_range": str(raw.get("page_range") or "")[:200],
        "dpi": max(96, min(int(raw.get("dpi") or 160), 300)),
        "max_length": max(2048, min(int(raw.get("max_length") or 8192), 32768)),
        "language_hint": str(raw.get("language_hint") or "auto")[:40],
        "output_style": str(raw.get("output_style") or "structured")[:40],
    }


READER_VIEW_MODES = {"split", "scan", "text"}
READER_THEMES = {"light", "dark", "sepia", "system"}
READER_SIDEBAR_TABS = {"pages", "search", "bookmarks", "notes"}
READER_STATE_FIELDS = {
    "last_page",
    "bookmarks",
    "notes",
    "view_mode",
    "theme",
    "font_size",
    "line_height",
    "split_percent",
    "spread",
    "show_raw",
    "zoom",
    "rotation",
    "sidebar_tab",
}
READER_READY_STATUSES = {"completed", "partial", "failed", "canceled"}


def _reader_state_defaults() -> dict[str, Any]:
    return {
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


def _reader_page_index(
    value: Any,
    *,
    field: str,
    page_count: int,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise HTTPException(status_code=422, detail=f"{field} 必须是整数页码")
    maximum = max(page_count - 1, 0)
    if value < 0 or value > maximum:
        raise HTTPException(
            status_code=422,
            detail=f"{field} 必须在 0 到 {maximum} 之间",
        )
    return value


def _reader_number(
    value: Any,
    *,
    field: str,
    minimum: float,
    maximum: float,
) -> int | float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
    ):
        raise HTTPException(status_code=422, detail=f"{field} 必须是有效数字")
    if value < minimum or value > maximum:
        raise HTTPException(
            status_code=422,
            detail=f"{field} 必须在 {minimum:g} 到 {maximum:g} 之间",
        )
    return value


def _validate_reader_state(
    payload: dict[str, Any],
    *,
    page_count: int,
    current: dict[str, Any] | None = None,
) -> dict[str, Any]:
    unknown = sorted(set(payload) - READER_STATE_FIELDS)
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"阅读状态包含不支持的字段：{', '.join(unknown)}",
        )

    state = _reader_state_defaults()
    if current:
        state.update(
            {
                key: current[key]
                for key in READER_STATE_FIELDS
                if key in current
            }
        )
    state.update(payload)

    state["last_page"] = _reader_page_index(
        state["last_page"],
        field="last_page",
        page_count=page_count,
    )

    bookmarks = state["bookmarks"]
    if not isinstance(bookmarks, list):
        raise HTTPException(status_code=422, detail="bookmarks 必须是页码数组")
    normalized_bookmarks: list[int] = []
    seen_bookmarks: set[int] = set()
    for value in bookmarks:
        page = _reader_page_index(
            value,
            field="bookmarks",
            page_count=page_count,
        )
        if page in seen_bookmarks:
            raise HTTPException(status_code=422, detail="bookmarks 不能包含重复页码")
        seen_bookmarks.add(page)
        normalized_bookmarks.append(page)
    state["bookmarks"] = sorted(normalized_bookmarks)

    notes = state["notes"]
    if not isinstance(notes, dict):
        raise HTTPException(
            status_code=422,
            detail="notes 必须是以页码为键、文字为值的对象",
        )
    normalized_notes: dict[str, str] = {}
    for raw_page, raw_note in notes.items():
        if not isinstance(raw_page, str) or not raw_page.isdigit():
            raise HTTPException(status_code=422, detail="notes 的键必须是整数页码")
        page = _reader_page_index(
            int(raw_page),
            field="notes",
            page_count=page_count,
        )
        if not isinstance(raw_note, str):
            raise HTTPException(status_code=422, detail="notes 的内容必须是文字")
        if len(raw_note) > 20_000:
            raise HTTPException(
                status_code=422,
                detail=f"第 {page + 1} 页笔记超过 20000 字符上限",
            )
        if raw_note:
            normalized_notes[str(page)] = raw_note
    state["notes"] = normalized_notes

    view_mode = state["view_mode"]
    if not isinstance(view_mode, str) or view_mode not in READER_VIEW_MODES:
        raise HTTPException(
            status_code=422,
            detail="view_mode 只支持 split、scan 或 text",
        )

    theme = state["theme"]
    if not isinstance(theme, str) or theme not in READER_THEMES:
        raise HTTPException(
            status_code=422,
            detail="theme 只支持 light、dark、sepia 或 system",
        )

    state["font_size"] = _reader_number(
        state["font_size"],
        field="font_size",
        minimum=12,
        maximum=32,
    )
    state["line_height"] = _reader_number(
        state["line_height"],
        field="line_height",
        minimum=1.2,
        maximum=2.6,
    )
    state["split_percent"] = _reader_number(
        state["split_percent"],
        field="split_percent",
        minimum=25,
        maximum=75,
    )
    state["zoom"] = _reader_number(
        state["zoom"],
        field="zoom",
        minimum=50,
        maximum=300,
    )

    for field in ("spread", "show_raw"):
        if not isinstance(state[field], bool):
            raise HTTPException(status_code=422, detail=f"{field} 必须是布尔值")

    rotation = state["rotation"]
    if (
        isinstance(rotation, bool)
        or not isinstance(rotation, int)
        or rotation not in {0, 90, 180, 270}
    ):
        raise HTTPException(
            status_code=422,
            detail="rotation 只支持 0、90、180 或 270",
        )

    sidebar_tab = state["sidebar_tab"]
    if (
        not isinstance(sidebar_tab, str)
        or sidebar_tab not in READER_SIDEBAR_TABS
    ):
        raise HTTPException(
            status_code=422,
            detail="sidebar_tab 只支持 pages、search、bookmarks 或 notes",
        )
    return state


def _job_or_404(job_id: str) -> dict[str, Any]:
    try:
        return store.get(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="没有找到这个任务") from exc


def _write_exports(job_id: str) -> None:
    job = store.get(job_id)
    directory = store.job_dir(job_id)
    exports = directory / "exports"
    exports.mkdir(exist_ok=True)
    stem = Path(safe_filename(job["filename"])).stem or "OCR结果"

    text_sections: list[str] = []
    markdown_sections: list[str] = []
    json_pages: list[dict[str, Any]] = []
    for page in job.get("pages", []):
        text = str(page.get("text") or "").strip()
        label = str(page.get("label") or f"第 {page.get('index', 0) + 1} 页")
        text_sections.append(f"===== {label} =====\n{text}")
        markdown_sections.append(f"## {label}\n\n{text}")
        json_pages.append(
            {
                "index": page.get("index"),
                "label": label,
                "source_name": page.get("source_name"),
                "status": page.get("status"),
                "text": text,
                "reading_text": page.get("reading_text"),
                "reading_repair": page.get("reading_repair"),
                "error": page.get("error"),
                "repetition_trimmed": page.get("repetition_trimmed", False),
                "repetition_diagnostics": page.get("repetition_diagnostics"),
            }
        )

    (exports / f"{stem}.txt").write_text(
        "\n\n".join(text_sections).strip() + "\n",
        encoding="utf-8",
    )
    (exports / f"{stem}.md").write_text(
        f"# {stem}\n\n" + "\n\n---\n\n".join(markdown_sections).strip() + "\n",
        encoding="utf-8",
    )
    (exports / f"{stem}.json").write_text(
        json.dumps(
            {
                "filename": job["filename"],
                "created_at": job["created_at"],
                "completed_at": job.get("completed_at"),
                "options": job.get("options"),
                "warnings": job.get("warnings"),
                "pages": json_pages,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _process_job(job_id: str) -> None:
    started = time.monotonic()
    try:
        job = store.get(job_id)
    except KeyError:
        return
    if job.get("status") == "canceled":
        return

    engine_id = str(job.get("engine_id") or LOCAL_ENGINE_ID)
    engine_name = _engine_label(engine_id)

    # 只有仍然是 queued 的任务才能进入 preparing；否则可能把用户刚提交的取消覆盖掉。
    begin_state = {"ok": False}

    def begin_run(data: dict[str, Any]) -> None:
        if data.get("status") != "queued" or data.get("cancel_requested"):
            return
        begin_state["ok"] = True
        data.update(
            {
                "status": "preparing",
                "stage": "正在拆分文件并生成页面预览",
                "progress": 5,
                "started_at": utc_now(),
                "completed_at": None,
                "error": None,
                "engine_id": engine_id,
                "engine_label": engine_name,
                "pages": [],
                "warnings": [],
                "stats": {
                    "total_pages": 0,
                    "completed_pages": 0,
                    "failed_pages": 0,
                    "elapsed_seconds": 0,
                },
            }
        )

    try:
        store.mutate(job_id, begin_run)
        if not begin_state["ok"]:
            logger.info("Job %s no longer queued; skipping dispatch", job_id)
            return
        job = store.get(job_id)
        options = _default_options(job.get("options"))
        pages_dir = store.job_dir(job_id) / "pages"
        if pages_dir.exists():
            shutil.rmtree(pages_dir)
        preparer = DocumentPreparer(
            pages_dir,
            dpi=options["dpi"],
            page_range=options["page_range"],
            max_pages=MAX_PAGES,
        )
        prepared = preparer.prepare(
            store.source_path(job_id),
            display_name=job["filename"],
        )

        page_records = []
        for page in prepared.pages:
            page_records.append(
                {
                    "index": page.index,
                    "label": page.label,
                    "source_name": page.source_name,
                    "image_file": page.image_path.name if page.image_path else None,
                    "status": "queued",
                    "text": "",
                    "error": None,
                    "elapsed_seconds": 0,
                    "_extracted_text": page.extracted_text,
                }
            )
        cancelled_while_preparing = {"value": False}

        def mark_prepared(data: dict[str, Any]) -> None:
            if data.get("cancel_requested"):
                cancelled_while_preparing["value"] = True
                data.update(
                    {
                        "status": "canceled",
                        "stage": "任务已取消；没有开始识别",
                        "completed_at": utc_now(),
                        "pages": page_records,
                        "warnings": prepared.warnings,
                    }
                )
                return
            data.update(
                {
                    "status": "running",
                    "stage": f"准备完成，共 {len(page_records)} 页",
                    "progress": 12,
                    "pages": page_records,
                    "warnings": prepared.warnings,
                    "stats": {
                        "total_pages": len(page_records),
                        "completed_pages": 0,
                        "failed_pages": 0,
                        "elapsed_seconds": 0,
                    },
                }
            )

        store.mutate(job_id, mark_prepared)
        if cancelled_while_preparing["value"]:
            _write_exports(job_id)
            return

        completed_pages = 0
        failed_pages = 0
        total = len(page_records)
        for index in range(total):
            latest = store.get(job_id)
            if latest.get("cancel_requested"):
                store.update(
                    job_id,
                    status="canceled",
                    stage="任务已取消；已经完成的页面仍会保留",
                    completed_at=utc_now(),
                )
                _write_exports(job_id)
                return

            def mark_running(data: dict[str, Any]) -> None:
                if not data.get("cancel_requested"):
                    data["status"] = "running"
                data["stage"] = (
                    f"{engine_name} · 正在识别第 {index + 1} / {total} 页"
                )
                data["progress"] = 12 + round(82 * index / max(total, 1))
                data["pages"][index]["status"] = "running"

            store.mutate(job_id, mark_running)
            page_started = time.monotonic()
            page = store.get(job_id)["pages"][index]
            try:
                direct_text = page.pop("_extracted_text", None)
                if direct_text is not None:
                    result = str(direct_text)
                    page_kind = "direct"
                    diagnostics: dict[str, Any] = {}
                else:
                    image_file = page.get("image_file")
                    if not image_file:
                        raise RuntimeError("页面预览文件不存在")
                    image_path = pages_dir / image_file
                    result, diagnostics, _used_engine = _scan_page_image(
                        engine_id,
                        image_path,
                        options,
                        should_cancel=lambda: bool(
                            store.get(job_id).get("cancel_requested")
                        ),
                    )
                    page_kind = "ocr"
                elapsed = round(time.monotonic() - page_started, 2)

                def mark_done(data: dict[str, Any]) -> None:
                    target = data["pages"][index]
                    target.pop("_extracted_text", None)
                    target.update(
                        {
                            "status": "completed",
                            "text": result,
                            "kind": page_kind,
                            "engine_id": engine_id,
                            "error": None,
                            "elapsed_seconds": elapsed,
                            "repetition_trimmed": bool(
                                diagnostics.get("repetition")
                            ),
                            "repetition_diagnostics": diagnostics.get(
                                "repetition"
                            ),
                            "usage": diagnostics.get("usage"),
                            "truncated": bool(diagnostics.get("truncated")),
                        }
                    )

                store.mutate(job_id, mark_done)
                result_dir = store.job_dir(job_id) / "page-results"
                result_dir.mkdir(exist_ok=True)
                (result_dir / f"page-{index + 1:04d}.txt").write_text(
                    result,
                    encoding="utf-8",
                )
                completed_pages += 1
            except Exception as exc:
                elapsed = round(time.monotonic() - page_started, 2)
                message = f"{type(exc).__name__}: {exc}"
                logger.exception("Page %s failed in job %s", index + 1, job_id)

                def mark_failed(data: dict[str, Any]) -> None:
                    target = data["pages"][index]
                    target.pop("_extracted_text", None)
                    target.update(
                        {
                            "status": "failed",
                            "text": "",
                            "error": message,
                            "elapsed_seconds": elapsed,
                        }
                    )

                store.mutate(job_id, mark_failed)
                failed_pages += 1

            def update_counts(data: dict[str, Any]) -> None:
                data["stats"]["completed_pages"] = completed_pages
                data["stats"]["failed_pages"] = failed_pages
                data["stats"]["elapsed_seconds"] = round(
                    time.monotonic() - started, 1
                )
                data["progress"] = 12 + round(
                    82 * (index + 1) / max(total, 1)
                )

            store.mutate(job_id, update_counts)

        final_status = "completed"
        final_stage = f"识别完成，共处理 {total} 页"
        if failed_pages and completed_pages:
            final_status = "partial"
            final_stage = f"已完成 {completed_pages} 页，{failed_pages} 页失败"
        elif failed_pages and not completed_pages:
            final_status = "failed"
            final_stage = "所有页面均识别失败"

        store.update(
            job_id,
            status=final_status,
            stage=final_stage,
            progress=100,
            completed_at=utc_now(),
            error="所有页面均识别失败" if final_status == "failed" else None,
            stats={
                "total_pages": total,
                "completed_pages": completed_pages,
                "failed_pages": failed_pages,
                "elapsed_seconds": round(time.monotonic() - started, 1),
            },
        )
        _write_exports(job_id)
    except Exception as exc:
        logger.exception("Job %s failed", job_id)
        try:
            current_stats = store.get(job_id).get("stats") or {}
        except Exception:
            current_stats = {}
        try:
            store.update(
                job_id,
                status="failed",
                stage="任务处理失败",
                progress=100,
                completed_at=utc_now(),
                error=f"{type(exc).__name__}: {exc}",
                stats={
                    **current_stats,
                    "elapsed_seconds": round(time.monotonic() - started, 1),
                },
            )
            _write_exports(job_id)
        except Exception:
            logger.exception("Unable to persist failure for job %s", job_id)
            # 兜底：至少把状态改成 failed，避免任务永远停在 running。
            try:
                store.update(
                    job_id,
                    status="failed",
                    stage="任务处理失败（细节未能写入）",
                    completed_at=utc_now(),
                    error=f"{type(exc).__name__}: {exc}",
                )
            except Exception:
                logger.exception("Unable to mark job %s failed", job_id)


def _run_job(job_id: str) -> None:
    try:
        _process_job(job_id)
    finally:
        _unload_model_if_idle("任务队列已全部完成")


def _start_worker() -> None:
    dispatcher.start()
    for job_id in store.queued_ids():
        dispatcher.submit(job_id)


@asynccontextmanager
async def lifespan(_: FastAPI):
    _start_worker()
    _start_client_monitor()
    yield
    model_download.cancel()
    client_monitor_stop.set()
    if client_monitor_thread:
        client_monitor_thread.join(timeout=3)
    dispatcher.stop()
    if engine.status()["loaded"] and not engine.busy:
        engine.unload()


app = FastAPI(
    title="Unlimited OCR Studio",
    version="1.3.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def local_request_guard(request: Request, call_next):
    """CORS alone does not stop cross-site form POSTs or DNS rebinding.

    The desktop shell/CLI may omit Origin; browser requests must come from
    the same two local UI origins already permitted by CORS.
    """
    allowed_origins = {"http://localhost:3000", "http://127.0.0.1:3000"}
    if request.headers.get("host", "").lower() not in {
        "localhost:18765", "127.0.0.1:18765",
    }:
        return JSONResponse({"detail": "仅允许通过本机地址访问墨析"}, status_code=403)
    origin = request.headers.get("origin")
    if origin is not None and origin not in allowed_origins:
        return JSONResponse({"detail": "已拒绝来自外部网页的操作"}, status_code=403)
    if origin is None:
        referer = request.headers.get("referer")
        if referer:
            parsed = urllib.parse.urlsplit(referer)
            if f"{parsed.scheme}://{parsed.netloc}" not in allowed_origins:
                return JSONResponse({"detail": "已拒绝来自外部网页的操作"}, status_code=403)
        elif request.headers.get("sec-fetch-site") == "cross-site":
            return JSONResponse({"detail": "已拒绝来自外部网页的操作"}, status_code=403)
    return await call_next(request)


@app.get("/api/health")
def health() -> dict[str, Any]:
    _mark_client_seen()
    return {
        "status": "ok",
        "local_only": True,
        "model": engine.status(),
        "model_download": model_download.status(),
        "converters": converter_status(),
        "supported_extensions": sorted(SUPPORTED_EXTENSIONS),
        "max_upload_bytes": MAX_UPLOAD_BYTES,
        "queue_size": dispatcher.pending_count(),
        "running_jobs": dispatcher.running_count(),
        "max_parallel": GLOBAL_MAX_PARALLEL,
        "engines": _engine_catalog(),
        "lifecycle": {
            "auto_unload": True,
            "client_connected": _client_is_connected(),
            "client_timeout_seconds": CLIENT_TIMEOUT_SECONDS,
        },
    }


@app.get("/api/readyz")
def readyz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/client/status")
def client_status() -> dict[str, Any]:
    return {
        "connected": _client_is_connected(),
        "client_timeout_seconds": CLIENT_TIMEOUT_SECONDS,
    }


@app.post("/api/client/disconnect")
def client_disconnect() -> dict[str, Any]:
    _mark_client_disconnected()
    unloaded = _unload_model_if_idle("网页已关闭")
    return {
        "connected": False,
        "model_unloaded": unloaded,
        "model": engine.status(),
    }


@app.get("/api/jobs")
def list_jobs(limit: int = 100) -> dict[str, Any]:
    return {"jobs": store.list(limit=limit)}


@app.post("/api/jobs", status_code=201)
async def create_job(request: Request) -> dict[str, Any]:
    encoded_name = request.headers.get("x-file-name", "")
    filename = urllib.parse.unquote(encoded_name) if encoded_name else "未命名文件"
    content_type = request.headers.get("x-file-type", "application/octet-stream")
    encoded_options = request.headers.get("x-ocr-options", "")
    try:
        options_raw = (
            json.loads(urllib.parse.unquote(encoded_options))
            if encoded_options
            else {}
        )
        options = _default_options(options_raw)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail=f"识别选项不正确：{exc}") from exc

    suffix = Path(safe_filename(filename)).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"暂不支持 {suffix or '未知'} 格式",
        )

    encoded_engine = request.headers.get("x-ocr-engine", "")
    engine_id = urllib.parse.unquote(encoded_engine).strip() or LOCAL_ENGINE_ID
    if engine_id != LOCAL_ENGINE_ID:
        endpoint = registry.get(engine_id)
        if endpoint is None:
            raise HTTPException(
                status_code=422,
                detail="选择的识别引擎不存在，请刷新后重新选择",
            )
        if not endpoint.get("enabled"):
            raise HTTPException(
                status_code=409,
                detail="选择的识别引擎已停用，请启用后再扫描",
            )
    if engine_id == LOCAL_ENGINE_ID and not (
        model_download.status().get("model_ready")
        and model_download.status().get("runtime_ready")
    ):
        raise HTTPException(
            status_code=409,
            detail="本机模型尚未下载或校验，请先完成模型准备，或改选已配置的模型接口",
        )

    job = store.create(
        filename=filename,
        content_type=content_type,
        options=options,
        engine_id=engine_id,
        engine_label=_engine_label(engine_id),
    )
    source = store.job_dir(job["id"]) / job["source_file"]
    received = 0
    try:
        with source.open("wb") as writer:
            async for chunk in request.stream():
                received += len(chunk)
                if received > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail="文件超过 1 GB 上限",
                    )
                writer.write(chunk)
        if received == 0:
            raise HTTPException(status_code=400, detail="上传的文件为空")
        store.update(
            job["id"],
            size=received,
            status="queued",
            stage="文件已接收，等待处理",
            progress=3,
        )
        with model_operation_lock:
            if model_download.status().get("running"):
                raise HTTPException(status_code=409, detail="模型正在下载或校验，请完成后再开始扫描")
            dispatcher.submit(job["id"])
        return store.get(job["id"])
    except Exception:
        try:
            store.delete(job["id"])
        except Exception:
            pass
        raise


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    return _job_or_404(job_id)


@app.post("/api/jobs/{job_id}/reader/prepare")
def prepare_reader(job_id: str) -> dict[str, Any]:
    job = _job_or_404(job_id)
    if job.get("status") not in READER_READY_STATUSES:
        raise HTTPException(
            status_code=409,
            detail="任务仍在处理或等待处理，完成后才能准备阅读版",
        )

    prepared_pages: list[dict[str, Any]] = []
    changed_pages = 0
    removed_chars = 0
    for page in job.get("pages", []):
        original = str(page.get("text") or "")
        result = trim_repetitive_tail(original)
        reading_text: str | None = None
        reading_repair: dict[str, Any] | None = None
        if result.finding.detected and result.text != original:
            reading_text = result.text
            reading_repair = {
                **result.finding.as_dict(),
                "source_chars": len(original),
                "reading_chars": len(result.text),
            }
            changed_pages += 1
            removed_chars += result.finding.removed_chars
        prepared_pages.append(
            {
                "source_text": original,
                "reading_text": reading_text,
                "reading_repair": reading_repair,
            }
        )

    def apply_reader_text(data: dict[str, Any]) -> None:
        if data.get("status") not in READER_READY_STATUSES:
            raise HTTPException(
                status_code=409,
                detail="任务状态已经改变，请在任务完成后重试",
            )
        pages = data.get("pages", [])
        if len(pages) != len(prepared_pages) or any(
            str(page.get("text") or "") != prepared["source_text"]
            for page, prepared in zip(pages, prepared_pages)
        ):
            raise HTTPException(
                status_code=409,
                detail="识别结果在准备阅读版期间发生变化，请重试",
            )
        for page, prepared in zip(pages, prepared_pages):
            reading_text = prepared["reading_text"]
            reading_repair = prepared["reading_repair"]
            if reading_text is None:
                page.pop("reading_text", None)
                page.pop("reading_repair", None)
            else:
                page["reading_text"] = reading_text
                page["reading_repair"] = reading_repair

    def reader_fields_match(
        page: dict[str, Any],
        prepared: dict[str, Any],
    ) -> bool:
        if prepared["reading_text"] is None:
            return (
                "reading_text" not in page
                and "reading_repair" not in page
            )
        return (
            page.get("reading_text") == prepared["reading_text"]
            and page.get("reading_repair") == prepared["reading_repair"]
        )

    latest = store.get(job_id)
    latest_pages = latest.get("pages", [])
    already_prepared = (
        latest.get("status") in READER_READY_STATUSES
        and len(latest_pages) == len(prepared_pages)
        and all(
            str(page.get("text") or "") == prepared["source_text"]
            and reader_fields_match(page, prepared)
            for page, prepared in zip(latest_pages, prepared_pages)
        )
    )
    updated = latest if already_prepared else store.mutate(job_id, apply_reader_text)
    _write_exports(job_id)
    return {
        "job": updated,
        "changed_pages": changed_pages,
        "removed_chars": removed_chars,
    }


@app.get("/api/jobs/{job_id}/reader-state")
def get_reader_state(job_id: str) -> dict[str, Any]:
    job = _job_or_404(job_id)
    current = job.get("reader_state")
    if current is not None and not isinstance(current, dict):
        raise HTTPException(status_code=500, detail="已保存的阅读状态格式不正确")
    return _validate_reader_state(
        {},
        page_count=len(job.get("pages", [])),
        current=current,
    )


@app.put("/api/jobs/{job_id}/reader-state")
def update_reader_state(
    job_id: str,
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    _job_or_404(job_id)

    def apply_reader_state(data: dict[str, Any]) -> None:
        current = data.get("reader_state")
        if current is not None and not isinstance(current, dict):
            raise HTTPException(
                status_code=500,
                detail="已保存的阅读状态格式不正确",
            )
        data["reader_state"] = _validate_reader_state(
            payload,
            page_count=len(data.get("pages", [])),
            current=current,
        )

    updated = store.mutate(job_id, apply_reader_state)
    return updated["reader_state"]


@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str) -> dict[str, Any]:
    job = _job_or_404(job_id)
    if job["status"] in {"completed", "partial", "failed", "canceled"}:
        return job
    if job["status"] == "queued":
        dispatcher.forget(job_id)
        return store.update(
            job_id,
            status="canceled",
            stage="任务已取消",
            cancel_requested=True,
            completed_at=utc_now(),
        )
    return store.update(
        job_id,
        status="canceling",
        stage="将在当前页面处理完成后取消",
        cancel_requested=True,
    )


@app.post("/api/jobs/{job_id}/retry")
def retry_job(job_id: str) -> dict[str, Any]:
    with model_operation_lock:
        if model_download.status().get("running"):
            raise HTTPException(status_code=409, detail="模型正在下载或校验，请完成后再重试扫描")
        return _retry_job_locked(job_id)


def _retry_job_locked(job_id: str) -> dict[str, Any]:
    job = _job_or_404(job_id)
    if job["status"] in {"running", "preparing", "canceling", "uploading"}:
        raise HTTPException(status_code=409, detail="任务仍在运行")
    updated = store.update(
        job_id,
        status="queued",
        stage="等待重新处理",
        progress=0,
        error=None,
        cancel_requested=False,
        completed_at=None,
    )
    dispatcher.submit(job_id)
    return updated


@app.delete("/api/jobs/{job_id}", status_code=204)
def delete_job(job_id: str) -> Response:
    _job_or_404(job_id)
    try:
        dispatcher.forget(job_id)
        store.delete(job_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return Response(status_code=204)


@app.get("/api/jobs/{job_id}/pages/{page_index}/image")
def page_image(job_id: str, page_index: int) -> FileResponse:
    job = _job_or_404(job_id)
    pages = job.get("pages", [])
    if page_index < 0 or page_index >= len(pages):
        raise HTTPException(status_code=404, detail="没有找到这个页面")
    image_file = pages[page_index].get("image_file")
    if not image_file:
        raise HTTPException(status_code=404, detail="该页面没有图像预览")
    path = store.job_dir(job_id) / "pages" / image_file
    if not path.exists():
        raise HTTPException(status_code=404, detail="页面预览文件不存在")
    return FileResponse(path, media_type="image/png")


@app.put("/api/jobs/{job_id}/pages/{page_index}")
def update_page(
    job_id: str,
    page_index: int,
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    job = _job_or_404(job_id)
    pages = job.get("pages", [])
    if page_index < 0 or page_index >= len(pages):
        raise HTTPException(status_code=404, detail="没有找到这个页面")
    text = str(payload.get("text") or "")

    def apply(data: dict[str, Any]) -> None:
        data["pages"][page_index]["text"] = text
        data["pages"][page_index]["edited"] = True
        data["pages"][page_index].pop("reading_text", None)
        data["pages"][page_index].pop("reading_repair", None)

    updated = store.mutate(job_id, apply)
    result_dir = store.job_dir(job_id) / "page-results"
    result_dir.mkdir(exist_ok=True)
    (result_dir / f"page-{page_index + 1:04d}.txt").write_text(
        text,
        encoding="utf-8",
    )
    _write_exports(job_id)
    return updated


def _download_headers(filename: str) -> dict[str, str]:
    encoded = urllib.parse.quote(filename)
    return {"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"}


@app.get("/api/jobs/{job_id}/download/{format_name}")
def download_result(job_id: str, format_name: str) -> FileResponse:
    job = _job_or_404(job_id)
    if format_name not in {"txt", "md", "json"}:
        raise HTTPException(status_code=400, detail="只支持 txt、md 或 json")
    _write_exports(job_id)
    stem = Path(safe_filename(job["filename"])).stem or "OCR结果"
    path = store.job_dir(job_id) / "exports" / f"{stem}.{format_name}"
    media_types = {
        "txt": "text/plain; charset=utf-8",
        "md": "text/markdown; charset=utf-8",
        "json": "application/json",
    }
    return FileResponse(
        path,
        media_type=media_types[format_name],
        headers=_download_headers(path.name),
    )


@app.get("/api/jobs/{job_id}/download/zip/package")
def download_package(job_id: str, include_pages: bool = True) -> FileResponse:
    job = _job_or_404(job_id)
    _write_exports(job_id)
    directory = store.job_dir(job_id)
    stem = Path(safe_filename(job["filename"])).stem or "OCR结果"
    archive_path = directory / "exports" / f"{stem}-完整结果.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        source = store.source_path(job_id)
        archive.write(source, f"原始文件/{job['filename']}")
        for output in (directory / "exports").glob(f"{stem}.*"):
            if output != archive_path:
                archive.write(output, f"识别结果/{output.name}")
        if include_pages:
            for page in sorted((directory / "pages").glob("*.png")):
                archive.write(page, f"页面预览/{page.name}")
    return FileResponse(
        archive_path,
        media_type="application/zip",
        headers=_download_headers(archive_path.name),
    )


def _background_load_model() -> None:
    try:
        engine.load()
    except Exception:
        logger.exception("Background model preload failed")


@app.post("/api/model/load", status_code=202)
def load_model() -> JSONResponse:
    global model_loader_thread
    with model_operation_lock:
        download = model_download.status()
        if download.get("running") or not download.get("model_ready") or not download.get("runtime_ready"):
            raise HTTPException(status_code=409, detail="请先在设置中完成模型下载与校验")
        status = engine.status()
        if status["loaded"] or (model_loader_thread and model_loader_thread.is_alive()):
            return JSONResponse(status)
        model_loader_thread = threading.Thread(
            target=_background_load_model, name="ocr-model-loader", daemon=True,
        )
        model_loader_thread.start()
        return JSONResponse(engine.status(), status_code=202)


@app.post("/api/model/download", status_code=202)
def download_model() -> JSONResponse:
    with model_operation_lock:
        if (engine.busy or engine.status()["loaded"] or _local_jobs_active()
                or (model_loader_thread and model_loader_thread.is_alive())):
            raise HTTPException(status_code=409, detail="请等待任务结束并卸载模型后再下载或校验")
        try:
            status = model_download.start()
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return JSONResponse(status, status_code=202)


@app.post("/api/model/download/cancel")
def cancel_model_download() -> dict[str, Any]:
    return model_download.cancel()


@app.post("/api/model/unload")
def unload_model() -> dict[str, Any]:
    if engine.busy:
        raise HTTPException(status_code=409, detail="模型正在处理任务")
    try:
        engine.unload()
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return engine.status()


@app.get("/api/models")
def list_engines() -> dict[str, Any]:
    return {
        "engines": _engine_catalog(),
        "max_parallel": GLOBAL_MAX_PARALLEL,
        "default_concurrency": DEFAULT_ENDPOINT_CONCURRENCY,
        "local_label": LOCAL_ENGINE_LABEL,
    }


@app.get("/api/models/endpoints")
def list_endpoints() -> dict[str, Any]:
    return {"endpoints": registry.public_list()}


@app.post("/api/models/endpoints", status_code=201)
def create_endpoint(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    try:
        endpoint = registry.create(payload)
    except EndpointValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    dispatcher.wake()
    return public_endpoint(endpoint)


@app.put("/api/models/endpoints/{endpoint_id}")
def update_endpoint(
    endpoint_id: str,
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    if payload.pop("clear_api_key", False):
        payload = {**payload, "api_key": ""}
    elif payload.get("api_key") == "":
        payload = {**payload, "api_key": KEEP_KEY_SENTINEL}
    current = registry.get(endpoint_id)
    if (
        current is not None
        and payload.get("base_url")
        and "api_key" not in payload
        and str(payload["base_url"]).rstrip("/") != current["base_url"]
    ):
        # 地址换了但没给新密钥：丢掉旧密钥，避免密钥被带到另一个主机。
        payload = {**payload, "api_key": ""}
    try:
        endpoint = registry.update(endpoint_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="没有找到这个模型接口") from exc
    except EndpointValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    dispatcher.wake()
    return public_endpoint(endpoint)


@app.delete("/api/models/endpoints/{endpoint_id}", status_code=204)
def delete_endpoint(endpoint_id: str) -> Response:
    running = dispatcher.running_by_engine().get(endpoint_id, 0)
    if running:
        raise HTTPException(
            status_code=409,
            detail="这个接口仍有任务在运行，请等待完成后再删除",
        )
    for job_id in dispatcher.pending_ids():
        try:
            pending_engine = store.get(job_id).get("engine_id")
        except KeyError:
            continue
        if pending_engine == endpoint_id:
            raise HTTPException(
                status_code=409,
                detail="这个接口还有排队中的任务，请先取消这些任务再删除",
            )
    try:
        registry.delete(endpoint_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="没有找到这个模型接口") from exc
    dispatcher.wake()
    return Response(status_code=204)


@app.post("/api/models/endpoints/{endpoint_id}/test")
def test_endpoint(
    endpoint_id: str,
    payload: dict[str, Any] = Body(default={}),
) -> JSONResponse:
    endpoint = registry.get(endpoint_id)
    if endpoint is None:
        raise HTTPException(status_code=404, detail="没有找到这个模型接口")
    candidate = dict(endpoint)
    if payload.get("base_url"):
        try:
            candidate["base_url"] = normalize_base_url(payload["base_url"])
        except EndpointValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        # 换成另一个地址时绝不携带已保存的密钥，只有本次显式提交的才使用。
        candidate["api_key"] = str(payload.get("api_key") or "").strip()
    elif payload.get("api_key"):
        candidate["api_key"] = str(payload["api_key"]).strip()
    if payload.get("model"):
        candidate["model"] = str(payload["model"]).strip()
    started = time.monotonic()
    try:
        models = RemoteEngine(candidate).list_models()
    except RemoteEngineError as exc:
        return JSONResponse(
            {"ok": False, "message": str(exc)},
            status_code=502,
        )
    latency_ms = round((time.monotonic() - started) * 1000)
    return JSONResponse(
        {
            "ok": True,
            "models": models,
            "model_found": candidate["model"] in models,
            "latency_ms": latency_ms,
            "message": (
                "连接正常，模型已加载"
                if candidate["model"] in models
                else "连接正常，但模型列表中没有这个模型 ID"
            ),
        }
    )


@app.post("/api/models/discover")
def discover_models(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    try:
        base_url = normalize_base_url(payload.get("base_url"))
    except EndpointValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    api_key = str(payload.get("api_key") or "").strip()
    try:
        models = probe_models(base_url, api_key)
    except RemoteEngineError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"models": models}


@app.exception_handler(Exception)
async def unhandled_error(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled API error")
    return JSONResponse(
        status_code=500,
        content={"detail": f"本机服务发生错误：{type(exc).__name__}: {exc}"},
    )
