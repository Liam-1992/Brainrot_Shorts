from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from .db import get_connection
from .hooks_pool import generate_hooks, score_hooks, select_top
from .llm import generate_script
from .models import GenerateRequest, ScriptOutput
from .virality_score import estimate_virality
from .automation.campaign_memory import get_memory, is_script_allowed
from .utils import ensure_dir, write_json


def load_hook_pool(settings, job_id: str, job_dir: Path) -> dict | None:
    path = job_dir / "hooks.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
    with get_connection(settings.DB_PATH) as conn:
        row = conn.execute(
            "SELECT hooks_json FROM hook_pools WHERE job_id = ?",
            (job_id,),
        ).fetchone()
    if not row or not row["hooks_json"]:
        return None
    try:
        return json.loads(row["hooks_json"])
    except Exception:
        return None


def generate_hook_pool(
    settings,
    req: GenerateRequest,
    job_id: str,
    job_dir: Path,
    model_paths: List[str],
    log_cb=None,
) -> dict:
    existing = load_hook_pool(settings, job_id, job_dir)
    if existing:
        return existing

    count = max(1, int(req.hook_pool_size))
    hooks = generate_hooks(
        settings,
        req.topic_prompt,
        req.style,
        count,
        model_paths=model_paths,
    )
    scored = score_hooks(hooks, req.hook_selection_mode)
    top = select_top(scored, max(1, int(req.hook_pick)))
    selected = top[0]["text"] if top else (hooks[0] if hooks else "")
    payload = {
        "selected": selected,
        "hooks": scored,
        "top": top,
        "created_at": datetime.utcnow().isoformat(),
    }
    save_hook_pool(settings, job_id, job_dir, payload)
    if log_cb:
        log_cb(f"Hook-first pool generated. Selected: {selected}")
    return payload


def save_hook_pool(settings, job_id: str, job_dir: Path, payload: dict) -> None:
    ensure_dir(job_dir)
    write_json(job_dir / "hooks.json", payload)
    with get_connection(settings.DB_PATH) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO hook_pools (job_id, created_at, hooks_json)
            VALUES (?, ?, ?)
            """,
            (job_id, payload.get("created_at"), json.dumps(payload)),
        )
        conn.commit()


def generate_script_candidates(
    settings,
    req: GenerateRequest,
    template,
    plugin_manager,
    selected_hook: str,
    model_paths: List[str],
    candidate_count: int,
) -> List[ScriptOutput]:
    scripts: List[ScriptOutput] = []
    for idx in range(candidate_count):
        req_copy = req.model_copy(deep=True)
        if req.seed is not None:
            req_copy.seed = int(req.seed) + idx
        script = generate_script(
            settings,
            req_copy,
            template,
            plugin_manager,
            model_paths=model_paths,
            forced_hook=selected_hook,
        )
        scripts.append(script)
    return scripts


def select_best_candidate(
    scripts: List[ScriptOutput],
    duration_seconds: int,
) -> Tuple[ScriptOutput, dict]:
    scored: List[dict] = []
    best = None
    for idx, script in enumerate(scripts, start=1):
        estimate = estimate_virality(script, duration_seconds)
        scored.append(
            {
                "index": idx,
                "score": estimate["score"],
                "reasons": estimate["reasons"],
                "metrics": estimate["metrics"],
            }
        )
        if not best or estimate["score"] > best["score"]:
            best = scored[-1]
    if best is None:
        raise ValueError("No candidates to select from")
    chosen = scripts[best["index"] - 1]
    return chosen, {"candidates": scored, "selected_index": best["index"]}


def run_generation_strategy(
    settings,
    req: GenerateRequest,
    template,
    plugin_manager,
    job_id: str,
    job_dir: Path,
    model_paths: List[str],
    log_cb=None,
) -> Tuple[ScriptOutput, dict]:
    meta: Dict[str, object] = {}
    selected_hook = ""
    hook_pool = None
    memory = None
    campaign_id = None
    if req.series_context:
        campaign_id = req.series_context.get("campaign_id")
    if campaign_id:
        memory = get_memory(settings, campaign_id)

    if req.hook_first_enabled:
        hook_pool = generate_hook_pool(settings, req, job_id, job_dir, model_paths, log_cb=log_cb)
        selected_hook = hook_pool.get("selected", "")
        if memory:
            selected_hook = _select_hook_with_memory(hook_pool, memory, fallback=selected_hook)
            hook_pool["selected"] = selected_hook
            save_hook_pool(settings, job_id, job_dir, hook_pool)
        meta["hook_pool"] = hook_pool

    if req.candidate_selection_enabled:
        candidate_count = max(1, int(req.script_candidate_count))
        scripts = generate_script_candidates(
            settings,
            req,
            template,
            plugin_manager,
            selected_hook,
            model_paths,
            candidate_count,
        )
        if memory:
            allowed = [script for script in scripts if is_script_allowed(memory, script)]
            if allowed:
                scripts = allowed
            else:
                meta["candidate_violations"] = "All candidates violated campaign memory"
        candidates_dir = job_dir / "candidates"
        ensure_dir(candidates_dir)
        for idx, script in enumerate(scripts, start=1):
            out_dir = candidates_dir / f"candidate_{idx:02d}"
            ensure_dir(out_dir)
            write_json(out_dir / "script.json", script.model_dump())
        chosen, selection_meta = select_best_candidate(scripts, req.duration_seconds)
        meta["candidate_selection"] = selection_meta
        if log_cb:
            log_cb(f"Selected candidate {selection_meta['selected_index']} of {candidate_count}.")
        return chosen, meta

    attempts = 0
    script = None
    while attempts < 3:
        attempts += 1
        script = generate_script(
            settings,
            req,
            template,
            plugin_manager,
            model_paths=model_paths,
            forced_hook=selected_hook if req.hook_first_enabled else None,
        )
        if not memory or is_script_allowed(memory, script):
            break
        if log_cb:
            log_cb("Script violated campaign memory; regenerating.")
    if memory and script and not is_script_allowed(memory, script):
        meta["candidate_violations"] = "Generated script violated campaign memory"
    if script is None:
        raise ValueError("Failed to generate script")
    return script, meta


def _select_hook_with_memory(hook_pool: dict, memory: dict, fallback: str) -> str:
    banned = set(memory.get("banned_phrases", []))
    used = set(memory.get("used_hooks", []))
    for candidate in hook_pool.get("top", []):
        text = candidate.get("text", "").strip()
        if text and text not in banned and text not in used:
            return text
    for candidate in hook_pool.get("hooks", []):
        text = candidate.get("text", "").strip()
        if text and text not in banned and text not in used:
            return text
    return fallback
