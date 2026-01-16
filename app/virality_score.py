from __future__ import annotations

import json
import math
from pathlib import Path
from typing import List, Tuple

from .metrics import compute_metrics, score_hook
from .models import ScriptOutput
from .utils import write_json


def compute_virality_score(settings, job_id: str) -> dict:
    job_dir = settings.OUTPUTS_DIR / job_id
    script_path = job_dir / "script.json"
    transcript_path = job_dir / "transcript.json"

    script = {}
    if script_path.exists():
        try:
            script = json.loads(script_path.read_text(encoding="utf-8"))
        except Exception:
            script = {}

    metrics = compute_metrics(settings, job_id)
    hook_score, hook_reasons = score_hook(script.get("hook", ""))
    words = []
    if transcript_path.exists():
        try:
            transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
            words = transcript.get("words", [])
        except Exception:
            words = []

    beat_density = metrics.get("beat_density", [])
    words_per_second = metrics.get("words_per_second", [])
    cut_frequency = metrics.get("cut_frequency", [])

    beat_score, beat_reason = _score_range(_beats_per_10s(beat_density), 4.0, 7.0, "beats/10s")
    wps_score, wps_reason = _score_range(_avg(words_per_second), 2.5, 4.2, "words/sec")
    cut_score, cut_reason = _score_range(_avg_per_10s(cut_frequency), 4.0, 8.0, "cuts/10s")
    stability_score = _caption_stability(words)

    score = _weighted_score(
        {
            "hook": hook_score,
            "beat": beat_score,
            "wps": wps_score,
            "stability": stability_score,
            "cuts": cut_score,
        }
    )

    reasons = list(hook_reasons)
    reasons.extend([beat_reason, wps_reason, cut_reason])
    if stability_score < 70:
        reasons.append("Caption stability is low; reduce flicker by grouping words.")

    problem_intervals = _problem_intervals(beat_density, words_per_second)

    payload = {
        "virality_score": score,
        "reasons": [r for r in reasons if r],
        "problem_intervals": problem_intervals,
        "metrics": {
            "hook_score": hook_score,
            "beats_per_10s": round(_beats_per_10s(beat_density), 2),
            "avg_words_per_second": round(_avg(words_per_second), 2),
            "caption_stability": stability_score,
            "cuts_per_10s": round(_avg_per_10s(cut_frequency), 2),
        },
    }
    write_json(job_dir / "virality_score.json", payload)
    return payload


def estimate_virality(script: ScriptOutput, duration_seconds: int) -> dict:
    hook_score, reasons = score_hook(script.hook)
    words = script.full_voiceover_text.split()
    wps = len(words) / max(1.0, float(duration_seconds))
    beats_per_10s = len(script.beats) / max(1.0, float(duration_seconds) / 10.0)

    beat_score, beat_reason = _score_range(beats_per_10s, 4.0, 7.0, "beats/10s")
    wps_score, wps_reason = _score_range(wps, 2.5, 4.0, "words/sec")
    score = _weighted_score(
        {
            "hook": hook_score,
            "beat": beat_score,
            "wps": wps_score,
            "stability": 85,
            "cuts": beat_score,
        }
    )
    reasons.extend([beat_reason, wps_reason])
    return {
        "score": score,
        "reasons": [r for r in reasons if r],
        "metrics": {
            "hook_score": hook_score,
            "beats_per_10s": round(beats_per_10s, 2),
            "words_per_second_estimate": round(wps, 2),
        },
    }


def _beats_per_10s(beat_density: List[int]) -> float:
    total_beats = sum(beat_density)
    total_seconds = max(1, len(beat_density))
    return total_beats / (total_seconds / 10.0)


def _avg(series: List[int]) -> float:
    if not series:
        return 0.0
    return sum(series) / len(series)


def _avg_per_10s(series: List[int]) -> float:
    if not series:
        return 0.0
    per_second = _avg(series)
    return per_second * 10.0


def _caption_stability(words: List[dict]) -> int:
    if not words:
        return 90
    durations = [max(0.0, float(w.get("end", 0)) - float(w.get("start", 0))) for w in words]
    short = [d for d in durations if d < 0.18]
    ratio = len(short) / max(1, len(durations))
    return max(0, min(100, int(round(100 - ratio * 100))))


def _score_range(value: float, minimum: float, maximum: float, label: str) -> Tuple[int, str]:
    if minimum <= value <= maximum:
        return 100, f"{label} within target range."
    if value < minimum:
        penalty = min(40, int((minimum - value) * 10))
        return max(40, 100 - penalty), f"{label} too low."
    penalty = min(40, int((value - maximum) * 10))
    return max(30, 100 - penalty), f"{label} too high."


def _weighted_score(parts: dict) -> int:
    weights = {"hook": 0.35, "beat": 0.2, "wps": 0.2, "stability": 0.15, "cuts": 0.1}
    total = 0.0
    for key, weight in weights.items():
        total += float(parts.get(key, 0)) * weight
    return int(round(total))


def _problem_intervals(beat_density: List[int], wps: List[int]) -> List[str]:
    problems = []
    slow = _find_ranges([v < 1 for v in beat_density])
    dense = _find_ranges([v > 6 for v in wps])
    for start, end in slow:
        if end - start >= 3:
            problems.append(f"{start}-{end}s too slow")
    for start, end in dense:
        if end - start >= 2:
            problems.append(f"{start}-{end}s too dense")
    return problems


def _find_ranges(flags: List[bool]) -> List[Tuple[int, int]]:
    ranges = []
    start = None
    for idx, flag in enumerate(flags):
        if flag and start is None:
            start = idx
        if not flag and start is not None:
            ranges.append((start, idx))
            start = None
    if start is not None:
        ranges.append((start, len(flags)))
    return ranges
