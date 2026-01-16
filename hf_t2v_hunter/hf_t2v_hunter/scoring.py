from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import List

from .types import Config, ModelCard, ScoredModel
from .filters import apply_filters


def rank_models(candidates: List[ModelCard] | List[ScoredModel], config: Config) -> List[ScoredModel]:
    if candidates and isinstance(candidates[0], ModelCard):
        candidates = apply_filters(config, candidates)  # type: ignore[assignment]
    filtered = [item for item in candidates if not item.filtered_out]  # type: ignore[attr-defined]
    if not filtered:
        return candidates  # type: ignore[return-value]

    max_downloads = max((c.model.downloads for c in filtered), default=1)
    max_likes = max((c.model.likes for c in filtered), default=1)

    for item in filtered:
        reasons = []
        downloads_score = _normalize(item.model.downloads, max_downloads)
        likes_score = _normalize(item.model.likes, max_likes)
        recency_score = _recency_score(item.model.last_modified, config.recency_days)
        quality_score, quality_reasons = _quality_score(item, config)

        weights = config.weights
        total = (
            downloads_score * weights.get("downloads", 0)
            + likes_score * weights.get("likes", 0)
            + recency_score * weights.get("recency", 0)
            + quality_score * weights.get("quality", 0)
        )
        score = int(round(total * 100))

        reasons.extend(_build_reason("downloads", downloads_score))
        reasons.extend(_build_reason("likes", likes_score))
        reasons.extend(_build_reason("recency", recency_score))
        reasons.extend(quality_reasons)

        if item.model.requires_trust_remote_code and not config.allow_trust_remote_code:
            score = max(0, score - 10)
            reasons.append("penalty: trust_remote_code")

        if item.vram_estimate.required_gb and item.vram_estimate.required_gb > config.vram_gb:
            score = max(0, score - 15)
            reasons.append("penalty: near_vram_limit")

        item.score = score
        item.reasons = reasons

    return sorted(candidates, key=lambda c: c.score, reverse=True)


def _normalize(value: int, max_value: int) -> float:
    if max_value <= 0:
        return 0.0
    return min(1.0, math.log1p(value) / math.log1p(max_value))


def _recency_score(last_modified: datetime | None, recency_days: int) -> float:
    if not last_modified:
        return 0.2
    if last_modified.tzinfo is None:
        last_modified = last_modified.replace(tzinfo=timezone.utc)
    days = (datetime.now(timezone.utc) - last_modified).days
    if days <= 30:
        return 1.0
    if days >= recency_days:
        return 0.2
    return max(0.2, 1.0 - (days / recency_days))


def _quality_score(item: ScoredModel, config: Config) -> tuple[float, List[str]]:
    score = 0.0
    reasons = []
    files = [s.name for s in item.model.siblings]

    if any(name.endswith("model_index.json") for name in files):
        score += 0.35
        reasons.append("quality: diffusers_pipeline")

    if any(name.lower().endswith((".mp4", ".gif")) for name in files):
        score += 0.15
        reasons.append("quality: example_media")

    if any(name.lower().endswith(".safetensors") for name in files):
        score += 0.15
        reasons.append("quality: safetensors")

    if item.vram_estimate.hints.get("quantized"):
        score += 0.15
        reasons.append("quality: quantized_weights")

    if item.model.license:
        score += 0.1

    if config.allow_cpu_offload:
        score += 0.1

    return min(1.0, score), reasons


def _build_reason(label: str, score: float) -> List[str]:
    if score >= 0.9:
        return [f"{label}: strong"]
    if score >= 0.6:
        return [f"{label}: solid"]
    return [f"{label}: weak"]

