from __future__ import annotations

from typing import Dict

from fastapi import APIRouter

from ..automation.scheduler import dry_run
from ..automation.scheduler_reports import list_runs

router = APIRouter()
_context: Dict[str, object] = {}


def init_context(settings) -> None:
    _context["settings"] = settings


@router.post("/scheduler/dry_run")
def scheduler_dry_run() -> Dict:
    settings = _context["settings"]
    return dry_run(settings)


@router.get("/scheduler/runs")
def scheduler_runs() -> Dict:
    settings = _context["settings"]
    return {"runs": list_runs(settings, limit=5)}
