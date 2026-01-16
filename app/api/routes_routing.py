from __future__ import annotations

from typing import Dict

from fastapi import APIRouter

from ..model_ops.routing import get_routing_status, save_routing_config

router = APIRouter()
_context: Dict[str, object] = {}


def init_context(settings) -> None:
    _context["settings"] = settings


@router.get("/routing/status")
def routing_status() -> Dict:
    settings = _context["settings"]
    return get_routing_status(settings)


@router.post("/routing/config")
def routing_config(payload: Dict) -> Dict:
    settings = _context["settings"]
    config = save_routing_config(settings, payload)
    return {"ok": True, "config": config}
