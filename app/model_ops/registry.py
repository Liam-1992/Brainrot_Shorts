from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List


def load_registry(settings) -> Dict[str, List[dict]]:
    registry_path = settings.MODELS_DIR / "registry.json"
    payload: Dict[str, List[dict]] = {"llm": [], "whisper": [], "tts": []}
    if registry_path.exists():
        try:
            raw = json.loads(registry_path.read_text(encoding="utf-8"))
            payload["llm"] = raw.get("llm", []) or []
            payload["whisper"] = raw.get("whisper", []) or []
            payload["tts"] = raw.get("tts", []) or []
        except Exception:
            payload = {"llm": [], "whisper": [], "tts": []}

    llm_paths = []
    if settings.LLM_HOOK_MODEL_PATH:
        llm_paths.append({"path": settings.LLM_HOOK_MODEL_PATH, "role": "hook"})
    if settings.LLM_SCRIPT_MODEL_PATH:
        llm_paths.append({"path": settings.LLM_SCRIPT_MODEL_PATH, "role": "script"})
    for path in settings.LLM_MODEL_PATHS:
        llm_paths.append({"path": path, "role": "general"})
    if settings.LLM_MODEL_PATH:
        llm_paths.append({"path": settings.LLM_MODEL_PATH, "role": "general"})

    llm_dir = settings.MODELS_DIR / "llm"
    if llm_dir.exists():
        for candidate in sorted(llm_dir.rglob("*.gguf")):
            llm_paths.append({"path": str(candidate), "role": "general"})

    for item in llm_paths:
        _add_model(payload["llm"], item)

    whisper_dir = settings.MODELS_DIR / "whisper"
    if whisper_dir.exists():
        for candidate in sorted(whisper_dir.rglob("model.bin")):
            _add_model(payload["whisper"], {"path": str(candidate.parent), "role": "asr"})

    tts_dir = settings.MODELS_DIR / "piper"
    if tts_dir.exists():
        for candidate in sorted(tts_dir.rglob("*.onnx")):
            _add_model(payload["tts"], {"path": str(candidate), "role": "tts"})

    return payload


def _add_model(target: List[dict], item: dict) -> None:
    path = str(item.get("path", "")).strip()
    if not path:
        return
    name = item.get("name")
    if not name:
        name = Path(path).stem
    role = item.get("role", "general")
    quality = float(item.get("quality", 0))
    vram_gb = item.get("vram_gb")
    entry = {
        "name": name,
        "path": path,
        "role": role,
        "quality": quality,
        "vram_gb": vram_gb,
    }
    for existing in target:
        if existing.get("path") == entry["path"]:
            return
    target.append(entry)
