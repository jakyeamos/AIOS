from __future__ import annotations

import sqlite3
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime

from services.business.llm.agent_provider import AgentLLMProvider
from services.business.llm.base import LLMProvider
from services.business.llm.client import resolve_llm_provider
from services.business.llm.models import SourceAnalysis
from services.business.paths import WIKI_CANDIDATES_ROOT, ensure_staging_dirs
from services.business.schema import ensure_business_memory_schema
from services.business.sources_db import (
    DbSource,
    fetch_uncompiled_sources,
    mark_sources_compiled,
    resolve_since_cursor,
)
from services.business.taxonomy import (
    DEFAULT_COURSE_SLUG,
    DEFAULT_COURSE_TITLE,
    ConceptMatch,
    detect_concepts,
    has_course_signal,
    summary_slug,
)
from services.business.wiki.graph import index_wiki_page_fts, upsert_reference, upsert_topic
from services.business.wiki.index import append_compile_log, rebuild_index
from services.business.wiki.io import atomic_write, read_existing_body
from services.business.wiki.templates import (
    render_concept_page,
    render_course_page,
    render_summary_page,
)


@dataclass
class CompileSummary:
    run_id: str
    status: str
    sources_processed: int
    pages_created: int
    pages_updated: int
    since_cursor: str | None
    llm_enabled: bool = False
    llm_provider: str | None = None
    llm_analyzed: int = 0
    llm_jobs_queued: int = 0
    agent_manifest: str | None = None
    errors: list[str] = field(default_factory=list)


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _new_run_id() -> str:
    return f"compile-{uuid.uuid4()}"


def _write_page(path, content: str, summary: CompileSummary) -> None:
    existed = path.exists()
    atomic_write(path, content)
    if existed:
        summary.pages_updated += 1
    else:
        summary.pages_created += 1


def _analyze_source(
    provider: LLMProvider,
    source: DbSource,
    summary: CompileSummary,
) -> SourceAnalysis | None:
    if isinstance(provider, AgentLLMProvider):
        provider.analyze_source(source)
        summary.llm_jobs_queued += 1
        return None
    try:
        analysis = provider.analyze_source(source)
        if analysis:
            summary.llm_analyzed += 1
        return analysis
    except Exception as exc:  # noqa: BLE001
        summary.errors.append(f"llm:{source.source_id}: {exc}")
        return None


def compile_business_sources(
    conn: sqlite3.Connection,
    *,
    since: str = "beginning",
    llm: bool = False,
    provider_name: str | None = None,
) -> CompileSummary:
    ensure_business_memory_schema(conn)
    ensure_staging_dirs()

    since_cursor = resolve_since_cursor(conn, since)
    sources = fetch_uncompiled_sources(conn, since_iso=since_cursor)
    run_id = _new_run_id()
    started_at = _now_iso()
    evidence_date = datetime.now(UTC).date().isoformat()

    llm_provider: LLMProvider | None = None
    if llm:
        llm_provider = resolve_llm_provider(provider_name)
        if llm_provider is None:
            llm_provider = AgentLLMProvider()

    summary = CompileSummary(
        run_id=run_id,
        status="success",
        sources_processed=0,
        pages_created=0,
        pages_updated=0,
        since_cursor=since_cursor,
        llm_enabled=bool(llm),
        llm_provider=llm_provider.name if llm_provider else None,
    )

    conn.execute(
        """
        INSERT INTO business_compile_runs (
            id, started_at, status, since_cursor, llm_enabled
        )
        VALUES (?, ?, 'running', ?, ?)
        """,
        (run_id, started_at, since_cursor or since, 1 if llm else 0),
    )
    conn.commit()

    concept_sources: dict[str, list[DbSource]] = defaultdict(list)
    concept_meta: dict[str, ConceptMatch] = {}
    course_sources: list[DbSource] = []
    processed_ids: list[str] = []
    agent_sources: list[DbSource] = []

    for source in sources:
        try:
            analysis: SourceAnalysis | None = None
            if llm_provider:
                analysis = _analyze_source(llm_provider, source, summary)
                if isinstance(llm_provider, AgentLLMProvider):
                    agent_sources.append(source)

            summary_path = WIKI_CANDIDATES_ROOT / "summaries" / f"{summary_slug(source)}.md"
            summary_content = render_summary_page(source, analysis=analysis)
            _write_page(summary_path, summary_content, summary)
            index_wiki_page_fts(conn, vault_path=str(summary_path), content=summary_content)

            for concept in detect_concepts(source):
                concept_sources[concept.slug].append(source)
                concept_meta[concept.slug] = concept

            if has_course_signal(source):
                course_sources.append(source)

            processed_ids.append(source.source_id)
            summary.sources_processed += 1
        except Exception as exc:  # noqa: BLE001
            summary.errors.append(f"{source.source_id}: {exc}")

    if llm_provider and isinstance(llm_provider, AgentLLMProvider) and agent_sources:
        manifest = llm_provider.finalize_manifest(agent_sources)
        summary.agent_manifest = str(manifest)

    for slug, matched_sources in concept_sources.items():
        try:
            concept = concept_meta[slug]
            concept_path = WIKI_CANDIDATES_ROOT / "concepts" / f"{slug}.md"
            existing = read_existing_body(concept_path)
            content = render_concept_page(
                concept,
                matched_sources,
                existing_body=existing,
                evidence_date=evidence_date,
            )
            _write_page(concept_path, content, summary)
            index_wiki_page_fts(conn, vault_path=str(concept_path), content=content)

            topic_id = upsert_topic(
                conn,
                slug=slug,
                title=concept.title,
                kind="concept",
                summary=concept.business_label,
                canonical_href=f"concepts/{slug}.md",
                tags=["concept", concept.business_label],
                source_ids=[source.source_id for source in matched_sources],
            )
            for source in matched_sources:
                upsert_reference(
                    conn,
                    topic_id=topic_id,
                    source_id=source.source_id,
                    label=source.subject_or_title or source.source_id,
                    excerpt=source.body_text[:220],
                )
        except Exception as exc:  # noqa: BLE001
            summary.errors.append(f"concept:{slug}: {exc}")

    if course_sources:
        try:
            course_path = WIKI_CANDIDATES_ROOT / "courses" / f"{DEFAULT_COURSE_SLUG}.md"
            existing = read_existing_body(course_path)
            content = render_course_page(
                course_sources,
                course_title=DEFAULT_COURSE_TITLE,
                course_slug=DEFAULT_COURSE_SLUG,
                existing_body=existing,
                evidence_date=evidence_date,
            )
            _write_page(course_path, content, summary)
            index_wiki_page_fts(conn, vault_path=str(course_path), content=content)
            upsert_topic(
                conn,
                slug=DEFAULT_COURSE_SLUG,
                title=DEFAULT_COURSE_TITLE,
                kind="course",
                summary="Compiled course feedback and planning signals",
                canonical_href=f"courses/{DEFAULT_COURSE_SLUG}.md",
                tags=["course"],
                source_ids=[source.source_id for source in course_sources],
            )
        except Exception as exc:  # noqa: BLE001
            summary.errors.append(f"course:{DEFAULT_COURSE_SLUG}: {exc}")

    finished_at = _now_iso()
    if processed_ids:
        mark_sources_compiled(conn, processed_ids, finished_at)

    if summary.errors and summary.sources_processed:
        summary.status = "partial"
    elif summary.errors:
        summary.status = "failed"
    else:
        summary.status = "success"

    rebuild_index()
    append_compile_log(
        run_id=run_id,
        sources_processed=summary.sources_processed,
        pages_created=summary.pages_created,
        pages_updated=summary.pages_updated,
    )

    conn.execute(
        """
        UPDATE business_compile_runs
        SET finished_at = ?, status = ?, sources_processed = ?,
            pages_created = ?, pages_updated = ?
        WHERE id = ?
        """,
        (
            finished_at,
            summary.status,
            summary.sources_processed,
            summary.pages_created,
            summary.pages_updated,
            run_id,
        ),
    )
    conn.commit()
    return summary
