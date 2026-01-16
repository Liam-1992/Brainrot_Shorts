from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


class PresetManager:
    def __init__(self, preset_path: Path):
        self.preset_path = preset_path

    def _load(self) -> Dict[str, Dict[str, Any]]:
        if not self.preset_path.exists():
            return {}
        try:
            data = json.loads(self.preset_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save(self, data: Dict[str, Dict[str, Any]]) -> None:
        self.preset_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.preset_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp_path.replace(self.preset_path)

    def list_presets(self) -> List[Dict[str, Any]]:
        data = self._load()
        return [value for _key, value in sorted(data.items())]

    def upsert(self, preset: Dict[str, Any]) -> Dict[str, Any]:
        data = self._load()
        name = str(preset.get("name", "")).strip()
        if not name:
            raise ValueError("Preset name is required")
        data[name] = preset
        self._save(data)
        return preset

    def delete(self, name: str) -> None:
        data = self._load()
        if name in data:
            del data[name]
            self._save(data)

    def get(self, name: str) -> Dict[str, Any] | None:
        data = self._load()
        return data.get(name)
