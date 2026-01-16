from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

from fastapi import APIRouter, HTTPException

from ..env_utils import apply_env_updates

router = APIRouter()
_context: Dict[str, object] = {}

CONFIG_KEYS = [
    "FFMPEG_PATH",
    "FFPROBE_PATH",
    "PIPER_PATH",
    "PIPER_MODEL_PATH",
    "PIPER_VOICES_DIR",
    "LLM_BACKEND",
    "LLM_MODEL_PATH",
    "LLM_HOOK_MODEL_PATH",
    "LLM_SCRIPT_MODEL_PATH",
    "LLM_MODEL_PATHS",
    "LLM_CTX",
    "LLM_MAX_TOKENS",
    "LLM_TEMPERATURE",
    "LLM_N_GPU_LAYERS",
    "WHISPER_MODEL_SIZE",
    "WHISPER_MODEL_PATH",
    "WHISPER_DEVICE",
    "WHISPER_COMPUTE_TYPE",
    "CAPTION_FONT",
    "CAPTION_FONT_SIZE",
    "ASSETS_DIR",
    "BG_CLIPS_DIR",
    "FONTS_DIR",
    "MUSIC_DIR",
    "SFX_DIR",
    "OUTPUTS_DIR",
    "MODELS_DIR",
    "TEMPLATES_DIR",
    "CAPTION_STYLES_DIR",
    "PRESETS_PATH",
    "DB_PATH",
    "MAX_CONCURRENT_JOBS",
    "SUBPROCESS_TIMEOUT_SECONDS",
    "ROUTING_MODE",
    "ROUTING_POLICY",
    "WATCH_FOLDER_PATH",
    "WATCH_FOLDER_ENABLED",
    "PLUGINS_ENABLED",
]


def init_context(settings) -> None:
    _context["settings"] = settings


@router.get("/config")
def get_config() -> Dict:
    settings = _context["settings"]
    values = {}
    defaults = {}
    for key in CONFIG_KEYS:
        defaults[key] = _default_for_key(settings, key)
        raw = os.getenv(key)
        values[key] = raw if raw is not None else ""

    missing = _missing_required(settings)
    return {
        "values": values,
        "defaults": defaults,
        "missing": missing,
        "env_path": str(settings.BASE_DIR / ".env"),
    }


@router.post("/config")
def update_config(payload: Dict) -> Dict:
    settings = _context["settings"]
    values = payload.get("values") if isinstance(payload, dict) else None
    if values is None:
        values = payload
    if not isinstance(values, dict):
        raise HTTPException(status_code=400, detail="Invalid payload")

    updates = {}
    for key in CONFIG_KEYS:
        if key in values:
            updates[key] = str(values[key]).strip()

    if not updates:
        return {"ok": False, "message": "No updates provided"}

    env_path = settings.BASE_DIR / ".env"
    apply_env_updates(env_path, updates)

    return {"ok": True, "updated": list(updates.keys())}


def _default_for_key(settings, key: str) -> str:
    mapping = {
        "FFMPEG_PATH": settings.FFMPEG_PATH,
        "FFPROBE_PATH": settings.FFPROBE_PATH,
        "PIPER_PATH": settings.PIPER_PATH,
        "PIPER_MODEL_PATH": settings.PIPER_MODEL_PATH,
        "PIPER_VOICES_DIR": settings.PIPER_VOICES_DIR,
        "LLM_BACKEND": settings.LLM_BACKEND,
        "LLM_MODEL_PATH": settings.LLM_MODEL_PATH,
        "LLM_HOOK_MODEL_PATH": settings.LLM_HOOK_MODEL_PATH,
        "LLM_SCRIPT_MODEL_PATH": settings.LLM_SCRIPT_MODEL_PATH,
        "LLM_MODEL_PATHS": ",".join(settings.LLM_MODEL_PATHS),
        "LLM_CTX": str(settings.LLM_CTX),
        "LLM_MAX_TOKENS": str(settings.LLM_MAX_TOKENS),
        "LLM_TEMPERATURE": str(settings.LLM_TEMPERATURE),
        "LLM_N_GPU_LAYERS": str(settings.LLM_N_GPU_LAYERS),
        "WHISPER_MODEL_SIZE": settings.WHISPER_MODEL_SIZE,
        "WHISPER_MODEL_PATH": settings.WHISPER_MODEL_PATH,
        "WHISPER_DEVICE": settings.WHISPER_DEVICE,
        "WHISPER_COMPUTE_TYPE": settings.WHISPER_COMPUTE_TYPE,
        "CAPTION_FONT": settings.CAPTION_FONT,
        "CAPTION_FONT_SIZE": str(settings.CAPTION_FONT_SIZE),
        "ASSETS_DIR": str(settings.ASSETS_DIR),
        "BG_CLIPS_DIR": str(settings.BG_CLIPS_DIR),
        "FONTS_DIR": str(settings.FONTS_DIR),
        "MUSIC_DIR": str(settings.MUSIC_DIR),
        "SFX_DIR": str(settings.SFX_DIR),
        "OUTPUTS_DIR": str(settings.OUTPUTS_DIR),
        "MODELS_DIR": str(settings.MODELS_DIR),
        "TEMPLATES_DIR": str(settings.TEMPLATES_DIR),
        "CAPTION_STYLES_DIR": str(settings.CAPTION_STYLES_DIR),
        "PRESETS_PATH": str(settings.PRESETS_PATH),
        "DB_PATH": str(settings.DB_PATH),
        "MAX_CONCURRENT_JOBS": str(settings.MAX_CONCURRENT_JOBS),
        "SUBPROCESS_TIMEOUT_SECONDS": str(settings.SUBPROCESS_TIMEOUT_SECONDS),
        "ROUTING_MODE": settings.ROUTING_MODE,
        "ROUTING_POLICY": settings.ROUTING_POLICY,
        "WATCH_FOLDER_PATH": str(settings.WATCH_FOLDER_PATH or ""),
        "WATCH_FOLDER_ENABLED": "true" if settings.WATCH_FOLDER_ENABLED else "false",
        "PLUGINS_ENABLED": ",".join(settings.PLUGINS_ENABLED),
    }
    return mapping.get(key, "")


def _missing_required(settings) -> list[str]:
    missing = []
    if not settings.resolve_llm_model_path() and not settings.LLM_MODEL_PATHS:
        missing.append("LLM_MODEL_PATH")
    if not settings.resolve_whisper_model_path():
        missing.append("WHISPER_MODEL_PATH")
    if not _has_piper_model(settings):
        missing.append("PIPER_MODEL_PATH")
    return missing


def _has_piper_model(settings) -> bool:
    if settings.PIPER_MODEL_PATH:
        return Path(settings.PIPER_MODEL_PATH).exists()
    if settings.PIPER_VOICES_DIR:
        path = Path(settings.PIPER_VOICES_DIR)
        if path.exists() and any(path.glob("*.onnx")):
            return True
    models_dir = settings.MODELS_DIR / "piper"
    return models_dir.exists() and any(models_dir.rglob("*.onnx"))

