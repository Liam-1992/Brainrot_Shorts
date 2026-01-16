from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List

from .db import get_connection
from .models import ScriptBeat


def _beats_table_payload(beats: List[ScriptBeat]) -> str:
    return json.dumps([beat.model_dump() for beat in beats])


def _voiceover_from_beats(beats: List[ScriptBeat]) -> str:
    return " ".join(beat.text for beat in beats if beat.text).strip()


def get_beats(settings, job_id: str) -> tuple[List[ScriptBeat], str, str | None, str | None]:
    script_path = settings.OUTPUTS_DIR / job_id / "script.json"
    hook = None
    title = None

    with get_connection(settings.DB_PATH) as conn:
        row = conn.execute(
            "SELECT beats_json, voiceover_text FROM beats WHERE job_id = ?",
            (job_id,),
        ).fetchone()
        if row and row["beats_json"]:
            beats = [ScriptBeat(**item) for item in json.loads(row["beats_json"])]
            voiceover = row["voiceover_text"] or _voiceover_from_beats(beats)
            if script_path.exists():
                try:
                    script = json.loads(script_path.read_text(encoding="utf-8"))
                    hook = script.get("hook")
                    title = script.get("title")
                except Exception:
                    pass
            return beats, voiceover, hook, title

    if not script_path.exists():
        return [], "", None, None

    script = json.loads(script_path.read_text(encoding="utf-8"))
    hook = script.get("hook")
    title = script.get("title")
    beats_raw = script.get("beats", [])
    beats = [ScriptBeat(**beat) for beat in beats_raw]
    voiceover = script.get("full_voiceover_text") or _voiceover_from_beats(beats)
    return beats, voiceover, hook, title


def update_beats(settings, job_id: str, beats: List[ScriptBeat], hook: str | None = None, title: str | None = None) -> str:
    voiceover = _voiceover_from_beats(beats)
    script_path = settings.OUTPUTS_DIR / job_id / "script.json"
    script = {}
    if script_path.exists():
        try:
            script = json.loads(script_path.read_text(encoding="utf-8"))
        except Exception:
            script = {}

    script["beats"] = [beat.model_dump() for beat in beats]
    script["full_voiceover_text"] = voiceover
    if hook is not None:
        script["hook"] = hook
    if title is not None:
        script["title"] = title
    if script_path.parent.exists():
        script_path.write_text(json.dumps(script, indent=2), encoding="utf-8")

    with get_connection(settings.DB_PATH) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO beats (job_id, beats_json, voiceover_text, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (job_id, _beats_table_payload(beats), voiceover, datetime.utcnow().isoformat()),
        )
        conn.commit()

    return voiceover


def save_initial_beats(settings, job_id: str, beats: List[ScriptBeat], voiceover_text: str) -> None:
    with get_connection(settings.DB_PATH) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO beats (job_id, beats_json, voiceover_text, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (job_id, _beats_table_payload(beats), voiceover_text, datetime.utcnow().isoformat()),
        )
        conn.commit()
