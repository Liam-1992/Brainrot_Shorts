from __future__ import annotations

from typing import Dict

from fastapi import APIRouter, HTTPException

from ..virality_report import build_report

router = APIRouter()
_context: Dict[str, object] = {}


def init_context(settings) -> None:
    _context["settings"] = settings


@router.post("/projects/{job_id}/export_virality_report")
def export_virality_report(job_id: str) -> Dict:
    settings = _context["settings"]
    job_dir = settings.OUTPUTS_DIR / job_id
    if not job_dir.exists():
        raise HTTPException(status_code=404, detail="Job not found")
    try:
        path = build_report(settings, job_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True, "path": f"/outputs/{job_id}/{path.name}"}
