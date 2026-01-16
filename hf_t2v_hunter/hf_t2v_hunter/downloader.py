from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List

from huggingface_hub import snapshot_download

from .types import Config, DownloadReport, DownloadedModel, ScoredModel


ALLOW_PATTERNS = [
    "model_index.json",
    "*.safetensors",
    "*.bin",
    "*.pt",
    "*.pth",
    "*.ckpt",
    "*.gguf",
    "*.json",
    "*.txt",
    "scheduler/*",
    "tokenizer/*",
    "text_encoder/*",
    "vae/*",
    "unet/*",
    "transformer/*",
    "README*",
    "LICENSE*",
]


def download_models(scored: List[ScoredModel], config: Config, dest: Path, top_n: int) -> DownloadReport:
    dest.mkdir(parents=True, exist_ok=True)
    downloaded: List[DownloadedModel] = []
    skipped: List[dict] = []
    total_bytes = 0

    selected = [item for item in scored if not item.filtered_out][:top_n]
    for item in selected:
        model = item.model
        size_bytes = model.total_weight_bytes()
        projected_gb = (total_bytes + size_bytes) / (1024**3)
        if projected_gb > config.max_disk_gb:
            skipped.append({"repo_id": model.repo_id, "reason": "max_disk_gb_exceeded"})
            continue

        target_dir = dest / model.repo_id.replace("/", "__")
        target_dir.mkdir(parents=True, exist_ok=True)
        try:
            local_path = snapshot_download(
                repo_id=model.repo_id,
                local_dir=str(target_dir),
                local_dir_use_symlinks=False,
                allow_patterns=ALLOW_PATTERNS,
            )
        except Exception as exc:
            skipped.append({"repo_id": model.repo_id, "reason": str(exc)})
            continue

        info = {
            "repo_id": model.repo_id,
            "license": model.license,
            "tags": model.tags,
            "score": item.score,
            "reasons": item.reasons,
            "vram_estimate": {
                "compatible": item.vram_estimate.compatible,
                "required_gb": item.vram_estimate.required_gb,
                "reasons": item.vram_estimate.reasons,
                "hints": item.vram_estimate.hints,
            },
            "downloaded_at": datetime.utcnow().isoformat(),
            "files": [s.name for s in model.siblings],
            "size_bytes": size_bytes,
        }
        info_path = Path(local_path) / "model_info.json"
        info_path.write_text(json.dumps(info, indent=2), encoding="utf-8")

        downloaded.append(
            DownloadedModel(
                repo_id=model.repo_id,
                local_path=str(local_path),
                size_bytes=size_bytes,
                info_path=str(info_path),
            )
        )
        total_bytes += size_bytes

    return DownloadReport(downloaded=downloaded, skipped=skipped, total_bytes=total_bytes)


def list_downloaded(dest: Path) -> List[dict]:
    if not dest.exists():
        return []
    results = []
    for entry in dest.iterdir():
        if not entry.is_dir():
            continue
        info_path = entry / "model_info.json"
        if not info_path.exists():
            continue
        try:
            payload = json.loads(info_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        results.append(payload)
    return results

