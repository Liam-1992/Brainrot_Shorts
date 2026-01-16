from __future__ import annotations

import random
from pathlib import Path

from .assets_manager import get_hotspots
from .editor import _load_clip_metadata
from .utils import get_media_duration, run_subprocess


def select_clips(bg_dir: Path, category: str | None, seed: int | None) -> list[Path]:
    clips = sorted([p for p in bg_dir.iterdir() if p.suffix.lower() in {".mp4", ".mov", ".mkv"}])
    if not clips:
        return []
    if category:
        meta = _load_clip_metadata(bg_dir)
        tagged = []
        for clip in meta.get("clips", []):
            tags = [t.lower() for t in clip.get("tags", [])]
            if category.lower() in tags:
                tagged.append(bg_dir / clip.get("file", ""))
        tagged = [p for p in tagged if p.exists()]
        if tagged:
            clips = tagged
    rng = random.Random(seed)
    rng.shuffle(clips)
    return clips


def build_stitched_background(
    settings,
    bg_dir: Path,
    target_duration: float,
    seed: int | None,
    category: str | None,
    output_path: Path,
    job_id: str | None = None,
) -> dict:
    clips = select_clips(bg_dir, category, seed)
    if not clips:
        raise FileNotFoundError("No background clips available for stitching.")

    rng = random.Random(seed)
    segments = []
    remaining = target_duration
    clip_index = 0
    while remaining > 0.1 and clip_index < len(clips):
        clip = clips[clip_index]
        clip_index += 1
        duration = get_media_duration(clip, settings.FFPROBE_PATH)
        if duration <= 0.2:
            continue
        seg_len = min(remaining, rng.uniform(3.0, 6.0))
        max_start = max(0.0, duration - seg_len)
        rel = None
        try:
            rel = clip.resolve().relative_to(settings.ASSETS_DIR.resolve()).as_posix()
        except Exception:
            rel = None
        hotspots = get_hotspots(settings, rel) if rel else []
        start = _pick_hotspot_start(hotspots, rng, max_start, seg_len)
        segments.append({"file": clip.name, "start": round(start, 2), "duration": round(seg_len, 2)})
        remaining -= seg_len

    if not segments:
        raise ValueError("Unable to create stitched background segments.")

    args = [settings.FFMPEG_PATH, "-y"]
    for seg in segments:
        clip_path = bg_dir / seg["file"]
        args.extend(["-ss", f"{seg['start']:.2f}", "-t", f"{seg['duration']:.2f}", "-i", str(clip_path)])

    filter_parts = []
    for index in range(len(segments)):
        filter_parts.append(
            f"[{index}:v]scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,setsar=1[v{index}]"
        )
    concat_inputs = "".join(f"[v{index}]" for index in range(len(segments)))
    filter_parts.append(f"{concat_inputs}concat=n={len(segments)}:v=1:a=0[bg]")
    filter_complex = ";".join(filter_parts)

    args.extend(
        [
            "-filter_complex",
            filter_complex,
            "-map",
            "[bg]",
            "-an",
            str(output_path),
        ]
    )
    run_subprocess(args, job_id=job_id)
    return {"segments": segments, "output_path": str(output_path)}


def _pick_hotspot_start(
    hotspots: list[dict],
    rng: random.Random,
    max_start: float,
    seg_len: float,
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
    if end - start > seg_len:
        start = rng.uniform(start, end - seg_len)
    start = max(0.0, min(start, max_start))
    return start
