from __future__ import annotations

import json
from pathlib import Path

from . import captions, editor, tts
from . import background, beats_editor
from .assets_manager import get_hotspots
from .models import GenerateRequest, ScriptBeat
from .optimization import run_optimization
from .generation_strategy import run_generation_strategy
from .automation.campaign_memory import update_from_script
from .automation.continuity import apply_series_postprocess
from .model_ops.registry import load_registry
from .model_ops.benchmarks import list_benchmarks
from .model_ops.routing import get_routing_config, pick_model_paths
from .quality_gates import apply_caption_gate, apply_hook_gate, save_report
from .template_manager import TemplateManager
from .utils import append_log, ensure_dir, get_media_duration, write_json
from .validation import validate_output, write_validation
from .effects_planner import plan_effects
from .captions_autofix import autofix_captions
from .virality_score import compute_virality_score


def _update(job_state: dict, log_path: Path, progress: int, message: str) -> None:
    job_state["progress"] = progress
    if message:
        job_state["logs"].append(message)
        append_log(log_path, message)


def _normalize_duration(requested: int, voice_path: Path, ffprobe_path: str) -> float:
    voice_duration = get_media_duration(voice_path, ffprobe_path)
    if voice_duration <= 0:
        return float(requested)
    return max(float(requested), voice_duration)


def _load_script(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def run_pipeline(
    settings,
    req: GenerateRequest,
    job_id: str,
    job_state: dict,
    template_manager: TemplateManager,
    plugin_manager,
    steps: list[str] | None = None,
) -> Path:
    job_dir = settings.OUTPUTS_DIR / job_id
    ensure_dir(job_dir)
    log_path = job_dir / "log.txt"

    steps = steps or ["script", "voice", "captions", "render"]
    template = template_manager.get(req.template_name or req.style)
    if not template:
        template = template_manager.get(req.style)
    if not template:
        raise ValueError("Template not found. Check /templates endpoint for available templates.")

    script_path = job_dir / "script.json"
    if "script" in steps:
        _update(job_state, log_path, 5, "Generating script...")
        if req.optimization_enabled:
            script, opt_meta = run_optimization(
                settings,
                req,
                template,
                plugin_manager,
                job_id,
                job_dir,
                log_cb=lambda msg: _update(job_state, log_path, 6, msg),
            )
        else:
            registry = load_registry(settings)
            benchmarks = list_benchmarks(settings, limit=50)
            routing_config = get_routing_config(settings)
            script_models = pick_model_paths(registry, benchmarks, routing_config, "script")
            script, _meta = run_generation_strategy(
                settings,
                req,
                template,
                plugin_manager,
                job_id,
                job_dir,
                script_models,
                log_cb=lambda msg: _update(job_state, log_path, 6, msg),
            )

        if req.series_context:
            script = apply_series_postprocess(script, req.series_context)
            campaign_id = req.series_context.get("campaign_id")
            if campaign_id:
                update_from_script(settings, campaign_id, script)
        script_data = script.model_dump()
        write_json(script_path, script_data)
        beats_editor.save_initial_beats(
            settings, job_id, script.beats, script.full_voiceover_text
        )
    else:
        script_data = _load_script(script_path)
        if not script_data:
            raise FileNotFoundError("Missing script.json for partial regeneration")
        script_data = script_data

    title = script_data.get("title", "")
    beats = script_data.get("beats", [])

    quality_report = {"hook_attempts": [], "caption_attempts": []}
    if req.quality_gate_enabled and "script" in steps:
        updated, attempts = apply_hook_gate(
            settings,
            script_data,
            req.min_hook_score,
            req.max_retries,
            req.style,
            log_cb=lambda msg: _update(job_state, log_path, 10, msg),
        )
        quality_report["hook_attempts"] = attempts
        script_data = updated
        beats = script_data.get("beats", [])
        beat_models = [ScriptBeat(**beat) for beat in beats]
        beats_editor.update_beats(settings, job_id, beat_models, script_data.get("hook"), title)
        write_json(script_path, script_data)
        save_report(job_dir, quality_report)

    _update(job_state, log_path, 15, "Synthesizing voiceover...")
    voice_path = job_dir / "voice.wav"
    if "voice" in steps:
        voice_path = tts.synthesize_voice(
            settings,
            script_data.get("full_voiceover_text", ""),
            req.voice,
            job_dir,
            req.speech_speed,
            job_id=job_id,
        )
    elif not voice_path.exists():
        raise FileNotFoundError("Missing voice.wav for partial regeneration")

    target_duration = _normalize_duration(req.duration_seconds, voice_path, settings.FFPROBE_PATH)
    _update(job_state, log_path, 30, f"Target duration set to {target_duration:.1f}s")

    transcript_path = job_dir / "transcript.json"
    ass_path = job_dir / "subtitles.ass"
    autofix_ass_path = job_dir / "subtitles_autofix.ass"
    preview_ass_path = job_dir / "preview_subtitles.ass"
    if "captions" in steps:
        _update(job_state, log_path, 45, "Transcribing voiceover...")
        words, segments = captions.transcribe_words(settings, voice_path)
        write_json(transcript_path, {"words": words})

        if req.quality_gate_enabled:
            words, attempts = apply_caption_gate(
                words, req.max_words_per_second, req.max_retries, log_cb=lambda msg: _update(job_state, log_path, 50, msg)
            )
            quality_report["caption_attempts"] = attempts
            write_json(transcript_path, {"words": words, "compressed": True})
            save_report(job_dir, quality_report)

        _update(job_state, log_path, 60, "Building subtitles...")
        captions.build_ass(settings, words, segments, ass_path, req.caption_style, plugin_manager)
        if req.caption_autofix_enabled:
            _update(job_state, log_path, 62, "Auto-fixing captions...")
            autofix_captions(
                settings,
                job_id,
                req.caption_style,
                plugin_manager,
                req.caption_autofix_mode,
                req.max_words_per_second,
                req.max_chars_per_line,
                req.min_caption_duration,
            )
    else:
        if not ass_path.exists():
            raise FileNotFoundError("Missing subtitles.ass for partial regeneration")

    effects_plan = plan_effects(job_dir, beats, req.impact_rate)
    zoom_beats = effects_plan.get("zoom_beats", [])
    shake_beats = effects_plan.get("shake_beats", [])

    _update(job_state, log_path, 70, "Selecting background clip...")
    beat_times = [float(beat.get("t", 0.0)) if isinstance(beat, dict) else float(beat.t) for beat in beats]
    clip_path = None
    bg_meta = {}
    if req.bg_mode == "stitched_clips":
        stitched_path = job_dir / "bg_stitched.mp4"
        bg_meta = background.build_stitched_background(
            settings,
            settings.BG_CLIPS_DIR,
            target_duration,
            req.seed,
            req.bg_category,
            stitched_path,
            job_id=job_id,
        )
        clip_path = stitched_path
        write_json(job_dir / "bg_segments.json", bg_meta)
    else:
        clip_path = editor.pick_background_clip(
            settings.BG_CLIPS_DIR, req.seed, req.bg_mode, req.bg_category
        )
        write_json(job_dir / "bg_segments.json", {"file": clip_path.name})

    output_path = job_dir / ("preview.mp4" if req.preview_mode else "final.mp4")
    if "render" in steps:
        preview_start = req.preview_start if req.preview_mode else 0.0
        preview_duration = req.preview_duration if req.preview_mode else target_duration
        preview_beats = [
            t - preview_start
            for t in beat_times
            if preview_start <= t <= preview_start + preview_duration
        ]
        preview_words = []
        if req.preview_mode:
            if transcript_path.exists():
                try:
                    transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
                    preview_words = transcript.get("words", [])
                except Exception:
                    preview_words = []
            if preview_words:
                captions.build_ass(
                    settings,
                    preview_words,
                    [],
                    preview_ass_path,
                    req.caption_style,
                    plugin_manager,
                    preview_start=preview_start,
                    preview_duration=preview_duration,
                )
                ass_used = preview_ass_path
            else:
                ass_used = ass_path
        else:
            ass_used = autofix_ass_path if autofix_ass_path.exists() else ass_path

        _update(job_state, log_path, 85, "Rendering final video...")
        hotspots = []
        try:
            rel_path = clip_path.resolve().relative_to(settings.ASSETS_DIR.resolve()).as_posix()
            hotspots = get_hotspots(settings, rel_path)
        except Exception:
            hotspots = []

        zoom_used = zoom_beats
        shake_used = shake_beats
        if req.preview_mode:
            zoom_used = [
                t - preview_start
                for t in zoom_beats
                if preview_start <= t <= preview_start + preview_duration
            ]
            shake_used = [
                t - preview_start
                for t in shake_beats
                if preview_start <= t <= preview_start + preview_duration
            ]

        editor.render_video(
            settings=settings,
            clip_path=clip_path,
            voice_path=voice_path,
            ass_path=ass_used,
            output_path=output_path,
            target_duration=target_duration,
            mode=req.bg_mode,
            seed=req.seed,
            beat_times=preview_beats if req.preview_mode else beat_times,
            zoom_beats=zoom_used,
            shake_beats=shake_used,
            music_bed=req.music_bed,
            sfx_pack=req.sfx_pack,
            zoom_punch_strength=req.zoom_punch_strength,
            shake_strength=req.shake_strength,
            drift_strength=req.drift_strength,
            loop_smoothing_seconds=req.loop_smoothing_seconds,
            render_mode=req.render_mode,
            audio_mastering_preset=req.audio_mastering_preset,
            music_ducking_strength=req.music_ducking_strength,
            plugin_manager=plugin_manager,
            preview_mode=req.preview_mode,
            preview_start=preview_start,
            preview_duration=preview_duration,
            hotspots=hotspots,
            job_id=job_id,
            log_cb=lambda msg: _update(job_state, log_path, 86, msg),
        )
    elif not output_path.exists():
        raise FileNotFoundError("Missing final.mp4 for partial regeneration")

    thumb_path = job_dir / "thumb.jpg"
    thumb_styled_path = job_dir / "thumb_styled.jpg"
    if "render" in steps and not req.preview_mode:
        _update(job_state, log_path, 95, "Generating thumbnails...")
        editor.render_thumbnails(
            settings,
            output_path,
            thumb_path,
            thumb_styled_path,
            title if title else "Viral Short",
            target_duration,
            job_id=job_id,
        )

    validation = validate_output(
        settings,
        output_path,
        preview_duration if req.preview_mode else target_duration,
        job_id=job_id,
    )
    write_validation(job_dir, validation)
    if not validation.get("ok"):
        _update(job_state, log_path, 99, f"Validation failed: {validation}")
        raise ValueError("Output validation failed")

    if not req.preview_mode:
        try:
            compute_virality_score(settings, job_id)
        except Exception as exc:
            _update(job_state, log_path, 99, f"Virality score failed: {exc}")

    _update(job_state, log_path, 100, "Done.")
    return output_path
