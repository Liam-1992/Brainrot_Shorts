from __future__ import annotations

import json
from datetime import datetime

from ..db import get_connection
from ..utils import generate_job_id


def start_run(settings) -> dict:
    run_id = generate_job_id()
    started_at = datetime.utcnow().isoformat()
    return {
        "run_id": run_id,
        "started_at": started_at,
        "tasks": [],
        "job_ids": [],
        "errors": [],
    }


def finish_run(settings, report: dict) -> dict:
    finished_at = datetime.utcnow().isoformat()
    payload = {
        "run_id": report.get("run_id"),
        "started_at": report.get("started_at"),
        "finished_at": finished_at,
        "tasks": report.get("tasks", []),
        "job_ids": report.get("job_ids", []),
        "errors": report.get("errors", []),
    }
    with get_connection(settings.DB_PATH) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO scheduler_runs (run_id, started_at, finished_at, report_json)
            VALUES (?, ?, ?, ?)
            """,
            (
                payload["run_id"],
                payload["started_at"],
                payload["finished_at"],
                json.dumps(payload),
            ),
        )
        conn.commit()
    return payload


def list_runs(settings, limit: int = 5) -> list[dict]:
    with get_connection(settings.DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT report_json
            FROM scheduler_runs
            ORDER BY datetime(started_at) DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    reports = []
    for row in rows:
        try:
            reports.append(json.loads(row["report_json"]))
        except Exception:
            continue
    return reports
