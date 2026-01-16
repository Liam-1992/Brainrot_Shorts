from __future__ import annotations

import json
import math
from typing import Dict, List


def build_report(settings, job_id: str) -> Dict:
    job_dir = settings.OUTPUTS_DIR / job_id
    script_path = job_dir / "script.json"
    transcript_path = job_dir / "transcript.json"

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

    duration = _estimate_duration(words, beats)
    words_per_second = _words_per_second(words, duration)
    avg_chars_per_line = _avg_chars_per_line(beats)
    max_consecutive_long = _max_consecutive_long(beats)
    caption_on_screen = _caption_on_screen(beats, duration)
    suggestions = _suggestions(words_per_second, avg_chars_per_line, max_consecutive_long)

    return {
        "duration_seconds": round(duration, 2),
        "words_per_second": words_per_second,
        "max_consecutive_long_captions": max_consecutive_long,
        "avg_caption_chars_per_line": round(avg_chars_per_line, 2),
        "avg_caption_time_on_screen": round(caption_on_screen, 2),
        "suggestions": suggestions,
    }


def compress_words(words: List[Dict], max_wps: float) -> List[Dict]:
    if not words:
        return words
    duration = _estimate_duration(words, [])
    wps = _words_per_second(words, duration)
    if not wps:
        return words
    max_allowed = max_wps
    if max(wps) <= max_allowed:
        return words

    keep = []
    for second in range(len(wps)):
        bucket = [w for w in words if int(w.get("start", 0)) == second]
        if not bucket:
            continue
        if len(bucket) <= max_allowed:
            keep.extend(bucket)
        else:
            stride = max(1, math.ceil(len(bucket) / max_allowed))
            keep.extend(bucket[::stride])
    keep.sort(key=lambda w: w.get("start", 0))
    return keep


def _estimate_duration(words: List[Dict], beats: List[Dict]) -> float:
    if words:
        return max(float(w.get("end", 0.0)) for w in words)
    if beats:
        return max(float(b.get("t", 0.0)) for b in beats) + 2.0
    return 30.0


def _words_per_second(words: List[Dict], duration: float) -> List[int]:
    total_seconds = max(1, int(math.ceil(duration)))
    counts = [0 for _ in range(total_seconds)]
    for word in words:
        start = float(word.get("start", 0.0))
        idx = min(total_seconds - 1, max(0, int(start)))
        counts[idx] += 1
    return counts


def _avg_chars_per_line(beats: List[Dict]) -> float:
    if not beats:
        return 0.0
    lengths = []
    for beat in beats:
        text = str(beat.get("text", "")).strip()
        if not text:
            continue
        lengths.append(min(len(text), 48))
    if not lengths:
        return 0.0
    return sum(lengths) / len(lengths)


def _max_consecutive_long(beats: List[Dict]) -> int:
    max_run = 0
    current = 0
    for beat in beats:
        text = str(beat.get("text", "")).strip()
        if len(text.split()) >= 9:
            current += 1
            max_run = max(max_run, current)
        else:
            current = 0
    return max_run


def _caption_on_screen(beats: List[Dict], duration: float) -> float:
    if not beats:
        return 0.0
    times = sorted([float(b.get("t", 0.0)) for b in beats])
    durations = []
    for idx, t in enumerate(times):
        next_t = times[idx + 1] if idx + 1 < len(times) else duration
        durations.append(max(0.5, next_t - t))
    return sum(durations) / len(durations)


def _suggestions(words_per_second: List[int], avg_chars: float, max_run: int) -> List[str]:
    suggestions = []
    if words_per_second and max(words_per_second) > 5:
        suggestions.append("Words-per-second spike detected; reduce on-screen density.")
    if avg_chars > 28:
        suggestions.append("Average caption length is high; shorten on-screen lines.")
    if max_run >= 3:
        suggestions.append("Several long captions in a row; break them up.")
    if not suggestions:
        suggestions.append("Caption readability looks healthy.")
    return suggestions
