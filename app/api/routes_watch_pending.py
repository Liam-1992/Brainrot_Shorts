from __future__ import annotations

from typing import Dict

from fastapi import APIRouter

from ..automation.watch_pending import approve_pending, delete_pending, list_pending
from ..models import GenerateRequest
from ..utils import generate_job_id

router = APIRouter()
_context: Dict[str, object] = {}


def init_context(settings, enqueue_fn) -> None:
    _context["settings"] = settings
    _context["enqueue_fn"] = enqueue_fn


@router.get("/watch_folder/pending")
def watch_pending_list() -> Dict:
    settings = _context["settings"]
    return {"pending": list_pending(settings)}


@router.post("/watch_folder/pending/{batch_id}/approve")
def watch_pending_approve(batch_id: str, payload: Dict | None = None) -> Dict:
    settings = _context["settings"]
    enqueue_fn = _context["enqueue_fn"]
    preset_name = payload.get("preset_name") if payload else None
    prompts, overrides = approve_pending(settings, batch_id)
    job_ids = []
    for prompt in prompts:
        req = GenerateRequest(topic_prompt=prompt, preset_name=preset_name, **overrides)
        job_id = generate_job_id()
        enqueue_fn(req, job_id)
        job_ids.append(job_id)
    return {"ok": True, "job_ids": job_ids}


@router.delete("/watch_folder/pending/{batch_id}")
def watch_pending_delete(batch_id: str) -> Dict:
    settings = _context["settings"]
    delete_pending(settings, batch_id)
    return {"ok": True}
