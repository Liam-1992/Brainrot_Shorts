from __future__ import annotations

from typing import List, Tuple

from .types import Config, ModelCard, ScoredModel
from .vram_estimator import estimate_vram_requirement


LICENSE_ALLOWLIST = {
    "apache-2.0",
    "mit",
    "bsd-2-clause",
    "bsd-3-clause",
    "cc-by-4.0",
    "creativeml-openrail-m",
    "stabilityai-openrail",
    "openrail",
    "openrail++",
}

NSFW_TAGS = {"nsfw", "adult", "porn", "explicit"}

EXCLUDE_TAGS = {
    "video-classification",
    "video-captioning",
    "video-segmentation",
    "vlm",
}
T2V_KEYWORDS = {
    "text-to-video",
    "text-to-video-generation",
    "text-to-video-synthesis",
    "text2video",
    "t2v",
    "video diffusion",
    "animatediff",
    "cogvideo",
    "videocrafter",
    "mochi",
    "ltx-video",
}
I2V_KEYWORDS = {
    "image-to-video",
    "image-to-video-generation",
}


def filter_and_estimate(config: Config, model: ModelCard) -> Tuple[bool, List[str], object]:
    reasons: List[str] = []
    hard_reasons: List[str] = []
    tags_lower = {t.lower() for t in model.tags}
    pipeline = (model.pipeline_tag or "").lower()
    if pipeline and pipeline in I2V_KEYWORDS and not config.include_i2v:
        reasons.append("i2v_excluded")
        hard_reasons.append("i2v_excluded")
    elif pipeline and "video" not in pipeline:
        reasons.append("not_text_to_video")
        hard_reasons.append("not_text_to_video")
    elif not tags_lower & (T2V_KEYWORDS | (I2V_KEYWORDS if config.include_i2v else set())):
        reasons.append("missing_t2v_tag")
        hard_reasons.append("missing_t2v_tag")
    if tags_lower & EXCLUDE_TAGS:
        reasons.append("excluded_task")
        hard_reasons.append("excluded_task")

    if not config.allow_nsfw and tags_lower & NSFW_TAGS:
        reasons.append("nsfw_blocked")
        hard_reasons.append("nsfw_blocked")

    license_value = (model.license or "").lower()
    if not license_value:
        reasons.append("missing_license")
        hard_reasons.append("missing_license")
    elif license_value in {"cc-by-nc-4.0", "cc-by-nc", "cc-by-nc-sa-4.0"} and not config.allow_nc:
        reasons.append("license_nc_disallowed")
        hard_reasons.append("license_nc_disallowed")
    elif license_value.startswith("gpl") and not config.allow_gpl:
        reasons.append("license_gpl_disallowed")
        hard_reasons.append("license_gpl_disallowed")
    elif license_value not in LICENSE_ALLOWLIST and not config.allow_nc and not config.allow_gpl:
        reasons.append("license_not_allowed")
        hard_reasons.append("license_not_allowed")

    files = [s.name for s in model.siblings]
    estimate = estimate_vram_requirement(model, files, {}, config)
    vram_reason_codes = {
        "weights_too_large",
        "requires_high_vram_hint",
        "heavy_architecture",
        "unknown_requirements",
    }
    vram_reasons = [reason for reason in estimate.reasons if reason in vram_reason_codes]
    reasons.extend(estimate.reasons)

    compatible = estimate.compatible
    if config.allow_over_vram:
        compatible = True
        for reason in vram_reasons:
            if reason in reasons:
                reasons.remove(reason)

    if hard_reasons:
        compatible = False

    if config.require_diffusers and "not_diffusers_compatible" in estimate.reasons:
        compatible = False

    return compatible, reasons, estimate


def apply_filters(config: Config, models: List[ModelCard]) -> List[ScoredModel]:
    scored: List[ScoredModel] = []
    for model in models:
        compatible, reasons, estimate = filter_and_estimate(config, model)
        scored.append(
            ScoredModel(
                model=model,
                score=0,
                reasons=[],
                vram_estimate=estimate,
                filtered_out=not compatible,
                filter_reasons=reasons,
            )
        )
    return scored

