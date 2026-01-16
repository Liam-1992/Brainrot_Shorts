from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from .db import get_connection


class ProjectManager:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def create_project(
        self,
        job_id: str,
        prompt: str,
        style: str,
        status: str,
        duration: float,
        voice: str,
        preset_name: str | None,
        group_id: str | None = None,
        variant_name: str | None = None,
    ) -> None:
        created_at = datetime.utcnow().isoformat()
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO projects
                (job_id, prompt, style, created_at, status, duration, voice, preset_name, group_id, variant_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    prompt,
                    style,
                    created_at,
                    status,
                    duration,
                    voice,
                    preset_name,
                    group_id,
                    variant_name,
                ),
            )
            conn.commit()

    def update_status(
        self,
        job_id: str,
        status: str,
        final_path: str | None = None,
        title: str | None = None,
        thumb_path: str | None = None,
        thumb_styled_path: str | None = None,
    ) -> None:
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                UPDATE projects
                SET status = ?,
                    final_path = COALESCE(?, final_path),
                    title = COALESCE(?, title),
                    thumb_path = COALESCE(?, thumb_path),
                    thumb_styled_path = COALESCE(?, thumb_styled_path)
                WHERE job_id = ?
                """,
                (status, final_path, title, thumb_path, thumb_styled_path, job_id),
            )
            conn.commit()

    def list_projects(self, limit: int, offset: int) -> List[Dict[str, Any]]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT job_id, prompt, style, created_at, status, final_path, duration, voice,
                       preset_name, title, thumb_path, thumb_styled_path, group_id, variant_name
                FROM projects
                ORDER BY datetime(created_at) DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_project(self, job_id: str) -> Dict[str, Any] | None:
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT job_id, prompt, style, created_at, status, final_path, duration, voice,
                       preset_name, title, thumb_path, thumb_styled_path, group_id, variant_name
                FROM projects
                WHERE job_id = ?
                """,
                (job_id,),
            ).fetchone()
        return dict(row) if row else None
