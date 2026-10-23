"""并行调度：每引擎槽位、全局上限、不互相阻塞。"""
from __future__ import annotations

import threading
import time

from backend.dispatcher import JobDispatcher


def wait_until(predicate, timeout: float = 3.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


def collect_dispatcher(engines: dict[str, int], *, max_parallel: int):
    state = {"active": 0, "peak": 0}
    lock = threading.Lock()
    release = threading.Event()
    processed: list[str] = []

    def process(job_id: str) -> None:
        with lock:
            state["active"] += 1
            state["peak"] = max(state["peak"], state["active"])
        release.wait(2.0)
        with lock:
            state["active"] -= 1
        processed.append(job_id)

    dispatcher = JobDispatcher(
        resolve_engine=lambda job_id: job_id.split(":")[0],
        slots_for=lambda engine_id: engines.get(engine_id, 1),
        process=process,
        max_parallel=max_parallel,
    )
    return dispatcher, state, release, processed


def test_engine_slots_limit_concurrency():
    dispatcher, state, release, processed = collect_dispatcher(
        {"a": 1}, max_parallel=9
    )
    dispatcher.start()
    try:
        for index in range(3):
            dispatcher.submit(f"a:{index}")
        assert wait_until(lambda: state["peak"] >= 1)
        time.sleep(0.2)
        assert state["peak"] == 1
        assert dispatcher.running_count() == 1
        assert dispatcher.pending_count() == 2
        release.set()
        assert wait_until(lambda: len(processed) == 3, timeout=3)
        assert state["peak"] == 1
    finally:
        release.set()
        dispatcher.stop()


def test_global_parallel_cap_applies():
    dispatcher, state, release, processed = collect_dispatcher(
        {"a": 3, "b": 3, "c": 3, "d": 3}, max_parallel=2
    )
    dispatcher.start()
    try:
        for engine in ("a", "b", "c", "d"):
            dispatcher.submit(f"{engine}:1")
        assert wait_until(lambda: state["peak"] >= 2)
        time.sleep(0.2)
        assert state["peak"] == 2
        release.set()
        assert wait_until(lambda: len(processed) == 4, timeout=3)
    finally:
        release.set()
        dispatcher.stop()


def test_busy_engine_does_not_block_other_engines():
    release = threading.Event()
    processed: list[str] = []

    def process(job_id: str) -> None:
        if job_id.startswith("hot"):
            release.wait(2.0)
        processed.append(job_id)

    dispatcher = JobDispatcher(
        resolve_engine=lambda job_id: job_id.split(":")[0],
        slots_for=lambda _engine_id: 1,
        process=process,
        max_parallel=9,
    )
    dispatcher.start()
    try:
        dispatcher.submit("hot:1")
        assert wait_until(lambda: dispatcher.running_by_engine().get("hot") == 1)
        dispatcher.submit("hot:2")
        dispatcher.submit("free:1")
        assert wait_until(lambda: "free:1" in processed, timeout=2)
        assert "hot:2" not in processed
        assert dispatcher.pending_count() == 1
        release.set()
        assert wait_until(lambda: len(processed) == 3, timeout=3)
    finally:
        release.set()
        dispatcher.stop()


def test_unresolvable_jobs_are_dropped():
    processed: list[str] = []

    def resolve(job_id: str) -> str | None:
        return None if job_id.startswith("gone") else "a"

    dispatcher = JobDispatcher(
        resolve_engine=resolve,
        slots_for=lambda _engine: 1,
        process=processed.append,
        max_parallel=4,
    )
    dispatcher.start()
    try:
        dispatcher.submit("gone:1")
        assert wait_until(lambda: dispatcher.pending_count() == 0, timeout=2)
        assert processed == []
    finally:
        dispatcher.stop()


def test_submit_is_idempotent_and_forget_removes_pending():
    dispatcher, _state, release, processed = collect_dispatcher(
        {"a": 1}, max_parallel=4
    )
    dispatcher.start()
    try:
        dispatcher.submit("a:1")
        dispatcher.submit("a:2")
        dispatcher.submit("a:2")
        dispatcher.submit("a:2")
        assert wait_until(lambda: dispatcher.running_count() == 1)
        assert dispatcher.pending_count() == 1
        dispatcher.forget("a:2")
        assert dispatcher.pending_count() == 0
        release.set()
        assert wait_until(lambda: processed == ["a:1"], timeout=3)
    finally:
        release.set()
        dispatcher.stop()


def test_busy_reports_pending_and_running():
    dispatcher, _state, release, _processed = collect_dispatcher(
        {"a": 1}, max_parallel=4
    )
    assert dispatcher.busy is False
    dispatcher.start()
    try:
        dispatcher.submit("a:1")
        assert wait_until(lambda: dispatcher.running_by_engine().get("a") == 1)
        assert dispatcher.busy is True
        release.set()
        assert wait_until(lambda: dispatcher.busy is False, timeout=3)
    finally:
        release.set()
        dispatcher.stop()
