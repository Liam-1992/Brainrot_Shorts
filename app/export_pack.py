from __future__ import annotations

import json
import zipfile
from pathlib import Path

from .llm import generate_text


def build_publish_pack(settings, job_id: str) -> Path:
    job_dir = settings.OUTPUTS_DIR / job_id
    script = _read_json(job_dir / "script.json")
    request = _read_json(job_dir / "request.json")

    title = script.get("title") or script.get("hook") or "Shorts Studio"
    hook = script.get("hook") or ""
    beats = script.get("beats") or []

    metadata = {
        "title": title,
        "hook": hook,
        "hashtags": script.get("keywords", []),
        "description": "",
        "beats": beats,
        "preset": request.get("preset_name"),
        "settings": request,
    }
    llm_payload = _generate_publish_metadata(settings, title, hook, beats)
    if llm_payload:
        metadata["hashtags"] = llm_payload.get("hashtags", metadata["hashtags"])
        metadata["description"] = llm_payload.get("description", "")
    if not metadata["description"]:
        metadata["description"] = hook or title

    meta_path = job_dir / "metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    zip_path = job_dir / "publish_pack.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        _add_if_exists(archive, job_dir / "final.mp4", "final.mp4")
        _add_if_exists(archive, job_dir / "thumb.jpg", "thumb.jpg")
        _add_if_exists(archive, job_dir / "thumb_styled.jpg", "thumb_styled.jpg")
        archive.write(meta_path, "metadata.json")

    return zip_path


def _add_if_exists(archive: zipfile.ZipFile, path: Path, arcname: str) -> None:
    if path.exists():
        archive.write(path, arcname)


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _generate_publish_metadata(settings, title: str, hook: str, beats: list) -> dict:
    system = "You generate social media metadata. Return strict JSON only."
    prompt = (
        f"Title: {title}\n"
        f"Hook: {hook}\n"
        f"Beats: {len(beats)}\n"
        "Return JSON: {\"description\":\"...\",\"hashtags\":[\"#tag\",\"#tag\"]}"
    )
    try:
        raw = generate_text(settings, system, prompt, seed=None)
    except Exception:
        return {}
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    try:
        return json.loads(raw[start : end + 1])
    except Exception:
        return {}
