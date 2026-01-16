from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

from .captions_report import compress_words
from .metrics import score_hook
from .variations import rewrite_hook


def apply_hook_gate(
    settings,
    script: Dict,
    min_score: float,
    max_retries: int,
    style: str,
    log_cb=None,
) -> Tuple[Dict, List[Dict]]:
    attempts: List[Dict] = []
    hook = str(script.get("hook", "")).strip()
    beats = script.get("beats", [])
    for attempt in range(max_retries + 1):
        score, reasons = score_hook(hook)
        attempts.append({"hook": hook, "score": score, "reasons": reasons})
        if score >= min_score:
            break
        try:
            candidates = rewrite_hook(settings, hook, style)
        except Exception:
            break
        if not candidates:
            break
        hook = candidates[0]
        if log_cb:
            log_cb(f"Quality gate: hook score {score} below {min_score}, rewriting.")
        if beats:
            beats[0]["text"] = hook
            beats[0]["on_screen"] = hook
        script["hook"] = hook
        script["beats"] = beats
        script["full_voiceover_text"] = " ".join(
            beat.get("text", "") for beat in beats if beat.get("text")
        ).strip()
    return script, attempts


def apply_caption_gate(
    words: List[Dict],
    max_words_per_second: float,
    max_retries: int,
    log_cb=None,
) -> Tuple[List[Dict], List[Dict]]:
    attempts: List[Dict] = []
    current = words
    for attempt in range(max_retries + 1):
        wps = _max_wps(current)
        attempts.append({"attempt": attempt, "max_wps": wps})
        if wps <= max_words_per_second:
            break
        if log_cb:
            log_cb(
                f"Quality gate: max words/sec {wps:.2f} above {max_words_per_second}, compressing captions."
            )
        current = compress_words(current, max_words_per_second)
    return current, attempts


def save_report(job_dir: Path, report: Dict) -> None:
    path = job_dir / "quality_report.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")


def _max_wps(words: List[Dict]) -> float:
    buckets = {}
    for word in words:
        second = int(float(word.get("start", 0.0)))
        buckets[second] = buckets.get(second, 0) + 1
    if not buckets:
        return 0.0
    return max(float(v) for v in buckets.values())
