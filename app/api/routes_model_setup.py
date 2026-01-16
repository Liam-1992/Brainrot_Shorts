from __future__ import annotations

import asyncio
from typing import Dict

from fastapi import APIRouter, HTTPException

from ..downloads import run_download
from ..model_setup import apply_download, get_recommended, list_recommended
from ..models import ModelDownloadRequest
from ..utils import generate_job_id

router = APIRouter()
_context: Dict[str, object] = {}


def init_context(settings, downloads_store: dict) -> None:
    _context["settings"] = settings
    _context["downloads"] = downloads_store


@router.get("/models/recommended")
def recommended_models() -> Dict:
    settings = _context["settings"]
    return {"models": list_recommended(settings)}


@router.post("/models/recommended/download")
async def download_recommended(payload: Dict) -> Dict:
    settings = _context["settings"]
    downloads_store = _context["downloads"]
    model_id = str(payload.get("model_id", "")).strip()
    if not model_id:
        raise HTTPException(status_code=400, detail="model_id required")
    model = get_recommended(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="model not found")

    download_id = generate_job_id()
    download_state = {
        "status": "queued",
        "progress": 0,
        "downloaded_bytes": 0,
        "total_bytes": 0,
        "logs": [],
        "output_dir": None,
    }
    downloads_store[download_id] = download_state
    request = ModelDownloadRequest(name=model.name, kind=model.kind, urls=model.urls, overwrite=False)

    async def runner() -> None:
        try:
            download_state["status"] = "downloading"
            output_dir = await asyncio.to_thread(run_download, settings, request, download_id, download_state)
            download_state["output_dir"] = str(output_dir)
            updates = apply_download(settings, model, output_dir)
            if updates:
                download_state["logs"].append(f"Applied env: {updates}")
            download_state["status"] = "done"
            download_state["progress"] = 100
        except Exception as exc:
            download_state["status"] = "error"
            message = f"ERROR: {exc}"
            download_state["logs"].append(message)

    asyncio.create_task(runner())
    return {"download_id": download_id}
