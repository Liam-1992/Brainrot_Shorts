from __future__ import annotations

import json
from pathlib import Path
from typing import List

from .types import DownloadReport, ScoredModel


def write_json_report(path: Path, candidates: List[ScoredModel], top: List[ScoredModel], downloaded: DownloadReport | None = None) -> None:
    payload = {
        "candidates": [_serialize_model(m) for m in candidates],
        "top": [_serialize_model(m) for m in top],
        "downloaded": [d.__dict__ for d in downloaded.downloaded] if downloaded else [],
        "skipped": downloaded.skipped if downloaded else [],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_markdown_report(path: Path, top: List[ScoredModel]) -> None:
    lines = ["# hf_t2v_hunter report", "", "| Rank | Repo | Score | License | VRAM | Reasons |", "|---|---|---|---|---|---|"]
    for idx, item in enumerate(top, start=1):
        reasons = ", ".join(item.reasons[:3])
        vram = item.vram_estimate.required_gb if item.vram_estimate.required_gb else "?"
        lines.append(
            f"| {idx} | {item.model.repo_id} | {item.score} | {item.model.license or 'unknown'} | {vram} | {reasons} |"
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def _serialize_model(item: ScoredModel) -> dict:
    return {
        "repo_id": item.model.repo_id,
        "score": item.score,
        "reasons": item.reasons,
        "license": item.model.license,
        "likes": item.model.likes,
        "downloads": item.model.downloads,
        "tags": item.model.tags,
        "filtered_out": item.filtered_out,
        "filter_reasons": item.filter_reasons,
        "vram_estimate": {
            "compatible": item.vram_estimate.compatible,
            "required_gb": item.vram_estimate.required_gb,
            "reasons": item.vram_estimate.reasons,
            "hints": item.vram_estimate.hints,
        },
    }

