from __future__ import annotations

from pathlib import Path
from typing import Dict

from fastapi import APIRouter, HTTPException

from ..automation.campaigns import create_campaign, export_campaign, export_campaign_pro, get_campaign, list_campaigns, run_campaign
from ..automation.campaign_memory import get_memory, reset_memory

router = APIRouter()
_context: Dict[str, object] = {}


def init_context(settings, preset_manager, enqueue_fn) -> None:
    _context["settings"] = settings
    _context["preset_manager"] = preset_manager
    _context["enqueue_fn"] = enqueue_fn


@router.post("/campaigns/create")
def create_campaign_endpoint(payload: Dict) -> Dict:
    settings = _context["settings"]
    name = str(payload.get("name", "")).strip()
    preset_name = payload.get("preset_name")
    prompts = payload.get("prompts") or []
    theme = payload.get("theme")
    file_path = payload.get("file_path")
    if not prompts and file_path:
        path = Path(file_path)
        if not path.exists():
            raise HTTPException(status_code=404, detail="Prompt file not found")
        prompts = _load_prompts(path)
    if not name or not prompts:
        raise HTTPException(status_code=400, detail="name and prompts are required")
    campaign_id = create_campaign(settings, name, preset_name, prompts, theme=theme)
    return {"campaign_id": campaign_id}


@router.get("/campaigns")
def list_campaigns_endpoint() -> Dict:
    settings = _context["settings"]
    return {"campaigns": list_campaigns(settings)}


@router.get("/campaigns/{campaign_id}")
def get_campaign_endpoint(campaign_id: str) -> Dict:
    settings = _context["settings"]
    campaign = get_campaign(settings, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.post("/campaigns/{campaign_id}/run")
def run_campaign_endpoint(campaign_id: str) -> Dict:
    settings = _context["settings"]
    preset_manager = _context["preset_manager"]
    enqueue_fn = _context["enqueue_fn"]
    campaign = get_campaign(settings, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    preset = None
    if campaign.get("preset_name"):
        preset = preset_manager.get(campaign.get("preset_name"))
    job_ids = run_campaign(settings, campaign_id, enqueue_fn, preset, overrides=None)
    return {"job_ids": job_ids}


@router.post("/campaigns/{campaign_id}/export")
def export_campaign_endpoint(campaign_id: str) -> Dict:
    settings = _context["settings"]
    try:
        path = export_campaign(settings, campaign_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True, "path": f"/outputs/campaigns/{campaign_id}/{path.name}"}


@router.post("/campaigns/{campaign_id}/export_pro")
def export_campaign_pro_endpoint(campaign_id: str) -> Dict:
    settings = _context["settings"]
    try:
        path = export_campaign_pro(settings, campaign_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True, "path": f"/outputs/campaigns/{campaign_id}/{path.name}"}


@router.get("/campaigns/{campaign_id}/memory")
def campaign_memory_endpoint(campaign_id: str) -> Dict:
    settings = _context["settings"]
    return get_memory(settings, campaign_id)


@router.post("/campaigns/{campaign_id}/memory/reset")
def campaign_memory_reset_endpoint(campaign_id: str) -> Dict:
    settings = _context["settings"]
    memory = reset_memory(settings, campaign_id)
    return {"ok": True, "memory": memory}


def _load_prompts(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".csv":
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if lines and "prompt" in lines[0].lower():
            lines = lines[1:]
        prompts = []
        for line in lines:
            prompt = line.split(",")[0].strip()
            if prompt:
                prompts.append(prompt)
        return prompts
    return [line.strip() for line in text.splitlines() if line.strip()]
