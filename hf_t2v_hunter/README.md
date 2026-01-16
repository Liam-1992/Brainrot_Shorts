# hf_t2v_hunter

Local-only CLI + Python library to discover, rank, and download Hugging Face text-to-video models that are realistically runnable on a 12GB VRAM GPU.

No cloud inference. All discovery uses Hugging Face Hub APIs.

## Install

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Optional (only for `--smoke-test` validation):

```bash
pip install torch diffusers
```

## CLI

Search and rank:

```bash
python -m hf_t2v_hunter.cli search --top 50 --out results.json
```

Recommend top 3 for 12GB VRAM:

```bash
python -m hf_t2v_hunter.cli recommend --vram 12 --policy balanced --top 3
```

Download top 3:

```bash
python -m hf_t2v_hunter.cli pull --top 3 --dest ./models --report report.json
```

Validate a model:

```bash
python -m hf_t2v_hunter.cli validate --model org/repo
python -m hf_t2v_hunter.cli validate --model org/repo --smoke-test
```

List downloaded:

```bash
python -m hf_t2v_hunter.cli list-downloaded --dest ./models
```

## Library API

```python
from hf_t2v_hunter import Config, search_candidates, rank_models, download_models, validate_model

config = Config(vram_gb=12)
models = search_candidates(config)
ranked = rank_models(models, config)
report = download_models(ranked, config, dest=Path("./models"), top_n=3)
```

## VRAM heuristics

The filter uses multiple signals to decide 12GB compatibility:

- total weight size (default `--max-model-size-gb 8.5`)
- model card hints like “24GB required”, “A100”, “H100”
- architecture family hints (large CogVideo, VideoCrafter, etc.)
- diffusers compatibility (default required)
- quantized weights present (int8/4bit/gguf)

Filtered-out models include reasons like:

- `weights_too_large`
- `requires_high_vram_hint`
- `heavy_architecture`
- `not_diffusers_compatible`
- `unknown_requirements`

Override with:

```bash
--allow-over-vram
--no-require-diffusers
--no-strict-vram
```

## Ranking

Score = 0–100 based on:

- downloads (30d)
- likes
- recency
- quality hints (diffusers, example videos, safetensors, quantized weights)

Weights are configurable:

```bash
--weights downloads=0.45 likes=0.20 recency=0.15 quality=0.20
```

## License & NSFW filters

Allowed licenses (default):

- apache-2.0, mit, bsd-2-clause, bsd-3-clause
- creativeml-openrail-m, stabilityai-openrail, openrail, openrail++
- cc-by-4.0

Disallowed by default:

- missing/unknown
- cc-by-nc-*
- gpl-*

Override with:

```bash
--allow-nc
--allow-gpl
```

NSFW is filtered unless `--allow-nsfw` is provided.

## Reports

`search` and `pull` produce:

- JSON report with candidates, filtered reasons, ranking
- Markdown summary table

Each downloaded model writes `model_info.json` with score, reasons, tags, and VRAM estimate.

## Done means

- `search` produces a ranked list filtered for 12GB VRAM with reasons.
- `recommend` returns top 3 for 12GB VRAM.
- `pull` downloads top N and writes per-model metadata + report.
- `validate` works in lightweight mode; smoke test runs when deps exist.
- README documents usage and VRAM heuristics.

