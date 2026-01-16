from __future__ import annotations

import json
from pathlib import Path
from typing import List


def _format_ass_time(seconds: float) -> str:
    total = max(0.0, seconds)
    hours = int(total // 3600)
    minutes = int((total % 3600) // 60)
    secs = total % 60
    centiseconds = int(round((secs - int(secs)) * 100))
    return f"{hours}:{minutes:02d}:{int(secs):02d}.{centiseconds:02d}"


def _escape_ass(text: str) -> str:
    return text.replace("{", "\\{").replace("}", "\\}").replace("\n", " ").strip()


def _select_device(settings) -> tuple[str, str]:
    device = settings.WHISPER_DEVICE
    compute = settings.WHISPER_COMPUTE_TYPE
    if device != "auto":
        return device, compute if compute != "auto" else "int8"
    try:
        from faster_whisper import WhisperModel  # noqa: F401

        return "cuda", "float16" if compute == "auto" else compute
    except Exception:
        return "cpu", "int8"


def transcribe_words(settings, audio_path: Path):
    from faster_whisper import WhisperModel

    resolved_path = settings.resolve_whisper_model_path()
    model_name = resolved_path or settings.WHISPER_MODEL_SIZE
    device, compute = _select_device(settings)

    try:
        model = WhisperModel(model_name, device=device, compute_type=compute)
    except Exception:
        model = WhisperModel(model_name, device="cpu", compute_type="int8")

    segments, _info = model.transcribe(
        str(audio_path),
        word_timestamps=True,
        beam_size=5,
    )

    words = []
    segments_out = []
    for segment in segments:
        segments_out.append(segment)
        if segment.words:
            for word in segment.words:
                words.append(
                    {
                        "start": float(word.start),
                        "end": float(word.end),
                        "text": word.word.strip(),
                    }
                )
    return words, segments_out


def load_caption_style(settings, style_name: str, plugin_manager) -> dict:
    style_path = settings.CAPTION_STYLES_DIR / f"{style_name}.json"
    style = {}
    if style_path.exists():
        try:
            style = json.loads(style_path.read_text(encoding="utf-8"))
        except Exception:
            style = {}
    if not style:
        style = {
            "name": style_name,
            "font": settings.CAPTION_FONT,
            "font_size": settings.CAPTION_FONT_SIZE,
            "primary_color": "&H00FFFFFF",
            "secondary_color": "&H0000FFFF",
            "outline_color": "&H00000000",
            "back_color": "&H64000000",
            "bold": -1,
            "outline": 6,
            "shadow": 3,
            "alignment": 2,
            "margin_l": 60,
            "margin_r": 60,
            "margin_v": 180,
            "bounce_scale": 112,
        }
    context = {"caption_style": style_name}
    return plugin_manager.apply_caption_style(style, context)


def build_ass(
    settings,
    words,
    segments,
    ass_path: Path,
    caption_style: str,
    plugin_manager,
    preview_start: float | None = None,
    preview_duration: float | None = None,
) -> Path:
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

    events: List[str] = []
    bounce_scale = int(style.get("bounce_scale", 110))
    if preview_start is not None and preview_duration is not None:
        words = [
            {
                "start": word["start"] - preview_start,
                "end": word["end"] - preview_start,
                "text": word["text"],
            }
            for word in words
            if preview_start <= word["start"] <= preview_start + preview_duration
        ]
    if words:
        current_segment = []
        segment_start = words[0]["start"]
        last_end = words[0]["end"]
        for word in words:
            if word["start"] - last_end > 0.8 and current_segment:
                events.append(_karaoke_event(segment_start, last_end, current_segment, bounce_scale))
                current_segment = []
                segment_start = word["start"]
            current_segment.append(word)
            last_end = word["end"]
        if current_segment:
            events.append(_karaoke_event(segment_start, last_end, current_segment, bounce_scale))
    else:
        for segment in segments:
            start_time = float(segment.start)
            end_time = float(segment.end)
            if preview_start is not None and preview_duration is not None:
                if end_time < preview_start or start_time > preview_start + preview_duration:
                    continue
                start_time = max(preview_start, start_time) - preview_start
                end_time = min(preview_start + preview_duration, end_time) - preview_start
            text = _escape_ass(segment.text)
            start = _format_ass_time(start_time)
            end = _format_ass_time(end_time)
            events.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")

    ass_path.parent.mkdir(parents=True, exist_ok=True)
    with ass_path.open("w", encoding="utf-8") as handle:
        for line in header:
            handle.write(line + "\n")
        for event in events:
            handle.write(event + "\n")
    return ass_path


def _karaoke_event(start_s: float, end_s: float, words, bounce_scale: int) -> str:
    start = _format_ass_time(start_s)
    end = _format_ass_time(end_s)
    pieces = []
    for word in words:
        dur_cs = max(1, int(round((word["end"] - word["start"]) * 100)))
        cleaned = _escape_ass(word["text"])
        pieces.append(
            f"{{\\k{dur_cs}\\fscx{bounce_scale}\\fscy{bounce_scale}}}{cleaned}{{\\fscx100\\fscy100}}"
        )
    text = " ".join(pieces)
    return f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}"
