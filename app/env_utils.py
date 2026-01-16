from __future__ import annotations

import os
from pathlib import Path
from typing import Dict


def apply_env_updates(env_path: Path, updates: Dict[str, str]) -> None:
    if not updates:
        return
    _write_env(env_path, updates)
    for key, value in updates.items():
        if value == "":
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def _write_env(path: Path, updates: Dict[str, str]) -> None:
    lines = []
    existing = {}
    if path.exists():
        raw_lines = path.read_text(encoding="utf-8").splitlines()
        for idx, line in enumerate(raw_lines):
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                lines.append(line)
                continue
            key = stripped.split("=", 1)[0].strip()
            existing[key] = idx
            lines.append(line)
    else:
        lines = []

    for key, value in updates.items():
        formatted = f"{key}={_format_env_value(value)}"
        if key in existing:
            lines[existing[key]] = formatted
        else:
            lines.append(formatted)

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _format_env_value(value: str) -> str:
    if value == "":
        return ""
    needs_quotes = any(ch.isspace() for ch in value) or "#" in value or ";" in value
    if not needs_quotes:
        return value
    escaped = value.replace("\\", "\\\\").replace("\"", "\\\"")
    return f"\"{escaped}\""
