from __future__ import annotations

import re
from typing import Dict, List, Tuple

from .types import Config, ModelCard, VramEstimate


HEAVY_FAMILIES = {
    "cogvideo",
    "videocrafter",
    "mochi",
    "ltx-video",
    "video diffusion",
    "videodiffusion",
    "svd",
    "gen-3",
    "lumina",
}

LOW_VRAM_HINTS = {
    "low vram",
    "8gb",
    "12gb",
    "attention slicing",
    "vae slicing",
    "cpu offload",
    "xformers",
    "sdpa",
}

HIGH_VRAM_HINTS = {
    "24gb",
    "32gb",
    "40gb",
    "48gb",
    "a100",
    "h100",
    "requires 24",
    "requires 16",
    "16gb",
}


def estimate_vram_requirement(
    model_card: ModelCard,
    files: List[str],
    hints: Dict[str, object],
    config: Config | None = None,
) -> VramEstimate:
    config = config or Config()
    reasons: List[str] = []
    required = None

    text = _combined_text(model_card)
    weight_gb = model_card.total_weight_bytes() / (1024**3)
    quantized = _has_quantized_weights(files)

    if weight_gb > 0:
        required = max(required or 0, weight_gb * 1.5)
    if weight_gb > config.max_model_size_gb and not quantized:
        reasons.append("weights_too_large")

    if _contains_hint(text, HIGH_VRAM_HINTS):
        reasons.append("requires_high_vram_hint")

    if _contains_hint(text, HEAVY_FAMILIES):
        if not _contains_hint(text, LOW_VRAM_HINTS) and not quantized:
            reasons.append("heavy_architecture")

    if not _is_diffusers(model_card, files):
        reasons.append("not_diffusers_compatible")

    if not model_card.total_weight_bytes() and not model_card.readme_text:
        reasons.append("unknown_requirements")

    if quantized:
        hints["quantized"] = True

    compatible = True
    if config.strict_vram and not config.allow_over_vram:
        if any(
            reason
            for reason in reasons
            if reason
            in {"weights_too_large", "requires_high_vram_hint", "heavy_architecture", "unknown_requirements"}
        ):
            compatible = False

    if config.require_diffusers and "not_diffusers_compatible" in reasons:
        compatible = False

    return VramEstimate(
        compatible=compatible,
        required_gb=round(required, 2) if required else None,
        reasons=reasons,
        hints=hints,
    )


def _combined_text(model_card: ModelCard) -> str:
    parts = []
    if model_card.readme_text:
        parts.append(model_card.readme_text)
    if isinstance(model_card.card_data, dict):
        parts.append(str(model_card.card_data))
    parts.append(" ".join(model_card.tags))
    return " ".join(parts).lower()


def _contains_hint(text: str, hints: set) -> bool:
    for hint in hints:
        if hint in text:
            return True
    return False


def _has_quantized_weights(files: List[str]) -> bool:
    for name in files:
        lower = name.lower()
        if any(token in lower for token in ("int8", "4bit", "gguf", "quant")):
            return True
    return False


def _is_diffusers(model_card: ModelCard, files: List[str]) -> bool:
    if model_card.library_name and "diffusers" in model_card.library_name:
        return True
    for tag in model_card.tags:
        if "diffusers" in tag:
            return True
    for name in files:
        if name.endswith("model_index.json"):
            return True
    return False

