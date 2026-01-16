from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List

from ..db import get_connection
from ..models import GenerateRequest
from ..utils import generate_job_id
from .watch_pending import create_pending


def scan_watch_folder(
    settings,
    enqueue_fn: Callable[[GenerateRequest, str], None],
    preset_name: str | None = None,
    approve_mode: bool = False,
) -> Dict[str, object]:
    watch_path = settings.WATCH_FOLDER_PATH
    if not watch_path or not watch_path.exists():
        return {"ok": False, "error": "WATCH_FOLDER_PATH not configured"}

    processed_dir = watch_path / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    results = {"ok": True, "jobs": [], "processed": [], "errors": []}

    for file_path in sorted(watch_path.glob("*.txt")) + sorted(watch_path.glob("*.json")):
        try:
            prompts, overrides = _load_prompts(file_path)
            if approve_mode:
                batch_id = create_pending(settings, file_path.name, prompts, overrides=overrides)
                results.setdefault("pending_batches", []).append(batch_id)
            else:
                for prompt in prompts:
                    req = GenerateRequest(topic_prompt=prompt, preset_name=preset_name, **overrides)
                    job_id = generate_job_id()
                    enqueue_fn(req, job_id)
                    results["jobs"].append(job_id)
            _archive_file(file_path, processed_dir)
            results["processed"].append(file_path.name)
        except Exception as exc:
            results["errors"].append(f"{file_path.name}: {exc}")

    _update_last_scan(settings)
    return results


def get_last_scan(settings) -> str | None:
    with get_connection(settings.DB_PATH) as conn:
        row = conn.execute(
            "SELECT value FROM automation_state WHERE key = ?",
            ("watch_folder_last_scan",),
        ).fetchone()
    return row["value"] if row else None


def _load_prompts(path: Path) -> tuple[List[str], dict]:
    overrides: dict = {}
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            prompts = payload.get("prompts") or []
            overrides = payload.get("overrides") or {}
            return [str(p).strip() for p in prompts if str(p).strip()], overrides
    text = path.read_text(encoding="utf-8")
    prompts = [line.strip() for line in text.splitlines() if line.strip()]
    return prompts, overrides


def _archive_file(path: Path, processed_dir: Path) -> None:
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    target = processed_dir / f"{path.stem}_{timestamp}{path.suffix}"
    path.replace(target)


def _update_last_scan(settings) -> None:
    now = datetime.utcnow().isoformat()
    with get_connection(settings.DB_PATH) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO automation_state (key, value, updated_at)
            VALUES (?, ?, ?)
            """,
            ("watch_folder_last_scan", now, now),
        )
        conn.commit()
