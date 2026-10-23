"""按引擎并发槽并行调度扫描任务。

每个任务只占用一个槽；同一引擎的槽数可配置（本机 MLX 固定 1，远程接口默认 3）。
调度器不会让排队任务占满线程：只有真正开始执行的任务才创建线程，
因此某个引擎排队很长也不会阻塞其他引擎的短任务。
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

logger = logging.getLogger("ocr-studio.dispatcher")


class JobDispatcher:
    def __init__(
        self,
        *,
        resolve_engine: Callable[[str], str | None],
        slots_for: Callable[[str], int],
        process: Callable[[str], None],
        max_parallel: int = 9,
        requeue_if: Callable[[str], bool] | None = None,
    ):
        self._resolve_engine = resolve_engine
        self._slots_for = slots_for
        self._process = process
        self._requeue_if = requeue_if
        self._max_parallel = max(1, int(max_parallel))
        self._condition = threading.Condition()
        self._pending: list[str] = []
        self._running: dict[str, str] = {}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # ---- 生命周期 ---------------------------------------------------------

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop,
            name="ocr-dispatcher",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        with self._condition:
            self._condition.notify_all()
        if self._thread:
            self._thread.join(timeout=3)

    # ---- 入队与唤醒 -------------------------------------------------------

    def submit(self, job_id: str) -> None:
        with self._condition:
            if job_id in self._running or job_id in self._pending:
                return
            self._pending.append(job_id)
            self._condition.notify_all()

    def wake(self) -> None:
        """配置或槽位变化后重新评估排队任务。"""
        with self._condition:
            self._condition.notify_all()

    def forget(self, job_id: str) -> None:
        """任务被删除或取消时移出排队列表。"""
        with self._condition:
            if job_id in self._pending:
                self._pending.remove(job_id)

    # ---- 状态 -------------------------------------------------------------

    @property
    def busy(self) -> bool:
        with self._condition:
            return bool(self._pending or self._running)

    def pending_count(self) -> int:
        with self._condition:
            return len(self._pending)

    def running_count(self) -> int:
        with self._condition:
            return len(self._running)

    def running_by_engine(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        with self._condition:
            for engine_id in self._running.values():
                counts[engine_id] = counts.get(engine_id, 0) + 1
        return counts

    def pending_ids(self) -> list[str]:
        with self._condition:
            return list(self._pending)

    def pending_engines(self) -> set[str]:
        """排队任务绑定的引擎，供“本机引擎是否真的空闲”判断使用。"""
        with self._condition:
            pending = list(self._pending)
        engines: set[str] = set()
        for job_id in pending:
            engine_id = self._resolve_engine(job_id)
            if engine_id:
                engines.add(engine_id)
        return engines

    # ---- 调度 -------------------------------------------------------------

    def _loop(self) -> None:
        while not self._stop.is_set():
            with self._condition:
                self._condition.wait(timeout=0.5)
            if self._stop.is_set():
                break
            try:
                self._schedule()
            except Exception:
                logger.exception("Task dispatch failed")

    def _schedule(self) -> None:
        with self._condition:
            candidate_ids = list(self._pending)
        for job_id in candidate_ids:
            with self._condition:
                if job_id not in self._pending:
                    continue
                if len(self._running) >= self._max_parallel:
                    return
            engine_id = self._resolve_engine(job_id)
            if engine_id is None:
                with self._condition:
                    if job_id in self._pending:
                        self._pending.remove(job_id)
                continue
            slots = max(1, int(self._slots_for(engine_id) or 1))
            with self._condition:
                if job_id not in self._pending:
                    continue
                active = sum(
                    1 for value in self._running.values() if value == engine_id
                )
                if active >= slots:
                    continue
                self._pending.remove(job_id)
                self._running[job_id] = engine_id
            thread = threading.Thread(
                target=self._run_job,
                args=(job_id, engine_id),
                name=f"ocr-job-{job_id[:8]}",
                daemon=True,
            )
            thread.start()

    def _run_job(self, job_id: str, engine_id: str) -> None:
        try:
            self._process(job_id)
        except Exception:
            logger.exception("Job %s crashed in dispatcher", job_id)
        finally:
            # 任务收尾期间可能被“重试”重新排队；此时不重新入队会永久丢失。
            requeue = bool(self._requeue_if and self._requeue_if(job_id))
            with self._condition:
                self._running.pop(job_id, None)
                if requeue and job_id not in self._pending:
                    self._pending.append(job_id)
                self._condition.notify_all()
