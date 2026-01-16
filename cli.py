from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.automation.campaigns import create_campaign, export_campaign_pro, run_campaign
from app.automation.scheduler import create_schedule, dry_run, run_scheduler
from app.automation.watch_folder import scan_watch_folder
from app.config import Settings
from app.db import init_db
from app.export_pack import build_publish_pack
from app.pipeline import run_pipeline
from app.preset_manager import PresetManager
from app.project_manager import ProjectManager
from app.template_manager import TemplateManager
from app.plugins.manager import PluginManager
from app.utils import ensure_dir, generate_job_id, write_json
from app.virality_report import build_report
from app.virality_score import compute_virality_score
from app.models import GenerateRequest


def main() -> int:
    parser = argparse.ArgumentParser(prog="brainrot", description="Shorts Studio CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    gen = subparsers.add_parser("generate", help="Generate a single job")
    gen.add_argument("--prompt", required=True)
    gen.add_argument("--preset")
    gen.add_argument("--optimize", action="store_true")
    gen.add_argument("--hook-first", action="store_true")
    gen.add_argument("--no-hook-first", action="store_true")

    batch = subparsers.add_parser("batch", help="Generate batch from file")
    batch.add_argument("--file", required=True)
    batch.add_argument("--preset")

    campaign = subparsers.add_parser("campaign", help="Create and run campaign")
    campaign.add_argument("--name", required=True)
    campaign.add_argument("--file", required=True)
    campaign.add_argument("--preset")
    campaign.add_argument("--optimize", action="store_true")
    campaign.add_argument("--export-pro", action="store_true")

    schedule = subparsers.add_parser("schedule", help="Create daily schedule")
    schedule.add_argument("--daily", type=int, required=True)
    schedule.add_argument("--preset")
    schedule.add_argument("--source", required=True)

    scheduler = subparsers.add_parser("scheduler", help="Run scheduler loop")
    scheduler.add_argument("--interval", type=int, default=30)
    scheduler.add_argument("--dry-run", action="store_true")

    watch = subparsers.add_parser("watch", help="Watch folder operations")
    watch.add_argument("--scan", action="store_true")
    watch.add_argument("--approve-mode", action="store_true")

    status = subparsers.add_parser("status", help="Show job status")
    status.add_argument("--job", required=True)

    export = subparsers.add_parser("export", help="Export publish pack or virality report")
    export.add_argument("--job", required=True)
    export.add_argument("--type", choices=["publish_pack", "virality_report"], required=True)

    score = subparsers.add_parser("score", help="Print virality score for a job")
    score.add_argument("--job", required=True)

    args = parser.parse_args()

    settings = Settings()
    ensure_dir(settings.OUTPUTS_DIR)
    ensure_dir(settings.MODELS_DIR)
    ensure_dir(settings.MUSIC_DIR)
    ensure_dir(settings.SFX_DIR)
    init_db(settings.DB_PATH)

    template_manager = TemplateManager(settings.TEMPLATES_DIR)
    template_manager.load()
    plugin_manager = PluginManager(settings.PLUGINS_ENABLED)
    plugin_manager.load()
    preset_manager = PresetManager(settings.PRESETS_PATH)
    project_manager = ProjectManager(settings.DB_PATH)

    if args.command == "generate":
        req = _build_request(args.prompt, args.preset, preset_manager)
        if args.optimize:
            req.optimization_enabled = True
        if args.hook_first:
            req.hook_first_enabled = True
        if args.no_hook_first:
            req.hook_first_enabled = False
        job_id = generate_job_id()
        _run_job(settings, req, job_id, template_manager, plugin_manager, project_manager)
        print(job_id)
        return 0

    if args.command == "batch":
        prompts = _load_prompts(Path(args.file))
        if not prompts:
            print("No prompts found.", file=sys.stderr)
            return 2
        for prompt in prompts:
            req = _build_request(prompt, args.preset, preset_manager)
            job_id = generate_job_id()
            _run_job(settings, req, job_id, template_manager, plugin_manager, project_manager)
            print(job_id)
        return 0

    if args.command == "campaign":
        prompts = _load_prompts(Path(args.file))
        if not prompts:
            print("No prompts found.", file=sys.stderr)
            return 2
        campaign_id = create_campaign(settings, args.name, args.preset, prompts)
        preset = preset_manager.get(args.preset) if args.preset else None
        overrides = {}
        if args.optimize:
            overrides["optimization_enabled"] = True
        job_ids = run_campaign(
            settings,
            campaign_id,
            lambda req, job_id, **kwargs: _run_job(
                settings,
                req,
                job_id,
                template_manager,
                plugin_manager,
                project_manager,
                group_id=kwargs.get("group_id"),
                variant_name=kwargs.get("variant_name"),
            ),
            preset,
            overrides=overrides,
        )
        print(campaign_id)
        for job_id in job_ids:
            print(job_id)
        if args.export_pro:
            path = export_campaign_pro(settings, campaign_id)
            print(path)
        return 0

    if args.command == "schedule":
        schedule_id = create_schedule(settings, "daily", args.daily, args.preset, args.source)
        print(schedule_id)
        return 0

    if args.command == "scheduler":
        if args.dry_run:
            report = dry_run(settings)
            print(json.dumps(report, indent=2))
            return 0
        run_scheduler(
            settings,
            lambda req, job_id, **kwargs: _run_job(
                settings,
                req,
                job_id,
                template_manager,
                plugin_manager,
                project_manager,
                group_id=kwargs.get("group_id"),
                variant_name=kwargs.get("variant_name"),
            ),
            interval_seconds=args.interval,
        )
        return 0

    if args.command == "watch":
        if not args.scan:
            print("Specify --scan to scan watch folder.", file=sys.stderr)
            return 2
        result = scan_watch_folder(settings, lambda req, job_id: _run_job(
            settings, req, job_id, template_manager, plugin_manager, project_manager
        ), approve_mode=args.approve_mode)
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "status":
        project = project_manager.get_project(args.job)
        if not project:
            print("Job not found", file=sys.stderr)
            return 1
        print(json.dumps(project, indent=2))
        return 0

    if args.command == "export":
        if args.type == "publish_pack":
            path = build_publish_pack(settings, args.job)
        else:
            path = build_report(settings, args.job)
        print(path)
        return 0

    if args.command == "score":
        payload = compute_virality_score(settings, args.job)
        print(json.dumps(payload, indent=2))
        return 0

    return 1


def _build_request(prompt: str, preset_name: str | None, preset_manager: PresetManager) -> GenerateRequest:
    req = GenerateRequest(topic_prompt=prompt, preset_name=preset_name)
    if not preset_name:
        return req
    preset = preset_manager.get(preset_name)
    if not preset:
        return req
    merged = req.model_dump()
    for key, value in preset.items():
        merged[key] = value
    return GenerateRequest(**merged)


def _run_job(
    settings: Settings,
    req: GenerateRequest,
    job_id: str,
    template_manager: TemplateManager,
    plugin_manager: PluginManager,
    project_manager: ProjectManager,
    group_id: str | None = None,
    variant_name: str | None = None,
) -> None:
    job_state = {"status": "running", "progress": 0, "logs": []}
    job_dir = settings.OUTPUTS_DIR / job_id
    ensure_dir(job_dir)
    write_json(job_dir / "request.json", req.model_dump())
    project_manager.create_project(
        job_id=job_id,
        prompt=req.topic_prompt,
        style=req.style,
        status="running",
        duration=float(req.duration_seconds),
        voice=req.voice,
        preset_name=req.preset_name,
        group_id=group_id,
        variant_name=variant_name,
    )
    output_path = run_pipeline(
        settings,
        req,
        job_id,
        job_state,
        template_manager,
        plugin_manager,
    )
    project_manager.update_status(job_id, "done", final_path=str(output_path))


def _load_prompts(path: Path) -> list[str]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".csv":
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if lines and "prompt" in lines[0].lower():
            lines = lines[1:]
        prompts = []
        for line in lines:
            prompt = line.split(",")[0].strip()
            if prompt:
                prompts.append(prompt)
        return prompts
    return [line.strip() for line in text.splitlines() if line.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
