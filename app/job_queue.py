from __future__ import annotations

import queue
import threading
from typing import Callable, Tuple


class JobQueue:
    def __init__(self, max_workers: int):
        self.max_workers = max(1, max_workers)
        self._queue: queue.Queue[Tuple[str, Callable[[], None], dict] | None] = queue.Queue()
        self._threads: list[threading.Thread] = []
        self._running = False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        for index in range(self.max_workers):
            thread = threading.Thread(target=self._worker, name=f"job-worker-{index}", daemon=True)
            thread.start()
            self._threads.append(thread)

    def stop(self) -> None:
        self._running = False
        for _ in self._threads:
            self._queue.put(None)

    def enqueue(self, job_id: str, fn: Callable[[], None], job_state: dict) -> None:
        job_state["status"] = "queued"
        self._queue.put((job_id, fn, job_state))

    def _worker(self) -> None:
        while True:
            item = self._queue.get()
            if item is None:
                self._queue.task_done()
                break
            job_id, fn, job_state = item
            job_state["status"] = "running"
            try:
                if job_state.get("cancelled"):
                    job_state["status"] = "error"
                    job_state["logs"].append("ERROR: Job cancelled before start.")
                    continue
                fn()
            except Exception as exc:
                job_state["status"] = "error"
                job_state["logs"].append(f"ERROR: {exc}")
            finally:
                self._queue.task_done()
