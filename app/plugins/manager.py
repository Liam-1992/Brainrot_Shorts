from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from types import ModuleType
from typing import Callable, List


@dataclass
class PluginHooks:
    script_hooks: List[Callable] = field(default_factory=list)
    caption_hooks: List[Callable] = field(default_factory=list)
    audio_hooks: List[Callable] = field(default_factory=list)
    video_hooks: List[Callable] = field(default_factory=list)


class PluginManager:
    def __init__(self, enabled: List[str]):
        self.enabled = [name.strip() for name in enabled if name.strip()]
        self.hooks = PluginHooks()
        self.loaded: List[str] = []

    def load(self) -> None:
        for name in self.enabled:
            module_name = f"app.plugins.{name}"
            try:
                module = importlib.import_module(module_name)
            except Exception:
                continue
            self._register_module(module)

    def _register_module(self, module: ModuleType) -> None:
        if hasattr(module, "postprocess_script"):
            self.hooks.script_hooks.append(module.postprocess_script)
        if hasattr(module, "augment_caption_style"):
            self.hooks.caption_hooks.append(module.augment_caption_style)
        if hasattr(module, "augment_audio_filters"):
            self.hooks.audio_hooks.append(module.augment_audio_filters)
        if hasattr(module, "augment_video_filters"):
            self.hooks.video_hooks.append(module.augment_video_filters)
        if getattr(module, "PLUGIN_NAME", None):
            self.loaded.append(module.PLUGIN_NAME)
        else:
            self.loaded.append(module.__name__.split(".")[-1])

    def apply_script(self, script: dict, context: dict) -> dict:
        output = script
        for hook in self.hooks.script_hooks:
            output = hook(output, context)
        return output

    def apply_caption_style(self, style: dict, context: dict) -> dict:
        output = style
        for hook in self.hooks.caption_hooks:
            output = hook(output, context)
        return output

    def apply_audio_filters(self, filters: list[str], context: dict) -> list[str]:
        output = filters
        for hook in self.hooks.audio_hooks:
            output = hook(output, context)
        return output

    def apply_video_filters(self, filters: list[str], context: dict) -> list[str]:
        output = filters
        for hook in self.hooks.video_hooks:
            output = hook(output, context)
        return output
