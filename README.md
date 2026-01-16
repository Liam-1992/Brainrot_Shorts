# Shorts Studio (Local-Only)

Shorts Studio is a local-first generator for vertical videos:

Prompt -> local LLM script JSON -> Piper TTS -> faster-whisper captions -> ASS subtitles
-> FFmpeg render -> `outputs/<job_id>/final.mp4` + `thumb.jpg`

No cloud APIs.

## Setup

### 1) Python environment
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2) Install local tools
- **FFmpeg**: ensure `ffmpeg` and `ffprobe` are on PATH
- **Piper**: download the Piper binary and a voice model `.onnx` + `.json`

### 3) Configure `.env`
Copy `.env.example` to `.env` and set paths:
```
FFMPEG_PATH=ffmpeg
FFPROBE_PATH=ffprobe
PIPER_PATH=C:\path\to\piper.exe
PIPER_MODEL_PATH=C:\path\to\en_US-voice.onnx
LLM_MODEL_PATH=D:\models\your-model.gguf
WHISPER_MODEL_PATH=D:\models\whisper\base
```

Optional:
```
MODELS_DIR=D:\Portfolio\brainrot_shorts\models
DB_PATH=D:\Portfolio\brainrot_shorts\projects.db
PRESETS_PATH=D:\Portfolio\brainrot_shorts\presets.json
MAX_CONCURRENT_JOBS=2
```

### 4) Add background clips
Put user-owned vertical-ish MP4s in:
```
assets/bg_clips/
```
Any `.mp4`, `.mov`, or `.mkv` is accepted. The app will crop/scale to 1080x1920.
Use `bg_mode=stitched_clips` to stitch multiple clips together.

Optional tags: edit `assets/bg_clips/clips.json`:
```
{
  "clips": [
    { "file": "parkour1.mp4", "tags": ["parkour"] }
  ]
}
```

### 5) Add music and SFX (optional)
```
assets/music/   # .mp3, .wav, .m4a
assets/sfx/
  default/
    whoosh_01.wav
    boom_01.wav
```
Music beds can be selected by filename or `random`. SFX packs use filename patterns `whoosh` and `boom`.

### 6) Optional fonts for captions
Drop `.ttf` fonts into:
```
assets/fonts/
```
Set `CAPTION_FONT` to match the font name if you want a global override.

## Run the server
```bash
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/` in your browser.

## API examples
Generate:
```bash
curl -X POST http://127.0.0.1:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"topic_prompt":"why pigeons are surveillance drones","style":"brainrot_facts","duration_seconds":35,"voice":"en_US","bg_mode":"random_clip","caption_style":"tiktok_pop","music_bed":"none","sfx_pack":"none","zoom_punch_strength":0.3,"shake_strength":0.2,"drift_strength":0.3}'
```

Batch:
```bash
curl -X POST http://127.0.0.1:8000/batch_generate \
  -H "Content-Type: application/json" \
  -d '{"prompts":["prompt one","prompt two"],"preset_name":"my-preset"}'
```

Rerun steps:
```bash
curl -X POST http://127.0.0.1:8000/rerun/<job_id> \
  -H "Content-Type: application/json" \
  -d '{"steps":["captions","render"]}'
```

Templates:
```bash
curl http://127.0.0.1:8000/templates
```

Projects:
```bash
curl http://127.0.0.1:8000/projects?limit=20&offset=0
```

Health:
```bash
curl http://127.0.0.1:8000/health
```

## Outputs
Each job writes:
```
outputs/<job_id>/
  script.json
  voice.wav
  transcript.json
  subtitles.ass
  subtitles_autofix.ass
  caption_report.json
  preview_subtitles.ass
  final.mp4
  preview.mp4
  bg_segments.json
  bg_stitched.mp4
  validation.json
  quality_report.json
  hooks.json
  virality_score.json
  effects_plan.json
  candidates/
  opt_attempts/
  metadata.json
  publish_pack.zip
  virality_report.html
  virality_report.pdf
  thumb.jpg
  thumb_styled.jpg
  log.txt
```

## Templates
Templates live in `app/templates/` as JSON or YAML.
Each file defines:
- `system_prompt`
- `schema`
- `beat_rules`
- optional `forbidden_words` and `safe_rewrites`

Add a new template file and it will appear in `/templates`.

## Caption styles
Caption style configs live in `app/caption_styles/`.
Each file defines font, size, colors, outline/shadow, margins, and bounce scale.

## Presets
Presets are stored in `presets.json` and can be created from the UI or via `/presets`.

## Plugins
Plugins live in `app/plugins/`.
Enable via `.env`:
```
PLUGINS_ENABLED=sample_plugin
```
Hooks supported:
- `postprocess_script(script, context)`
- `augment_caption_style(style, context)`
- `augment_audio_filters(filters, context)`
- `augment_video_filters(filters, context)`

## Model downloads (UI)
Use the **Settings > Model Downloads** panel to fetch model files directly to `models/`.
- Paste one or more URLs (one per line).
- For models that need multiple files (Whisper CT2, Piper), paste every required file URL or a zip archive.
- After downloading, point `.env` at the downloaded path(s), or let the app auto-detect a model from `models/`.
Downloads are stored under `models/<type>/<name>/`.

## Troubleshooting (Windows)
- Use full paths in `.env` when binaries are not on PATH.
- If FFmpeg fails to read subtitle paths, ensure there are no smart quotes and try forward slashes.
- Piper requires the `.onnx` model and its matching `.json` sidecar in the same folder.
- If audio mixing fails, ensure your SFX files are `.wav` and your music files are `.mp3` or `.wav`.

## Notes
- No cloud APIs are used. Everything runs locally.
- Model downloads require internet access once; generation runs offline after models are present.
- GPU acceleration is used automatically when available (LLM + Whisper).
- For transformers fallback, install `transformers` + `torch` manually and set `LLM_BACKEND=transformers`.

## Self-check (optional)
```bash
python scripts/self_check.py
```

## Optimization Lab (V4)
Enable **Optimization** in the Generate form or presets to iterate on scripts until
hook score + pacing thresholds are met. Attempts are saved under:
```
outputs/<job_id>/opt_attempts/attempt_01/
```
and available via:
```
GET /projects/<job_id>/optimization
```

## Hook-first generation (Q1)
Hook-first mode generates a hook pool, scores it, and builds the script around
the selected hook. The pool is stored at:
```
outputs/<job_id>/hooks.json
```
Endpoint:
```
GET /projects/<job_id>/hooks
```
Controls (Generate + presets):
```
hook_first_enabled
hook_pool_size
hook_pick
hook_selection_mode
```

## Hook pool generation
Generate a hook pool locally:
```
POST /generate_hooks
```
Payload: `{ "topic_prompt": "...", "style": "...", "count": 10 }`

## Caption autofix (Q2)
Enable caption autofix to group or rewrite captions for readability.
Outputs:
```
outputs/<job_id>/caption_report.json
outputs/<job_id>/subtitles_autofix.ass
```
Manual rerun:
```
POST /projects/<job_id>/captions/autofix
```
Controls (Generate + presets):
```
caption_autofix_enabled
caption_autofix_mode
max_words_per_second
max_chars_per_line
min_caption_duration
```

## Audio mastering + ducking (Q3)
Select an audio mastering preset (`clean`, `hype`, `aggressive`) and set
`music_ducking_strength` to control sidechain compression under voiceover.

## Effects plan (Q4)
Beat-aware zoom/shake plans are saved to:
```
outputs/<job_id>/effects_plan.json
```
Control:
```
impact_rate
```

## Virality score (Q5)
Combined score and problem intervals are stored at:
```
outputs/<job_id>/virality_score.json
```
Endpoint:
```
GET /projects/<job_id>/virality_score
```

## Candidate selection (Q6)
When enabled, script candidates are written to:
```
outputs/<job_id>/candidates/candidate_01/script.json
```
Only the selected candidate proceeds to TTS/Whisper/render.
Controls (Generate + presets):
```
candidate_selection_enabled
script_candidate_count
```

## Virality report
Export HTML report:
```
POST /projects/<job_id>/export_virality_report
```
Generates `outputs/<job_id>/virality_report.html`. If `wkhtmltopdf` is installed,
`virality_report.pdf` is also created.

## Model routing + benchmarks
Run local benchmarks:
```
POST /benchmarks/run
GET /benchmarks
GET /routing/status
```
Routing supports manual or auto selection (fastest/balanced/best_quality). Use
`.env` to define multiple LLM paths:
```
LLM_MODEL_PATHS=path1.gguf,path2.gguf
LLM_HOOK_MODEL_PATH=small.gguf
LLM_SCRIPT_MODEL_PATH=large.gguf
ROUTING_MODE=auto
ROUTING_POLICY=balanced
```

## CLI (V5)
Run without the web UI:
```bash
python cli.py generate --prompt "..." --preset my-preset
python cli.py generate --prompt "..." --preset my-preset --optimize --hook-first
python cli.py batch --file prompts.txt --preset my-preset
python cli.py campaign --name "Series A" --file prompts.txt --preset my-preset
python cli.py campaign --name "Series A" --file prompts.txt --preset my-preset --optimize --export-pro
python cli.py schedule --daily 3 --preset my-preset --source prompts.txt
python cli.py scheduler --interval 10
python cli.py scheduler --dry-run
python cli.py status --job <job_id>
python cli.py export --job <job_id> --type publish_pack
python cli.py export --job <job_id> --type virality_report
python cli.py score --job <job_id>
python cli.py watch --scan --approve-mode
```

## Watch-folder automation
Set in `.env`:
```
WATCH_FOLDER_PATH=path\\to\\watch
WATCH_FOLDER_ENABLED=true
```
Manual scan:
```
POST /watch_folder/scan
```
Approve mode:
```
POST /watch_folder/scan {"approve_mode": true}
GET /watch_folder/pending
POST /watch_folder/pending/<batch_id>/approve
DELETE /watch_folder/pending/<batch_id>
```
Scheduler status:
```
GET /scheduler/status
```
Dry run:
```
POST /scheduler/dry_run
GET /scheduler/runs
```

## Campaigns
Create a campaign from a file of prompts (.txt or .csv), run it, and export:
```
POST /campaigns/create
POST /campaigns/<campaign_id>/run
POST /campaigns/<campaign_id>/export
POST /campaigns/<campaign_id>/export_pro
```
Campaign exports are written to:
```
outputs/campaigns/<campaign_id>/
```
Continuity memory:
```
GET /campaigns/<campaign_id>/memory
POST /campaigns/<campaign_id>/memory/reset
```

## Assets browser + tagging
Use the **Assets** tab to browse clips, music, SFX, and fonts. You can preview
media, add tags, and save background clip hotspots locally.

### Assets API
```
GET /assets/list?type=bg_clips|music|sfx|fonts
GET /assets/metadata?path=bg_clips/example.mp4
GET /assets/preview?path=bg_clips/example.mp4
GET /assets/tags?type=bg_clips
PUT /assets/tags
GET /assets/hotspots?path=bg_clips/example.mp4
PUT /assets/hotspots
```

## Hotspots + stitched clips
Hotspots are preferred sampling ranges when `bg_mode=stitched_clips` and when
randomly trimming single clips.

## Loop smoothing
Set `loop_smoothing_seconds` to add a short crossfade at loop points when using
`single_clip_loop`.

## Output validation
After render, `validation.json` records resolution, duration, and loudness checks.
Access via `/projects/<job_id>/validation`.

## Quality gates
Enable quality gates in the Generate form or presets to auto-rewrite weak hooks
and compress dense captions (using local LLM + heuristics).

## Caption readability report
Access `/projects/<job_id>/caption_report` for readability metrics and suggestions.

## Cancel jobs
Stop a running job with:
```
POST /cancel/<job_id>
```

## Publish pack export
Create a zip bundle with final video, thumbnails, and metadata:
```
POST /projects/<job_id>/export_publish_pack
```
Then download `outputs/<job_id>/publish_pack.zip`.

## Smoke test (optional)
With the server running:
```bash
python scripts/smoke_test.py
```

## Beats editor
Use the Gallery detail view to edit beats (time + text), reorder, add/remove, then
re-render from the edited beats. The backend persists beats in SQLite and updates
`outputs/<job_id>/script.json`.

## Preview renders
Preview mode renders a subrange (default 10s) to `outputs/<job_id>/preview.mp4`
without overwriting the final render. Use the Gallery detail controls to set
start/duration and render a quick preview.

## Stitched background clips
`bg_mode=stitched_clips` selects multiple background clips and stitches them
into `outputs/<job_id>/bg_stitched.mp4`. Segment boundaries are saved to
`outputs/<job_id>/bg_segments.json`.

## Variations, Variant Lab, and AB tests
- **Generate 5 Variations**: creates 5 jobs from the same prompt with small
  randomizations.
- **Variant Lab**: generates hook/title candidates and lets you pick a combo
  before generating.
- **AB Test**: create multiple variants with different overrides and compare
  them side-by-side in the Gallery detail view.

## Hook scoring + rewrite
Use the Hook tools in the Gallery detail view to score hooks (0-100 with
reasons) and request rewrites locally via the LLM.

## Metrics + retention suggestions
The Metrics panel shows beat density and words-per-second charts with heuristic
suggestions like "Too slow between 12-18s".

## Unhinged mode
The UNHINGED toggle on the Generate page applies aggressive defaults: faster
speech, stronger zoom/shake, heavier SFX, and higher caption emphasis. It does
not overwrite saved presets.

## Done means (manual checks)
- Generate a short normally and confirm `final.mp4` appears.
- Preview 10s render produces `preview.mp4` quickly.
- Edit beat text -> regenerate voice -> final changes.
- Edit beat timestamps -> captions shift accordingly.
- `stitched_clips` mode uses multiple background clips.
- Generate 5 variations returns 5 job IDs and all render.
- Hook score endpoint returns score + reasons.
- Rewrite hook returns 5 candidates and can apply one.
- Metrics charts render and suggestions appear.
- Unhinged mode produces more intense settings and faster pacing.
- Assets tab lists clips/music/sfx/fonts and previews them.
- Tagging works and persists after refresh.
- Hotspots save and stitched clips prefer hotspots.
- Loop smoothing produces smoother loop transitions.
- Output validator returns info; fails if wrong resolution.
- Quality gates auto retry low-scoring hooks.
- Caption report displays WPS graph + suggestions.
- If main FFmpeg graph fails, fallback succeeds.
- Cancel endpoint stops running job and cleans up processes.
- Publish pack zip downloads with correct files and metadata.
- Optimization loop runs multiple attempts and selects best.
- Hook pool generation returns 10 hooks and uses winner.
- Virality report exports HTML and opens correctly.
- Benchmark run produces results in UI and DB.
- Routing chooses models according to policy and falls back if needed.
- CLI can generate a job and outputs final.mp4.
- Scheduler can run daily N jobs (simulate with small interval).
- Watch-folder scan picks up prompts file and creates jobs.
- Campaign mode generates multiple parts with continuity enforced.
- Campaign export zip contains outputs and metadata.
- Hook-first enabled saves `hooks.json` and uses selected hook.
- Caption autofix reduces WPS or rewrites captions and saves `subtitles_autofix.ass`.
- Sidechain ducking is audible and voice is clear.
- Beat-aware effects plan limits shake to top impact beats.
- Virality score endpoint returns score + reasons + problem intervals.
- Candidate selection generates 3 scripts and renders only the chosen one.
- Campaign memory prevents repeating hooks; memory endpoint shows entries.
- Scheduler dry-run returns planned tasks without enqueuing.
- Watch-folder approve mode lists pending batches and approval enqueues jobs.
- Campaign export pro zip includes publish packs + virality reports + summary.
