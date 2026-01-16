from __future__ import annotations

import re
import urllib.request
import zipfile
from pathlib import Path
from urllib.parse import urlparse

from .utils import append_log, ensure_dir


def _sanitize_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    cleaned = cleaned.strip("-") or "model"
    return cleaned[:80]


def _filename_from_url(url: str) -> str:
    parsed = urlparse(url)
    name = Path(parsed.path).name
    if not name:
        return "file.bin"
    return name


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme}")


def _safe_output_dir(base: Path, kind: str, name: str) -> Path:
    target = (base / kind / name).resolve()
    base_resolved = base.resolve()
    if not target.is_relative_to(base_resolved):
        raise ValueError("Invalid output path")
    return target


def _unique_filename(output_dir: Path, filename: str, seen: set[str]) -> str:
    name = _sanitize_name(Path(filename).stem) + Path(filename).suffix
    candidate = name
    counter = 1
    while candidate in seen or (output_dir / candidate).exists():
        candidate = f"{Path(name).stem}_{counter}{Path(name).suffix}"
        counter += 1
    seen.add(candidate)
    return candidate


def _download_file(url: str, dest: Path, job_state: dict, log_path: Path, total_holder: dict) -> None:
    _validate_url(url)
    request = urllib.request.Request(url, headers={"User-Agent": "brainrot-shorts/0.1"})
    with urllib.request.urlopen(request) as response:
        length_header = response.headers.get("Content-Length")
        file_total = int(length_header) if length_header and length_header.isdigit() else 0
        if file_total:
            total_holder["total_bytes"] += file_total
            job_state["total_bytes"] = total_holder["total_bytes"]
        with dest.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
                job_state["downloaded_bytes"] += len(chunk)
                if job_state["total_bytes"] > 0:
                    job_state["progress"] = min(
                        99, int(job_state["downloaded_bytes"] / job_state["total_bytes"] * 100)
                    )
    append_log(log_path, f"Saved {dest.name}")
    job_state["logs"].append(f"Saved {dest.name}")


def _log_and_store(job_state: dict, log_path: Path, message: str) -> None:
    append_log(log_path, message)
    job_state["logs"].append(message)


def run_download(settings, request, download_id: str, job_state: dict) -> Path:
    urls = [url.strip() for url in request.urls if url.strip()]
    if not urls:
        raise ValueError("No valid URLs provided")

    default_name = _sanitize_name(Path(_filename_from_url(urls[0])).stem or "model")
    output_dir = _safe_output_dir(
        settings.MODELS_DIR,
        request.kind,
        _sanitize_name(request.name or default_name),
    )
    ensure_dir(output_dir)
    log_path = (settings.OUTPUTS_DIR / "downloads" / download_id / "log.txt").resolve()
    ensure_dir(log_path.parent)

    _log_and_store(job_state, log_path, f"Starting download to {output_dir}")

    seen: set[str] = set()
    total_holder = {"total_bytes": 0}
    job_state["downloaded_bytes"] = 0
    job_state["total_bytes"] = 0
    job_state["progress"] = 0

    for url in urls:
        filename = _unique_filename(output_dir, _filename_from_url(url), seen)
        dest = output_dir / filename
        if dest.exists() and not request.overwrite:
            raise FileExistsError(f"{dest.name} already exists")
        _log_and_store(job_state, log_path, f"Downloading {url}")
        _download_file(url, dest, job_state, log_path, total_holder)
        if dest.suffix.lower() == ".zip":
            with zipfile.ZipFile(dest, "r") as archive:
                archive.extractall(output_dir)
            _log_and_store(job_state, log_path, f"Extracted {dest.name}")

    job_state["progress"] = 100
    _log_and_store(job_state, log_path, "Download complete")
    return output_dir
