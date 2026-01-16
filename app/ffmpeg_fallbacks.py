from __future__ import annotations

from typing import Callable, Iterable, Tuple


def run_attempts(
    attempts: Iterable[Tuple[str, Callable[[], None]]],
    log_cb: Callable[[str], None] | None = None,
) -> str:
    last_error: Exception | None = None
    for name, fn in attempts:
        try:
            if log_cb:
                log_cb(f"FFmpeg attempt: {name}")
            fn()
            if log_cb:
                log_cb(f"FFmpeg attempt succeeded: {name}")
            return name
        except Exception as exc:
            last_error = exc
            if log_cb:
                log_cb(f"FFmpeg attempt failed ({name}): {exc}")
            continue
    raise RuntimeError(f"All FFmpeg fallback attempts failed: {last_error}")
