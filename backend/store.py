from __future__ import annotations

import copy
import json
import re
import shutil
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .config import JOBS_ROOT, ensure_data_dirs


JOB_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_filename(value: str) -> str:
    name = Path(value.replace("\x00", "")).name.strip()
    return name[:240] or "未命名文件"


class JobStore:
    def __init__(self) -> None:
        ensure_data_dirs()
        self._lock = threading.RLock()
        self._jobs: dict[str, dict[str, Any]] = {}
        self._load_existing()

    def _validate_id(self, job_id: str) -> None:
        if not JOB_ID_PATTERN.fullmatch(job_id):
            raise KeyError(job_id)

    def job_dir(self, job_id: str) -> Path:
        self._validate_id(job_id)
        return JOBS_ROOT / job_id

    def source_path(self, job_id: str) -> Path:
        job = self.get(job_id)
        return self.job_dir(job_id) / job["source_file"]

    def _load_existing(self) -> None:
        for metadata_path in JOBS_ROOT.glob("*/job.json"):
            try:
                data = json.loads(metadata_path.read_text("utf-8"))
                job_id = data.get("id", "")
                self._validate_id(job_id)
                if data.get("status") in {"running", "preparing", "canceling"}:
                    data["status"] = "queued"
                    data["stage"] = "上次运行中断，等待重新处理"
                    data["progress"] = 0
                    data["cancel_requested"] = False
                    self._write(data)
                self._jobs[job_id] = data
            except Exception:
                continue

    def _write(self, job: dict[str, Any]) -> None:
        directory = self.job_dir(job["id"])
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / "job.json"
        temporary = directory / "job.json.tmp"
        temporary.write_text(
            json.dumps(job, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(target)

    def create(
        self,
        *,
        filename: str,
        content_type: str,
        options: dict[str, Any],
        engine_id: str = "local",
        engine_label: str = "本机 MLX",
    ) -> dict[str, Any]:
        with self._lock:
            job_id = uuid.uuid4().hex
            clean_name = safe_filename(filename)
            suffix = Path(clean_name).suffix.lower()
            source_file = f"source{suffix}" if suffix else "source.bin"
            now = utc_now()
            job = {
                "id": job_id,
                "filename": clean_name,
                "source_file": source_file,
                "content_type": content_type or "application/octet-stream",
                "engine_id": engine_id,
                "engine_label": engine_label,
                "size": 0,
                "status": "uploading",
                "stage": "正在接收文件",
                "progress": 1,
                "created_at": now,
                "updated_at": now,
                "started_at": None,
                "completed_at": None,
                "options": options,
                "pages": [],
                "warnings": [],
                "error": None,
                "cancel_requested": False,
                "stats": {
                    "total_pages": 0,
                    "completed_pages": 0,
                    "failed_pages": 0,
                    "elapsed_seconds": 0,
                },
            }
            self._jobs[job_id] = job
            self._write(job)
            return copy.deepcopy(job)

    def get(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            self._validate_id(job_id)
            if job_id not in self._jobs:
                raise KeyError(job_id)
            return copy.deepcopy(self._jobs[job_id])

    def mutate(
        self,
        job_id: str,
        callback: Callable[[dict[str, Any]], None],
    ) -> dict[str, Any]:
        with self._lock:
            self._validate_id(job_id)
            if job_id not in self._jobs:
                raise KeyError(job_id)
            job = self._jobs[job_id]
            callback(job)
            job["updated_at"] = utc_now()
            self._write(job)
            return copy.deepcopy(job)

    def update(self, job_id: str, **values: Any) -> dict[str, Any]:
        return self.mutate(job_id, lambda job: job.update(values))

    def list(self, *, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            jobs = sorted(
                self._jobs.values(),
                key=lambda item: item.get("created_at", ""),
                reverse=True,
            )[: max(1, min(limit, 500))]
            summaries = []
            for job in jobs:
                summaries.append(
                    {
                        key: copy.deepcopy(job.get(key))
                        for key in (
                            "id",
                            "filename",
                            "content_type",
                            "size",
                            "status",
                            "stage",
                            "progress",
                            "created_at",
                            "updated_at",
                            "completed_at",
                            "error",
                            "stats",
                            "warnings",
                            "engine_id",
                            "engine_label",
                        )
                    }
                )
            return summaries

    def delete(self, job_id: str) -> None:
        with self._lock:
            self._validate_id(job_id)
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError(job_id)
            if job.get("status") in {"running", "preparing", "canceling"}:
                raise RuntimeError("任务仍在运行，不能删除")
            directory = self.job_dir(job_id)
            del self._jobs[job_id]
            if directory.exists():
                shutil.rmtree(directory)

    def queued_ids(self) -> list[str]:
        with self._lock:
            return [
                job_id
                for job_id, job in self._jobs.items()
                if job.get("status") == "queued"
            ]
