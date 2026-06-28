from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from services.meta_learning_router import route_scored_signals
from services.meta_learning_scoring import score_meta_learning_signals
from services.meta_learning_signals import extract_meta_learning_signals
from services.session_providers.base import NormalizedSession, SessionProvider
from services.workflow_synthesis import (
    _skill_spec,
    _store_archetype_proposal,
    _validation_plan,
    _workflow_spec,
    ensure_workflow_synthesis_schema,
)

Lane = Literal["friction_tool", "workflow_skill", "impact_idea"]
CandidateStatus = Literal["pending_review", "approved", "rejected", "observed", "superseded"]
LANES: set[str] = {"friction_tool", "workflow_skill", "impact_idea"}
STATUSES: set[str] = {"pending_review", "approved", "rejected", "observed", "superseded"}
DEFAULT_REDACTION_PATTERNS = {
    "api_key": r"sk-[A-Za-z0-9]{20,}",
    "bearer_token": r"Bearer [A-Za-z0-9._-]{10,}",
    "auth_header": r"Authorization: [^\n]+",
    "env_secret": r"\b[A-Z_]{3,}=[A-Za-z0-9._~\-+/]{8,}",
    "pem_key": r"-----BEGIN [^-]+-----.*?-----END [^-]+-----",
    "github_token": r"ghp_[A-Za-z0-9]{36}",
    "slack_token": r"xoxb-[0-9]+-[A-Za-z0-9]+",
}


@dataclass(frozen=True)
class SessionIntelligenceOptions:
    since: str = "last"
    lane: str = "all"
    write_report: bool = False
    report_root: Path | None = None
    config_path: Path | None = None


@dataclass(frozen=True)
class SessionIntelligenceBackfillOptions:
    since: str = "all"
    lane: str = "all"
    batch_size: int = 250
    write_report: bool = False
    report_root: Path | None = None
    config_path: Path | None = None


@dataclass(frozen=True)
class _CandidateDraft:
    lane: Lane
    title: str
    summary: str
    impact_score: int
    confidence: float
    source_sessions: list[str]
    evidence: list[dict[str, str]]
    proposed_artifact_type: str
    proposed_next_action: str


def ensure_session_intelligence_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS session_intelligence_runs (
          id TEXT PRIMARY KEY,
          provider TEXT NOT NULL,
          scanned_range TEXT NOT NULL,
          source_count INTEGER NOT NULL DEFAULT 0,
          session_count INTEGER NOT NULL DEFAULT 0,
          candidate_count INTEGER NOT NULL DEFAULT 0,
          report_path TEXT,
          report_json_path TEXT,
          status TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS session_intelligence_candidates (
          id TEXT PRIMARY KEY,
          lane TEXT NOT NULL,
          title TEXT NOT NULL,
          summary TEXT NOT NULL,
          impact_score INTEGER NOT NULL,
          confidence REAL NOT NULL,
          status TEXT NOT NULL DEFAULT 'pending_review',
          source_sessions_json TEXT NOT NULL DEFAULT '[]',
          redacted_evidence_json TEXT NOT NULL DEFAULT '[]',
          proposed_artifact_type TEXT NOT NULL,
          proposed_next_action TEXT NOT NULL,
          review_note TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS session_intelligence_cursors (
          provider TEXT NOT NULL,
          source_path TEXT NOT NULL,
          content_hash TEXT NOT NULL,
          last_mtime REAL,
          last_size INTEGER,
          last_scanned_at TEXT NOT NULL,
          PRIMARY KEY (provider, source_path)
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_session_intelligence_candidates_review
          ON session_intelligence_candidates(status, lane, updated_at DESC)
        """
    )


def run_session_intelligence(
    conn: sqlite3.Connection,
    *,
    provider: SessionProvider,
    options: SessionIntelligenceOptions,
) -> dict[str, Any]:
    ensure_session_intelligence_schema(conn)
    return _run_session_intelligence_for_sources(
        conn,
        provider=provider,
        options=options,
        sources=_sources_for_options(conn, provider, options),
    )


def run_session_intelligence_backfill(
    conn: sqlite3.Connection,
    *,
    provider: SessionProvider,
    options: SessionIntelligenceBackfillOptions,
) -> dict[str, Any]:
    ensure_session_intelligence_schema(conn)
    batch_size = max(1, options.batch_size)
    eligible_sources = _eligible_sources_for_since(provider.discover_sources(), options.since)
    pending_sources = [
        source
        for source in eligible_sources
        if not _cursor_matches_source_stat(conn, provider=provider, source=source)
    ]
    batches = []
    report_paths = []
    report_json_paths = []
    for batch_index, source_batch in enumerate(_chunks(pending_sources, batch_size), start=1):
        batch_options = SessionIntelligenceOptions(
            since=f"backfill:{options.since}:batch-{batch_index}",
            lane=options.lane,
            write_report=options.write_report,
            report_root=options.report_root,
            config_path=options.config_path,
        )
        result = _run_session_intelligence_for_sources(
            conn,
            provider=provider,
            options=batch_options,
            sources=source_batch,
            skip_current_hash=True,
        )
        batches.append(result)
        if result.get("report_path"):
            report_paths.append(result["report_path"])
        if result.get("report_json_path"):
            report_json_paths.append(result["report_json_path"])

    session_count = sum(batch["summary"]["session_count"] for batch in batches)
    candidate_count = sum(batch["summary"]["candidate_count"] for batch in batches)
    hash_skipped_count = sum(
        batch["summary"].get("hash_skipped_source_count", 0) for batch in batches
    )
    return {
        "backfill_id": f"session-intel-backfill-{uuid.uuid4()}",
        "provider": provider.provider_id,
        "summary": {
            "eligible_source_count": len(eligible_sources),
            "processed_source_count": sum(batch["summary"]["source_count"] for batch in batches),
            "skipped_source_count": len(eligible_sources)
            - len(pending_sources)
            + hash_skipped_count,
            "batch_count": len(batches),
            "session_count": session_count,
            "candidate_count": candidate_count,
        },
        "batches": batches,
        "report_paths": report_paths,
        "report_json_paths": report_json_paths,
    }


def _run_session_intelligence_for_sources(
    conn: sqlite3.Connection,
    *,
    provider: SessionProvider,
    options: SessionIntelligenceOptions,
    sources: list[Any],
    skip_current_hash: bool = False,
) -> dict[str, Any]:
    run_id = f"session-intel-{uuid.uuid4()}"
    now = _now()
    redactors = _load_redactors(options.config_path)
    source_session_pairs = [(source, _normalize_source(provider, source)) for source in sources]
    hash_skipped_pairs = []
    if skip_current_hash:
        pending_pairs = []
        for source, session in source_session_pairs:
            if _cursor_matches_content_hash(
                conn, provider=provider, source=source, content_hash=session.content_hash
            ):
                hash_skipped_pairs.append((source, session))
                continue
            pending_pairs.append((source, session))
        source_session_pairs = pending_pairs
        for source, session in hash_skipped_pairs:
            _upsert_cursor(
                conn,
                provider=provider,
                source=source,
                session=session,
                now=now,
            )
    sources = [source for source, _session in source_session_pairs]
    sessions = [session for _source, session in source_session_pairs]
    candidates = _candidate_drafts(sessions, lane=options.lane)
    stored_candidates = [
        _upsert_candidate(conn, draft, redactors=redactors, now=now) for draft in candidates
    ]
    _seed_workflow_synthesis(
        conn,
        [candidate for candidate in stored_candidates if candidate["lane"] == "workflow_skill"],
    )
    for source, session in zip(sources, sessions, strict=False):
        _upsert_cursor(conn, provider=provider, source=source, session=session, now=now)

    report_path: str | None = None
    report_json_path: str | None = None
    if options.write_report:
        report_path, report_json_path = _write_report(
            options.report_root or Path("data/session-intelligence/reports"),
            run_id=run_id,
            provider=provider.provider_id,
            scanned_range=options.since,
            candidates=stored_candidates,
        )

    conn.execute(
        """
        INSERT INTO session_intelligence_runs (
          id, provider, scanned_range, source_count, session_count, candidate_count,
          report_path, report_json_path, status, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'completed', ?, ?)
        """,
        (
            run_id,
            provider.provider_id,
            options.since,
            len(sources),
            len(sessions),
            len(stored_candidates),
            report_path,
            report_json_path,
            now,
            now,
        ),
    )
    return {
        "run_id": run_id,
        "provider": provider.provider_id,
        "summary": {
            "source_count": len(sources),
            "hash_skipped_source_count": len(hash_skipped_pairs),
            "session_count": len(sessions),
            "candidate_count": len(stored_candidates),
        },
        "candidates": stored_candidates,
        "report_path": report_path,
        "report_json_path": report_json_path,
    }


def list_session_intelligence_candidates(
    conn: sqlite3.Connection,
    *,
    status: str | None = None,
    lane: str = "all",
) -> list[dict[str, Any]]:
    ensure_session_intelligence_schema(conn)
    clauses: list[str] = []
    params: list[str] = []
    if status:
        clauses.append("status = ?")
        params.append(status)
    if lane != "all":
        clauses.append("lane = ?")
        params.append(lane)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = conn.execute(
        f"""
        SELECT *
        FROM session_intelligence_candidates
        {where}
        ORDER BY impact_score DESC, updated_at DESC
        """,
        params,
    ).fetchall()
    return [_candidate_row_to_dict(row) for row in rows]


def mark_session_intelligence_candidate(
    conn: sqlite3.Connection,
    *,
    candidate_id: str,
    status: CandidateStatus,
    note: str = "",
) -> dict[str, Any]:
    ensure_session_intelligence_schema(conn)
    if status not in STATUSES:
        raise ValueError(f"Unsupported candidate status: {status}")
    now = _now()
    conn.execute(
        """
        UPDATE session_intelligence_candidates
        SET status = ?, review_note = ?, updated_at = ?
        WHERE id = ?
        """,
        (status, note, now, candidate_id),
    )
    row = conn.execute(
        "SELECT * FROM session_intelligence_candidates WHERE id = ?",
        (candidate_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Session intelligence candidate not found: {candidate_id}")
    return _candidate_row_to_dict(row)


def _sources_for_options(
    conn: sqlite3.Connection,
    provider: SessionProvider,
    options: SessionIntelligenceOptions,
) -> list[Any]:
    all_sources = _eligible_sources_for_since(provider.discover_sources(), options.since)
    if options.since == "all":
        return all_sources
    result = []
    for source in all_sources:
        stat = source.path.stat()
        cursor = conn.execute(
            """
            SELECT content_hash, last_mtime, last_size
            FROM session_intelligence_cursors
            WHERE provider = ? AND source_path = ?
            """,
            (provider.provider_id, str(source.path)),
        ).fetchone()
        if (
            options.since == "last"
            and cursor is not None
            and cursor["last_mtime"] == stat.st_mtime
            and cursor["last_size"] == stat.st_size
        ):
            continue
        result.append(source)
    return result


def _eligible_sources_for_since(sources: list[Any], since: str) -> list[Any]:
    cutoff = _since_cutoff(since)
    if cutoff is None:
        return sources
    return [
        source
        for source in sources
        if datetime.fromtimestamp(source.path.stat().st_mtime, tz=UTC) >= cutoff
    ]


def _cursor_matches_source_stat(
    conn: sqlite3.Connection,
    *,
    provider: SessionProvider,
    source: Any,
) -> bool:
    stat = source.path.stat()
    cursor = conn.execute(
        """
        SELECT last_mtime, last_size
        FROM session_intelligence_cursors
        WHERE provider = ? AND source_path = ?
        """,
        (provider.provider_id, str(source.path)),
    ).fetchone()
    return (
        cursor is not None
        and cursor["last_mtime"] == stat.st_mtime
        and cursor["last_size"] == stat.st_size
    )


def _cursor_matches_content_hash(
    conn: sqlite3.Connection,
    *,
    provider: SessionProvider,
    source: Any,
    content_hash: str,
) -> bool:
    cursor = conn.execute(
        """
        SELECT content_hash
        FROM session_intelligence_cursors
        WHERE provider = ? AND source_path = ?
        """,
        (provider.provider_id, str(source.path)),
    ).fetchone()
    return cursor is not None and cursor["content_hash"] == content_hash


def _normalize_source(provider: SessionProvider, source: Any) -> NormalizedSession:
    raw = provider.extract_raw_session(source)
    return provider.normalize_session(raw)


def _candidate_drafts(sessions: list[NormalizedSession], *, lane: str) -> list[_CandidateDraft]:
    drafts: list[_CandidateDraft] = []
    if lane in {"all", "friction_tool"}:
        drafts.extend(_friction_candidates(sessions))
    if lane in {"all", "workflow_skill"}:
        drafts.extend(_workflow_candidates(sessions))
    if lane in {"all", "impact_idea"}:
        drafts.extend(_impact_candidates(sessions))
    return drafts


def _friction_candidates(sessions: list[NormalizedSession]) -> list[_CandidateDraft]:
    grouped: dict[str, list[NormalizedSession]] = defaultdict(list)
    for session in sessions:
        if not session.errors_extracted and not session.provider_metadata.get("approval_friction"):
            continue
        command = session.commands_run[-1] if session.commands_run else "tool execution"
        grouped[command].append(session)

    drafts = []
    for command, group in grouped.items():
        evidence = []
        for session in group:
            error = session.errors_extracted[0] if session.errors_extracted else "approval friction"
            evidence.append(
                {
                    "session_id": session.provider_session_id,
                    "summary": f"{command}: {error}",
                    "source": _source_file(session),
                }
            )
        drafts.append(
            _CandidateDraft(
                lane="friction_tool",
                title=f"Deterministic helper for repeated friction: {command}",
                summary=f"Codex hit repeatable friction around `{command}`.",
                impact_score=min(10, 4 + len(group)),
                confidence=0.65 if len(group) == 1 else 0.8,
                source_sessions=_session_ids(group),
                evidence=evidence,
                proposed_artifact_type="deterministic_tool_candidate",
                proposed_next_action="Review whether this repeated failure should become a narrow script, command wrapper, or eval.",
            )
        )

    meta_drafts = _meta_learning_friction_candidates(sessions)
    return _dedupe_drafts([*drafts, *meta_drafts])


def _meta_learning_friction_candidates(sessions: list[NormalizedSession]) -> list[_CandidateDraft]:
    raw_sessions = [_session_to_meta_payload(session) for session in sessions]
    scored = score_meta_learning_signals(extract_meta_learning_signals({"sessions": raw_sessions}))
    routes = {route.signal_id: route for route in route_scored_signals(scored)}
    drafts = []
    for item in scored:
        if item.signal.type != "context_miss":
            continue
        route = routes.get(item.signal.signal_id)
        if route is None:
            continue
        drafts.append(
            _CandidateDraft(
                lane="friction_tool",
                title=f"Regression evidence for {item.signal.type.replace('_', ' ')}",
                summary=item.signal.summary,
                impact_score=max(3, min(10, item.score)),
                confidence=0.6 + min(0.3, item.score / 30),
                source_sessions=item.signal.source_sessions,
                evidence=[
                    {str(key): str(value) for key, value in evidence.items()}
                    for evidence in item.signal.evidence
                ],
                proposed_artifact_type="meta_learning_proposal",
                proposed_next_action=f"Review the {route.target_layer} route before adding rules or eval fixtures.",
            )
        )
    return drafts


def _workflow_candidates(sessions: list[NormalizedSession]) -> list[_CandidateDraft]:
    matched = [
        session
        for session in sessions
        if _session_text(session, include_tools=False).lower().count("workflow") > 0
        and any(
            phrase in _session_text(session, include_tools=False).lower()
            for phrase in (
                "completed cleanly",
                "went well",
                "reusable workflow",
                "repeatable workflow",
            )
        )
    ]
    if not matched:
        return []
    evidence = [
        {
            "session_id": session.provider_session_id,
            "summary": _first_matching_text(
                session, ("workflow", "completed cleanly", "went well")
            ),
            "source": _source_file(session),
        }
        for session in matched
    ]
    return [
        _CandidateDraft(
            lane="workflow_skill",
            title="Reusable Codex workflow pattern",
            summary="One or more Codex sessions describe a repeatable workflow that completed cleanly.",
            impact_score=min(10, 5 + len(matched)),
            confidence=0.7 if len(matched) == 1 else 0.82,
            source_sessions=_session_ids(matched),
            evidence=evidence,
            proposed_artifact_type="skill_or_workflow_candidate",
            proposed_next_action="Review the evidence and decide whether to promote it into a skill or workflow proposal.",
        )
    ]


def _impact_candidates(sessions: list[NormalizedSession]) -> list[_CandidateDraft]:
    matched = [
        session
        for session in sessions
        if any(
            phrase in _session_text(session, include_tools=False).lower()
            for phrase in (
                "highest leverage",
                "impact idea",
                "automation opportunity",
                "project drag",
            )
        )
    ]
    if not matched:
        return []
    evidence = [
        {
            "session_id": session.provider_session_id,
            "summary": _first_matching_text(
                session, ("highest leverage", "impact idea", "automation opportunity")
            ),
            "source": _source_file(session),
        }
        for session in matched
    ]
    return [
        _CandidateDraft(
            lane="impact_idea",
            title="High-leverage idea from Codex sessions",
            summary="Codex sessions surfaced a broad improvement opportunity worth review.",
            impact_score=min(10, 5 + len(matched)),
            confidence=0.68 if len(matched) == 1 else 0.78,
            source_sessions=_session_ids(matched),
            evidence=evidence,
            proposed_artifact_type="review_note",
            proposed_next_action="Review and either convert into a scoped candidate tool/skill or mark observed.",
        )
    ]


def _upsert_candidate(
    conn: sqlite3.Connection,
    draft: _CandidateDraft,
    *,
    redactors: list[tuple[str, re.Pattern[str]]],
    now: str,
) -> dict[str, Any]:
    redacted_evidence = [_redact_evidence(item, redactors) for item in draft.evidence]
    candidate_id = _candidate_id(draft.lane, draft.title, draft.source_sessions, redacted_evidence)
    existing = conn.execute(
        "SELECT * FROM session_intelligence_candidates WHERE id = ?",
        (candidate_id,),
    ).fetchone()
    if existing is None:
        existing = conn.execute(
            """
            SELECT *
            FROM session_intelligence_candidates
            WHERE lane = ? AND title = ?
            ORDER BY created_at ASC
            LIMIT 1
            """,
            (draft.lane, draft.title),
        ).fetchone()
        if existing is not None:
            candidate_id = existing["id"]
    status = existing["status"] if existing is not None else "pending_review"
    review_note = existing["review_note"] if existing is not None else None
    created_at = existing["created_at"] if existing is not None else now
    source_sessions = sorted(
        set(draft.source_sessions) | set(_existing_json_list(existing, "source_sessions_json"))
    )
    redacted_evidence = _merge_evidence(
        _existing_json_list(existing, "redacted_evidence_json"), redacted_evidence
    )
    impact_score = max(draft.impact_score, existing["impact_score"] if existing is not None else 0)
    confidence = max(draft.confidence, existing["confidence"] if existing is not None else 0.0)
    conn.execute(
        """
        INSERT INTO session_intelligence_candidates (
          id, lane, title, summary, impact_score, confidence, status, source_sessions_json,
          redacted_evidence_json, proposed_artifact_type, proposed_next_action, review_note,
          created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
          title = excluded.title,
          summary = excluded.summary,
          impact_score = excluded.impact_score,
          confidence = excluded.confidence,
          source_sessions_json = excluded.source_sessions_json,
          redacted_evidence_json = excluded.redacted_evidence_json,
          proposed_artifact_type = excluded.proposed_artifact_type,
          proposed_next_action = excluded.proposed_next_action,
          updated_at = excluded.updated_at
        """,
        (
            candidate_id,
            draft.lane,
            draft.title,
            draft.summary,
            impact_score,
            confidence,
            status,
            json.dumps(source_sessions, sort_keys=True),
            json.dumps(redacted_evidence, sort_keys=True),
            draft.proposed_artifact_type,
            draft.proposed_next_action,
            review_note,
            created_at,
            now,
        ),
    )
    row = conn.execute(
        "SELECT * FROM session_intelligence_candidates WHERE id = ?",
        (candidate_id,),
    ).fetchone()
    return _candidate_row_to_dict(row)


def _existing_json_list(row: sqlite3.Row | None, column: str) -> list[Any]:
    if row is None:
        return []
    value = json.loads(row[column])
    return value if isinstance(value, list) else []


def _merge_evidence(existing: list[Any], incoming: list[dict[str, str]]) -> list[dict[str, str]]:
    merged: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in [*existing, *incoming]:
        if not isinstance(item, dict):
            continue
        normalized = {str(key): str(value) for key, value in item.items()}
        key = json.dumps(normalized, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        merged.append(normalized)
    return merged


def _seed_workflow_synthesis(
    conn: sqlite3.Connection, workflow_candidates: list[dict[str, Any]]
) -> None:
    if not workflow_candidates:
        return
    ensure_workflow_synthesis_schema(conn)
    for candidate in workflow_candidates:
        proposal_key = "codex_session_workflow_pattern_v1"
        evidence = [item["summary"] for item in candidate["redacted_evidence"]]
        workflow_spec = _workflow_spec(proposal_key, candidate["title"], evidence)
        skill_specs = [_skill_spec(proposal_key, candidate["title"])]
        validation_plan = _validation_plan(proposal_key, evidence)
        _store_archetype_proposal(
            conn,
            proposal_key=proposal_key,
            title=f"Workflow: {candidate['title']}",
            summary=candidate["summary"],
            source_ids=candidate["source_sessions"],
            workflow_spec=workflow_spec,
            skill_specs=skill_specs,
            validation_plan=validation_plan,
            evidence=evidence,
        )


def _upsert_cursor(
    conn: sqlite3.Connection,
    *,
    provider: SessionProvider,
    source: Any,
    session: NormalizedSession,
    now: str,
) -> None:
    stat = source.path.stat()
    conn.execute(
        """
        INSERT INTO session_intelligence_cursors (
          provider, source_path, content_hash, last_mtime, last_size, last_scanned_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(provider, source_path) DO UPDATE SET
          content_hash = excluded.content_hash,
          last_mtime = excluded.last_mtime,
          last_size = excluded.last_size,
          last_scanned_at = excluded.last_scanned_at
        """,
        (
            provider.provider_id,
            str(source.path),
            session.content_hash,
            stat.st_mtime,
            stat.st_size,
            now,
        ),
    )


def _write_report(
    report_root: Path,
    *,
    run_id: str,
    provider: str,
    scanned_range: str,
    candidates: list[dict[str, Any]],
) -> tuple[str, str]:
    report_root.mkdir(parents=True, exist_ok=True)
    markdown_path = report_root / f"{run_id}.md"
    json_path = report_root / f"{run_id}.json"
    lines = [
        f"# Codex Session Intelligence {run_id}",
        "",
        f"- provider: {provider}",
        f"- scanned range: {scanned_range}",
        f"- candidates: {len(candidates)}",
        "",
    ]
    for candidate in candidates:
        lines.extend(
            [
                f"## {candidate['title']}",
                "",
                f"- lane: {candidate['lane']}",
                f"- status: {candidate['status']}",
                f"- impact: {candidate['impact_score']}",
                f"- next: {candidate['proposed_next_action']}",
                "",
                candidate["summary"],
                "",
            ]
        )
        for evidence in candidate["redacted_evidence"][:5]:
            lines.append(
                f"- {evidence.get('session_id', 'unknown')}: {evidence.get('summary', '')}"
            )
        lines.append("")
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    json_path.write_text(
        json.dumps({"run_id": run_id, "candidates": candidates}, indent=2), encoding="utf-8"
    )
    return str(markdown_path), str(json_path)


def _candidate_row_to_dict(row: sqlite3.Row | None) -> dict[str, Any]:
    if row is None:
        raise ValueError("Missing session intelligence candidate row")
    return {
        "id": row["id"],
        "lane": row["lane"],
        "title": row["title"],
        "summary": row["summary"],
        "impact_score": row["impact_score"],
        "confidence": row["confidence"],
        "status": row["status"],
        "source_sessions": json.loads(row["source_sessions_json"]),
        "redacted_evidence": json.loads(row["redacted_evidence_json"]),
        "proposed_artifact_type": row["proposed_artifact_type"],
        "proposed_next_action": row["proposed_next_action"],
        "review_note": row["review_note"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _candidate_id(
    lane: str,
    title: str,
    source_sessions: list[str],
    evidence: list[dict[str, str]],
) -> str:
    payload = {
        "lane": lane,
        "title": _normalize_key(title),
        "source_sessions": sorted(source_sessions),
        "evidence": evidence,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    return f"session-intel-{digest}"


def _dedupe_drafts(drafts: list[_CandidateDraft]) -> list[_CandidateDraft]:
    seen: set[tuple[str, str]] = set()
    deduped = []
    for draft in drafts:
        key = (draft.lane, _normalize_key(draft.title))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(draft)
    return deduped


def _load_redactors(config_path: Path | None) -> list[tuple[str, re.Pattern[str]]]:
    patterns = dict(DEFAULT_REDACTION_PATTERNS)
    path = config_path or Path.home() / "AIOS" / "config" / "session-provider-config.yaml"
    if path.exists():
        in_section = False
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            if raw_line.strip() == "redaction_patterns:":
                in_section = True
                continue
            if in_section and raw_line and not raw_line.startswith(" "):
                break
            if not in_section or ":" not in raw_line:
                continue
            key, raw_value = raw_line.strip().split(":", 1)
            value = raw_value.strip().strip('"').strip("'")
            value = value.replace("\\\\", "\\")
            if key and value:
                patterns[key] = value
    return [(key, re.compile(pattern, re.DOTALL)) for key, pattern in patterns.items()]


def _redact_evidence(
    evidence: dict[str, str],
    redactors: list[tuple[str, re.Pattern[str]]],
) -> dict[str, str]:
    redacted: dict[str, str] = {}
    for key, value in evidence.items():
        text = str(value)
        for name, pattern in redactors:
            text = pattern.sub(f"[REDACTED:{name}]", text)
        redacted[key] = text
    return redacted


def _since_cutoff(value: str) -> datetime | None:
    match = re.fullmatch(r"(\d+)d", value)
    if not match:
        return None
    return datetime.now(UTC) - timedelta(days=int(match.group(1)))


def _chunks(items: list[Any], size: int) -> list[list[Any]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def _session_to_meta_payload(session: NormalizedSession) -> dict[str, Any]:
    return {
        "session_id": session.provider_session_id,
        "messages": session.messages,
        "commands": session.commands_run,
        "tool_events": session.tool_calls,
        "context_events": [],
        "model_events": [],
    }


def _session_text(session: NormalizedSession, *, include_tools: bool) -> str:
    parts = [session.title]
    parts.extend(str(message.get("text") or "") for message in session.messages)
    if include_tools:
        parts.extend(session.commands_run)
        parts.extend(session.errors_extracted)
    return "\n".join(part for part in parts if part)


def _first_matching_text(session: NormalizedSession, phrases: tuple[str, ...]) -> str:
    for message in session.messages:
        text = str(message.get("text") or "")
        lowered = text.lower()
        if any(phrase in lowered for phrase in phrases):
            return text[:240]
    return _session_text(session, include_tools=True)[:240]


def _source_file(session: NormalizedSession) -> str:
    return session.source_files[0] if session.source_files else ""


def _session_ids(sessions: list[NormalizedSession]) -> list[str]:
    return sorted({session.provider_session_id for session in sessions})


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _now() -> str:
    return datetime.now(UTC).isoformat()
