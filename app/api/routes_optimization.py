from __future__ import annotations

from typing import Dict

from fastapi import APIRouter

from ..optimization import load_attempts

router = APIRouter()
_context: Dict[str, object] = {}


def init_context(settings) -> None:
    _context["settings"] = settings


@router.get("/projects/{job_id}/optimization")
def optimization_history(job_id: str) -> Dict:
    settings = _context["settings"]
    return load_attempts(settings, job_id)
