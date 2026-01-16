from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from ..db import get_connection
from .benchmarks import list_benchmarks
from .registry import load_registry


def get_routing_config(settings) -> Dict[str, object]:
    default = {
        "routing_mode": settings.ROUTING_MODE,
        "policy": settings.ROUTING_POLICY,
        "hook_model": None,
        "script_model": None,
    }
    with get_connection(settings.DB_PATH) as conn:
        row = conn.execute(
            "SELECT value FROM routing_prefs WHERE key = ?",
            ("config",),
        ).fetchone()
    if not row:
        return default
    try:
        stored = json.loads(row["value"])
        default.update({k: stored.get(k, default[k]) for k in default})
        return default
    except Exception:
        return default


def save_routing_config(settings, payload: Dict[str, object]) -> Dict[str, object]:
    config = get_routing_config(settings)
    config.update(payload)
    with get_connection(settings.DB_PATH) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO routing_prefs (key, value, updated_at)
            VALUES (?, ?, ?)
            """,
            ("config", json.dumps(config), datetime.utcnow().isoformat()),
        )
        conn.commit()
    return config


def get_routing_status(settings) -> Dict[str, object]:
    config = get_routing_config(settings)
    registry = load_registry(settings)
    benchmarks = list_benchmarks(settings, limit=50)
    available_vram_gb = _available_vram_gb()
    hook_paths = pick_model_paths(registry, benchmarks, config, "hook", available_vram_gb)
    script_paths = pick_model_paths(registry, benchmarks, config, "script", available_vram_gb)
    return {
        "config": config,
        "registry": registry,
        "available_vram_gb": available_vram_gb,
        "selected": {
            "hook": hook_paths[0] if hook_paths else None,
            "script": script_paths[0] if script_paths else None,
        },
    }


def pick_model_paths(
    registry: Dict[str, List[dict]],
    benchmarks: List[dict],
    config: Dict[str, object],
    role: str,
    available_vram_gb: float | None = None,
) -> List[str]:
    candidates = [m for m in registry.get("llm", []) if m.get("role") in {role, "general"}]
    if not candidates:
        candidates = registry.get("llm", [])

    manual_name = None
    if role == "hook":
        manual_name = config.get("hook_model")
    elif role == "script":
        manual_name = config.get("script_model")

    if config.get("routing_mode") == "manual" and manual_name:
        for candidate in candidates:
            if candidate.get("name") == manual_name or candidate.get("path") == manual_name:
                return [candidate.get("path")]
        return [str(manual_name)]

    policy = config.get("policy", "balanced")
    bench_map = _benchmark_map(benchmarks)
    scored = []
    for candidate in candidates:
        path = str(candidate.get("path", ""))
        if not path:
            continue
        candidate_vram = candidate.get("vram_gb")
        if candidate_vram and available_vram_gb:
            try:
                if float(candidate_vram) > float(available_vram_gb):
                    continue
            except Exception:
                pass
        name = candidate.get("name") or Path(path).stem
        quality = float(candidate.get("quality", 0))
        if quality <= 0:
            try:
                quality = Path(path).stat().st_size / (1024 * 1024 * 1024)
            except Exception:
                quality = 0.0
        metrics = bench_map.get(name, {})
        speed = float(metrics.get("tokens_per_second", 0.0)) or 0.1
        if policy == "fastest":
            score = speed
        elif policy == "best_quality":
            score = quality
        else:
            score = quality * 0.7 + speed * 0.3
        scored.append((score, path))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [path for _, path in scored] or [c.get("path") for c in candidates if c.get("path")]


def _benchmark_map(benchmarks: List[dict]) -> Dict[str, dict]:
    mapping = {}
    for item in benchmarks:
        if item.get("tool") != "llm":
            continue
        mapping[item.get("model_name", "")] = item.get("metrics", {})
    return mapping


def _available_vram_gb() -> float | None:
    try:
        import torch  # type: ignore

        if not torch.cuda.is_available():
            return None
        props = torch.cuda.get_device_properties(0)
        return round(props.total_memory / (1024**3), 2)
    except Exception:
        return None
