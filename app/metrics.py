from __future__ import annotations

import json
import math
from typing import List, Tuple

from .utils import get_media_duration

CURIOUS_WORDS = {"wait", "secret", "nobody", "this is why", "what if", "you wont"}
SHOCK_WORDS = {"crazy", "insane", "wild", "unbelievable", "terrifying", "banned"}


def score_hook(hook_text: str) -> tuple[int, List[str]]:
    text = hook_text.strip().lower()
    reasons: List[str] = []
    score = 50

    length = len(text.split())
    if 6 <= length <= 14:
        score += 15
        reasons.append("Good length for a hook.")
    elif length > 18:
        score -= 10
        reasons.append("Hook is long; shorten for punch.")
    else:
        score += 5

    if any(word in text for word in CURIOUS_WORDS):
        score += 15
        reasons.append("Curiosity gap words detected.")

    if any(char.isdigit() for char in text):
        score += 10
        reasons.append("Numbers boost specificity.")

    if any(word in text for word in SHOCK_WORDS):
        score += 10
        reasons.append("Shock words add intensity.")

    if text.count(",") > 1 or text.count("and") > 2:
        score -= 8
        reasons.append("Too complex; simplify phrasing.")

    score = max(0, min(100, score))
    if not reasons:
        reasons.append("Baseline hook with room to sharpen.")
    return score, reasons


def compute_metrics(settings, job_id: str) -> dict:
    job_dir = settings.OUTPUTS_DIR / job_id
    script_path = job_dir / "script.json"
    transcript_path = job_dir / "transcript.json"
    voice_path = job_dir / "voice.wav"
    duration = 30.0
    if voice_path.exists():
        try:
            duration = get_media_duration(voice_path, settings.FFPROBE_PATH)
        except Exception:
            duration = 30.0
    if duration <= 0:
        duration = 30.0

    beats = []
    if script_path.exists():
        try:
            script = json.loads(script_path.read_text(encoding="utf-8"))
            beats = script.get("beats", [])
        except Exception:
            beats = []

    words = []
    if transcript_path.exists():
        try:
            transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
            words = transcript.get("words", [])
        except Exception:
            words = []

    total_seconds = max(1, int(math.ceil(duration)))
    beat_density = [0 for _ in range(total_seconds)]
    cut_frequency = [0 for _ in range(total_seconds)]
    for beat in beats:
        t = float(beat.get("t", 0.0))
        idx = min(total_seconds - 1, max(0, int(t)))
        beat_density[idx] += 1
        cut_frequency[idx] += 1

    words_per_second = [0 for _ in range(total_seconds)]
    for word in words:
        t = float(word.get("start", 0.0))
        idx = min(total_seconds - 1, max(0, int(t)))
        words_per_second[idx] += 1

    avg_caption_length = 0.0
    words_per_caption_event = 0.0
    if beats:
        avg_caption_length = sum(len(beat.get("text", "").split()) for beat in beats) / max(1, len(beats))
    if words:
        words_per_caption_event = len(words) / max(1, len(beats))

    suggestions = _suggestions(beat_density, words_per_second)

    return {
        "beat_density": beat_density,
        "words_per_second": words_per_second,
        "cut_frequency": cut_frequency,
        "avg_caption_length": round(avg_caption_length, 2),
        "words_per_caption_event": round(words_per_caption_event, 2),
        "suggestions": suggestions,
    }


def _suggestions(beat_density: List[int], words_per_second: List[int]) -> List[str]:
    suggestions: List[str] = []
    slow_sections = _find_ranges([v < 1 for v in beat_density])
    dense_sections = _find_ranges([v > 6 for v in words_per_second])

    for start, end in slow_sections:
        if end - start >= 3:
            suggestions.append(f"Too slow between {start}-{end}s; add a beat.")
    for start, end in dense_sections:
        if end - start >= 2:
            suggestions.append(f"Too dense between {start}-{end}s; cut words.")

    if not suggestions:
        suggestions.append("Pacing looks balanced.")
    return suggestions


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
