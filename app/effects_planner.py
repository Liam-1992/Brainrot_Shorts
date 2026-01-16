from __future__ import annotations

import json
from pathlib import Path
from typing import List

IMPACT_WORDS = {"explode", "insane", "wild", "crazy", "shocking", "unbelievable", "secret"}


def plan_effects(job_dir: Path, beats: List[dict], impact_rate: float) -> dict:
    impact_rate = max(0.0, min(1.0, impact_rate))
    scored = []
    for beat in beats:
        text = str(beat.get("text", "")).strip()
        emphasis = bool(beat.get("emphasis"))
        score = _impact_score(text, emphasis)
        scored.append(
            {
                "t": float(beat.get("t", 0.0)),
                "text": text,
                "score": score,
                "emphasis": emphasis,
            }
        )

    scored.sort(key=lambda item: item["score"], reverse=True)
    impact_count = max(1, int(len(scored) * impact_rate)) if scored else 0
    shake = sorted(scored[:impact_count], key=lambda item: item["t"])
    zoom = sorted([item for item in scored if item["score"] >= 2], key=lambda item: item["t"])

    plan = {
        "impact_rate": impact_rate,
        "shake_beats": [item["t"] for item in shake],
        "zoom_beats": [item["t"] for item in zoom],
        "scores": scored,
    }
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "effects_plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
    return plan


def _impact_score(text: str, emphasis: bool) -> int:
    score = 0
    if emphasis:
        score += 3
    if "!" in text or "?" in text:
        score += 1
    words = set(text.lower().split())
    if words & IMPACT_WORDS:
        score += 2
    if text.isupper() and len(text) > 3:
        score += 1
    return score
