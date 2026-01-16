from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class Config:
    vram_gb: float = 12.0
    max_model_size_gb: float = 8.5
    strict_vram: bool = True
    allow_over_vram: bool = False
    allow_cpu_offload: bool = True
    require_diffusers: bool = True
    include_i2v: bool = False
    allow_nsfw: bool = False
    allow_nc: bool = False
    allow_gpl: bool = False
    allow_trust_remote_code: bool = False
    max_disk_gb: float = 30.0
    search_limit: int = 200
    recency_days: int = 180
    scan_readme: bool = True
    weights: Dict[str, float] = field(
        default_factory=lambda: {
            "downloads": 0.45,
            "likes": 0.20,
            "recency": 0.15,
            "quality": 0.20,
        }
    )


@dataclass
class ModelFile:
    name: str
    size: int


@dataclass
class ModelCard:
    repo_id: str
    model_name: str
    tags: List[str]
    pipeline_tag: Optional[str]
    library_name: Optional[str]
    license: Optional[str]
    likes: int
    downloads: int
    last_modified: Optional[datetime]
    siblings: List[ModelFile]
    card_data: Dict
    readme_text: Optional[str]
    requires_trust_remote_code: bool = False

    def total_weight_bytes(self) -> int:
        weight_exts = (
            ".safetensors",
            ".bin",
            ".pt",
            ".pth",
            ".ckpt",
            ".gguf",
            ".onnx",
        )
        total = 0
        for sibling in self.siblings:
            if sibling.name.lower().endswith(weight_exts):
                total += sibling.size
        return total


@dataclass
class VramEstimate:
    compatible: bool
    required_gb: Optional[float]
    reasons: List[str]
    hints: Dict[str, object] = field(default_factory=dict)


@dataclass
class ScoredModel:
    model: ModelCard
    score: int
    reasons: List[str]
    vram_estimate: VramEstimate
    filtered_out: bool = False
    filter_reasons: List[str] = field(default_factory=list)


@dataclass
class DownloadedModel:
    repo_id: str
    local_path: str
    size_bytes: int
    info_path: str


@dataclass
class DownloadReport:
    downloaded: List[DownloadedModel]
    skipped: List[Dict[str, object]]
    total_bytes: int


@dataclass
class ValidationResult:
    repo_id: str
    ok: bool
    mode: str
    reasons: List[str]
    details: Dict[str, object] = field(default_factory=dict)


@dataclass
class CandidateReport:
    candidates: List[ScoredModel]
    filtered: List[ScoredModel]
    top: List[ScoredModel]


@dataclass
class HookScore:
    score: int
    reasons: List[str]

