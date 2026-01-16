from __future__ import annotations

from typing import Dict

from fastapi import APIRouter

from ..model_ops.benchmarks import list_benchmarks, run_benchmarks

router = APIRouter()
_context: Dict[str, object] = {}


def init_context(settings) -> None:
    _context["settings"] = settings


@router.post("/benchmarks/run")
def run_benchmark_endpoint() -> Dict:
    settings = _context["settings"]
    results = run_benchmarks(settings)
    return {"results": results}


@router.get("/benchmarks")
def list_benchmarks_endpoint() -> Dict:
    settings = _context["settings"]
    return {"benchmarks": list_benchmarks(settings)}
