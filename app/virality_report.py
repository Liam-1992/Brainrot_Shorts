from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from .metrics import compute_metrics, score_hook
from .optimization import load_attempts
from .utils import ensure_dir, run_subprocess


def build_report(settings, job_id: str) -> Path:
    job_dir = settings.OUTPUTS_DIR / job_id
    ensure_dir(job_dir)

    script = _read_json(job_dir / "script.json")
    request = _read_json(job_dir / "request.json")
    metrics = compute_metrics(settings, job_id)
    hook_score, hook_reasons = score_hook(script.get("hook", ""))
    opt_history = load_attempts(settings, job_id)
    bg_segments = _read_json(job_dir / "bg_segments.json")
    validation = _read_json(job_dir / "validation.json")
    model_info = {
        "llm_model": str(settings.resolve_llm_model_path() or ""),
        "whisper_model": settings.resolve_whisper_model_path(),
        "tts_voice": request.get("voice", ""),
        "ffmpeg": settings.FFMPEG_PATH,
    }

    report_path = job_dir / "virality_report.html"
    html = _render_html(
        job_id,
        script,
        request,
        metrics,
        hook_score,
        hook_reasons,
        opt_history,
        bg_segments,
        model_info,
        validation,
    )
    report_path.write_text(html, encoding="utf-8")

    pdf_path = job_dir / "virality_report.pdf"
    _maybe_render_pdf(settings, report_path, pdf_path)
    return report_path


def _render_html(
    job_id: str,
    script: dict,
    request: dict,
    metrics: dict,
    hook_score: int,
    hook_reasons: List[str],
    opt_history: dict,
    bg_segments: dict,
    model_info: dict,
    validation: dict,
) -> str:
    beat_chart = _sparkline(metrics.get("beat_density", []))
    wps_chart = _sparkline(metrics.get("words_per_second", []))
    cut_chart = _sparkline(metrics.get("cut_frequency", []))
    suggestions = metrics.get("suggestions", [])

    title = script.get("title") or script.get("hook") or "Untitled"
    prompt = request.get("topic_prompt", "")
    style = request.get("style", "")
    preset = request.get("preset_name") or "none"
    music = request.get("music_bed", "none")
    sfx = request.get("sfx_pack", "none")
    bg_mode = request.get("bg_mode", "")
    voice = request.get("voice", "")
    render_mode = request.get("render_mode", "")
    caption_style = request.get("caption_style", "")
    llm_model = model_info.get("llm_model", "")
    whisper_model = model_info.get("whisper_model", "")
    ffmpeg_path = model_info.get("ffmpeg", "")
    render_duration = validation.get("checks", {}).get("duration") if validation else None

    opt_summary = ""
    if opt_history.get("attempts"):
        opt_summary = "<ul>" + "".join(
            f"<li>Attempt {a['attempt']}: score {a['hook_score']}, pass {a.get('pass', False)}</li>"
            for a in opt_history["attempts"]
        ) + "</ul>"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Virality Report - {job_id}</title>
  <style>
    body {{ font-family: Arial, sans-serif; padding: 24px; color: #111; }}
    h1 {{ margin-bottom: 6px; }}
    .section {{ margin-top: 24px; }}
    .chart {{ border: 1px solid #ddd; padding: 8px; background: #fafafa; }}
    .meta {{ color: #555; }}
    ul {{ padding-left: 20px; }}
    code {{ background: #f3f3f3; padding: 2px 6px; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>Virality Report</h1>
  <p class="meta">Job: {job_id} | Generated: {datetime.utcnow().isoformat()}</p>

  <div class="section">
    <h2>Summary</h2>
    <p><strong>Title:</strong> {title}</p>
    <p><strong>Prompt:</strong> {prompt}</p>
    <p><strong>Style:</strong> {style}</p>
    <p><strong>Preset:</strong> {preset}</p>
  </div>

  <div class="section">
    <h2>Hook Score</h2>
    <p><strong>Score:</strong> {hook_score}</p>
    <ul>{"".join(f"<li>{r}</li>" for r in hook_reasons)}</ul>
  </div>

  <div class="section">
    <h2>Performance Charts</h2>
    <p>Beat Density</p>
    <div class="chart">{beat_chart}</div>
    <p>Words Per Second</p>
    <div class="chart">{wps_chart}</div>
    <p>Cut Frequency</p>
    <div class="chart">{cut_chart}</div>
  </div>

  <div class="section">
    <h2>Retention Suggestions</h2>
    <ul>{"".join(f"<li>{s}</li>" for s in suggestions)}</ul>
  </div>

    <div class="section">
    <h2>Assets</h2>
    <p><strong>Background mode:</strong> {bg_mode}</p>
    <p><strong>Segments:</strong> <code>{json.dumps(bg_segments)}</code></p>
    <p><strong>Music bed:</strong> {music}</p>
    <p><strong>SFX pack:</strong> {sfx}</p>
    <p><strong>Voice:</strong> {voice}</p>
  </div>

  <div class="section">
    <h2>Render Stats</h2>
    <p><strong>Render mode:</strong> {render_mode}</p>
    <p><strong>Caption style:</strong> {caption_style}</p>
    <p><strong>LLM model:</strong> {llm_model}</p>
    <p><strong>Whisper model:</strong> {whisper_model}</p>
    <p><strong>FFmpeg:</strong> {ffmpeg_path}</p>
    <p><strong>Duration:</strong> {render_duration if render_duration else "n/a"}s</p>
  </div>

  <div class="section">
    <h2>Optimization Attempts</h2>
    {opt_summary or "<p>No optimization attempts recorded.</p>"}
  </div>
</body>
</html>"""


def _sparkline(series: List[int]) -> str:
    if not series:
        return "<em>No data</em>"
    width = 360
    height = 80
    max_val = max(series) or 1
    points = []
    for idx, val in enumerate(series):
        x = (idx / max(1, len(series) - 1)) * (width - 10) + 5
        y = height - (val / max_val) * (height - 10) - 5
        points.append(f"{x:.1f},{y:.1f}")
    return (
        f"<svg width='{width}' height='{height}' viewBox='0 0 {width} {height}'>"
        f"<polyline fill='none' stroke='#ff6f00' stroke-width='2' points='{' '.join(points)}' />"
        "</svg>"
    )


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _maybe_render_pdf(settings, html_path: Path, pdf_path: Path) -> None:
    if shutil.which("wkhtmltopdf") is None:
        return
    try:
        run_subprocess(["wkhtmltopdf", str(html_path), str(pdf_path)])
    except Exception:
        return
