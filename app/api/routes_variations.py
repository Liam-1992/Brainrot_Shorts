from __future__ import annotations

import random
from typing import Callable, Dict

from fastapi import APIRouter

from ..utils import generate_job_id
from ..models import (
    ABGenerateRequest,
    ABGenerateResponse,
    GenerateRequest,
    GenerateVariationsRequest,
    GenerateVariationsResponse,
    GenerateVariantsRequest,
    GenerateVariantsResponse,
    RewriteHookRequest,
    RewriteHookResponse,
)
from ..variations import build_variation_requests, generate_variants, rewrite_hook

router = APIRouter()
_context: Dict[str, object] = {}


def init_context(settings, preset_manager, enqueue_job: Callable, jobs: dict) -> None:
    _context["settings"] = settings
    _context["preset_manager"] = preset_manager
    _context["enqueue_job"] = enqueue_job
    _context["jobs"] = jobs


def _apply_preset(preset_manager, req: GenerateRequest) -> GenerateRequest:
    if not req.preset_name:
        return req
    preset = preset_manager.get(req.preset_name)
    if not preset:
        return req
    merged = req.model_dump()
    for key, value in preset.items():
        if key in merged:
            merged[key] = value
    return GenerateRequest(**merged)


@router.post("/generate_variations", response_model=GenerateVariationsResponse)
def generate_variations(payload: GenerateVariationsRequest) -> GenerateVariationsResponse:
    settings = _context["settings"]
    preset_manager = _context["preset_manager"]
    enqueue_job = _context["enqueue_job"]
    jobs = _context["jobs"]

    base_req = GenerateRequest(topic_prompt=payload.topic_prompt, preset_name=payload.preset_name)
    base_req = _apply_preset(preset_manager, base_req)
    variations = build_variation_requests(settings, base_req, payload.count)

    group_id = f"var-{random.randint(1000, 9999)}"
    job_ids = []
    for idx, req in enumerate(variations, start=1):
        job_id = generate_job_id()
        job_state = {"status": "queued", "progress": 0, "logs": []}
        jobs[job_id] = job_state
        enqueue_job(req, job_id, group_id=group_id, variant_name=f"var-{idx}")
        job_ids.append(job_id)

    return GenerateVariationsResponse(job_ids=job_ids)


@router.post("/generate_variants", response_model=GenerateVariantsResponse)
def generate_variant_lists(payload: GenerateVariantsRequest) -> GenerateVariantsResponse:
    settings = _context["settings"]
    data = generate_variants(
        settings,
        payload.topic_prompt,
        payload.style,
        payload.num_hooks,
        payload.num_titles,
        payload.pick,
    )
    return GenerateVariantsResponse(**data)


@router.post("/rewrite_hook", response_model=RewriteHookResponse)
def rewrite_hook_endpoint(payload: RewriteHookRequest) -> RewriteHookResponse:
    settings = _context["settings"]
    candidates = rewrite_hook(settings, payload.hook_text, payload.style)
    return RewriteHookResponse(candidates=candidates)


@router.post("/ab_generate", response_model=ABGenerateResponse)
def ab_generate(payload: ABGenerateRequest) -> ABGenerateResponse:
    settings = _context["settings"]
    preset_manager = _context["preset_manager"]
    enqueue_job = _context["enqueue_job"]
    jobs = _context["jobs"]

    base_req = GenerateRequest(topic_prompt=payload.topic_prompt, preset_name=payload.preset_name)
    base_req = _apply_preset(preset_manager, base_req)

    group_id = f"ab-{random.randint(1000, 9999)}"
    job_ids = []
    for variant in payload.variants:
        merged = base_req.model_dump()
        merged.update(variant.overrides or {})
        req = GenerateRequest(**merged)
        job_id = generate_job_id()
        job_state = {"status": "queued", "progress": 0, "logs": []}
        jobs[job_id] = job_state
        enqueue_job(req, job_id, group_id=group_id, variant_name=variant.name)
        job_ids.append(job_id)

    return ABGenerateResponse(job_ids=job_ids)
