from __future__ import annotations

import json
import random
from pathlib import Path

from .audio_mastering import build_audio_filter_complex
from .ffmpeg_fallbacks import run_attempts
from .utils import ffmpeg_filter_path, get_media_duration, run_subprocess


def _load_clip_metadata(bg_dir: Path) -> dict:
    meta_path = bg_dir / "clips.json"
    if not meta_path.exists():
        return {}
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def pick_background_clip(
    bg_dir: Path,
    seed: int | None,
    mode: str,
    category: str | None,
) -> Path:
    clips = sorted([p for p in bg_dir.iterdir() if p.suffix.lower() in {".mp4", ".mov", ".mkv"}])
    if not clips:
        raise FileNotFoundError("No background clips found in assets/bg_clips")
    if mode == "single_clip_loop":
        return clips[0]

    if category:
        meta = _load_clip_metadata(bg_dir)
        tagged = []
        for clip in meta.get("clips", []):
            tags = [t.lower() for t in clip.get("tags", [])]
            if category.lower() in tags:
                tagged.append(bg_dir / clip.get("file", ""))
        tagged = [p for p in tagged if p.exists()]
        if tagged:
            rng = random.Random(seed)
            return rng.choice(tagged)

    rng = random.Random(seed)
    return rng.choice(clips)


def build_background_args(
    clip_path: Path,
    target_duration: float,
    ffprobe_path: str,
    mode: str,
    seed: int | None,
    hotspots: list[dict] | None = None,
) -> list[str]:
    duration = get_media_duration(clip_path, ffprobe_path)
    if duration <= 0:
        return ["-stream_loop", "-1", "-i", str(clip_path)]

    if mode == "single_clip_loop":
        return ["-stream_loop", "-1", "-i", str(clip_path)]

    if duration > target_duration:
        max_start = max(0.0, duration - target_duration)
        rng = random.Random(seed)
        start = _pick_hotspot_start(hotspots, rng, max_start, target_duration)
        return ["-ss", f"{start:.2f}", "-t", f"{target_duration:.2f}", "-i", str(clip_path)]
    return ["-stream_loop", "-1", "-i", str(clip_path)]


def select_music_bed(music_dir: Path, music_bed: str, seed: int | None) -> Path | None:
    if music_bed == "none":
        return None
    files = sorted([p for p in music_dir.iterdir() if p.suffix.lower() in {".mp3", ".wav", ".m4a"}])
    if not files:
        return None
    if music_bed == "random":
        rng = random.Random(seed)
        return rng.choice(files)
    chosen = music_dir / music_bed
    return chosen if chosen.exists() else None


def select_sfx_pack(sfx_dir: Path, sfx_pack: str) -> dict:
    if sfx_pack == "none":
        return {}
    pack_dir = sfx_dir / sfx_pack
    if sfx_pack == "default":
        pack_dir = sfx_dir / "default"
    if not pack_dir.exists():
        return {}
    whoosh = sorted(pack_dir.glob("*whoosh*.wav"))
    boom = sorted(pack_dir.glob("*boom*.wav"))
    return {"whoosh": whoosh, "boom": boom}


def build_video_filters(
    ass_path: Path,
    fonts_dir: Path,
    zoom_beats: list[float],
    shake_beats: list[float],
    zoom_punch_strength: float,
    shake_strength: float,
    drift_strength: float,
    plugin_manager,
) -> str:
    subtitle_path = ffmpeg_filter_path(ass_path)
    fonts_dir_escaped = ffmpeg_filter_path(fonts_dir)

    base_zoom = 1.0 + drift_strength * 0.02
    punches = []
    for beat in zoom_beats[:24]:
        start = beat
        end = beat + 0.35
        punches.append(f"if(between(t,{start:.2f},{end:.2f}),{zoom_punch_strength}*0.12,0)")
    punch_expr = "+".join(punches) if punches else "0"
    zoom_expr = f"{base_zoom}+({punch_expr})"

    filters = [
        "scale=1080:1920:force_original_aspect_ratio=increase",
        f"zoompan=z='{zoom_expr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920",
    ]

    if shake_strength > 0.0 and shake_beats:
        shake_px = max(1.0, shake_strength * 12.0)
        terms_x = [
            f"if(between(t,{beat:.2f},{(beat + 0.25):.2f}),sin(t*40)*{shake_px:.2f},0)"
            for beat in shake_beats[:20]
        ]
        terms_y = [
            f"if(between(t,{beat:.2f},{(beat + 0.25):.2f}),cos(t*55)*{shake_px:.2f},0)"
            for beat in shake_beats[:20]
        ]
        expr_x = "+".join(terms_x) if terms_x else "0"
        expr_y = "+".join(terms_y) if terms_y else "0"
        filters.append(
            "crop=1080:1920:"
            f"x='(iw-ow)/2 + ({expr_x})':"
            f"y='(ih-oh)/2 + ({expr_y})'"
        )
    else:
        filters.append("crop=1080:1920")

    filters.append("setsar=1")
    filters = plugin_manager.apply_video_filters(filters, {"type": "video_filters"})
    filters.append(f"subtitles='{subtitle_path}':fontsdir='{fonts_dir_escaped}'")
    return ",".join(filters)


def _build_audio_filters(
    voice_index: int,
    music_index: int | None,
    sfx_indices: list[tuple[int, int]],
    target_duration: float,
    start_offset: float,
    mastering_preset: str,
    ducking_strength: float,
    plugin_manager,
) -> str:
    filter_complex = build_audio_filter_complex(
        voice_index=voice_index,
        music_index=music_index,
        sfx_indices=sfx_indices,
        target_duration=target_duration,
        start_offset=start_offset,
        mastering_preset=mastering_preset,
        ducking_strength=ducking_strength,
    )
    filters = filter_complex.split(";")
    filters = plugin_manager.apply_audio_filters(filters, {"type": "audio_filters"})
    return ";".join(filters)


def render_video(
    settings,
    clip_path: Path,
    voice_path: Path,
    ass_path: Path,
    output_path: Path,
    target_duration: float,
    mode: str,
    seed: int | None,
    beat_times: list[float],
    zoom_beats: list[float],
    shake_beats: list[float],
    music_bed: str,
    sfx_pack: str,
    zoom_punch_strength: float,
    shake_strength: float,
    drift_strength: float,
    loop_smoothing_seconds: float,
    render_mode: str,
    audio_mastering_preset: str,
    music_ducking_strength: float,
    plugin_manager,
    preview_mode: bool = False,
    preview_start: float = 0.0,
    preview_duration: float = 10.0,
    hotspots: list[dict] | None = None,
    job_id: str | None = None,
    log_cb=None,
) -> None:
    render_duration = preview_duration if preview_mode else target_duration
    start_offset = preview_start if preview_mode else 0.0

    if preview_mode:
        if mode == "single_clip_loop":
            bg_args = [
                "-stream_loop",
                "-1",
                "-ss",
                f"{preview_start:.2f}",
                "-t",
                f"{render_duration:.2f}",
                "-i",
                str(clip_path),
            ]
        else:
            bg_args = [
                "-ss",
                f"{preview_start:.2f}",
                "-t",
                f"{render_duration:.2f}",
                "-i",
                str(clip_path),
            ]
    else:
        if mode == "single_clip_loop" and loop_smoothing_seconds > 0:
            looped_path = output_path.parent / "bg_looped.mp4"
            clip_path = _prepare_smoothed_loop(
                settings, clip_path, looped_path, loop_smoothing_seconds, job_id
            )
        bg_args = build_background_args(
            clip_path,
            target_duration,
            settings.FFPROBE_PATH,
            mode,
            seed,
            hotspots,
        )

    music_path = select_music_bed(settings.MUSIC_DIR, music_bed, seed)
    sfx_pack_files = select_sfx_pack(settings.SFX_DIR, sfx_pack)

    args = [
        settings.FFMPEG_PATH,
        "-y",
        *bg_args,
        "-i",
        str(voice_path),
    ]

    input_index = 2
    music_index = None
    if music_path:
        args.extend(["-stream_loop", "-1", "-i", str(music_path)])
        music_index = input_index
        input_index += 1

    sfx_indices: list[tuple[int, int]] = []
    if sfx_pack_files:
        whoosh = sfx_pack_files.get("whoosh", [])
        boom = sfx_pack_files.get("boom", [])
        for idx, beat_time in enumerate(beat_times):
            if whoosh:
                sfx_file = whoosh[idx % len(whoosh)]
                args.extend(["-i", str(sfx_file)])
                sfx_indices.append((input_index, int(beat_time * 1000)))
                input_index += 1
            if boom and idx % 3 == 0:
                sfx_file = boom[idx % len(boom)]
                args.extend(["-i", str(sfx_file)])
                sfx_indices.append((input_index, int(beat_time * 1000)))
                input_index += 1

    vf = build_video_filters(
        ass_path,
        settings.FONTS_DIR,
        zoom_beats,
        shake_beats,
        zoom_punch_strength,
        shake_strength,
        drift_strength,
        plugin_manager,
    )

    filter_complex = _build_audio_filters(
        voice_index=1,
        music_index=music_index,
        sfx_indices=sfx_indices,
        target_duration=render_duration,
        start_offset=start_offset,
        mastering_preset=audio_mastering_preset,
        ducking_strength=music_ducking_strength,
        plugin_manager=plugin_manager,
    )
    if log_cb:
        log_cb(f"Audio filters: {filter_complex}")

    preset = "veryfast"
    crf = "18"
    if render_mode == "preview":
        preset = "ultrafast"
        crf = "26"

    args.extend(
        [
            "-t",
            f"{render_duration:.2f}",
            "-vf",
            vf,
            "-filter_complex",
            filter_complex,
            "-map",
            "0:v:0",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-preset",
            preset,
            "-crf",
            crf,
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(output_path),
        ]
    )
    def attempt_main() -> None:
        run_subprocess(args, job_id=job_id)

    vf_simple = ",".join(
        [
            "scale=1080:1920:force_original_aspect_ratio=increase",
            "crop=1080:1920",
            "setsar=1",
            f"subtitles='{ffmpeg_filter_path(ass_path)}':fontsdir='{ffmpeg_filter_path(settings.FONTS_DIR)}'",
        ]
    )

    vf_plain = ",".join(
        [
            "scale=1080:1920:force_original_aspect_ratio=increase",
            "crop=1080:1920",
            "setsar=1",
        ]
    )

    def _build_args_with_vf(vf_value: str, out_path: Path) -> list[str]:
        new_args = list(args)
        vf_index = new_args.index("-vf") + 1
        new_args[vf_index] = vf_value
        new_args[-1] = str(out_path)
        return new_args

    def attempt_simple() -> None:
        run_subprocess(_build_args_with_vf(vf_simple, output_path), job_id=job_id)

    def attempt_plain() -> None:
        run_subprocess(_build_args_with_vf(vf_plain, output_path), job_id=job_id)

    def attempt_plain_then_subs() -> None:
        temp_path = output_path.parent / "render_plain.mp4"
        run_subprocess(_build_args_with_vf(vf_plain, temp_path), job_id=job_id)
        burn_args = [
            settings.FFMPEG_PATH,
            "-y",
            "-i",
            str(temp_path),
            "-vf",
            f"subtitles='{ffmpeg_filter_path(ass_path)}':fontsdir='{ffmpeg_filter_path(settings.FONTS_DIR)}'",
            "-c:v",
            "libx264",
            "-preset",
            preset,
            "-crf",
            crf,
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(output_path),
        ]
        run_subprocess(burn_args, job_id=job_id)

    def attempt_fps_normalized() -> None:
        vf_fps = vf_plain + ",fps=30"
        run_subprocess(_build_args_with_vf(vf_fps, output_path), job_id=job_id)

    attempts = [
        ("primary", attempt_main),
        ("simple", attempt_simple),
        ("plain", attempt_plain),
        ("plain_then_subs", attempt_plain_then_subs),
        ("fps_normalized", attempt_fps_normalized),
    ]
    run_attempts(attempts, log_cb=log_cb)


def render_thumbnails(
    settings,
    video_path: Path,
    thumb_path: Path,
    thumb_styled_path: Path,
    title_text: str,
    duration: float,
    job_id: str | None = None,
) -> None:
    mid_time = max(0.1, duration / 2.0)
    args = [
        settings.FFMPEG_PATH,
        "-y",
        "-ss",
        f"{mid_time:.2f}",
        "-i",
        str(video_path),
        "-frames:v",
        "1",
        "-q:v",
        "2",
        str(thumb_path),
    ]
    run_subprocess(args, job_id=job_id)

    fonts_dir = ffmpeg_filter_path(settings.FONTS_DIR)
    safe_text = title_text.replace(":", "\\:").replace("'", "\\'")
    draw = (
        f"drawtext=text='{safe_text}':fontcolor=white:fontsize=72:"
        "box=1:boxcolor=black@0.55:boxborderw=16:"
        "x=(w-text_w)/2:y=h*0.75:shadowx=2:shadowy=2"
    )
    args = [
        settings.FFMPEG_PATH,
        "-y",
        "-i",
        str(thumb_path),
        "-vf",
        f"{draw}:fontsdir='{fonts_dir}'",
        "-q:v",
        "2",
        str(thumb_styled_path),
    ]
    run_subprocess(args, job_id=job_id)


def _pick_hotspot_start(
    hotspots: list[dict] | None,
    rng: random.Random,
    max_start: float,
    target_duration: float,
) -> float:
    if not hotspots:
        return rng.uniform(0.0, max_start)
    candidates = [h for h in hotspots if isinstance(h, dict)]
    if not candidates:
        return rng.uniform(0.0, max_start)
    choice = rng.choice(candidates)
    start = float(choice.get("start", 0.0))
    end = float(choice.get("end", max_start))
    if end < start:
        start, end = end, start
    if end - start > target_duration:
        start = rng.uniform(start, end - target_duration)
    start = max(0.0, min(start, max_start))
    return start


def _prepare_smoothed_loop(
    settings,
    clip_path: Path,
    output_path: Path,
    smoothing_seconds: float,
    job_id: str | None,
) -> Path:
    if output_path.exists():
        return output_path
    duration = get_media_duration(clip_path, settings.FFPROBE_PATH)
    if duration <= smoothing_seconds * 1.5:
        return clip_path
    offset = max(0.0, duration - smoothing_seconds)
    filter_complex = (
        f"[0:v]setpts=PTS-STARTPTS[v0];"
        f"[0:v]setpts=PTS-STARTPTS[v1];"
        f"[v0][v1]xfade=transition=fade:duration={smoothing_seconds:.2f}:"
        f"offset={offset:.2f},format=yuv420p[bg]"
    )
    args = [
        settings.FFMPEG_PATH,
        "-y",
        "-i",
        str(clip_path),
        "-filter_complex",
        filter_complex,
        "-map",
        "[bg]",
        "-an",
        "-t",
        f"{duration:.2f}",
        str(output_path),
    ]
    run_subprocess(args, job_id=job_id)
    return output_path
