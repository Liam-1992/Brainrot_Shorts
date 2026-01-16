from __future__ import annotations

import json
from typing import Dict

from fastapi import APIRouter

from ..virality_score import compute_virality_score

router = APIRouter()
_context: Dict[str, object] = {}


def init_context(settings) -> None:
    _context["settings"] = settings


@router.get("/projects/{job_id}/virality_score")
def virality_score(job_id: str) -> Dict:
    settings = _context["settings"]
    path = settings.OUTPUTS_DIR / job_id / "virality_score.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return compute_virality_score(settings, job_id)
    return compute_virality_score(settings, job_id)
