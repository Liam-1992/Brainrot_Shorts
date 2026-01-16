from __future__ import annotations

import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List

from ..db import get_connection
from ..export_pack import build_publish_pack
from ..virality_report import build_report
from ..virality_score import compute_virality_score
from ..models import GenerateRequest
from ..utils import ensure_dir, generate_job_id
from .continuity import build_series_context
from .campaign_memory import get_memory, reset_memory


def create_campaign(
    settings,
    name: str,
    preset_name: str | None,
    prompts: List[str],
    theme: str | None = None,
) -> str:
    campaign_id = generate_job_id()
    metadata = {
        "prompts": prompts,
        "theme": theme,
        "used_hooks": [],
        "used_keywords": [],
        "banned_phrases": [],
    }
    with get_connection(settings.DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO campaigns (campaign_id, name, created_at, preset_name, status, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                campaign_id,
                name,
                datetime.utcnow().isoformat(),
                preset_name,
                "created",
                json.dumps(metadata),
            ),
        )
        conn.commit()
    reset_memory(settings, campaign_id)
    return campaign_id


def list_campaigns(settings) -> List[dict]:
    with get_connection(settings.DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT campaign_id, name, created_at, preset_name, status, metadata_json
            FROM campaigns
            ORDER BY datetime(created_at) DESC
            """
        ).fetchall()
    payload = []
    for row in rows:
        meta = _safe_json(row["metadata_json"])
        payload.append({**dict(row), "metadata": meta})
    return payload


def get_campaign(settings, campaign_id: str) -> dict | None:
    with get_connection(settings.DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT campaign_id, name, created_at, preset_name, status, metadata_json
            FROM campaigns
            WHERE campaign_id = ?
            """,
            (campaign_id,),
        ).fetchone()
        jobs = conn.execute(
            """
            SELECT campaign_id, job_id, order_index, series_number
            FROM campaign_jobs
            WHERE campaign_id = ?
            ORDER BY order_index ASC
            """,
            (campaign_id,),
        ).fetchall()
    if not row:
        return None
    return {**dict(row), "metadata": _safe_json(row["metadata_json"]), "jobs": [dict(j) for j in jobs]}


def run_campaign(
    settings,
    campaign_id: str,
    enqueue_fn: Callable[..., None],
    preset: dict | None,
    overrides: dict | None = None,
) -> List[str]:
    campaign = get_campaign(settings, campaign_id)
    if not campaign:
        raise ValueError("Campaign not found")
    metadata = campaign.get("metadata") or {}
    prompts = metadata.get("prompts", [])
    if not prompts:
        raise ValueError("Campaign has no prompts")
    memory = get_memory(settings, campaign_id)

    job_ids = []
    for idx, prompt in enumerate(prompts, start=1):
        req_payload = {
            "topic_prompt": prompt,
            "preset_name": campaign.get("preset_name"),
        }
        if overrides:
            req_payload.update(overrides)
        if preset:
            preset_payload = {k: v for k, v in preset.items() if k != "name"}
            req_payload.update(preset_payload)
        req = GenerateRequest(**req_payload)
        series_context = build_series_context(
            metadata,
            idx,
            metadata.get("theme"),
            campaign_id=campaign_id,
            memory=memory,
        )
        req.series_context = series_context
        job_id = generate_job_id()
        enqueue_fn(req, job_id, group_id=campaign_id, variant_name=f"Part {idx}")
        _add_campaign_job(settings, campaign_id, job_id, idx, idx)
        job_ids.append(job_id)
    _update_campaign_status(settings, campaign_id, "running")
    return job_ids


def export_campaign(settings, campaign_id: str) -> Path:
    campaign = get_campaign(settings, campaign_id)
    if not campaign:
        raise ValueError("Campaign not found")
    out_dir = settings.OUTPUTS_DIR / "campaigns" / campaign_id
    ensure_dir(out_dir)
    zip_path = out_dir / "campaign_export.zip"

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        metadata_path = out_dir / "metadata.json"
        metadata_path.write_text(json.dumps(campaign, indent=2), encoding="utf-8")
        archive.write(metadata_path, "metadata.json")
        for job in campaign.get("jobs", []):
            job_id = job["job_id"]
            job_dir = settings.OUTPUTS_DIR / job_id
            if not job_dir.exists():
                continue
            for file_path in job_dir.glob("*"):
                if file_path.is_file():
                    arcname = f"{job_id}/{file_path.name}"
                    archive.write(file_path, arcname)
    return zip_path


def export_campaign_pro(settings, campaign_id: str) -> Path:
    campaign = get_campaign(settings, campaign_id)
    if not campaign:
        raise ValueError("Campaign not found")
    out_dir = settings.OUTPUTS_DIR / "campaigns" / campaign_id
    ensure_dir(out_dir)
    zip_path = out_dir / "campaign_export_pro.zip"
    summary = {"campaign_id": campaign_id, "parts": [], "best_part": None, "common_issues": []}
    best_score = -1
    issues: dict[str, int] = {}

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        summary_path = out_dir / "campaign_summary.json"
        for job in campaign.get("jobs", []):
            job_id = job["job_id"]
            job_dir = settings.OUTPUTS_DIR / job_id
            if not job_dir.exists():
                continue
            publish_pack = build_publish_pack(settings, job_id)
            report_path = build_report(settings, job_id)
            score_payload = compute_virality_score(settings, job_id)

            summary["parts"].append(
                {
                    "job_id": job_id,
                    "score": score_payload.get("virality_score"),
                    "reasons": score_payload.get("reasons", []),
                }
            )
            score_val = score_payload.get("virality_score", 0)
            if score_val > best_score:
                best_score = score_val
                summary["best_part"] = job_id
            for reason in score_payload.get("reasons", []):
                issues[reason] = issues.get(reason, 0) + 1

            for file_name in [
                "final.mp4",
                "thumb.jpg",
                "thumb_styled.jpg",
                "virality_report.html",
                "virality_score.json",
            ]:
                file_path = job_dir / file_name
                if file_path.exists():
                    archive.write(file_path, f"{job_id}/{file_name}")
            if publish_pack.exists():
                archive.write(publish_pack, f"{job_id}/publish_pack.zip")

        summary["common_issues"] = sorted(issues.keys(), key=lambda k: issues[k], reverse=True)[:5]
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        archive.write(summary_path, "campaign_summary.json")

    return zip_path


def update_campaign_metadata(settings, campaign_id: str, metadata: dict) -> None:
    with get_connection(settings.DB_PATH) as conn:
        conn.execute(
            "UPDATE campaigns SET metadata_json = ? WHERE campaign_id = ?",
            (json.dumps(metadata), campaign_id),
        )
        conn.commit()


def _add_campaign_job(
    settings,
    campaign_id: str,
    job_id: str,
    order_index: int,
    series_number: int,
) -> None:
    with get_connection(settings.DB_PATH) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO campaign_jobs (campaign_id, job_id, order_index, series_number)
            VALUES (?, ?, ?, ?)
            """,
            (campaign_id, job_id, order_index, series_number),
        )
        conn.commit()


def _update_campaign_status(settings, campaign_id: str, status: str) -> None:
    with get_connection(settings.DB_PATH) as conn:
        conn.execute(
            "UPDATE campaigns SET status = ? WHERE campaign_id = ?",
            (status, campaign_id),
        )
        conn.commit()


def _safe_json(text: str | None) -> dict:
    if not text:
        return {}
    try:
        return json.loads(text)
    except Exception:
        return {}
