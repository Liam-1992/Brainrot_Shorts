from __future__ import annotations

import os
import signal
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

_MANAGER = None


@dataclass
class ProcessInfo:
    pid: int
    args: List[str]
    started_at: float
    timeout: float
    job_id: Optional[str]


class SubprocessManager:
    def __init__(self, default_timeout: float) -> None:
        self.default_timeout = default_timeout
        self._lock = threading.Lock()
        self._processes: Dict[str, List[ProcessInfo]] = {}

    def run(self, args: List[str], job_id: Optional[str] = None, timeout: Optional[float] = None) -> subprocess.CompletedProcess:
        timeout = timeout if timeout is not None else self.default_timeout
        start = time.time()
        creationflags = 0
        preexec = None
        if os.name == "nt":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
        else:
            preexec = os.setsid

        process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=creationflags,
            preexec_fn=preexec,
        )

        info = ProcessInfo(
            pid=process.pid,
            args=args,
            started_at=start,
            timeout=timeout,
            job_id=job_id,
        )
        if job_id:
            with self._lock:
                self._processes.setdefault(job_id, []).append(info)

        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            self._kill_process(process.pid)
            raise RuntimeError(f"Subprocess timed out after {timeout:.0f}s: {args}")
        finally:
            if job_id:
                with self._lock:
                    active = self._processes.get(job_id, [])
                    self._processes[job_id] = [p for p in active if p.pid != process.pid]
                    if not self._processes[job_id]:
                        self._processes.pop(job_id, None)

        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, args, output=stdout, stderr=stderr)

        return subprocess.CompletedProcess(args, process.returncode, stdout, stderr)

    def cancel_job(self, job_id: str) -> int:
        with self._lock:
            processes = list(self._processes.get(job_id, []))
        killed = 0
        for proc in processes:
            if self._kill_pid(proc.pid):
                killed += 1
        with self._lock:
            self._processes.pop(job_id, None)
        return killed

    def _kill_pid(self, pid: int) -> bool:
        try:
            self._kill_process(pid)
            return True
        except Exception:
            return False

    def _kill_process(self, pid: int) -> None:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                text=True,
            )
        else:
            os.killpg(pid, signal.SIGKILL)


def init_manager(default_timeout: float) -> None:
    global _MANAGER
    _MANAGER = SubprocessManager(default_timeout)


def get_manager() -> SubprocessManager | None:
    return _MANAGER
