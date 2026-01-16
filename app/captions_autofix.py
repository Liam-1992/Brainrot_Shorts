from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

from .captions import load_caption_style
from .llm import generate_text
from .utils import write_json


def autofix_captions(
    settings,
    job_id: str,
    caption_style: str,
    plugin_manager,
    mode: str,
    max_words_per_second: float,
    max_chars_per_line: int,
    min_caption_duration: float,
) -> dict:
    job_dir = settings.OUTPUTS_DIR / job_id
    transcript_path = job_dir / "transcript.json"
    report_path = job_dir / "caption_report.json"
    ass_path = job_dir / "subtitles_autofix.ass"

    if not transcript_path.exists():
        return {"changed": False, "reason": "transcript.json not found"}

    payload = json.loads(transcript_path.read_text(encoding="utf-8"))
    words = payload.get("words", [])
    if not words:
        return {"changed": False, "reason": "no words"}

    events = group_words(
        words,
        max_words_per_second=max_words_per_second,
        max_chars_per_line=max_chars_per_line,
        min_caption_duration=min_caption_duration,
    )

    changed = True
    if mode in {"rewrite", "group_then_rewrite"}:
        events = rewrite_events(
            settings, events, max_chars_per_line=max_chars_per_line, target_wps=max_words_per_second
        )

    report = build_report_from_events(events, max_words_per_second, max_chars_per_line)
    write_json(report_path, report)
    render_ass(settings, events, ass_path, caption_style, plugin_manager)
    return {"changed": changed, "ass_path": str(ass_path), "report": report}


def build_report_from_events(events: List[dict], max_wps: float, max_chars_per_line: int) -> dict:
    total_words = sum(len(e["text"].split()) for e in events)
    total_duration = sum(max(0.01, e["end"] - e["start"]) for e in events)
    avg_wps = total_words / max(0.01, total_duration)
    max_len = 0
    for event in events:
        max_len = max(max_len, max(len(line) for line in event["lines"]))
    suggestions = []
    if avg_wps > max_wps:
        suggestions.append("Words-per-second still high; try rewrite mode.")
    if max_len > max_chars_per_line:
        suggestions.append("Caption lines exceed max length; shorten text.")
    if not suggestions:
        suggestions.append("Caption readability looks healthy.")
    return {
        "events": len(events),
        "avg_words_per_second": round(avg_wps, 2),
        "max_chars_per_line": max_len,
        "suggestions": suggestions,
    }


def group_words(
    words: List[Dict],
    max_words_per_second: float,
    max_chars_per_line: int,
    min_caption_duration: float,
) -> List[dict]:
    events: List[dict] = []
    current: List[str] = []
    start = None
    last_end = None

    for word in words:
        text = str(word.get("text", "")).strip()
        if not text:
            continue
        if start is None:
            start = float(word.get("start", 0.0))
        last_end = float(word.get("end", 0.0))
        candidate = " ".join(current + [text])
        if len(candidate) > max_chars_per_line * 2 and current:
            _flush_event(events, current, start, last_end, max_words_per_second, min_caption_duration, max_chars_per_line)
            current = [text]
            start = float(word.get("start", 0.0))
            last_end = float(word.get("end", 0.0))
            continue
        current.append(text)
        if last_end - start >= min_caption_duration and len(candidate) >= max_chars_per_line:
            _flush_event(events, current, start, last_end, max_words_per_second, min_caption_duration, max_chars_per_line)
            current = []
            start = None
            last_end = None

    if current and start is not None and last_end is not None:
        _flush_event(events, current, start, last_end, max_words_per_second, min_caption_duration, max_chars_per_line)
    return events


def rewrite_events(
    settings,
    events: List[dict],
    max_chars_per_line: int,
    target_wps: float,
) -> List[dict]:
    lines = [" ".join(event["lines"]).replace("\\N", " ") for event in events]
    system = "You shorten captions for readability. Return strict JSON only."
    prompt = (
        "Rewrite each line to be shorter and punchier.\n"
        f"Max chars per line: {max_chars_per_line}\n"
        f"Target words/sec: {target_wps}\n"
        f"Lines: {json.dumps(lines)}\n"
        "Return JSON: {\"lines\": [\"...\", \"...\"]}"
    )
    try:
        raw = generate_text(settings, system, prompt, seed=None)
        payload = _extract_json(raw)
        rewrites = payload.get("lines", [])
        if len(rewrites) != len(events):
            return events
        updated = []
        for event, rewrite in zip(events, rewrites):
            text = str(rewrite).strip()
            if not text:
                text = " ".join(event["lines"]).replace("\\N", " ")
            lines = _wrap_lines(text, max_chars_per_line)
            updated.append({**event, "lines": lines, "text": text})
        return updated
    except Exception:
        return events


def render_ass(settings, events: List[dict], ass_path: Path, caption_style: str, plugin_manager) -> None:
    style = load_caption_style(settings, caption_style, plugin_manager)
    header = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour,"
        " BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing,"
        " Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        (
            "Style: Default,"
            f"{style.get('font')},{style.get('font_size')},"
            f"{style.get('primary_color')},{style.get('secondary_color')},"
            f"{style.get('outline_color')},{style.get('back_color')},"
            f"{style.get('bold', -1)},0,0,0,100,100,0,0,1,"
            f"{style.get('outline')},{style.get('shadow')},"
            f"{style.get('alignment')},{style.get('margin_l')},"
            f"{style.get('margin_r')},{style.get('margin_v')},1"
        ),
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    ass_path.parent.mkdir(parents=True, exist_ok=True)
    with ass_path.open("w", encoding="utf-8") as handle:
        for line in header:
            handle.write(line + "\n")
        for event in events:
            start = _format_ass_time(event["start"])
            end = _format_ass_time(event["end"])
            text = _escape_ass("\\N".join(event["lines"]))
            handle.write(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}\n")


def _flush_event(
    events: List[dict],
    words: List[str],
    start: float,
    last_end: float,
    max_words_per_second: float,
    min_caption_duration: float,
    max_chars_per_line: int,
) -> None:
    text = " ".join(words).strip()
    if not text:
        return
    target_duration = max(min_caption_duration, len(words) / max(1.0, max_words_per_second))
    end = max(last_end, start + target_duration)
    lines = _wrap_lines(text, max_chars_per_line)
    events.append({"start": start, "end": end, "text": text, "lines": lines})


def _wrap_lines(text: str, max_chars_per_line: int) -> List[str]:
    words = text.split()
    if not words:
        return [""]
    lines: List[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > max_chars_per_line and current:
            lines.append(current)
            current = word
        else:
            current = candidate
        if len(lines) == 1 and len(current) > max_chars_per_line:
            break
    if current:
        lines.append(current)
    if len(lines) > 2:
        lines = lines[:2]
    return lines


def _format_ass_time(seconds: float) -> str:
    total = max(0.0, seconds)
    hours = int(total // 3600)
    minutes = int((total % 3600) // 60)
    secs = total % 60
    centiseconds = int(round((secs - int(secs)) * 100))
    return f"{hours}:{minutes:02d}:{int(secs):02d}.{centiseconds:02d}"


def _escape_ass(text: str) -> str:
    return text.replace("{", "\\{").replace("}", "\\}").replace("\n", " ").strip()


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
