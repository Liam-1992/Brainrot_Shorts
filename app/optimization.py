from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from .beats_editor import update_beats
from .generation_strategy import run_generation_strategy
from .metrics import score_hook
from .models import GenerateRequest, ScriptBeat, ScriptOutput
from .utils import ensure_dir, write_json
from .variations import rewrite_hook
from .db import get_connection
from .model_ops.routing import get_routing_config, pick_model_paths
from .model_ops.registry import load_registry
from .model_ops.benchmarks import list_benchmarks
from .virality_score import estimate_virality


def run_optimization(
    settings,
    req: GenerateRequest,
    template,
    plugin_manager,
    job_id: str,
    job_dir: Path,
    log_cb=None,
) -> Tuple[ScriptOutput, dict]:
    attempts_dir = job_dir / "opt_attempts"
    ensure_dir(attempts_dir)
    registry = load_registry(settings)
    benchmarks = list_benchmarks(settings, limit=50)
    routing_config = get_routing_config(settings)
    script_models = pick_model_paths(registry, benchmarks, routing_config, "script")

    attempts: List[dict] = []
    best_attempt = None
    base_script: ScriptOutput | None = None

    for attempt in range(1, req.optimization_max_attempts + 1):
        if log_cb:
            log_cb(f"Optimization attempt {attempt}/{req.optimization_max_attempts}")

        if req.optimization_strategy == "hook_only":
            if base_script is None:
                base_script, _ = run_generation_strategy(
                    settings,
                    req,
                    template,
                    plugin_manager,
                    job_id,
                    job_dir,
                    script_models,
                    log_cb=log_cb,
                )
            script = base_script
        else:
            script, _ = run_generation_strategy(
                settings,
                req,
                template,
                plugin_manager,
                job_id,
                job_dir,
                script_models,
                log_cb=log_cb,
            )
            base_script = script

        if req.optimization_strategy in {"hook_only", "script_and_hook"}:
            script = _maybe_rewrite_hook(settings, req, script)

        metrics = _estimate_metrics(script, req.duration_seconds)
        hook_score, reasons = score_hook(script.hook)
        pass_gate = _passes_thresholds(metrics, hook_score, req)
        virality_est = estimate_virality(script, req.duration_seconds)
        selection_score = virality_est["score"]
        metrics_payload = {**metrics, "virality_estimate": virality_est}

        attempt_dir = attempts_dir / f"attempt_{attempt:02d}"
        ensure_dir(attempt_dir)
        write_json(attempt_dir / "script.json", script.model_dump())
        write_json(
            attempt_dir / "metadata.json",
            {
                "attempt": attempt,
                "hook_score": hook_score,
                "reasons": reasons,
                "metrics": metrics,
                "pass": pass_gate,
                "selection_score": selection_score,
                "virality_estimate": virality_est,
            },
        )
        _save_attempt(
            settings,
            job_id,
            attempt,
            hook_score,
            reasons,
            metrics_payload,
            attempt_dir / "script.json",
            selected=False,
        )
        attempt_payload = {
            "attempt": attempt,
            "hook_score": hook_score,
            "reasons": reasons,
            "metrics": metrics_payload,
            "pass": pass_gate,
            "selection_score": selection_score,
            "script": script,
        }
        attempts.append(attempt_payload)

        if pass_gate:
            best_attempt = attempt_payload
            break
        if not best_attempt or selection_score > best_attempt["selection_score"]:
            best_attempt = attempt_payload

    if not best_attempt:
        raise RuntimeError("Optimization failed to produce a script")

    _mark_selected(settings, job_id, best_attempt["attempt"])
    selected_script = best_attempt["script"]
    beats = [ScriptBeat(**beat.model_dump()) for beat in selected_script.beats]
    update_beats(settings, job_id, beats, selected_script.hook, selected_script.title)
    return selected_script, {
        "attempts": [
            {
                "attempt": item["attempt"],
                "hook_score": item["hook_score"],
                "reasons": item["reasons"],
                "metrics": item["metrics"],
                "pass": item["pass"],
                "selection_score": item["selection_score"],
            }
            for item in attempts
        ],
        "selected_attempt": best_attempt["attempt"],
    }


def load_attempts(settings, job_id: str) -> dict:
    with get_connection(settings.DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT attempt, selected, hook_score, reasons_json, metrics_json, script_path
            FROM optimization_attempts
            WHERE job_id = ?
            ORDER BY attempt ASC
            """,
            (job_id,),
        ).fetchall()
    attempts = []
    selected_attempt = None
    for row in rows:
        reasons = _safe_json(row["reasons_json"])
        metrics = _safe_json(row["metrics_json"])
        attempts.append(
            {
                "attempt": row["attempt"],
                "selected": bool(row["selected"]),
                "hook_score": int(row["hook_score"] or 0),
                "reasons": reasons,
                "metrics": metrics,
                "script_path": row["script_path"],
            }
        )
        if row["selected"]:
            selected_attempt = row["attempt"]
    return {"job_id": job_id, "selected_attempt": selected_attempt, "attempts": attempts}


def _maybe_rewrite_hook(settings, req: GenerateRequest, script: ScriptOutput) -> ScriptOutput:
    score, _ = score_hook(script.hook)
    if score >= req.min_hook_score:
        return script
    try:
        candidates = rewrite_hook(settings, script.hook, req.style)
    except Exception:
        return script
    if not candidates:
        return script
    script.hook = candidates[0]
    if script.beats:
        script.beats[0].text = script.hook
        script.beats[0].on_screen = script.hook
    script.full_voiceover_text = " ".join(
        beat.text for beat in script.beats if beat.text
    ).strip()
    return script


def _estimate_metrics(script: ScriptOutput, duration_seconds: int) -> dict:
    words = script.full_voiceover_text.split()
    wps = len(words) / max(1.0, float(duration_seconds))
    beats_per_10s = len(script.beats) / max(1.0, (float(duration_seconds) / 10.0))
    return {
        "words_per_second_estimate": round(wps, 2),
        "beats_per_10s": round(beats_per_10s, 2),
        "beats_count": len(script.beats),
    }


def _passes_thresholds(metrics: dict, hook_score: int, req: GenerateRequest) -> bool:
    return (
        hook_score >= req.min_hook_score
        and metrics["words_per_second_estimate"] <= req.max_words_per_second_estimate
        and req.min_beats_per_10s <= metrics["beats_per_10s"] <= req.max_beats_per_10s
    )


def _selection_score(metrics: dict, hook_score: int, req: GenerateRequest) -> float:
    penalty = 0.0
    if metrics["words_per_second_estimate"] > req.max_words_per_second_estimate:
        penalty += (metrics["words_per_second_estimate"] - req.max_words_per_second_estimate) * 5
    if metrics["beats_per_10s"] < req.min_beats_per_10s:
        penalty += (req.min_beats_per_10s - metrics["beats_per_10s"]) * 5
    if metrics["beats_per_10s"] > req.max_beats_per_10s:
        penalty += (metrics["beats_per_10s"] - req.max_beats_per_10s) * 5
    return hook_score - penalty


def _save_attempt(
    settings,
    job_id: str,
    attempt: int,
    hook_score: int,
    reasons: List[str],
    metrics: dict,
    script_path: Path,
    selected: bool,
) -> None:
    with get_connection(settings.DB_PATH) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO optimization_attempts
            (job_id, attempt, selected, hook_score, reasons_json, metrics_json, script_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                attempt,
                1 if selected else 0,
                hook_score,
                json.dumps(reasons),
                json.dumps(metrics),
                str(script_path),
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()


def _mark_selected(settings, job_id: str, attempt: int) -> None:
    with get_connection(settings.DB_PATH) as conn:
        conn.execute(
            """
            UPDATE optimization_attempts
            SET selected = CASE WHEN attempt = ? THEN 1 ELSE 0 END
            WHERE job_id = ?
            """,
            (attempt, job_id),
        )
        conn.commit()


def _safe_json(text: str | None) -> dict:
    if not text:
        return {}
    try:
        return json.loads(text)
    except Exception:
        return {}
