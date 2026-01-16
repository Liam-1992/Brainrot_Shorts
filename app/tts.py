from __future__ import annotations

from pathlib import Path

from .utils import run_subprocess


def _build_atempo(speed: float) -> str:
    if abs(speed - 1.0) < 0.01:
        return ""
    parts = []
    remaining = speed
    while remaining > 2.0:
        parts.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        parts.append("atempo=0.5")
        remaining /= 0.5
    parts.append(f"atempo={remaining:.3f}")
    return ",".join(parts)


def synthesize_voice(
    settings,
    text: str,
    voice: str,
    out_dir: Path,
    speech_speed: float,
    job_id: str | None = None,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / "voice_raw.wav"
    final_path = out_dir / "voice.wav"

    model_path = settings.resolve_piper_model(voice)
    if not model_path:
        raise ValueError(
            "Piper model not found. Set PIPER_MODEL_PATH/PIPER_VOICES_DIR or place a .onnx in models/piper."
        )

    piper_args = [
        settings.PIPER_PATH,
        "--model",
        str(model_path),
        "--output_file",
        str(raw_path),
        "--text",
        text,
    ]
    run_subprocess(piper_args, job_id=job_id)

    filters = []
    atempo = _build_atempo(speech_speed)
    if atempo:
        filters.append(atempo)
    filters.append("loudnorm=I=-14:LRA=11:TP=-1.5")
    filter_str = ",".join(filters)

    ffmpeg_args = [
        settings.FFMPEG_PATH,
        "-y",
        "-i",
        str(raw_path),
        "-af",
        filter_str,
        str(final_path),
    ]
    run_subprocess(ffmpeg_args, job_id=job_id)
    return final_path


def synthesize_preview(settings, text: str, voice: str, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / f"{voice}_raw.wav"
    final_path = out_dir / f"{voice}.wav"

    model_path = settings.resolve_piper_model(voice)
    if not model_path:
        raise ValueError(
            "Piper model not found. Set PIPER_MODEL_PATH/PIPER_VOICES_DIR or place a .onnx in models/piper."
        )

    piper_args = [
        settings.PIPER_PATH,
        "--model",
        str(model_path),
        "--output_file",
        str(raw_path),
        "--text",
        text,
    ]
    run_subprocess(piper_args)

    ffmpeg_args = [
        settings.FFMPEG_PATH,
        "-y",
        "-i",
        str(raw_path),
        "-af",
        "loudnorm=I=-14:LRA=11:TP=-1.5",
        str(final_path),
    ]
    run_subprocess(ffmpeg_args)
    return final_path
