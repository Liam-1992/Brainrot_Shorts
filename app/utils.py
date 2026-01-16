from __future__ import annotations

import json
import subprocess
import uuid
from pathlib import Path
from typing import List


def generate_job_id() -> str:
    return uuid.uuid4().hex[:12]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def append_log(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line.rstrip() + "\n")


def run_subprocess(
    args: List[str],
    job_id: str | None = None,
    timeout: float | None = None,
) -> subprocess.CompletedProcess:
    try:
        from .subprocess_manager import get_manager
    except Exception:
        get_manager = None

    if get_manager:
        manager = get_manager()
        if manager:
            return manager.run(args, job_id=job_id, timeout=timeout)

    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        check=True,
        timeout=timeout,
    )


def ffmpeg_filter_path(path: Path) -> str:
    raw = str(path).replace("\\", "/")
    return raw.replace(":", "\\:")


def get_media_duration(path: Path, ffprobe_path: str) -> float:
    args = [
        ffprobe_path,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    result = run_subprocess(args)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))
