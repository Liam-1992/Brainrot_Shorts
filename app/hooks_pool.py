from __future__ import annotations

import json
from typing import List, Tuple

from .llm import generate_text
from .metrics import score_hook


def generate_hooks(
    settings,
    topic_prompt: str,
    style: str,
    count: int,
    model_paths: List[str] | None = None,
) -> List[dict]:
    system = "You generate short punchy hooks. Return strict JSON only."
    prompt = (
        f"Topic: {topic_prompt}\n"
        f"Style: {style}\n"
        f"Generate {count} hook ideas.\n"
        "Return JSON: {\"hooks\": [\"...\", \"...\"]}"
    )
    raw = generate_text(settings, system, prompt, seed=None, model_paths=model_paths)
    payload = _extract_json(raw)
    hooks = [str(item).strip() for item in payload.get("hooks", []) if str(item).strip()]
    return hooks[:count]


def score_hooks(hooks: List[str], mode: str) -> List[dict]:
    scored = []
    for hook in hooks:
        score, reasons = score_hook(hook)
        clarity_score = None
        final_score = score
        if mode == "score_plus_clarity":
            clarity_score = _clarity_score(hook)
            final_score = min(100, score + clarity_score)
        scored.append(
            {
                "text": hook,
                "score": final_score,
                "reasons": reasons,
                "clarity_score": clarity_score,
            }
        )
    return scored


def select_top(scored: List[dict], pick: int) -> List[dict]:
    return sorted(scored, key=lambda x: x.get("score", 0), reverse=True)[:pick]


def _clarity_score(text: str) -> int:
    words = text.split()
    if not words:
        return 0
    long_words = [w for w in words if len(w) > 10]
    punctuation = text.count(",") + text.count(";")
    score = 10
    score -= len(long_words) * 2
    score -= punctuation
    if len(words) <= 12:
        score += 5
    return max(-10, min(15, score))


def _extract_json(raw: str) -> dict:
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    payload = raw[start : end + 1]
    try:
        return json.loads(payload)
    except Exception:
        return {}
