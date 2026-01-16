from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

from .types import Config
from .hub import search_candidates
from .filters import apply_filters
from .scoring import rank_models
from .downloader import download_models, list_downloaded
from .validators import validate_model
from .report import write_json_report, write_markdown_report


def parse_weights(weights: List[str]) -> Dict[str, float]:
    parsed = {}
    for item in weights:
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        try:
            parsed[key.strip()] = float(value)
        except Exception:
            continue
    return parsed


def build_config(args) -> Config:
    config = Config(
        vram_gb=args.vram,
        max_model_size_gb=args.max_model_size_gb,
        strict_vram=not args.no_strict_vram,
        allow_over_vram=args.allow_over_vram,
        allow_cpu_offload=not args.no_cpu_offload,
        require_diffusers=not args.no_require_diffusers,
        include_i2v=args.include_i2v,
        allow_nsfw=args.allow_nsfw,
        allow_nc=args.allow_nc,
        allow_gpl=args.allow_gpl,
        allow_trust_remote_code=args.allow_trust_remote_code,
        max_disk_gb=args.max_disk_gb,
        search_limit=args.search_limit,
        recency_days=args.recency_days,
        scan_readme=not args.no_readme,
    )
    if args.weights:
        config.weights.update(parse_weights(args.weights))
    return config


def cmd_search(args) -> int:
    config = build_config(args)
    candidates = search_candidates(config)
    scored = apply_filters(config, candidates)
    ranked = rank_models(scored, config)
    top = ranked[: args.top]

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_json_report(out_path, ranked, top)
    md_path = out_path.with_suffix(".md")
    write_markdown_report(md_path, top)
    print(f"Wrote {out_path} and {md_path}")
    return 0


def cmd_recommend(args) -> int:
    config = build_config(args)
    if args.policy == "popularity":
        config.weights.update({"downloads": 0.55, "likes": 0.25, "recency": 0.1, "quality": 0.1})
    elif args.policy == "recent":
        config.weights.update({"downloads": 0.3, "likes": 0.2, "recency": 0.3, "quality": 0.2})

    candidates = search_candidates(config)
    scored = apply_filters(config, candidates)
    ranked = rank_models(scored, config)
    top = ranked[: args.top]
    for idx, item in enumerate(top, start=1):
        print(f"{idx}. {item.model.repo_id} ({item.score})")
        print(f"   reasons: {', '.join(item.reasons[:3])}")
    return 0


def cmd_pull(args) -> int:
    config = build_config(args)
    candidates = search_candidates(config)
    scored = apply_filters(config, candidates)
    ranked = rank_models(scored, config)
    top = ranked[: args.top]

    dest = Path(args.dest)
    report = download_models(ranked, config, dest, args.top)

    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        write_json_report(report_path, ranked, top, downloaded=report)
        md_path = report_path.with_suffix(".md")
        write_markdown_report(md_path, top)
        print(f"Wrote {report_path} and {md_path}")

    print(f"Downloaded {len(report.downloaded)} models. Skipped {len(report.skipped)}.")
    return 0


def cmd_validate(args) -> int:
    config = build_config(args)
    result = validate_model(args.model, config, smoke_test=args.smoke_test)
    print(json.dumps(result.__dict__, indent=2))
    return 0 if result.ok else 1


def cmd_list_downloaded(args) -> int:
    dest = Path(args.dest)
    payload = list_downloaded(dest)
    print(json.dumps(payload, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hf_t2v_hunter")
    parser.add_argument("--vram", type=float, default=12.0)
    parser.add_argument("--max-model-size-gb", type=float, default=8.5)
    parser.add_argument("--no-strict-vram", action="store_true")
    parser.add_argument("--allow-over-vram", action="store_true")
    parser.add_argument("--no-cpu-offload", action="store_true")
    parser.add_argument("--no-require-diffusers", action="store_true")
    parser.add_argument("--include-i2v", action="store_true")
    parser.add_argument("--allow-nsfw", action="store_true")
    parser.add_argument("--allow-nc", action="store_true")
    parser.add_argument("--allow-gpl", action="store_true")
    parser.add_argument("--allow-trust-remote-code", action="store_true")
    parser.add_argument("--max-disk-gb", type=float, default=30.0)
    parser.add_argument("--search-limit", type=int, default=200)
    parser.add_argument("--recency-days", type=int, default=180)
    parser.add_argument("--no-readme", action="store_true")
    parser.add_argument("--weights", nargs="*")

    sub = parser.add_subparsers(dest="command", required=True)

    search = sub.add_parser("search")
    search.add_argument("--top", type=int, default=50)
    search.add_argument("--out", type=str, default="results.json")
    search.set_defaults(func=cmd_search)

    pull = sub.add_parser("pull")
    pull.add_argument("--top", type=int, default=3)
    pull.add_argument("--dest", type=str, required=True)
    pull.add_argument("--report", type=str)
    pull.set_defaults(func=cmd_pull)

    recommend = sub.add_parser("recommend")
    recommend.add_argument("--top", type=int, default=3)
    recommend.add_argument("--policy", type=str, default="balanced", choices=["balanced", "popularity", "recent"])
    recommend.set_defaults(func=cmd_recommend)

    validate = sub.add_parser("validate")
    validate.add_argument("--model", type=str, required=True)
    validate.add_argument("--smoke-test", action="store_true")
    validate.set_defaults(func=cmd_validate)

    list_cmd = sub.add_parser("list-downloaded")
    list_cmd.add_argument("--dest", type=str, required=True)
    list_cmd.set_defaults(func=cmd_list_downloaded)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

