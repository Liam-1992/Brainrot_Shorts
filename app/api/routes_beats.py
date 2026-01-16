from __future__ import annotations

import json
from typing import Callable, Dict

from fastapi import APIRouter, HTTPException

from ..beats_editor import get_beats, update_beats
from ..models import BeatsResponse, BeatsUpdate, GenerateResponse, RenderFromBeatsRequest

router = APIRouter()

_context: Dict[str, object] = {}


def init_context(settings, enqueue_job: Callable, jobs: dict) -> None:
    _context["settings"] = settings
    _context["enqueue_job"] = enqueue_job
    _context["jobs"] = jobs


@router.get("/projects/{job_id}/beats", response_model=BeatsResponse)
def project_beats(job_id: str) -> BeatsResponse:
    settings = _context["settings"]
    beats, voiceover, hook, title = get_beats(settings, job_id)
    return BeatsResponse(beats=beats, full_voiceover_text=voiceover, hook=hook, title=title)


@router.put("/projects/{job_id}/beats", response_model=BeatsResponse)
def update_project_beats(job_id: str, payload: BeatsUpdate) -> BeatsResponse:
    settings = _context["settings"]
    voiceover = update_beats(settings, job_id, payload.beats, payload.hook, payload.title)
    return BeatsResponse(beats=payload.beats, full_voiceover_text=voiceover)


@router.post("/projects/{job_id}/render_from_beats", response_model=GenerateResponse)
def render_from_beats(job_id: str, payload: RenderFromBeatsRequest) -> GenerateResponse:
    settings = _context["settings"]
    enqueue_job = _context["enqueue_job"]
    jobs = _context["jobs"]

    request_path = settings.OUTPUTS_DIR / job_id / "request.json"
    if not request_path.exists():
        raise HTTPException(status_code=404, detail="request.json not found")
    try:
        request_data = json.loads(request_path.read_text(encoding="utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request.json")

    request_data["preview_mode"] = payload.preview_mode
    request_data["preview_start"] = payload.preview_start
    request_data["preview_duration"] = payload.preview_duration
    request_data["render_mode"] = "preview" if payload.preview_mode else "final"

    steps = []
    if payload.regenerate_voice:
        steps.append("voice")
    if payload.regenerate_captions:
        steps.append("captions")
    if payload.regenerate_render:
        steps.append("render")
    if not steps:
        steps.append("render")

    job_state = jobs.get(job_id)
    if not job_state:
        job_state = {"status": "queued", "progress": 0, "logs": []}
        jobs[job_id] = job_state

    enqueue_job(request_data, job_id, steps=steps, save_request=False, create_project=False)
    return GenerateResponse(job_id=job_id)
