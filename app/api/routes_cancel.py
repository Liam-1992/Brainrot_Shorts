from __future__ import annotations

from typing import Dict

from fastapi import APIRouter, HTTPException

from ..subprocess_manager import get_manager

router = APIRouter()
_context: Dict[str, object] = {}


def init_context(settings, jobs: dict, project_manager) -> None:
    _context["settings"] = settings
    _context["jobs"] = jobs
    _context["project_manager"] = project_manager


@router.post("/cancel/{job_id}")
def cancel_job(job_id: str) -> Dict:
    jobs = _context["jobs"]
    project_manager = _context["project_manager"]
    job_state = jobs.get(job_id)
    if not job_state:
        raise HTTPException(status_code=404, detail="Job not found")
    job_state["cancelled"] = True
    job_state["status"] = "error"
    job_state.setdefault("logs", []).append("ERROR: Job cancelled by user.")

    killed = 0
    manager = get_manager()
    if manager:
        killed = manager.cancel_job(job_id)

    project_manager.update_status(job_id, "error")
    return {"ok": True, "killed": killed}
