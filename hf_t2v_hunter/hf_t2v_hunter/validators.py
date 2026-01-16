from __future__ import annotations

import json
from typing import Optional

from huggingface_hub import HfApi, hf_hub_download

from .types import Config, ValidationResult


def validate_model(repo_id: str, config: Config, smoke_test: bool = False) -> ValidationResult:
    api = HfApi()
    reasons = []
    try:
        info = api.model_info(repo_id)
    except Exception as exc:
        return ValidationResult(repo_id=repo_id, ok=False, mode="info", reasons=[str(exc)])

    files = [s.rfilename for s in info.siblings or []]
    if config.require_diffusers:
        if not any(name.endswith("model_index.json") for name in files):
            reasons.append("missing_model_index")

    card_data = getattr(info, "cardData", None) or getattr(info, "card_data", None)
    hints = []
    if card_data:
        hints.append(json.dumps(card_data))
    readme = _load_readme(repo_id)
    if readme:
        hints.append(readme)
    card_text = " ".join(hints).lower()
    if any(token in card_text for token in ("24gb", "a100", "h100", "40gb", "32gb")):
        reasons.append("high_vram_hint")

    if reasons:
        return ValidationResult(repo_id=repo_id, ok=False, mode="light", reasons=reasons)

    if smoke_test:
        return _smoke_test(repo_id, config)

    return ValidationResult(repo_id=repo_id, ok=True, mode="light", reasons=[])


def _smoke_test(repo_id: str, config: Config) -> ValidationResult:
    reasons = []
    try:
        import torch  # type: ignore
        from diffusers import DiffusionPipeline  # type: ignore

        pipe = DiffusionPipeline.from_pretrained(repo_id, torch_dtype=torch.float16)
        if torch.cuda.is_available():
            pipe = pipe.to("cuda")
        if hasattr(pipe, "enable_attention_slicing"):
            pipe.enable_attention_slicing()
        if hasattr(pipe, "enable_vae_slicing"):
            pipe.enable_vae_slicing()
        if config.allow_cpu_offload and hasattr(pipe, "enable_model_cpu_offload"):
            pipe.enable_model_cpu_offload()

        kwargs = {"num_inference_steps": 1}
        if "video" in pipe.__class__.__name__.lower():
            kwargs.update({"num_frames": 8, "height": 256, "width": 256})
        pipe("test prompt", **kwargs)
        return ValidationResult(repo_id=repo_id, ok=True, mode="smoke", reasons=[])
    except Exception as exc:
        msg = str(exc).lower()
        if "out of memory" in msg or "cuda" in msg:
            reasons.append("oom_or_cuda_error")
        else:
            reasons.append(str(exc))
        return ValidationResult(repo_id=repo_id, ok=False, mode="smoke", reasons=reasons)


def _load_readme(repo_id: str) -> Optional[str]:
    for name in ("README.md", "README.MD", "readme.md"):
        try:
            path = hf_hub_download(repo_id=repo_id, filename=name)
            with open(path, "r", encoding="utf-8") as handle:
                return handle.read()
        except Exception:
            continue
    return None

