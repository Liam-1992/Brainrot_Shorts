from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

StyleType = Literal[
    "brainrot_facts",
    "reddit_story",
    "confession",
    "ai_scary",
    "fast_rage",
]
BgMode = Literal["random_clip", "single_clip_loop", "stitched_clips"]
RenderMode = Literal["preview", "final"]
OptimizationStrategy = Literal["hook_only", "script_and_hook", "script_only"]
HookSelectionMode = Literal["score_only", "score_plus_clarity"]
RoutingMode = Literal["manual", "auto"]
RoutingPolicy = Literal["fastest", "best_quality", "balanced"]
CaptionAutofixMode = Literal["group", "rewrite", "group_then_rewrite"]
AudioMasteringPreset = Literal["clean", "hype", "aggressive"]


class GenerateRequest(BaseModel):
    topic_prompt: str = Field(..., min_length=3)
    style: StyleType = "brainrot_facts"
    template_name: Optional[str] = None
    duration_seconds: int = Field(default=35, ge=10, le=120)
    voice: str = "en_US"
    bg_mode: BgMode = "random_clip"
    bg_category: Optional[str] = None
    seed: Optional[int] = None
    speech_speed: float = Field(default=1.08, ge=0.5, le=2.0)
    caption_style: str = "tiktok_pop"
    music_bed: str = "none"
    sfx_pack: str = "none"
    zoom_punch_strength: float = Field(default=0.3, ge=0.0, le=1.0)
    shake_strength: float = Field(default=0.2, ge=0.0, le=1.0)
    drift_strength: float = Field(default=0.3, ge=0.0, le=1.0)
    loop_smoothing_seconds: float = Field(default=0.35, ge=0.0, le=2.0)
    quality_gate_enabled: bool = False
    min_hook_score: float = Field(default=70.0, ge=0.0, le=100.0)
    max_words_per_second: float = Field(default=4.0, ge=1.0, le=10.0)
    max_retries: int = Field(default=2, ge=0, le=5)
    optimization_enabled: bool = False
    optimization_max_attempts: int = Field(default=5, ge=1, le=10)
    optimization_strategy: OptimizationStrategy = "script_and_hook"
    max_words_per_second_estimate: float = Field(default=4.0, ge=1.0, le=10.0)
    min_beats_per_10s: float = Field(default=4.0, ge=1.0, le=10.0)
    max_beats_per_10s: float = Field(default=7.0, ge=1.0, le=12.0)
    hook_pool_size: int = Field(default=10, ge=1, le=20)
    hook_pick: int = Field(default=3, ge=1, le=10)
    hook_selection_mode: HookSelectionMode = "score_only"
    hook_first_enabled: bool = True
    candidate_selection_enabled: bool = True
    script_candidate_count: int = Field(default=3, ge=1, le=5)
    caption_autofix_enabled: bool = False
    max_chars_per_line: int = Field(default=18, ge=8, le=32)
    min_caption_duration: float = Field(default=0.55, ge=0.2, le=2.0)
    caption_autofix_mode: CaptionAutofixMode = "group"
    audio_mastering_preset: AudioMasteringPreset = "hype"
    music_ducking_strength: float = Field(default=0.6, ge=0.0, le=1.0)
    impact_rate: float = Field(default=0.2, ge=0.0, le=1.0)
    preset_name: Optional[str] = None
    render_mode: RenderMode = "final"
    preview_mode: bool = False
    preview_start: float = Field(default=0.0, ge=0.0)
    preview_duration: float = Field(default=10.0, ge=1.0)
    unhinged: bool = False
    series_context: Optional[dict] = None


class GenerateResponse(BaseModel):
    job_id: str


class StatusResponse(BaseModel):
    status: Literal["queued", "running", "done", "error"]
    progress: int
    logs: List[str]
    output_video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    thumbnail_styled_url: Optional[str] = None
    preview_video_url: Optional[str] = None


class ScriptBeat(BaseModel):
    t: float
    text: str
    on_screen: str
    emphasis: Optional[bool] = None


class ScriptOutput(BaseModel):
    title: str
    hook: str
    beats: List[ScriptBeat]
    full_voiceover_text: str
    keywords: List[str]


DownloadKind = Literal["llm", "whisper", "piper", "custom"]


class ModelDownloadRequest(BaseModel):
    name: Optional[str] = None
    kind: DownloadKind = "custom"
    urls: List[str]
    overwrite: bool = False


class ModelDownloadResponse(BaseModel):
    download_id: str


class ModelStatusResponse(BaseModel):
    status: Literal["queued", "downloading", "done", "error"]
    progress: int
    downloaded_bytes: int
    total_bytes: int
    logs: List[str]
    output_dir: Optional[str] = None


class TemplateInfo(BaseModel):
    name: str
    style: str
    description: str


class Preset(BaseModel):
    name: str
    style: StyleType
    duration_seconds: int
    voice: str
    bg_mode: BgMode
    speech_speed: float
    caption_style: str
    music_bed: str
    sfx_pack: str
    zoom_punch_strength: float
    shake_strength: float
    drift_strength: float
    loop_smoothing_seconds: float = 0.35
    quality_gate_enabled: bool = False
    min_hook_score: float = 70.0
    max_words_per_second: float = 4.0
    max_retries: int = 2
    optimization_enabled: bool = False
    optimization_max_attempts: int = 5
    optimization_strategy: OptimizationStrategy = "script_and_hook"
    max_words_per_second_estimate: float = 4.0
    min_beats_per_10s: float = 4.0
    max_beats_per_10s: float = 7.0
    hook_pool_size: int = 10
    hook_pick: int = 3
    hook_selection_mode: HookSelectionMode = "score_only"
    hook_first_enabled: bool = True
    candidate_selection_enabled: bool = True
    script_candidate_count: int = 3
    caption_autofix_enabled: bool = False
    max_chars_per_line: int = 18
    min_caption_duration: float = 0.55
    caption_autofix_mode: CaptionAutofixMode = "group"
    audio_mastering_preset: AudioMasteringPreset = "hype"
    music_ducking_strength: float = 0.6
    impact_rate: float = 0.2


class PresetListResponse(BaseModel):
    presets: List[Preset]


class PresetResponse(BaseModel):
    preset: Preset


class ProjectInfo(BaseModel):
    job_id: str
    prompt: str
    style: str
    created_at: str
    status: str
    final_path: Optional[str] = None
    duration: float
    voice: str
    preset_name: Optional[str] = None
    title: Optional[str] = None
    thumb_path: Optional[str] = None
    thumb_styled_path: Optional[str] = None
    group_id: Optional[str] = None
    variant_name: Optional[str] = None


class ProjectListResponse(BaseModel):
    projects: List[ProjectInfo]


class RerunRequest(BaseModel):
    steps: List[Literal["script", "voice", "captions", "render"]]


class BatchGenerateRequest(BaseModel):
    prompts: List[str] = Field(..., min_length=1)
    preset_name: Optional[str] = None


class BatchGenerateResponse(BaseModel):
    batch_id: str
    job_ids: List[str]


class BeatsResponse(BaseModel):
    beats: List[ScriptBeat]
    full_voiceover_text: str
    hook: Optional[str] = None
    title: Optional[str] = None


class BeatsUpdate(BaseModel):
    beats: List[ScriptBeat]
    hook: Optional[str] = None
    title: Optional[str] = None


class RenderFromBeatsRequest(BaseModel):
    regenerate_voice: bool = False
    regenerate_captions: bool = False
    regenerate_render: bool = True
    preview_mode: bool = False
    preview_start: float = 0.0
    preview_duration: float = 10.0


class GenerateVariationsRequest(BaseModel):
    topic_prompt: str
    preset_name: Optional[str] = None
    count: int = Field(default=5, ge=1, le=10)


class GenerateVariationsResponse(BaseModel):
    job_ids: List[str]


class HookScoreRequest(BaseModel):
    hook_text: str


class HookScoreResponse(BaseModel):
    score: int
    reasons: List[str]


class RewriteHookRequest(BaseModel):
    hook_text: str
    style: str


class RewriteHookResponse(BaseModel):
    candidates: List[str]


class GenerateVariantsRequest(BaseModel):
    topic_prompt: str
    style: str
    num_hooks: int = Field(default=10, ge=1, le=20)
    num_titles: int = Field(default=10, ge=1, le=20)
    pick: int = Field(default=3, ge=1, le=10)


class GenerateVariantsResponse(BaseModel):
    hooks: List[dict]
    titles: List[dict]
    picks: List[dict]


class ABVariant(BaseModel):
    name: str
    overrides: dict


class ABGenerateRequest(BaseModel):
    topic_prompt: str
    preset_name: Optional[str] = None
    variants: List[ABVariant]


class ABGenerateResponse(BaseModel):
    job_ids: List[str]


class GenerateHooksRequest(BaseModel):
    topic_prompt: str
    style: str
    count: int = Field(default=10, ge=1, le=20)


class HookCandidate(BaseModel):
    text: str
    score: int
    reasons: List[str]
    clarity_score: Optional[int] = None


class GenerateHooksResponse(BaseModel):
    hooks: List[HookCandidate]
    top: List[HookCandidate]


class OptimizationAttempt(BaseModel):
    attempt: int
    selected: bool
    hook_score: int
    reasons: List[str]
    metrics: dict
    script_path: str


class OptimizationResponse(BaseModel):
    job_id: str
    selected_attempt: Optional[int] = None
    attempts: List[OptimizationAttempt]


class RoutingConfig(BaseModel):
    routing_mode: RoutingMode
    policy: RoutingPolicy
    hook_model: Optional[str] = None
    script_model: Optional[str] = None


class BenchmarkResult(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    tool: str
    model_name: str
    created_at: str
    metrics: dict


class BenchmarkListResponse(BaseModel):
    benchmarks: List[BenchmarkResult]


class MetricsResponse(BaseModel):
    beat_density: List[int]
    words_per_second: List[float]
    cut_frequency: List[int]
    avg_caption_length: float
    words_per_caption_event: float
    suggestions: List[str]


class ViralityScoreResponse(BaseModel):
    virality_score: int
    reasons: List[str]
    problem_intervals: List[str]
    metrics: dict


class HealthResponse(BaseModel):
    ffmpeg_ok: bool
    ffprobe_ok: bool
    piper_ok: bool
    llm_model_ok: bool
    whisper_model_ok: bool
    gpu_available: bool
    available_voices: List[str]
