from __future__ import annotations

import json
from datetime import datetime
from typing import List

from ..db import get_connection
from ..models import ScriptOutput


def get_memory(settings, campaign_id: str) -> dict:
    with get_connection(settings.DB_PATH) as conn:
        row = conn.execute(
            "SELECT memory_json FROM campaign_memory WHERE campaign_id = ?",
            (campaign_id,),
        ).fetchone()
    if row and row["memory_json"]:
        try:
            return json.loads(row["memory_json"])
        except Exception:
            return _default_memory()
    return _default_memory()


def update_memory(settings, campaign_id: str, memory: dict) -> None:
    with get_connection(settings.DB_PATH) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO campaign_memory (campaign_id, memory_json, updated_at)
            VALUES (?, ?, ?)
            """,
            (campaign_id, json.dumps(memory), datetime.utcnow().isoformat()),
        )
        conn.commit()


def reset_memory(settings, campaign_id: str) -> dict:
    memory = _default_memory()
    update_memory(settings, campaign_id, memory)
    return memory


def update_from_script(settings, campaign_id: str, script: ScriptOutput) -> dict:
    memory = get_memory(settings, campaign_id)
    used_hooks = memory.get("used_hooks", [])
    used_facts = memory.get("used_facts", [])
    banned_phrases = memory.get("banned_phrases", [])

    if script.hook:
        if script.hook in used_hooks and script.hook not in banned_phrases:
            banned_phrases.append(script.hook)
        used_hooks.append(script.hook)

    facts = extract_facts(script)
    for fact in facts:
        if fact in used_facts and fact not in banned_phrases:
            banned_phrases.append(fact)
        used_facts.append(fact)

    memory["used_hooks"] = _dedupe(used_hooks)
    memory["used_facts"] = _dedupe(used_facts)
    memory["banned_phrases"] = _dedupe(banned_phrases)
    update_memory(settings, campaign_id, memory)
    return memory


def extract_facts(script: ScriptOutput) -> List[str]:
    facts: List[str] = []
    for beat in script.beats:
        text = beat.text.strip()
        if not text:
            continue
        if any(token in text.lower() for token in [" is ", " are ", " was ", " were "]):
            facts.append(_normalize_phrase(text))
        if any(char.isdigit() for char in text):
            facts.append(_normalize_phrase(text))
    if script.keywords:
        for keyword in script.keywords:
            facts.append(_normalize_phrase(keyword))
    return _dedupe(facts)[:20]


def is_script_allowed(memory: dict, script: ScriptOutput) -> bool:
    hook = script.hook.strip()
    banned = set(memory.get("banned_phrases", []))
    used_hooks = set(memory.get("used_hooks", []))
    if hook in used_hooks or hook in banned:
        return False
    for beat in script.beats:
        text = _normalize_phrase(beat.text)
        if text in banned:
            return False
    return True


def _normalize_phrase(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _dedupe(items: List[str]) -> List[str]:
    seen = set()
    output = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output


def _default_memory() -> dict:
    return {"used_hooks": [], "used_facts": [], "banned_phrases": []}
