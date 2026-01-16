from __future__ import annotations

from typing import Dict

from fastapi import APIRouter, HTTPException

from ..hooks_pool import generate_hooks, score_hooks, select_top
from ..model_ops.benchmarks import list_benchmarks
from ..model_ops.registry import load_registry
from ..model_ops.routing import get_routing_config, pick_model_paths

router = APIRouter()
_context: Dict[str, object] = {}


def init_context(settings) -> None:
    _context["settings"] = settings


@router.post("/generate_hooks")
def generate_hooks_endpoint(payload: Dict) -> Dict:
    settings = _context["settings"]
    topic_prompt = str(payload.get("topic_prompt", "")).strip()
    style = str(payload.get("style", "")).strip() or "brainrot_facts"
    count = int(payload.get("count", 10))
    if not topic_prompt:
        raise HTTPException(status_code=400, detail="topic_prompt required")
    registry = load_registry(settings)
    benchmarks = list_benchmarks(settings, limit=50)
    routing_config = get_routing_config(settings)
    model_paths = pick_model_paths(registry, benchmarks, routing_config, "hook")

    hooks = generate_hooks(settings, topic_prompt, style, count, model_paths=model_paths)
    scored = score_hooks(hooks, "score_only")
    top = select_top(scored, min(3, count))
    return {"hooks": scored, "top": top}
