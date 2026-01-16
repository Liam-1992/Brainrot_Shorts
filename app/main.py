from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import Settings
from .db import init_db
from .downloads import run_download
from .job_queue import JobQueue
from .models import (
    BatchGenerateRequest,
    BatchGenerateResponse,
    GenerateRequest,
    GenerateResponse,
    HealthResponse,
    ModelDownloadRequest,
    ModelDownloadResponse,
    ModelStatusResponse,
    Preset,
    PresetListResponse,
    PresetResponse,
    ProjectInfo,
    ProjectListResponse,
    RerunRequest,
    StatusResponse,
    TemplateInfo,
)
from .pipeline import run_pipeline
from .preset_manager import PresetManager
from .project_manager import ProjectManager
from .template_manager import TemplateManager
from .tts import synthesize_preview
from .utils import append_log, ensure_dir, generate_job_id, run_subprocess, write_json
from .plugins.manager import PluginManager
from .api import (
    routes_assets,
    routes_beats,
    routes_benchmarks,
    routes_cancel,
    routes_campaigns,
    routes_captions_autofix,
    routes_config,
    routes_export,
    routes_hooks,
    routes_hooks_pool,
    routes_metrics,
    routes_model_setup,
    routes_optimization,
    routes_routing,
    routes_scheduler,
    routes_virality,
    routes_virality_score,
    routes_validation,
    routes_variations,
    routes_watch_folder,
    routes_watch_pending,
)
from .subprocess_manager import init_manager

settings = Settings()
ensure_dir(settings.OUTPUTS_DIR)
ensure_dir(settings.MODELS_DIR)
ensure_dir(settings.MUSIC_DIR)
ensure_dir(settings.SFX_DIR)

init_manager(settings.SUBPROCESS_TIMEOUT_SECONDS)

init_db(settings.DB_PATH)

template_manager = TemplateManager(settings.TEMPLATES_DIR)
template_manager.load()

plugin_manager = PluginManager(settings.PLUGINS_ENABLED)
plugin_manager.load()

preset_manager = PresetManager(settings.PRESETS_PATH)
project_manager = ProjectManager(settings.DB_PATH)
job_queue = JobQueue(settings.MAX_CONCURRENT_JOBS)

app = FastAPI(title="Shorts Studio", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def _no_cache_web(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/web/"):
        response.headers["Cache-Control"] = "no-store"
    return response

JOBS: dict[str, dict] = {}
DOWNLOADS: dict[str, dict] = {}

app.mount("/outputs", StaticFiles(directory=settings.OUTPUTS_DIR), name="outputs")
app.mount("/web", StaticFiles(directory=settings.BASE_DIR / "web"), name="web")


@app.on_event("startup")
def _startup() -> None:
    job_queue.start()
    template_manager.load()


@app.on_event("shutdown")
def _shutdown() -> None:
    job_queue.stop()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(
        settings.BASE_DIR / "web" / "index.html",
        headers={"Cache-Control": "no-store"},
    )


def _apply_preset(req: GenerateRequest) -> GenerateRequest:
    if not req.preset_name:
        return req
    preset = preset_manager.get(req.preset_name)
    if not preset:
        return req
    merged = req.model_dump()
    for key in [
        "style",
        "duration_seconds",
        "voice",
        "bg_mode",
        "speech_speed",
        "caption_style",
        "music_bed",
        "sfx_pack",
        "zoom_punch_strength",
        "shake_strength",
        "drift_strength",
        "loop_smoothing_seconds",
        "quality_gate_enabled",
        "min_hook_score",
        "max_words_per_second",
        "max_retries",
        "optimization_enabled",
        "optimization_max_attempts",
        "optimization_strategy",
        "max_words_per_second_estimate",
        "min_beats_per_10s",
        "max_beats_per_10s",
        "hook_pool_size",
        "hook_pick",
        "hook_selection_mode",
        "hook_first_enabled",
        "candidate_selection_enabled",
        "script_candidate_count",
        "caption_autofix_enabled",
        "max_chars_per_line",
        "min_caption_duration",
        "caption_autofix_mode",
        "audio_mastering_preset",
        "music_ducking_strength",
        "impact_rate",
    ]:
        if key in preset:
            merged[key] = preset[key]
    return GenerateRequest(**merged)


def _apply_unhinged(req: GenerateRequest) -> GenerateRequest:
    if not req.unhinged:
        return req
    data = req.model_dump()
    data["speech_speed"] = min(2.0, max(req.speech_speed, 1.25))
    data["zoom_punch_strength"] = min(1.0, max(req.zoom_punch_strength, 0.7))
    data["shake_strength"] = min(1.0, max(req.shake_strength, 0.6))
    data["drift_strength"] = min(1.0, max(req.drift_strength, 0.5))
    data["sfx_pack"] = "default"
    if data.get("music_bed") == "none":
        data["music_bed"] = "random"
    data["caption_style"] = "tiktok_pop"
    data["topic_prompt"] = f"{req.topic_prompt} (unhinged: faster beats, chaos energy)"
    return GenerateRequest(**data)


def _enqueue_job(
    request_input,
    job_id: str,
    steps: list[str] | None = None,
    save_request: bool = True,
    create_project: bool = True,
    group_id: str | None = None,
    variant_name: str | None = None,
) -> None:
    request = request_input if isinstance(request_input, GenerateRequest) else GenerateRequest(**request_input)
    job_state = JOBS.get(job_id)
    if not job_state:
        job_state = {"status": "queued", "progress": 0, "logs": []}
        JOBS[job_id] = job_state
    job_dir = settings.OUTPUTS_DIR / job_id
    log_path = job_dir / "log.txt"
    ensure_dir(job_dir)
    if save_request:
        write_json(job_dir / "request.json", request.model_dump())

    if create_project:
        project_manager.create_project(
            job_id=job_id,
            prompt=request.topic_prompt,
            style=request.style,
            status="queued",
            duration=float(request.duration_seconds),
            voice=request.voice,
            preset_name=request.preset_name,
            group_id=group_id,
            variant_name=variant_name,
        )

    def runner() -> None:
        try:
            job_state["status"] = "running"
            project_manager.update_status(job_id, "running")
            output_path = run_pipeline(
                settings,
                request,
                job_id,
                job_state,
                template_manager,
                plugin_manager,
                steps=steps,
            )
            job_state["status"] = "done"
            if request.preview_mode:
                job_state["preview_video_url"] = f"/outputs/{job_id}/preview.mp4"
                project_manager.update_status(job_id, "done")
            else:
                job_state["output_video_url"] = f"/outputs/{job_id}/final.mp4"
                job_state["thumbnail_url"] = f"/outputs/{job_id}/thumb.jpg"
                job_state["thumbnail_styled_url"] = f"/outputs/{job_id}/thumb_styled.jpg"
                project_manager.update_status(
                    job_id,
                    "done",
                    final_path=str(output_path),
                    title=_read_title(job_id),
                    thumb_path=str(settings.OUTPUTS_DIR / job_id / "thumb.jpg"),
                    thumb_styled_path=str(settings.OUTPUTS_DIR / job_id / "thumb_styled.jpg"),
                )
        except Exception as exc:
            job_state["status"] = "error"
            message = f"ERROR: {exc}"
            job_state["logs"].append(message)
            append_log(log_path, message)
            project_manager.update_status(job_id, "error")

    job_queue.enqueue(job_id, runner, job_state)


def _read_title(job_id: str) -> str | None:
    script_path = settings.OUTPUTS_DIR / job_id / "script.json"
    if not script_path.exists():
        return None
    try:
        payload = json.loads(script_path.read_text(encoding="utf-8"))
        return payload.get("title") or payload.get("hook")
    except Exception:
        return None


routes_assets.init_context(settings)
routes_config.init_context(settings)
routes_model_setup.init_context(settings, DOWNLOADS)
routes_beats.init_context(settings, _enqueue_job, JOBS)
routes_variations.init_context(settings, preset_manager, _enqueue_job, JOBS)
routes_metrics.init_context(settings)
routes_validation.init_context(settings)
routes_cancel.init_context(settings, JOBS, project_manager)
routes_export.init_context(settings)
routes_hooks.init_context(settings)
routes_hooks_pool.init_context(settings)
routes_captions_autofix.init_context(settings, plugin_manager)
routes_optimization.init_context(settings)
routes_virality.init_context(settings)
routes_virality_score.init_context(settings)
routes_benchmarks.init_context(settings)
routes_routing.init_context(settings)
routes_campaigns.init_context(settings, preset_manager, _enqueue_job)
routes_watch_folder.init_context(settings, _enqueue_job)
routes_watch_pending.init_context(settings, _enqueue_job)
routes_scheduler.init_context(settings)
app.include_router(routes_beats.router)
app.include_router(routes_variations.router)
app.include_router(routes_metrics.router)
app.include_router(routes_assets.router)
app.include_router(routes_config.router)
app.include_router(routes_model_setup.router)
app.include_router(routes_validation.router)
app.include_router(routes_cancel.router)
app.include_router(routes_export.router)
app.include_router(routes_hooks.router)
app.include_router(routes_hooks_pool.router)
app.include_router(routes_captions_autofix.router)
app.include_router(routes_optimization.router)
app.include_router(routes_virality.router)
app.include_router(routes_virality_score.router)
app.include_router(routes_benchmarks.router)
app.include_router(routes_routing.router)
app.include_router(routes_campaigns.router)
app.include_router(routes_watch_folder.router)
app.include_router(routes_watch_pending.router)
app.include_router(routes_scheduler.router)


@app.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest) -> GenerateResponse:
    request = _apply_preset(request)
    request = _apply_unhinged(request)
    job_id = generate_job_id()
    job_state = {"status": "queued", "progress": 0, "logs": []}
    JOBS[job_id] = job_state
    _enqueue_job(request, job_id)
    return GenerateResponse(job_id=job_id)


@app.post("/batch_generate", response_model=BatchGenerateResponse)
async def batch_generate(request: BatchGenerateRequest) -> BatchGenerateResponse:
    batch_id = generate_job_id()
    job_ids = []
    for prompt in request.prompts:
        job_id = generate_job_id()
        job_state = {"status": "queued", "progress": 0, "logs": []}
        JOBS[job_id] = job_state
        req = GenerateRequest(topic_prompt=prompt, preset_name=request.preset_name)
        req = _apply_preset(req)
        req = _apply_unhinged(req)
        _enqueue_job(req, job_id)
        job_ids.append(job_id)
    return BatchGenerateResponse(batch_id=batch_id, job_ids=job_ids)


@app.post("/rerun/{job_id}", response_model=GenerateResponse)
async def rerun(job_id: str, request: RerunRequest) -> GenerateResponse:
    job_dir = settings.OUTPUTS_DIR / job_id
    request_path = job_dir / "request.json"
    if not request_path.exists():
        raise HTTPException(status_code=404, detail="request.json not found")
    try:
        payload = json.loads(request_path.read_text(encoding="utf-8"))
        original = GenerateRequest(**payload)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request.json")
    job_state = JOBS.get(job_id)
    if not job_state:
        job_state = {"status": "queued", "progress": 0, "logs": []}
        JOBS[job_id] = job_state
    _enqueue_job(original, job_id, steps=request.steps)
    return GenerateResponse(job_id=job_id)


@app.get("/status/{job_id}", response_model=StatusResponse)
def status(job_id: str) -> StatusResponse:
    job_state = JOBS.get(job_id)
    if not job_state:
        raise HTTPException(status_code=404, detail="Job not found")
    preview_path = settings.OUTPUTS_DIR / job_id / "preview.mp4"
    if preview_path.exists():
        job_state.setdefault("preview_video_url", f"/outputs/{job_id}/preview.mp4")
    return StatusResponse(**job_state)


@app.get("/templates", response_model=list[TemplateInfo])
def templates() -> list[TemplateInfo]:
    template_manager.load()
    return [
        TemplateInfo(name=t.name, style=t.style, description=t.description)
        for t in template_manager.list_templates()
    ]


@app.get("/presets", response_model=PresetListResponse)
def list_presets() -> PresetListResponse:
    presets = [Preset(**preset) for preset in preset_manager.list_presets()]
    return PresetListResponse(presets=presets)


@app.post("/presets", response_model=PresetResponse)
def upsert_preset(preset: Preset) -> PresetResponse:
    stored = preset_manager.upsert(preset.model_dump())
    return PresetResponse(preset=Preset(**stored))


@app.delete("/presets/{preset_name}")
def delete_preset(preset_name: str) -> dict:
    preset_manager.delete(preset_name)
    return {"ok": True}


@app.get("/projects", response_model=ProjectListResponse)
def projects(limit: int = 50, offset: int = 0) -> ProjectListResponse:
    rows = project_manager.list_projects(limit, offset)
    return ProjectListResponse(projects=[ProjectInfo(**row) for row in rows])


@app.get("/projects/{job_id}", response_model=ProjectInfo)
def project(job_id: str) -> ProjectInfo:
    row = project_manager.get_project(job_id)
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectInfo(**row)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    def check_cmd(args: list[str]) -> bool:
        try:
            run_subprocess(args)
            return True
        except Exception:
            return False

    ffmpeg_ok = check_cmd([settings.FFMPEG_PATH, "-version"])
    ffprobe_ok = check_cmd([settings.FFPROBE_PATH, "-version"])
    piper_ok = check_cmd([settings.PIPER_PATH, "--help"])
    llm_model_ok = settings.resolve_llm_model_path() is not None
    whisper_model_ok = bool(settings.resolve_whisper_model_path())

    gpu_available = False
    try:
        import torch  # type: ignore

        gpu_available = torch.cuda.is_available()
    except Exception:
        gpu_available = False

    return HealthResponse(
        ffmpeg_ok=ffmpeg_ok,
        ffprobe_ok=ffprobe_ok,
        piper_ok=piper_ok,
        llm_model_ok=llm_model_ok,
        whisper_model_ok=whisper_model_ok,
        gpu_available=gpu_available,
        available_voices=settings.available_voices(),
    )


@app.post("/voices/preview")
async def voice_preview(payload: dict[str, Any]) -> dict:
    voice = str(payload.get("voice", "en_US"))
    text = str(payload.get("text", "This is a quick voice preview."))
    out_dir = settings.OUTPUTS_DIR / "voice_previews"
    ensure_dir(out_dir)
    try:
        path = await asyncio.to_thread(synthesize_preview, settings, text, voice, out_dir)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    rel = path.relative_to(settings.OUTPUTS_DIR)
    return {"url": f"/outputs/{rel.as_posix()}"}


@app.post("/models/download", response_model=ModelDownloadResponse)
async def download_model(request: ModelDownloadRequest) -> ModelDownloadResponse:
    download_id = generate_job_id()
    download_state = {
        "status": "queued",
        "progress": 0,
        "downloaded_bytes": 0,
        "total_bytes": 0,
        "logs": [],
        "output_dir": None,
    }
    DOWNLOADS[download_id] = download_state

    async def runner() -> None:
        try:
            download_state["status"] = "downloading"
            output_dir = await asyncio.to_thread(
                run_download, settings, request, download_id, download_state
            )
            download_state["status"] = "done"
            download_state["progress"] = 100
            download_state["output_dir"] = str(output_dir)
        except Exception as exc:
            download_state["status"] = "error"
            message = f"ERROR: {exc}"
            download_state["logs"].append(message)
            log_path = settings.OUTPUTS_DIR / "downloads" / download_id / "log.txt"
            append_log(log_path, message)

    asyncio.create_task(runner())
    return ModelDownloadResponse(download_id=download_id)


@app.get("/models/status/{download_id}", response_model=ModelStatusResponse)
def download_status(download_id: str) -> ModelStatusResponse:
    download_state = DOWNLOADS.get(download_id)
    if not download_state:
        raise HTTPException(status_code=404, detail="Download not found")
    return ModelStatusResponse(**download_state)
