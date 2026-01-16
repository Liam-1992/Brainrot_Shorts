from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency
    load_dotenv = None


def _load_env() -> None:
    if load_dotenv is not None:
        load_dotenv()


def _env_path(name: str, default: Path) -> Path:
    raw = os.getenv(name, "").strip()
    return Path(raw) if raw else default


@dataclass(frozen=True)
class Settings:
    _loaded: bool = False

    def __post_init__(self) -> None:
        if not self._loaded:
            _load_env()
            object.__setattr__(self, "_loaded", True)

    @property
    def BASE_DIR(self) -> Path:
        return Path(__file__).resolve().parents[1]

    @property
    def ASSETS_DIR(self) -> Path:
        return _env_path("ASSETS_DIR", self.BASE_DIR / "assets")

    @property
    def BG_CLIPS_DIR(self) -> Path:
        return _env_path("BG_CLIPS_DIR", self.ASSETS_DIR / "bg_clips")

    @property
    def FONTS_DIR(self) -> Path:
        return _env_path("FONTS_DIR", self.ASSETS_DIR / "fonts")

    @property
    def MUSIC_DIR(self) -> Path:
        return _env_path("MUSIC_DIR", self.ASSETS_DIR / "music")

    @property
    def SFX_DIR(self) -> Path:
        return _env_path("SFX_DIR", self.ASSETS_DIR / "sfx")

    @property
    def OUTPUTS_DIR(self) -> Path:
        return _env_path("OUTPUTS_DIR", self.BASE_DIR / "outputs")

    @property
    def MODELS_DIR(self) -> Path:
        return _env_path("MODELS_DIR", self.BASE_DIR / "models")

    @property
    def TEMPLATES_DIR(self) -> Path:
        return _env_path("TEMPLATES_DIR", self.BASE_DIR / "app" / "templates")

    @property
    def CAPTION_STYLES_DIR(self) -> Path:
        return _env_path("CAPTION_STYLES_DIR", self.BASE_DIR / "app" / "caption_styles")

    @property
    def PRESETS_PATH(self) -> Path:
        return _env_path("PRESETS_PATH", self.BASE_DIR / "presets.json")

    @property
    def DB_PATH(self) -> Path:
        return _env_path("DB_PATH", self.BASE_DIR / "projects.db")

    @property
    def MAX_CONCURRENT_JOBS(self) -> int:
        return int(os.getenv("MAX_CONCURRENT_JOBS", "2"))

    @property
    def SUBPROCESS_TIMEOUT_SECONDS(self) -> float:
        return float(os.getenv("SUBPROCESS_TIMEOUT_SECONDS", "1800"))

    @property
    def ROUTING_MODE(self) -> str:
        return os.getenv("ROUTING_MODE", "manual").strip()

    @property
    def ROUTING_POLICY(self) -> str:
        return os.getenv("ROUTING_POLICY", "balanced").strip()

    @property
    def WATCH_FOLDER_PATH(self) -> Path | None:
        raw = os.getenv("WATCH_FOLDER_PATH", "").strip()
        return Path(raw) if raw else None

    @property
    def WATCH_FOLDER_ENABLED(self) -> bool:
        raw = os.getenv("WATCH_FOLDER_ENABLED", "false").strip().lower()
        return raw in {"1", "true", "yes", "on"}

    @property
    def PLUGINS_ENABLED(self) -> list[str]:
        raw = os.getenv("PLUGINS_ENABLED", "").strip()
        if not raw:
            return []
        return [item.strip() for item in raw.split(",") if item.strip()]

    @property
    def FFMPEG_PATH(self) -> str:
        return os.getenv("FFMPEG_PATH", "ffmpeg")

    @property
    def FFPROBE_PATH(self) -> str:
        return os.getenv("FFPROBE_PATH", "ffprobe")

    @property
    def PIPER_PATH(self) -> str:
        return os.getenv("PIPER_PATH", "piper")

    @property
    def PIPER_MODEL_PATH(self) -> str:
        return os.getenv("PIPER_MODEL_PATH", "").strip()

    @property
    def PIPER_VOICES_DIR(self) -> str:
        return os.getenv("PIPER_VOICES_DIR", "").strip()

    @property
    def LLM_BACKEND(self) -> str:
        return os.getenv("LLM_BACKEND", "llama_cpp").strip()

    @property
    def LLM_MODEL_PATH(self) -> str:
        return os.getenv("LLM_MODEL_PATH", "").strip()

    @property
    def LLM_HOOK_MODEL_PATH(self) -> str:
        return os.getenv("LLM_HOOK_MODEL_PATH", "").strip()

    @property
    def LLM_SCRIPT_MODEL_PATH(self) -> str:
        return os.getenv("LLM_SCRIPT_MODEL_PATH", "").strip()

    @property
    def LLM_MODEL_PATHS(self) -> list[str]:
        raw = os.getenv("LLM_MODEL_PATHS", "").strip()
        if not raw:
            return []
        return [item.strip() for item in raw.split(",") if item.strip()]

    @property
    def LLM_CTX(self) -> int:
        return int(os.getenv("LLM_CTX", "4096"))

    @property
    def LLM_MAX_TOKENS(self) -> int:
        return int(os.getenv("LLM_MAX_TOKENS", "512"))

    @property
    def LLM_TEMPERATURE(self) -> float:
        return float(os.getenv("LLM_TEMPERATURE", "0.8"))

    @property
    def LLM_N_GPU_LAYERS(self) -> int:
        return int(os.getenv("LLM_N_GPU_LAYERS", "0"))

    @property
    def WHISPER_MODEL_SIZE(self) -> str:
        return os.getenv("WHISPER_MODEL_SIZE", "base").strip()

    @property
    def WHISPER_MODEL_PATH(self) -> str:
        return os.getenv("WHISPER_MODEL_PATH", "").strip()

    @property
    def WHISPER_DEVICE(self) -> str:
        return os.getenv("WHISPER_DEVICE", "auto").strip()

    @property
    def WHISPER_COMPUTE_TYPE(self) -> str:
        return os.getenv("WHISPER_COMPUTE_TYPE", "auto").strip()

    @property
    def CAPTION_FONT(self) -> str:
        return os.getenv("CAPTION_FONT", "Impact").strip()

    @property
    def CAPTION_FONT_SIZE(self) -> int:
        return int(os.getenv("CAPTION_FONT_SIZE", "72"))

    def resolve_piper_model(self, voice: str) -> Path | None:
        if self.PIPER_MODEL_PATH:
            return Path(self.PIPER_MODEL_PATH)
        if self.PIPER_VOICES_DIR:
            return Path(self.PIPER_VOICES_DIR) / f"{voice}.onnx"
        models_dir = self.MODELS_DIR / "piper"
        if models_dir.exists():
            candidates = sorted(models_dir.rglob("*.onnx"))
            for candidate in candidates:
                if candidate.stem == voice or candidate.name.startswith(f"{voice}-"):
                    return candidate
            if candidates:
                return candidates[0]
        return None

    def resolve_llm_model_path(self) -> Path | None:
        if self.LLM_MODEL_PATH:
            return Path(self.LLM_MODEL_PATH)
        models_dir = self.MODELS_DIR / "llm"
        if not models_dir.exists():
            return None
        candidates = sorted(models_dir.rglob("*.gguf"))
        return candidates[0] if candidates else None

    def resolve_whisper_model_path(self) -> str:
        if self.WHISPER_MODEL_PATH:
            return self.WHISPER_MODEL_PATH
        models_dir = self.MODELS_DIR / "whisper"
        if not models_dir.exists():
            return ""
        candidates = sorted(models_dir.rglob("model.bin"))
        if candidates:
            return str(candidates[0].parent)
        return ""

    def available_voices(self) -> list[str]:
        voices = []
        if self.PIPER_VOICES_DIR:
            candidates = Path(self.PIPER_VOICES_DIR).glob("*.onnx")
            voices.extend([c.stem for c in candidates])
        models_dir = self.MODELS_DIR / "piper"
        if models_dir.exists():
            voices.extend([c.stem for c in models_dir.rglob("*.onnx")])
        return sorted(set(voices))
