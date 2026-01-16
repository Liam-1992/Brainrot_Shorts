from __future__ import annotations

import json
from datetime import datetime
from typing import List

from ..db import get_connection
from ..utils import generate_job_id


def create_pending(settings, source_file: str, prompts: List[str], overrides: dict | None = None) -> str:
    batch_id = generate_job_id()
    payload = {"prompts": prompts, "overrides": overrides or {}}
    with get_connection(settings.DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO watch_pending (batch_id, source_file, prompts_json, created_at, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (batch_id, source_file, json.dumps(payload), datetime.utcnow().isoformat(), "pending"),
        )
        conn.commit()
    return batch_id


def list_pending(settings) -> List[dict]:
    with get_connection(settings.DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT batch_id, source_file, prompts_json, created_at, status
            FROM watch_pending
            WHERE status = 'pending'
            ORDER BY datetime(created_at) DESC
            """
        ).fetchall()
    items = []
    for row in rows:
        try:
            payload = json.loads(row["prompts_json"])
        except Exception:
            payload = {}
        prompts = payload.get("prompts", []) if isinstance(payload, dict) else payload
        overrides = payload.get("overrides", {}) if isinstance(payload, dict) else {}
        items.append(
            {
                "batch_id": row["batch_id"],
                "source_file": row["source_file"],
                "created_at": row["created_at"],
                "status": row["status"],
                "prompts": prompts,
                "overrides": overrides,
            }
        )
    return items


def approve_pending(settings, batch_id: str) -> tuple[List[str], dict]:
    with get_connection(settings.DB_PATH) as conn:
        row = conn.execute(
            "SELECT prompts_json FROM watch_pending WHERE batch_id = ? AND status = 'pending'",
            (batch_id,),
        ).fetchone()
        if not row:
            return [], {}
        conn.execute(
            "UPDATE watch_pending SET status = ? WHERE batch_id = ?",
            ("approved", batch_id),
        )
        conn.commit()
    try:
        payload = json.loads(row["prompts_json"])
        if isinstance(payload, dict):
            return payload.get("prompts", []), payload.get("overrides", {}) or {}
        return payload, {}
    except Exception:
        return [], {}


def delete_pending(settings, batch_id: str) -> None:
    with get_connection(settings.DB_PATH) as conn:
        conn.execute(
            "UPDATE watch_pending SET status = ? WHERE batch_id = ?",
            ("deleted", batch_id),
        )
        conn.commit()
