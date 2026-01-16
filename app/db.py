from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    job_id TEXT PRIMARY KEY,
    prompt TEXT,
    style TEXT,
    created_at TEXT,
    status TEXT,
    final_path TEXT,
    duration REAL,
    voice TEXT,
    preset_name TEXT,
    title TEXT,
    thumb_path TEXT,
    thumb_styled_path TEXT,
    group_id TEXT,
    variant_name TEXT
);

CREATE TABLE IF NOT EXISTS beats (
    job_id TEXT PRIMARY KEY,
    beats_json TEXT,
    voiceover_text TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS asset_tags (
    path TEXT PRIMARY KEY,
    type TEXT,
    tags TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS clip_hotspots (
    path TEXT PRIMARY KEY,
    hotspots TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS optimization_attempts (
    job_id TEXT,
    attempt INTEGER,
    selected INTEGER DEFAULT 0,
    hook_score REAL,
    reasons_json TEXT,
    metrics_json TEXT,
    script_path TEXT,
    created_at TEXT,
    PRIMARY KEY (job_id, attempt)
);

CREATE TABLE IF NOT EXISTS hook_pools (
    job_id TEXT PRIMARY KEY,
    created_at TEXT,
    hooks_json TEXT
);

CREATE TABLE IF NOT EXISTS benchmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool TEXT,
    model_name TEXT,
    created_at TEXT,
    metrics_json TEXT
);

CREATE TABLE IF NOT EXISTS routing_prefs (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS schedules (
    schedule_id TEXT PRIMARY KEY,
    type TEXT,
    daily_count INTEGER,
    preset_name TEXT,
    source_path TEXT,
    enabled INTEGER,
    last_run TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS campaigns (
    campaign_id TEXT PRIMARY KEY,
    name TEXT,
    created_at TEXT,
    preset_name TEXT,
    status TEXT,
    metadata_json TEXT
);

CREATE TABLE IF NOT EXISTS campaign_memory (
    campaign_id TEXT PRIMARY KEY,
    memory_json TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS campaign_jobs (
    campaign_id TEXT,
    job_id TEXT,
    order_index INTEGER,
    series_number INTEGER,
    PRIMARY KEY (campaign_id, job_id)
);

CREATE TABLE IF NOT EXISTS automation_state (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS scheduler_runs (
    run_id TEXT PRIMARY KEY,
    started_at TEXT,
    finished_at TEXT,
    report_json TEXT
);

CREATE TABLE IF NOT EXISTS watch_pending (
    batch_id TEXT PRIMARY KEY,
    source_file TEXT,
    prompts_json TEXT,
    created_at TEXT,
    status TEXT
);
"""


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA)
        _ensure_columns(conn, "projects", ["group_id", "variant_name"])


def _ensure_columns(conn: sqlite3.Connection, table: str, columns: list[str]) -> None:
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    for column in columns:
        if column in existing:
            continue
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} TEXT")


def get_connection(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
