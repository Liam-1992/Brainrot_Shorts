from __future__ import annotations

from typing import Dict

from fastapi import APIRouter

from ..metrics import compute_metrics, score_hook
from ..models import HookScoreRequest, HookScoreResponse, MetricsResponse

router = APIRouter()
_context: Dict[str, object] = {}


def init_context(settings) -> None:
    _context["settings"] = settings


@router.post("/score_hook", response_model=HookScoreResponse)
def score_hook_endpoint(payload: HookScoreRequest) -> HookScoreResponse:
    score, reasons = score_hook(payload.hook_text)
    return HookScoreResponse(score=score, reasons=reasons)


@router.get("/projects/{job_id}/metrics", response_model=MetricsResponse)
def project_metrics(job_id: str) -> MetricsResponse:
    settings = _context["settings"]
    data = compute_metrics(settings, job_id)
    return MetricsResponse(**data)
