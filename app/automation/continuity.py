from __future__ import annotations

from typing import Dict, List

from ..models import ScriptBeat, ScriptOutput


def build_series_context(
    campaign_meta: dict,
    part_index: int,
    theme: str | None = None,
    campaign_id: str | None = None,
    memory: dict | None = None,
) -> dict:
    memory = memory or {}
    return {
        "campaign_id": campaign_id,
        "part_index": part_index,
        "theme": theme or campaign_meta.get("theme"),
        "used_hooks": memory.get("used_hooks", campaign_meta.get("used_hooks", [])),
        "used_keywords": campaign_meta.get("used_keywords", []),
        "banned_phrases": memory.get("banned_phrases", campaign_meta.get("banned_phrases", [])),
        "cta": f"Follow for part {part_index + 1}",
        "title_suffix": f"Part {part_index}",
    }


def apply_series_postprocess(script: ScriptOutput, series_context: dict) -> ScriptOutput:
    if not series_context:
        return script
    banned = series_context.get("banned_phrases", [])
    if banned:
        for phrase in banned:
            if phrase:
                script.hook = script.hook.replace(phrase, "").strip()
                script.title = script.title.replace(phrase, "").strip()

    used_hooks = set(series_context.get("used_hooks", []))
    if script.hook in used_hooks:
        suffix = series_context.get("title_suffix") or ""
        script.hook = f"{script.hook} {suffix}".strip()
        if script.beats:
            script.beats[0].text = script.hook
            script.beats[0].on_screen = script.hook

    title_suffix = series_context.get("title_suffix")
    if title_suffix and title_suffix not in script.title:
        script.title = f"{script.title} - {title_suffix}"
    cta = series_context.get("cta")
    if cta:
        script.beats.append(
            ScriptBeat(
                t=script.beats[-1].t + 2.0 if script.beats else 0.0,
                text=cta,
                on_screen=cta,
            )
        )
    script.full_voiceover_text = " ".join(
        beat.text for beat in script.beats if beat.text
    ).strip()
    return script


def update_campaign_memory(meta: dict, script: ScriptOutput) -> dict:
    used_hooks = meta.get("used_hooks", [])
    used_keywords = meta.get("used_keywords", [])
    if script.hook:
        used_hooks.append(script.hook)
    for keyword in script.keywords:
        used_keywords.append(keyword)
    meta["used_hooks"] = _dedupe(used_hooks)
    meta["used_keywords"] = _dedupe(used_keywords)
    return meta


def _dedupe(items: List[str]) -> List[str]:
    seen = set()
    output = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output
