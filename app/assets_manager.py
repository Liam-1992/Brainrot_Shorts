from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from .db import get_connection
from .utils import get_media_duration

ASSET_TYPES = {
    "bg_clips": {"exts": {".mp4", ".mov", ".mkv"}},
    "music": {"exts": {".mp3", ".wav", ".m4a"}},
    "sfx": {"exts": {".mp3", ".wav", ".m4a"}},
    "fonts": {"exts": {".ttf", ".otf"}},
}


def _asset_dir(settings, asset_type: str) -> Path:
    if asset_type == "bg_clips":
        return settings.BG_CLIPS_DIR
    if asset_type == "music":
        return settings.MUSIC_DIR
    if asset_type == "sfx":
        return settings.SFX_DIR
    if asset_type == "fonts":
        return settings.FONTS_DIR
    raise ValueError("Unknown asset type")


def resolve_asset_path(settings, rel_path: str) -> Path:
    raw = rel_path.strip().replace("\\", "/")
    if raw.startswith("assets/"):
        raw = raw[len("assets/") :]
    if raw.startswith("/") or ":" in raw:
        raise ValueError("Invalid path")
    candidate = (settings.ASSETS_DIR / raw).resolve()
    base = settings.ASSETS_DIR.resolve()
    if not candidate.is_relative_to(base):
        raise ValueError("Path traversal blocked")
    return candidate


def list_assets(settings, asset_type: str, query: str | None = None) -> List[Dict]:
    asset_type = _normalize_type(asset_type)
    base_dir = _asset_dir(settings, asset_type)
    exts = ASSET_TYPES[asset_type]["exts"]
    files = []
    if asset_type == "sfx":
        candidates = base_dir.rglob("*")
    else:
        candidates = base_dir.glob("*")
    for path in candidates:
        if not path.is_file():
            continue
        if path.suffix.lower() not in exts:
            continue
        rel_path = path.resolve().relative_to(settings.ASSETS_DIR.resolve()).as_posix()
        files.append(
            {
                "path": rel_path,
                "name": path.name,
                "size_bytes": path.stat().st_size,
                "type": asset_type,
            }
        )

    tags_map = _tags_for_type(settings, asset_type)
    for item in files:
        item["tags"] = tags_map.get(item["path"], [])

    if query:
        term = query.strip().lower()
        files = [
            item
            for item in files
            if term in item["name"].lower()
            or any(term in tag.lower() for tag in item.get("tags", []))
        ]
    return sorted(files, key=lambda x: x["name"].lower())


def get_metadata(settings, rel_path: str) -> Dict:
    path = resolve_asset_path(settings, rel_path)
    if not path.exists():
        raise FileNotFoundError("Asset not found")
    asset_type = _detect_type(settings, path)
    size_bytes = path.stat().st_size
    duration = None
    if path.suffix.lower() in {".mp4", ".mov", ".mkv", ".mp3", ".wav", ".m4a"}:
        try:
            duration = get_media_duration(path, settings.FFPROBE_PATH)
        except Exception:
            duration = None
    tags = get_tags(settings, rel_path, asset_type)
    hotspots = get_hotspots(settings, rel_path) if asset_type == "bg_clips" else []
    return {
        "path": rel_path,
        "name": path.name,
        "type": asset_type,
        "size_bytes": size_bytes,
        "duration_seconds": duration,
        "tags": tags,
        "hotspots": hotspots,
    }


def get_tags(settings, rel_path: str, asset_type: str) -> List[str]:
    with get_connection(settings.DB_PATH) as conn:
        row = conn.execute(
            "SELECT tags FROM asset_tags WHERE path = ? AND type = ?",
            (rel_path, asset_type),
        ).fetchone()
    if row and row["tags"]:
        try:
            return json.loads(row["tags"])
        except Exception:
            return []
    return []


def set_tags(settings, rel_path: str, asset_type: str, tags: List[str]) -> None:
    now = datetime.utcnow().isoformat()
    payload = json.dumps(sorted({t.strip() for t in tags if t.strip()}))
    with get_connection(settings.DB_PATH) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO asset_tags (path, type, tags, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (rel_path, asset_type, payload, now),
        )
        conn.commit()


def get_tags_for_type(settings, asset_type: str) -> Dict[str, List[str]]:
    asset_type = _normalize_type(asset_type)
    return _tags_for_type(settings, asset_type)


def get_hotspots(settings, rel_path: str) -> List[Dict]:
    with get_connection(settings.DB_PATH) as conn:
        row = conn.execute(
            "SELECT hotspots FROM clip_hotspots WHERE path = ?",
            (rel_path,),
        ).fetchone()
    if row and row["hotspots"]:
        try:
            return json.loads(row["hotspots"])
        except Exception:
            return []
    return []


def set_hotspots(settings, rel_path: str, hotspots: List[Dict]) -> None:
    now = datetime.utcnow().isoformat()
    payload = json.dumps(hotspots, indent=2)
    with get_connection(settings.DB_PATH) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO clip_hotspots (path, hotspots, updated_at)
            VALUES (?, ?, ?)
            """,
            (rel_path, payload, now),
        )
        conn.commit()


def _normalize_type(asset_type: str) -> str:
    if asset_type not in ASSET_TYPES:
        raise ValueError("Invalid asset type")
    return asset_type


def _detect_type(settings, path: Path) -> str:
    for key in ASSET_TYPES:
        base = _asset_dir(settings, key).resolve()
        if path.resolve().is_relative_to(base):
            return key
    raise ValueError("Unknown asset type")


def _tags_for_type(settings, asset_type: str) -> Dict[str, List[str]]:
    tags_map: Dict[str, List[str]] = {}
    with get_connection(settings.DB_PATH) as conn:
        rows = conn.execute(
            "SELECT path, tags FROM asset_tags WHERE type = ?",
            (asset_type,),
        ).fetchall()
    for row in rows:
        try:
            tags_map[row["path"]] = json.loads(row["tags"]) if row["tags"] else []
        except Exception:
            tags_map[row["path"]] = []
    return tags_map
