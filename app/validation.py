from __future__ import annotations

import json
from pathlib import Path

from .utils import run_subprocess


def validate_output(
    settings,
    output_path: Path,
    expected_duration: float,
    job_id: str | None = None,
) -> dict:
    result = {
        "ok": True,
        "checks": {},
    }

    if not output_path.exists():
        result["ok"] = False
        result["checks"]["exists"] = False
        return result

    try:
        probe = run_subprocess(
            [
                settings.FFPROBE_PATH,
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                str(output_path),
            ],
            job_id=job_id,
        )
        payload = json.loads(probe.stdout or "{}")
        stream = (payload.get("streams") or [{}])[0]
        width = int(stream.get("width", 0))
        height = int(stream.get("height", 0))
        duration = float((payload.get("format") or {}).get("duration", 0.0))
        result["checks"]["resolution"] = {"width": width, "height": height}
        result["checks"]["duration"] = duration
        if width != 1080 or height != 1920:
            result["ok"] = False
        if abs(duration - expected_duration) > 0.25:
            result["ok"] = False
    except Exception as exc:
        result["ok"] = False
        result["checks"]["probe_error"] = str(exc)

    try:
        loud = run_subprocess(
            [
                settings.FFMPEG_PATH,
                "-i",
                str(output_path),
                "-af",
                "loudnorm=I=-14:LRA=11:TP=-1.5:print_format=json",
                "-f",
                "null",
                "-",
            ],
            job_id=job_id,
        )
        loud_json = _extract_loudnorm_json(loud.stderr or "")
        result["checks"]["loudness"] = loud_json
        if loud_json:
            input_i = float(loud_json.get("input_i", -99))
            if input_i < -22 or input_i > -8:
                result["ok"] = False
    except Exception as exc:
        result["checks"]["loudness_error"] = str(exc)
        result["ok"] = False

    return result


def write_validation(job_dir: Path, payload: dict) -> Path:
    path = job_dir / "validation.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _extract_loudnorm_json(stderr_text: str) -> dict:
    start = stderr_text.find("{")
    end = stderr_text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    try:
        return json.loads(stderr_text[start : end + 1])
    except Exception:
        return {}
