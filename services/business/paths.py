from __future__ import annotations

import os
from pathlib import Path

AIOS_ROOT = Path(os.environ.get("AIOS_ROOT", Path.home() / "AIOS")).expanduser().resolve()
DB_PATH = (
    Path(os.environ.get("AIOS_DB", str(AIOS_ROOT / "data" / "aios.db"))).expanduser().resolve()
)
CONFIG_DIR = AIOS_ROOT / "config"
STAGING_ROOT = AIOS_ROOT / "staging"
RAW_SOURCES_ROOT = STAGING_ROOT / "raw-sources"
WIKI_CANDIDATES_ROOT = STAGING_ROOT / "business-wiki-candidates"
LLM_JOBS_ROOT = STAGING_ROOT / "business-llm-jobs"
LLM_RESPONSES_ROOT = STAGING_ROOT / "business-llm-responses"
MANUAL_INBOX = RAW_SOURCES_ROOT / "manual" / "inbox"
MANUAL_PROCESSED = RAW_SOURCES_ROOT / "manual" / "inbox" / "processed"


def raw_source_dir(source_type: str, occurred_at_iso: str) -> Path:
    """Date-partitioned immutable raw storage: raw-sources/{type}/YYYY/MM/DD/."""
    date_part = occurred_at_iso[:10]  # YYYY-MM-DD
    year, month, day = date_part.split("-")
    return RAW_SOURCES_ROOT / source_type / year / month / day


def ensure_staging_dirs() -> list[Path]:
    dirs = [
        RAW_SOURCES_ROOT / "manual" / "inbox",
        MANUAL_PROCESSED,
        RAW_SOURCES_ROOT / "gmail",
        RAW_SOURCES_ROOT / "discord",
        RAW_SOURCES_ROOT / "x",
        WIKI_CANDIDATES_ROOT / "summaries",
        WIKI_CANDIDATES_ROOT / "concepts",
        WIKI_CANDIDATES_ROOT / "entities",
        WIKI_CANDIDATES_ROOT / "courses",
        WIKI_CANDIDATES_ROOT / "questions",
        WIKI_CANDIDATES_ROOT / "decisions",
        WIKI_CANDIDATES_ROOT / "contradictions",
        LLM_JOBS_ROOT,
        LLM_RESPONSES_ROOT,
    ]
    for path in dirs:
        path.mkdir(parents=True, exist_ok=True)
    return dirs
