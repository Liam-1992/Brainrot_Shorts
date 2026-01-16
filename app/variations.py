from __future__ import annotations

import json
import random
from typing import List

from .llm import generate_text
from .metrics import score_hook
from .models import GenerateRequest


def build_variation_requests(settings, base: GenerateRequest, count: int) -> List[GenerateRequest]:
    voices = settings.available_voices()
    caption_styles = [p.stem for p in settings.CAPTION_STYLES_DIR.glob("*.json")]
    music_files = [p.name for p in settings.MUSIC_DIR.glob("*") if p.is_file()]

    variations = []
    for idx in range(count):
        seed = random.randint(1, 999999)
        voice = base.voice
        if voices:
            voice = random.choice(voices)
        caption_style = base.caption_style
        if caption_styles:
            caption_style = random.choice(caption_styles)
        music_bed = base.music_bed
        if music_files and random.random() > 0.5:
            music_bed = random.choice(music_files)

        topic = f"{base.topic_prompt} (variation: new angle, new phrasing)"
        variations.append(
            GenerateRequest(
                **{
                    **base.model_dump(),
                    "topic_prompt": topic,
                    "seed": seed,
                    "voice": voice,
                    "caption_style": caption_style,
                    "music_bed": music_bed,
                }
            )
        )
    return variations


def rewrite_hook(settings, hook_text: str, style: str) -> List[str]:
    system = "You rewrite hooks for short-form videos. Return strict JSON only."
    prompt = (
        f"Original hook: {hook_text}\n"
        f"Style: {style}\n"
        "Return JSON: {\"candidates\": [\"...\", \"...\", \"...\", \"...\", \"...\"]}"
    )
    raw = generate_text(settings, system, prompt, seed=None)
    payload = _extract_json(raw)
    candidates = payload.get("candidates", [])
    return [str(item).strip() for item in candidates if str(item).strip()][:5]


def generate_variants(settings, topic_prompt: str, style: str, num_hooks: int, num_titles: int, pick: int) -> dict:
    system = "You generate lists of hooks and titles. Return strict JSON only."
    prompt = (
        f"Topic: {topic_prompt}\n"
        f"Style: {style}\n"
        f"Generate {num_hooks} hook ideas and {num_titles} title ideas.\n"
        "Return JSON: {\"hooks\": [\"...\"], \"titles\": [\"...\"]}"
    )
    raw = generate_text(settings, system, prompt, seed=None)
    payload = _extract_json(raw)
    hooks = [str(item).strip() for item in payload.get("hooks", [])][:num_hooks]
    titles = [str(item).strip() for item in payload.get("titles", [])][:num_titles]

    scored_hooks = []
    for hook in hooks:
        score, reasons = score_hook(hook)
        scored_hooks.append({"text": hook, "score": score, "reasons": reasons})

    scored_titles = []
    for title in titles:
        score, reasons = score_hook(title)
        scored_titles.append({"text": title, "score": score, "reasons": reasons})

    picks = []
    for hook in sorted(scored_hooks, key=lambda x: x["score"], reverse=True)[:pick]:
        for title in sorted(scored_titles, key=lambda x: x["score"], reverse=True)[:1]:
            picks.append({"hook": hook, "title": title})
            if len(picks) >= pick:
                break
        if len(picks) >= pick:
            break

    return {"hooks": scored_hooks, "titles": scored_titles, "picks": picks}


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
