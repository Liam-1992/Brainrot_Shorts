from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from .env_utils import apply_env_updates


@dataclass
class RecommendedModel:
    model_id: str
    kind: str
    name: str
    description: str
    urls: List[str]


RECOMMENDED_MODELS = [
    RecommendedModel(
        model_id="llm_mistral_q4",
        kind="llm",
        name="Mistral-7B-Instruct Q4",
        description="Balanced local LLM for script generation (GGUF, Q4_K_M).",
        urls=[
            "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
        ],
    ),
    RecommendedModel(
        model_id="whisper_base_ct2",
        kind="whisper",
        name="faster-whisper base",
        description="Fast captioning model (CT2 base).",
        urls=[
            "https://huggingface.co/Systran/faster-whisper-base/resolve/main/model.bin",
            "https://huggingface.co/Systran/faster-whisper-base/resolve/main/config.json",
            "https://huggingface.co/Systran/faster-whisper-base/resolve/main/preprocessor_config.json",
            "https://huggingface.co/Systran/faster-whisper-base/resolve/main/tokenizer.json",
            "https://huggingface.co/Systran/faster-whisper-base/resolve/main/vocabulary.json",
        ],
    ),
    RecommendedModel(
        model_id="piper_lessac_medium",
        kind="piper",
        name="Piper en_US-lessac medium",
        description="Clear English voice (Piper).",
        urls=[
            "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx",
            "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json",
        ],
    ),
]


def list_recommended(settings) -> List[dict]:
    items = []
    for model in RECOMMENDED_MODELS:
        installed, resolved = _resolve_installed(settings, model)
        items.append(
            {
                "model_id": model.model_id,
                "kind": model.kind,
                "name": model.name,
                "description": model.description,
                "urls": model.urls,
                "installed": installed,
                "resolved_path": resolved or "",
            }
        )
    return items


def get_recommended(model_id: str) -> Optional[RecommendedModel]:
    for model in RECOMMENDED_MODELS:
        if model.model_id == model_id:
            return model
    return None


def apply_download(settings, model: RecommendedModel, output_dir: Path) -> Dict[str, str]:
    updates: Dict[str, str] = {}
    if model.kind == "llm":
        ggufs = sorted(output_dir.glob("*.gguf"))
        if ggufs:
            updates["LLM_MODEL_PATH"] = str(ggufs[0])
            updates["LLM_MODEL_PATHS"] = ",".join(str(p) for p in ggufs)
            updates["LLM_BACKEND"] = "llama_cpp"
    elif model.kind == "whisper":
        model_bin = _find_model_bin(output_dir)
        if model_bin:
            updates["WHISPER_MODEL_PATH"] = str(model_bin.parent)
    elif model.kind == "piper":
        onnx = sorted(output_dir.glob("*.onnx"))
        if onnx:
            updates["PIPER_MODEL_PATH"] = str(onnx[0])
    if updates:
        apply_env_updates(settings.BASE_DIR / ".env", updates)
    return updates


def _resolve_installed(settings, model: RecommendedModel) -> tuple[bool, str | None]:
    models_dir = settings.MODELS_DIR / model.kind / _sanitize_name(model.name)
    if models_dir.exists():
        if model.kind == "llm":
            ggufs = sorted(models_dir.glob("*.gguf"))
            if ggufs:
                return True, str(ggufs[0])
        if model.kind == "whisper":
            model_bin = _find_model_bin(models_dir)
            if model_bin:
                return True, str(model_bin.parent)
        if model.kind == "piper":
            onnx = sorted(models_dir.glob("*.onnx"))
            if onnx:
                return True, str(onnx[0])
    return False, None


def _find_model_bin(base_dir: Path) -> Path | None:
    candidates = list(base_dir.rglob("model.bin"))
    return candidates[0] if candidates else None


def _sanitize_name(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in value)
    return cleaned.strip("-").lower()
