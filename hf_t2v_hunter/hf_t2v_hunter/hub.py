from __future__ import annotations

from datetime import datetime
from typing import Iterable, List, Optional

from huggingface_hub import HfApi, hf_hub_download

from .types import Config, ModelCard, ModelFile


TASK_TAGS = [
    "text-to-video",
    "text-to-video-generation",
    "text-to-video-synthesis",
]
I2V_TAGS = [
    "image-to-video",
    "image-to-video-generation",
]


def search_candidates(config: Config) -> List[ModelCard]:
    api = HfApi()
    tasks = list(TASK_TAGS)
    if config.include_i2v:
        tasks.extend(I2V_TAGS)

    model_ids = _collect_model_ids(api, tasks, config.search_limit)
    cards = []
    for repo_id in model_ids:
        card = _load_model_card(api, repo_id, config)
        if card:
            cards.append(card)
    return cards


def _collect_model_ids(api: HfApi, filters: Iterable[str], limit: int) -> List[str]:
    seen = set()
    items: List[str] = []
    for model_filter in filters:
        try:
            for info in api.list_models(filter=model_filter, limit=limit):
                repo_id = info.modelId
                if repo_id in seen:
                    continue
                seen.add(repo_id)
                items.append(repo_id)
        except Exception:
            try:
                for info in api.list_models(filter={"task": model_filter}, limit=limit):
                    repo_id = info.modelId
                    if repo_id in seen:
                        continue
                    seen.add(repo_id)
                    items.append(repo_id)
            except Exception:
                continue
    keyword_search = [
        "text-to-video",
        "text2video",
        "video diffusion",
        "diffusers video",
        "cogvideo",
        "animatediff",
    ]
    for query in keyword_search:
        try:
            for info in api.list_models(search=query, limit=limit):
                repo_id = info.modelId
                if repo_id in seen:
                    continue
                seen.add(repo_id)
                items.append(repo_id)
        except Exception:
            continue
    return items


def _load_model_card(api: HfApi, repo_id: str, config: Config) -> Optional[ModelCard]:
    try:
        info = api.model_info(repo_id)
    except Exception:
        return None

    tags = list(info.tags or [])
    card_data = getattr(info, "cardData", None) or getattr(info, "card_data", None) or {}
    license_value = None
    if isinstance(card_data, dict):
        license_value = card_data.get("license") or card_data.get("license_name")
    if not license_value:
        license_value = getattr(info, "license", None)

    siblings = []
    for sibling in info.siblings or []:
        size = getattr(sibling, "size", None)
        try:
            size = int(size) if size is not None else 0
        except Exception:
            size = 0
        siblings.append(ModelFile(name=sibling.rfilename, size=size))

    last_modified = None
    try:
        if info.lastModified:
            last_modified = datetime.fromisoformat(info.lastModified.replace("Z", "+00:00"))
    except Exception:
        last_modified = None

    readme_text = None
    if config.scan_readme:
        readme_text = _load_readme(api, repo_id)

    requires_trust_remote_code = bool(getattr(info, "trusted", False))
    config_data = getattr(info, "config", None)
    if isinstance(config_data, dict) and config_data.get("trust_remote_code"):
        requires_trust_remote_code = True

    return ModelCard(
        repo_id=repo_id,
        model_name=info.modelId.split("/")[-1],
        tags=tags,
        pipeline_tag=getattr(info, "pipeline_tag", None),
        library_name=getattr(info, "library_name", None),
        license=license_value,
        likes=int(getattr(info, "likes", 0) or 0),
        downloads=int(getattr(info, "downloads", 0) or 0),
        last_modified=last_modified,
        siblings=siblings,
        card_data=card_data or {},
        readme_text=readme_text,
        requires_trust_remote_code=requires_trust_remote_code,
    )


def _load_readme(api: HfApi, repo_id: str) -> Optional[str]:
    for name in ("README.md", "README.MD", "readme.md"):
        try:
            path = hf_hub_download(repo_id=repo_id, filename=name)
            return _safe_read(path)
        except Exception:
            continue
    return None


def _safe_read(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except Exception:
        return None

