from __future__ import annotations

from typing import Dict

from fastapi import APIRouter

from ..automation.scheduler import get_scheduler_status
from ..automation.watch_folder import get_last_scan, scan_watch_folder

router = APIRouter()
_context: Dict[str, object] = {}


def init_context(settings, enqueue_fn) -> None:
    _context["settings"] = settings
    _context["enqueue_fn"] = enqueue_fn


@router.get("/watch_folder/status")
def watch_folder_status() -> Dict:
    settings = _context["settings"]
    return {
        "enabled": settings.WATCH_FOLDER_ENABLED,
        "path": str(settings.WATCH_FOLDER_PATH) if settings.WATCH_FOLDER_PATH else None,
        "last_scan": get_last_scan(settings),
    }


@router.get("/scheduler/status")
def scheduler_status() -> Dict:
    settings = _context["settings"]
    return get_scheduler_status(settings)


@router.post("/watch_folder/scan")
def scan_watch_folder_endpoint(payload: Dict | None = None) -> Dict:
    settings = _context["settings"]
    enqueue_fn = _context["enqueue_fn"]
    preset_name = None
    approve_mode = False
    if payload:
        preset_name = payload.get("preset_name")
        approve_mode = bool(payload.get("approve_mode", False))
    result = scan_watch_folder(settings, enqueue_fn, preset_name=preset_name, approve_mode=approve_mode)
    result["last_scan"] = get_last_scan(settings)
    return result
