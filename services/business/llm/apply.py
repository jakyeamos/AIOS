from __future__ import annotations

import sqlite3

from services.business.llm.agent_provider import load_agent_responses
from services.business.llm.models import SourceAnalysis
from services.business.paths import WIKI_CANDIDATES_ROOT
from services.business.schema import ensure_business_memory_schema
from services.business.sources_db import DbSource
from services.business.taxonomy import summary_slug
from services.business.wiki.graph import index_wiki_page_fts
from services.business.wiki.io import atomic_write
from services.business.wiki.templates import render_summary_page


def _row_to_source(row: sqlite3.Row) -> DbSource:
    import json

    tags: list[str] = []
    raw_tags = row["tags_json"]
    if raw_tags:
        try:
            parsed = json.loads(raw_tags)
            if isinstance(parsed, list):
                tags = [str(item) for item in parsed]
        except json.JSONDecodeError:
            pass
    return DbSource(
        source_id=str(row["id"]),
        source_type=str(row["source_type"]),
        body_text=str(row["body_text"] or row["original_content"] or ""),
        subject_or_title=row["subject_or_title"],
        author_name=row["author_name"],
        channel_or_thread=row["channel_or_thread"],
        occurred_at=str(row["occurred_at"] or row["created_at"]),
        privacy_level=str(row["privacy_level"] or "internal"),
        raw_path=row["raw_path"],
        tags=tags,
    )


def fetch_source(conn: sqlite3.Connection, source_id: str) -> DbSource | None:
    row = conn.execute("SELECT * FROM memory_raw_sources WHERE id = ?", (source_id,)).fetchone()
    if not row:
        return None
    return _row_to_source(row)


def apply_llm_analyses(
    conn: sqlite3.Connection,
    analyses: dict[str, SourceAnalysis],
) -> dict:
    ensure_business_memory_schema(conn)
    applied = 0
    missing_sources: list[str] = []
    for source_id, analysis in analyses.items():
        source = fetch_source(conn, source_id)
        if not source:
            missing_sources.append(source_id)
            continue
        summary_path = WIKI_CANDIDATES_ROOT / "summaries" / f"{summary_slug(source)}.md"
        content = render_summary_page(source, analysis=analysis)
        atomic_write(summary_path, content)
        index_wiki_page_fts(conn, vault_path=str(summary_path), content=content)
        applied += 1
    conn.commit()
    return {"applied": applied, "missing_sources": missing_sources}


def apply_agent_run(conn: sqlite3.Connection, run_id: str) -> dict:
    analyses = load_agent_responses(run_id)
    result = apply_llm_analyses(conn, analyses)
    result["run_id"] = run_id
    result["responses_found"] = len(analyses)
    return result
