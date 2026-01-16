from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main() -> int:
    templates_dir = BASE / "app" / "templates"
    styles_dir = BASE / "app" / "caption_styles"
    missing = []

    if not templates_dir.exists():
        missing.append("templates dir")
    if not styles_dir.exists():
        missing.append("caption_styles dir")

    templates = sorted(templates_dir.glob("*.json")) if templates_dir.exists() else []
    styles = sorted(styles_dir.glob("*.json")) if styles_dir.exists() else []

    if not templates:
        missing.append("template files")
    if not styles:
        missing.append("caption style files")

    for path in templates:
        payload = _load_json(path)
        for key in ["name", "style", "system_prompt", "schema", "beat_rules"]:
            if key not in payload:
                print(f"Template missing {key}: {path}")
                return 1

    for path in styles:
        payload = _load_json(path)
        for key in ["name", "font", "font_size"]:
            if key not in payload:
                print(f"Caption style missing {key}: {path}")
                return 1

    if missing:
        print("Missing:", ", ".join(missing))
        return 1

    print("Self-check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
