from __future__ import annotations

import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Dict, List

from ..db import get_connection
from ..models import GenerateRequest
from ..utils import append_log, generate_job_id
from .scheduler_reports import finish_run, list_runs, start_run
from .watch_folder import get_last_scan, scan_watch_folder


def create_schedule(
    settings,
    schedule_type: str,
    daily_count: int,
    preset_name: str | None,
    source_path: str,
) -> str:
    schedule_id = generate_job_id()
    with get_connection(settings.DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO schedules (schedule_id, type, daily_count, preset_name, source_path, enabled, last_run, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                schedule_id,
                schedule_type,
                daily_count,
                preset_name,
                source_path,
                1,
                None,
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
    return schedule_id


def list_schedules(settings) -> List[Dict[str, object]]:
    with get_connection(settings.DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT schedule_id, type, daily_count, preset_name, source_path, enabled, last_run, created_at
            FROM schedules
            ORDER BY datetime(created_at) DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_scheduler_status(settings) -> Dict[str, object]:
    with get_connection(settings.DB_PATH) as conn:
        row = conn.execute(
            "SELECT value FROM automation_state WHERE key = ?",
            ("scheduler_last_tick",),
        ).fetchone()
    return {
        "last_tick": row["value"] if row else None,
        "schedule_count": len(list_schedules(settings)),
        "recent_runs": list_runs(settings, limit=5),
    }


def run_scheduler(
    settings,
    enqueue_fn: Callable[[GenerateRequest, str], None],
    interval_seconds: int = 30,
) -> None:
    log_path = settings.OUTPUTS_DIR / "scheduler.log"
    append_log(log_path, f"Scheduler started at {datetime.utcnow().isoformat()}")
    while True:
        report = start_run(settings)
        try:
            _update_scheduler_tick(settings)
            _run_schedules(settings, enqueue_fn, log_path, report)
            if settings.WATCH_FOLDER_ENABLED:
                if _should_scan(get_last_scan(settings)):
                    scan_watch_folder(settings, enqueue_fn)
        except Exception as exc:
            append_log(log_path, f"Scheduler error: {exc}")
            report.setdefault("errors", []).append(str(exc))
        finally:
            finish_run(settings, report)
        time.sleep(interval_seconds)


def _run_schedules(
    settings,
    enqueue_fn: Callable[[GenerateRequest, str], None],
    log_path: Path,
    report: Dict[str, object] | None = None,
) -> None:
    schedules = list_schedules(settings)
    for schedule in schedules:
        if not schedule.get("enabled"):
            continue
        schedule_type = schedule.get("type")
        if schedule_type != "daily":
            continue
        last_run = schedule.get("last_run")
        should_run = True
        if last_run:
            try:
                last = datetime.fromisoformat(last_run)
                should_run = datetime.utcnow() - last >= timedelta(hours=24)
            except Exception:
                should_run = True
        if not should_run:
            continue
        source_path = schedule.get("source_path") or ""
        prompts = _load_prompts(Path(source_path))
        if not prompts:
            append_log(log_path, f"No prompts found for schedule {schedule['schedule_id']}")
            _update_last_run(settings, schedule["schedule_id"])
            continue
        daily_count = int(schedule.get("daily_count") or 0)
        for prompt in prompts[:daily_count]:
            req = GenerateRequest(topic_prompt=prompt, preset_name=schedule.get("preset_name"))
            job_id = generate_job_id()
            enqueue_fn(req, job_id)
            append_log(log_path, f"Scheduled job {job_id} from {schedule['schedule_id']}")
            if report is not None:
                report.setdefault("job_ids", []).append(job_id)
        _update_last_run(settings, schedule["schedule_id"])
        if report is not None:
            report.setdefault("tasks", []).append(
                {"schedule_id": schedule["schedule_id"], "count": daily_count}
            )


def dry_run(settings) -> Dict[str, object]:
    schedules = list_schedules(settings)
    tasks = []
    total_jobs = 0
    for schedule in schedules:
        if not schedule.get("enabled"):
            continue
        schedule_type = schedule.get("type")
        if schedule_type != "daily":
            continue
        source_path = schedule.get("source_path") or ""
        prompts = _load_prompts(Path(source_path))
        daily_count = int(schedule.get("daily_count") or 0)
        planned = prompts[:daily_count]
        tasks.append(
            {
                "schedule_id": schedule.get("schedule_id"),
                "preset_name": schedule.get("preset_name"),
                "count": len(planned),
                "prompts_preview": planned[:3],
            }
        )
        total_jobs += len(planned)
    return {"total_jobs": total_jobs, "tasks": tasks}


def _load_prompts(path: Path) -> List[str]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".csv":
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if lines and "prompt" in lines[0].lower():
            lines = lines[1:]
        prompts = []
        for line in lines:
            prompt = line.split(",")[0].strip()
            if prompt:
                prompts.append(prompt)
        return prompts
    return [line.strip() for line in text.splitlines() if line.strip()]


def _update_last_run(settings, schedule_id: str) -> None:
    with get_connection(settings.DB_PATH) as conn:
        conn.execute(
            "UPDATE schedules SET last_run = ? WHERE schedule_id = ?",
            (datetime.utcnow().isoformat(), schedule_id),
        )
        conn.commit()


def _update_scheduler_tick(settings) -> None:
    now = datetime.utcnow().isoformat()
    with get_connection(settings.DB_PATH) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO automation_state (key, value, updated_at)
            VALUES (?, ?, ?)
            """,
            ("scheduler_last_tick", now, now),
        )
        conn.commit()


def _should_scan(last_scan: str | None) -> bool:
    if not last_scan:
        return True
    try:
        last = datetime.fromisoformat(last_scan)
    except Exception:
        return True
    return datetime.utcnow() - last >= timedelta(hours=1)
