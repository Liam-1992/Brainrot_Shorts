from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from ..captions import transcribe_words
from ..db import get_connection
from ..llm import generate_text
from ..tts import synthesize_voice
from ..utils import ensure_dir, run_subprocess
from .registry import load_registry


def run_benchmarks(settings) -> List[dict]:
    results = []
    registry = load_registry(settings)

    results.extend(_benchmark_llm(settings, registry.get("llm", [])))
    results.extend(_benchmark_whisper(settings))
    results.extend(_benchmark_tts(settings))
    results.extend(_benchmark_render(settings))

    for item in results:
        _save_benchmark(settings, item["tool"], item["model_name"], item["metrics"])
    return results


def list_benchmarks(settings, limit: int = 25) -> List[dict]:
    with get_connection(settings.DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT tool, model_name, created_at, metrics_json
            FROM benchmarks
            ORDER BY datetime(created_at) DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    payload = []
    for row in rows:
        try:
            metrics = json.loads(row["metrics_json"]) if row["metrics_json"] else {}
        except Exception:
            metrics = {}
        payload.append(
            {
                "tool": row["tool"],
                "model_name": row["model_name"],
                "created_at": row["created_at"],
                "metrics": metrics,
            }
        )
    return payload


def _benchmark_llm(settings, llm_models: List[dict]) -> List[dict]:
    results = []
    models = llm_models[:3] if llm_models else []
    if not models:
        resolved = settings.resolve_llm_model_path()
        if resolved:
            models = [{"name": resolved.stem, "path": str(resolved)}]
    for model in models:
        name = model.get("name") or Path(model.get("path", "model")).stem
        path = model.get("path")
        prompt = "Write a 1 sentence hook about why cats are secretly plotting."
        start = time.time()
        try:
            output = generate_text(
                settings,
                "You are a concise hook generator.",
                prompt,
                seed=123,
                model_paths=[path] if path else None,
            )
            elapsed = max(0.01, time.time() - start)
            tokens = max(1, len(output.split()))
            results.append(
                {
                    "tool": "llm",
                    "model_name": name,
                    "metrics": {
                        "latency_seconds": round(elapsed, 3),
                        "tokens": tokens,
                        "tokens_per_second": round(tokens / elapsed, 2),
                    },
                }
            )
        except Exception as exc:
            results.append(
                {
                    "tool": "llm",
                    "model_name": name,
                    "metrics": {"error": str(exc)},
                }
            )
    return results


def _benchmark_whisper(settings) -> List[dict]:
    results = []
    temp_dir = settings.OUTPUTS_DIR / "benchmarks"
    ensure_dir(temp_dir)
    audio_path = temp_dir / "whisper_sample.wav"
    if not audio_path.exists():
        run_subprocess(
            [
                settings.FFMPEG_PATH,
                "-y",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=1000:duration=15",
                str(audio_path),
            ]
        )
    start = time.time()
    try:
        transcribe_words(settings, audio_path)
        elapsed = max(0.01, time.time() - start)
        results.append(
            {
                "tool": "whisper",
                "model_name": settings.WHISPER_MODEL_SIZE,
                "metrics": {"seconds_per_minute": round(elapsed / 15.0 * 60.0, 2)},
            }
        )
    except Exception as exc:
        results.append(
            {
                "tool": "whisper",
                "model_name": settings.WHISPER_MODEL_SIZE,
                "metrics": {"error": str(exc)},
            }
        )
    return results


def _benchmark_tts(settings) -> List[dict]:
    results = []
    temp_dir = settings.OUTPUTS_DIR / "benchmarks"
    ensure_dir(temp_dir)
    voice = settings.available_voices()[0] if settings.available_voices() else "en_US"
    text = "This is a thirty second synthetic test. " * 4
    start = time.time()
    try:
        synthesize_voice(settings, text, voice, temp_dir, 1.0)
        elapsed = max(0.01, time.time() - start)
        results.append(
            {
                "tool": "tts",
                "model_name": voice,
                "metrics": {"seconds_per_30s": round(elapsed, 2)},
            }
        )
    except Exception as exc:
        results.append(
            {
                "tool": "tts",
                "model_name": voice,
                "metrics": {"error": str(exc)},
            }
        )
    return results


def _benchmark_render(settings) -> List[dict]:
    results = []
    temp_dir = settings.OUTPUTS_DIR / "benchmarks"
    ensure_dir(temp_dir)
    input_path = temp_dir / "render_input.mp4"
    output_path = temp_dir / "render_output.mp4"
    if not input_path.exists():
        run_subprocess(
            [
                settings.FFMPEG_PATH,
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=black:s=1080x1920:d=15",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(input_path),
            ]
        )
    start = time.time()
    try:
        run_subprocess(
            [
                settings.FFMPEG_PATH,
                "-y",
                "-i",
                str(input_path),
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "23",
                str(output_path),
            ]
        )
        elapsed = max(0.01, time.time() - start)
        results.append(
            {
                "tool": "render",
                "model_name": "ffmpeg",
                "metrics": {"seconds_per_30s": round(elapsed / 15.0 * 30.0, 2)},
            }
        )
    except Exception as exc:
        results.append(
            {
                "tool": "render",
                "model_name": "ffmpeg",
                "metrics": {"error": str(exc)},
            }
        )
    return results


def _save_benchmark(settings, tool: str, model_name: str, metrics: dict) -> None:
    created_at = datetime.utcnow().isoformat()
    with get_connection(settings.DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO benchmarks (tool, model_name, created_at, metrics_json)
            VALUES (?, ?, ?, ?)
            """,
            (tool, model_name, created_at, json.dumps(metrics)),
        )
        conn.commit()
