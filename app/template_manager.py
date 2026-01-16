from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class Template:
    name: str
    style: str
    description: str
    system_prompt: str
    schema: Dict[str, Any]
    beat_rules: Dict[str, Any]
    forbidden_words: List[str]
    safe_rewrites: Dict[str, str]


class TemplateManager:
    def __init__(self, templates_dir: Path):
        self.templates_dir = templates_dir
        self._templates: Dict[str, Template] = {}

    def load(self) -> None:
        self._templates.clear()
        if not self.templates_dir.exists():
            return
        for path in sorted(self.templates_dir.iterdir()):
            if path.suffix.lower() not in {".json", ".yaml", ".yml"}:
                continue
            data = self._load_file(path)
            if not data:
                continue
            try:
                template = self._validate(data)
            except Exception:
                continue
            self._templates[template.name] = template

    def _load_file(self, path: Path) -> Dict[str, Any] | None:
        if path.suffix.lower() == ".json":
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return None
        try:
            import yaml  # type: ignore
        except Exception:
            return None
        try:
            return yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _validate(self, data: Dict[str, Any]) -> Template:
        required = ["name", "style", "description", "system_prompt", "schema", "beat_rules"]
        for key in required:
            if key not in data:
                raise ValueError(f"Template missing {key}")
        return Template(
            name=str(data["name"]),
            style=str(data["style"]),
            description=str(data["description"]),
            system_prompt=str(data["system_prompt"]),
            schema=data.get("schema", {}),
            beat_rules=data.get("beat_rules", {}),
            forbidden_words=[str(word) for word in data.get("forbidden_words", [])],
            safe_rewrites={str(k): str(v) for k, v in data.get("safe_rewrites", {}).items()},
        )

    def list_templates(self) -> List[Template]:
        return list(self._templates.values())

    def get(self, name: str) -> Template | None:
        return self._templates.get(name)
