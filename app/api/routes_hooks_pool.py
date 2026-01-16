from __future__ import annotations

from typing import Dict

from fastapi import APIRouter, HTTPException

from ..generation_strategy import load_hook_pool

router = APIRouter()
_context: Dict[str, object] = {}


def init_context(settings) -> None:
    _context["settings"] = settings


@router.get("/projects/{job_id}/hooks")
def hook_pool(job_id: str) -> Dict:
    settings = _context["settings"]
    job_dir = settings.OUTPUTS_DIR / job_id
    data = load_hook_pool(settings, job_id, job_dir)
    if not data:
        raise HTTPException(status_code=404, detail="hooks.json not found")
    return data
