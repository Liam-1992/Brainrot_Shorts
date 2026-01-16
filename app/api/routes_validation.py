from __future__ import annotations

import json
from typing import Dict

from fastapi import APIRouter, HTTPException

from ..captions_report import build_report

router = APIRouter()
_context: Dict[str, object] = {}


def init_context(settings) -> None:
    _context["settings"] = settings


@router.get("/projects/{job_id}/validation")
def project_validation(job_id: str) -> Dict:
    settings = _context["settings"]
    path = settings.OUTPUTS_DIR / job_id / "validation.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="validation.json not found")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid validation.json")


@router.get("/projects/{job_id}/caption_report")
def caption_report(job_id: str) -> Dict:
    settings = _context["settings"]
    report_path = settings.OUTPUTS_DIR / job_id / "caption_report.json"
    if report_path.exists():
        try:
            return json.loads(report_path.read_text(encoding="utf-8"))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid caption_report.json")
    return build_report(settings, job_id)
