from __future__ import annotations

from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from ..assets_manager import (
    get_hotspots,
    get_metadata,
    get_tags_for_type,
    list_assets,
    resolve_asset_path,
    set_hotspots,
    set_tags,
)

router = APIRouter()
_context: Dict[str, object] = {}


def init_context(settings) -> None:
    _context["settings"] = settings


@router.get("/assets/list")
def assets_list(asset_type: str = Query(..., alias="type"), q: Optional[str] = None) -> Dict:
    settings = _context["settings"]
    try:
        items = list_assets(settings, asset_type, query=q)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"items": items}


@router.get("/assets/metadata")
def assets_metadata(path: str) -> Dict:
    settings = _context["settings"]
    try:
        data = get_metadata(settings, path)
        return data
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Asset not found")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/assets/preview")
def assets_preview(path: str) -> FileResponse:
    settings = _context["settings"]
    try:
        asset_path = resolve_asset_path(settings, path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not asset_path.exists():
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(asset_path)


@router.get("/assets/tags")
def assets_tags(asset_type: str = Query(..., alias="type")) -> Dict:
    settings = _context["settings"]
    try:
        tags = get_tags_for_type(settings, asset_type)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"items": [{"path": path, "tags": tags[path]} for path in tags]}


@router.put("/assets/tags")
def assets_set_tags(payload: Dict) -> Dict:
    settings = _context["settings"]
    path = str(payload.get("path", "")).strip()
    asset_type = str(payload.get("type", "")).strip()
    tags = payload.get("tags", [])
    if not path or not asset_type:
        raise HTTPException(status_code=400, detail="path and type are required")
    try:
        resolve_asset_path(settings, path)
        set_tags(settings, path, asset_type, tags)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True}


@router.get("/assets/hotspots")
def assets_hotspots(path: str) -> Dict:
    settings = _context["settings"]
    try:
        resolve_asset_path(settings, path)
        hotspots = get_hotspots(settings, path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"hotspots": hotspots}


@router.put("/assets/hotspots")
def assets_set_hotspots(payload: Dict) -> Dict:
    settings = _context["settings"]
    path = str(payload.get("path", "")).strip()
    hotspots = payload.get("hotspots", [])
    if not path:
        raise HTTPException(status_code=400, detail="path is required")
    try:
        resolve_asset_path(settings, path)
        set_hotspots(settings, path, hotspots)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True}
