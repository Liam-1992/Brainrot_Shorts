from __future__ import annotations

import json
from typing import Dict

from fastapi import APIRouter, HTTPException

from ..captions_autofix import autofix_captions

router = APIRouter()
_context: Dict[str, object] = {}


def init_context(settings, plugin_manager) -> None:
    _context["settings"] = settings
    _context["plugin_manager"] = plugin_manager


@router.post("/projects/{job_id}/captions/autofix")
def captions_autofix(job_id: str, payload: Dict | None = None) -> Dict:
    settings = _context["settings"]
    plugin_manager = _context["plugin_manager"]
    job_dir = settings.OUTPUTS_DIR / job_id
    request_path = job_dir / "request.json"
    if not request_path.exists():
        raise HTTPException(status_code=404, detail="request.json not found")
    try:
        request = json.loads(request_path.read_text(encoding="utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request.json")
    if payload:
        request.update(payload)
    result = autofix_captions(
        settings,
        job_id,
        request.get("caption_style", "tiktok_pop"),
        plugin_manager,
        request.get("caption_autofix_mode", "group"),
        float(request.get("max_words_per_second", 4.0)),
        int(request.get("max_chars_per_line", 18)),
        float(request.get("min_caption_duration", 0.55)),
    )
    return {"ok": True, "result": result}
