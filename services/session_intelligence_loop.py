from __future__ import annotations

import hashlib
import json
import re
import shlex
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
CandidateStatus = Literal[
    "pending_review", "approved", "implemented", "rejected", "observed", "superseded"
]
LANES: set[str] = {"friction_tool", "workflow_skill", "impact_idea"}
STATUSES: set[str] = {
    "pending_review",
    "approved",
    "implemented",
    "rejected",
    "observed",
    "superseded",
}
HELPER_FAMILY_PRESETS: dict[str, str] = {
    "repo_state": "Repo state inspection preset for branch, status, diff, and worktree checks.",
    "git_history": "Git history preset for recent commits, tags, and branch divergence.",
    "deployment_flow": "Deployment flow preset for preflight and deployment evidence review.",
    "artifact_probe": "Artifact probe preset for JSON, CSV, manifest, and row-count inspection.",
    "doc_excerpt": "Document excerpt preset for bounded file reads with line-oriented evidence.",
    "package_check": "Package quality preset for package-manager and test/lint command planning.",
    "bespoke_review": "Bespoke review queue for low-shape candidates that need telemetry before narrowing.",
    "workflow_skill": "Workflow skill adoption preset for repeatable successful delivery sequences.",
    "impact_idea": "Impact idea adoption preset for scoped product or workflow improvement bets.",
}
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
        CREATE TABLE IF NOT EXISTS session_intelligence_review_events (
          id TEXT PRIMARY KEY,
          candidate_id TEXT NOT NULL,
          status TEXT NOT NULL,
          note TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS session_intelligence_implementations (
          id TEXT PRIMARY KEY,
          lane TEXT NOT NULL,
          helper_family TEXT NOT NULL,
          candidate_ids_json TEXT NOT NULL DEFAULT '[]',
          candidate_count INTEGER NOT NULL DEFAULT 0,
          implementation_status TEXT NOT NULL DEFAULT 'implemented',
          telemetry_status TEXT NOT NULL DEFAULT 'awaiting_telemetry',
          removal_status TEXT NOT NULL DEFAULT 'monitor',
          removal_reason TEXT NOT NULL,
          implemented_artifact_type TEXT NOT NULL,
          implemented_artifact_ref TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_session_intelligence_candidates_review
          ON session_intelligence_candidates(status, lane, updated_at DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_session_intelligence_implementations_review
          ON session_intelligence_implementations(removal_status, helper_family, updated_at DESC)
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
    decision_report_path: str | None = None
    if options.write_report:
        all_pending_candidates = list_session_intelligence_candidates(
            conn, status="pending_review", lane="all"
        )
        implementations = list_session_intelligence_implementations(conn)
        report_path, report_json_path, decision_report_path = _write_report(
            options.report_root or Path("data/session-intelligence/reports"),
            run_id=run_id,
            provider=provider.provider_id,
            scanned_range=options.since,
            candidates=stored_candidates,
            all_pending_candidates=all_pending_candidates,
            implementations=implementations,
            generated_at=now,
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
        "decision_report_path": decision_report_path,
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


def list_session_intelligence_clusters(
    conn: sqlite3.Connection,
    *,
    status: str | None = None,
    lane: str = "all",
    limit: int | None = None,
) -> list[dict[str, Any]]:
    candidates = list_session_intelligence_candidates(conn, status=status, lane=lane)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        grouped[_candidate_cluster_key(candidate)].append(candidate)

    clusters = []
    for cluster_key, group in grouped.items():
        source_sessions = sorted(
            {str(session_id) for candidate in group for session_id in candidate["source_sessions"]}
        )
        status_counts: dict[str, int] = defaultdict(int)
        for candidate in group:
            status_counts[str(candidate["status"])] += 1
        exemplar = max(
            group, key=lambda item: (int(item["impact_score"]), float(item["confidence"]))
        )
        clusters.append(
            {
                "cluster_key": cluster_key,
                "lane": exemplar["lane"],
                "title": _cluster_title(exemplar),
                "candidate_count": len(group),
                "source_session_count": len(source_sessions),
                "max_impact_score": max(int(candidate["impact_score"]) for candidate in group),
                "avg_confidence": round(
                    sum(float(candidate["confidence"]) for candidate in group) / len(group), 3
                ),
                "status_counts": dict(sorted(status_counts.items())),
                "candidate_ids": [candidate["id"] for candidate in group],
                "top_candidates": [
                    _cluster_candidate_preview(candidate) for candidate in group[:5]
                ],
                "recommended_review_action": _cluster_review_action(exemplar),
            }
        )
    sorted_clusters = sorted(
        clusters,
        key=lambda item: (
            int(item["max_impact_score"]),
            int(item["source_session_count"]),
            int(item["candidate_count"]),
        ),
        reverse=True,
    )
    if limit is None:
        return sorted_clusters
    return sorted_clusters[: max(0, limit)]


def list_session_intelligence_implementations(
    conn: sqlite3.Connection,
    *,
    removal_status: str | None = None,
) -> list[dict[str, Any]]:
    ensure_session_intelligence_schema(conn)
    clauses: list[str] = []
    params: list[str] = []
    if removal_status:
        clauses.append("removal_status = ?")
        params.append(removal_status)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = conn.execute(
        f"""
        SELECT *
        FROM session_intelligence_implementations
        {where}
        ORDER BY
          CASE removal_status WHEN 'removal_candidate' THEN 0 ELSE 1 END,
          candidate_count DESC,
          helper_family ASC
        """,
        params,
    ).fetchall()
    return [_implementation_row_to_dict(row) for row in rows]


def implement_session_intelligence_candidates(
    conn: sqlite3.Connection,
    *,
    status: str = "pending_review",
    lane: str = "all",
    actor_note: str = "",
) -> dict[str, Any]:
    ensure_session_intelligence_schema(conn)
    candidates = list_session_intelligence_candidates(
        conn,
        status=None if status == "all" else status,
        lane=lane,
    )
    now = _now()
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        grouped[(candidate["lane"], _candidate_implementation_family(candidate))].append(
            candidate
        )

    implementation_ids: list[str] = []
    for (candidate_lane, helper_family), family_candidates in sorted(
        grouped.items(),
        key=lambda item: (-len(item[1]), item[0][0], item[0][1]),
    ):
        implementation_id = _implementation_id(candidate_lane, helper_family)
        candidate_ids = sorted(
            set(_implementation_candidate_ids(conn, implementation_id))
            | {candidate["id"] for candidate in family_candidates}
        )
        implementation_ids.append(implementation_id)
        conn.execute(
            """
            INSERT INTO session_intelligence_implementations (
              id, lane, helper_family, candidate_ids_json, candidate_count,
              implementation_status, telemetry_status, removal_status, removal_reason,
              implemented_artifact_type, implemented_artifact_ref, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, 'implemented', 'awaiting_telemetry', 'monitor', ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              candidate_ids_json = excluded.candidate_ids_json,
              candidate_count = excluded.candidate_count,
              implementation_status = excluded.implementation_status,
              telemetry_status = excluded.telemetry_status,
              removal_status = excluded.removal_status,
              removal_reason = excluded.removal_reason,
              implemented_artifact_type = excluded.implemented_artifact_type,
              implemented_artifact_ref = excluded.implemented_artifact_ref,
              updated_at = excluded.updated_at
            """,
            (
                implementation_id,
                candidate_lane,
                helper_family,
                json.dumps(candidate_ids),
                len(candidate_ids),
                _implementation_removal_reason(helper_family),
                "helper_family_preset",
                f"session-intel-helper-family:{helper_family}",
                now,
                now,
            ),
        )
        note_parts = [
            f"Implemented through helper family `{helper_family}` with telemetry and removal tracking."
        ]
        if actor_note:
            note_parts.append(actor_note)
        review_note = " ".join(note_parts)
        for candidate_id in candidate_ids:
            conn.execute(
                """
                UPDATE session_intelligence_candidates
                SET status = 'implemented', review_note = ?, updated_at = ?
                WHERE id = ?
                """,
                (review_note, now, candidate_id),
            )
            conn.execute(
                """
                INSERT INTO session_intelligence_review_events (
                  id, candidate_id, status, note, created_at
                )
                VALUES (?, ?, 'implemented', ?, ?)
                """,
                (f"session-intel-review-{uuid.uuid4()}", candidate_id, review_note, now),
            )

    return {
        "candidate_count": len(candidates),
        "implementation_count": len(implementation_ids),
        "implementation_ids": implementation_ids,
        "status": "implemented",
    }


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
    conn.execute(
        """
        INSERT INTO session_intelligence_review_events (
          id, candidate_id, status, note, created_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (f"session-intel-review-{uuid.uuid4()}", candidate_id, status, note, now),
    )
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
    grouped: dict[str, list[tuple[NormalizedSession, str]]] = defaultdict(list)
    intent_labels: dict[str, str] = {}
    for session in sessions:
        if not session.errors_extracted and not session.provider_metadata.get("approval_friction"):
            continue
        command = session.commands_run[-1] if session.commands_run else "tool execution"
        intent_key, intent_label = _friction_intent(command)
        grouped[intent_key].append((session, command))
        intent_labels[intent_key] = intent_label

    drafts = []
    for intent_key, group in grouped.items():
        intent_label = intent_labels[intent_key]
        commands = sorted({command for _session, command in group})
        evidence = []
        for session, command in group:
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
                title=f"Deterministic helper for {intent_label}",
                summary=(
                    f"Codex hit repeatable friction around {intent_label}. "
                    f"Commands: {_format_command_list(commands)}."
                ),
                impact_score=min(10, 4 + len(group)),
                confidence=0.65 if len(group) == 1 else 0.8,
                source_sessions=_session_ids([session for session, _command in group]),
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
    sequence_matched = [
        session
        for session in sessions
        if session not in matched and _looks_like_successful_implementation_workflow(session)
    ]
    drafts: list[_CandidateDraft] = []
    if matched:
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
        drafts.append(
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
        )
    if sequence_matched:
        evidence = [
            {
                "session_id": session.provider_session_id,
                "summary": _workflow_sequence_summary(session),
                "source": _source_file(session),
            }
            for session in sequence_matched
        ]
        drafts.append(
            _CandidateDraft(
                lane="workflow_skill",
                title="Reusable implementation verification workflow",
                summary="Sessions repeatedly inspect code, implement changes, and verify with tests or quality checks without extracted errors.",
                impact_score=min(10, 5 + len(sequence_matched)),
                confidence=0.72 if len(sequence_matched) == 1 else 0.84,
                source_sessions=_session_ids(sequence_matched),
                evidence=evidence,
                proposed_artifact_type="skill_or_workflow_candidate",
                proposed_next_action="Review whether this successful command sequence should become a skill, workflow checklist, or deterministic closeout helper.",
            )
        )
    return _dedupe_drafts(drafts)


def _friction_intent(command: str) -> tuple[str, str]:
    normalized = _canonical_command(command)
    lower = normalized.lower()
    if (
        lower.startswith("git status")
        or lower.startswith("git diff")
        or lower.startswith("git rev-parse")
    ):
        return "repo_state_inspection", "repo state inspection"
    if lower.startswith("git log") or lower.startswith("git show"):
        return "git_history_review", "git history review"
    if lower.startswith("git push") or lower.startswith("git commit"):
        return "git_commit_publish", "git commit and publish flow"
    if lower.startswith(("pnpm ", "npm ", "yarn ")):
        return "javascript_package_quality", "JavaScript package quality command"
    if (
        lower.startswith(("uv run ", "pytest", "ruff ", "basedpyright", "vulture "))
        or "/pytest" in lower
    ):
        return "python_quality_ladder", "Python quality ladder command"
    if "skill.md" in lower:
        return "skill_instruction_review", "skill instruction review"
    if lower.startswith("date "):
        return "timestamp_metadata", "timestamp metadata"
    if lower == "tool execution":
        return "tool_execution", "tool execution"
    return f"command:{_normalize_key(normalized)}", f"repeated friction: {normalized}"


def _canonical_command(command: str) -> str:
    normalized = command.strip()
    try:
        parts = shlex.split(normalized)
    except ValueError:
        return normalized
    if len(parts) >= 4 and parts[0] == "git" and parts[1] == "-C":
        return "git " + " ".join(parts[3:])
    return normalized


def _format_command_list(commands: list[str]) -> str:
    return ", ".join(f"`{command}`" for command in commands[:5])


def _looks_like_successful_implementation_workflow(session: NormalizedSession) -> bool:
    if session.errors_extracted or len(session.commands_run) < 2:
        return False
    commands = [command.lower() for command in session.commands_run]
    has_inspection = any(
        command.startswith(("rg ", "sed ", "git status", "git diff", "git log"))
        for command in commands
    )
    has_verification = any(
        token in command
        for command in commands
        for token in (
            "pytest",
            "ruff",
            "basedpyright",
            "vulture",
            "pnpm test",
            "pnpm lint",
            "pnpm typecheck",
            "pnpm build",
        )
    )
    text = _session_text(session, include_tools=False).lower()
    has_closeout_language = any(
        phrase in text
        for phrase in (
            "implemented",
            "verified",
            "tests",
            "updated truth",
            "committed",
            "pushed",
        )
    )
    return has_inspection and has_verification and has_closeout_language


def _workflow_sequence_summary(session: NormalizedSession) -> str:
    return " -> ".join(session.commands_run[:5])


def _candidate_cluster_key(candidate: dict[str, Any]) -> str:
    lane = str(candidate["lane"])
    title = str(candidate["title"])
    if lane == "friction_tool":
        for evidence in candidate["redacted_evidence"]:
            summary = str(evidence.get("summary", ""))
            command = summary.split(":", 1)[0]
            intent_key, _intent_label = _friction_intent(command)
            return f"{lane}:{intent_key}"
    return f"{lane}:{_normalize_key(title)}"


def _cluster_title(candidate: dict[str, Any]) -> str:
    lane = str(candidate["lane"])
    if lane == "friction_tool":
        key = _candidate_cluster_key(candidate).split(":", 1)[1]
        label_by_key = {
            "repo_state_inspection": "Repo State Inspection Friction",
            "git_history_review": "Git History Review Friction",
            "git_commit_publish": "Git Commit And Publish Friction",
            "javascript_package_quality": "JavaScript Package Quality Friction",
            "python_quality_ladder": "Python Quality Ladder Friction",
            "skill_instruction_review": "Skill Instruction Review Friction",
            "timestamp_metadata": "Timestamp Metadata Friction",
            "tool_execution": "Tool Execution Friction",
        }
        return label_by_key.get(key, str(candidate["title"]))
    return str(candidate["title"])


def _cluster_review_action(candidate: dict[str, Any]) -> str:
    artifact_type = str(candidate["proposed_artifact_type"])
    if artifact_type == "deterministic_tool_candidate":
        return "Review as a deterministic tool candidate."
    if artifact_type == "skill_or_workflow_candidate":
        return "Review as a skill or workflow promotion candidate."
    if artifact_type == "meta_learning_proposal":
        return "Review as a meta-learning proposal before changing rules."
    return "Review, mark observed, or convert into a scoped implementation target."


def _cluster_candidate_preview(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": candidate["id"],
        "title": candidate["title"],
        "status": candidate["status"],
        "impact_score": candidate["impact_score"],
        "confidence": candidate["confidence"],
        "source_session_count": len(candidate["source_sessions"]),
        "proposed_artifact_type": candidate["proposed_artifact_type"],
    }


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
    all_pending_candidates: list[dict[str, Any]],
    implementations: list[dict[str, Any]],
    generated_at: str,
) -> tuple[str, str, str]:
    report_root.mkdir(parents=True, exist_ok=True)
    markdown_path = report_root / f"{run_id}.md"
    json_path = report_root / f"{run_id}.json"
    decision_path = report_root / f"{provider}-daily-candidate-decisions.md"
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
    decision_path.write_text(
        _decision_report_markdown(
            run_id=run_id,
            provider=provider,
            scanned_range=scanned_range,
            candidates=candidates,
            all_pending_candidates=all_pending_candidates,
            implementations=implementations,
            generated_at=generated_at,
        ),
        encoding="utf-8",
    )
    return str(markdown_path), str(json_path), str(decision_path)


def _decision_report_markdown(
    *,
    run_id: str,
    provider: str,
    scanned_range: str,
    candidates: list[dict[str, Any]],
    all_pending_candidates: list[dict[str, Any]],
    implementations: list[dict[str, Any]],
    generated_at: str,
) -> str:
    latest_pending = [
        candidate for candidate in candidates if candidate["status"] == "pending_review"
    ]
    latest_pending_by_lane = _pending_candidates_by_lane(latest_pending)
    all_pending_by_lane = _pending_candidates_by_lane(all_pending_candidates)
    lines = [
        "# Codex Daily Candidate Decisions",
        "",
        "## Review Queue",
        "",
        f"- provider: {provider}",
        f"- latest run: {run_id}",
        f"- scanned range: {scanned_range}",
        f"- updated at: {generated_at}",
        f"- latest pending candidates: {len(latest_pending)}",
        f"- all pending candidates: {len(all_pending_candidates)}",
        f"- latest friction_tool: {len(latest_pending_by_lane['friction_tool'])}",
        f"- latest workflow_skill: {len(latest_pending_by_lane['workflow_skill'])}",
        f"- latest impact_idea: {len(latest_pending_by_lane['impact_idea'])}",
        f"- all friction_tool: {len(all_pending_by_lane['friction_tool'])}",
        f"- all workflow_skill: {len(all_pending_by_lane['workflow_skill'])}",
        f"- all impact_idea: {len(all_pending_by_lane['impact_idea'])}",
        "",
    ]
    lines.extend(["## New in latest scan", ""])
    _append_candidate_lane_sections(lines, latest_pending_by_lane, lane_heading_level=3)
    lines.extend(["## All pending candidates", ""])
    _append_candidate_lane_sections(lines, all_pending_by_lane, lane_heading_level=3)
    lines.extend(_implementation_telemetry_contract_lines())
    lines.extend(_removal_candidate_lines(implementations))
    return "\n".join(lines)


def _pending_candidates_by_lane(
    candidates: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    return {
        lane: sorted(
            [candidate for candidate in candidates if candidate["lane"] == lane],
            key=lambda candidate: (
                -candidate["impact_score"],
                -candidate["confidence"],
                candidate["title"],
            ),
        )
        for lane in ("friction_tool", "workflow_skill", "impact_idea")
    }


def _append_candidate_lane_sections(
    lines: list[str],
    candidates_by_lane: dict[str, list[dict[str, Any]]],
    *,
    lane_heading_level: int,
) -> None:
    lane_heading = "#" * lane_heading_level
    for lane in ("friction_tool", "workflow_skill", "impact_idea"):
        lane_candidates = candidates_by_lane[lane]
        lines.extend([f"{lane_heading} {lane}", ""])
        if not lane_candidates:
            lines.extend(["No pending candidates in this lane.", ""])
            continue
        if lane == "friction_tool":
            _append_friction_helper_family_sections(
                lines,
                lane_candidates,
                family_heading_level=lane_heading_level + 1,
            )
            continue
        for candidate in lane_candidates:
            _append_candidate_detail(
                lines,
                candidate,
                candidate_heading_level=lane_heading_level + 1,
            )


def _append_friction_helper_family_sections(
    lines: list[str],
    candidates: list[dict[str, Any]],
    *,
    family_heading_level: int,
) -> None:
    family_heading = "#" * family_heading_level
    candidate_heading_level = family_heading_level + 1
    candidates_by_family = _friction_candidates_by_helper_family(candidates)
    for family, family_candidates in sorted(
        candidates_by_family.items(),
        key=lambda item: (
            -len(item[1]),
            -max(candidate["impact_score"] for candidate in item[1]),
            item[0],
        ),
    ):
        lines.extend([f"{family_heading} helper family: {family}", ""])
        lines.extend(_helper_family_strategy_lines(family, family_candidates))
        for candidate in family_candidates:
            _append_candidate_detail(
                lines,
                candidate,
                candidate_heading_level=candidate_heading_level,
            )


def _append_candidate_detail(
    lines: list[str],
    candidate: dict[str, Any],
    *,
    candidate_heading_level: int,
) -> None:
    candidate_heading = "#" * candidate_heading_level
    lines.extend(
        [
            f"{candidate_heading} {candidate['title']}",
            "",
            f"- id: {candidate['id']}",
            f"- impact: {candidate['impact_score']}",
            f"- confidence: {candidate['confidence']}",
            f"- proposed artifact: {candidate['proposed_artifact_type']}",
            f"- next decision: {candidate['proposed_next_action']}",
            "",
            candidate["summary"],
            "",
            f"Anecdotal setting: {_candidate_anecdotal_setting(candidate)}",
            "",
        ]
    )
    evidence_items = candidate["redacted_evidence"][:3]
    if evidence_items:
        lines.append("Evidence:")
        for evidence in evidence_items:
            lines.append(
                f"- {evidence.get('session_id', 'unknown')}: {evidence.get('summary', '')}"
            )
        lines.append("")


def _friction_candidates_by_helper_family(
    candidates: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    candidates_by_family: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        candidates_by_family.setdefault(_candidate_helper_family(candidate), []).append(candidate)
    return candidates_by_family


def _candidate_anecdotal_setting(candidate: dict[str, Any]) -> str:
    title = candidate["title"].rstrip(".")
    if candidate["lane"] == "friction_tool":
        return (
            "When a Codex run repeatedly hits this friction, this candidate would help turn "
            f"the pattern behind {title} into a small repeatable check or helper instead of "
            "making the agent rediscover the same command shape during every closeout."
        )
    if candidate["lane"] == "workflow_skill":
        return (
            "When a future task looks like this successful sequence, this candidate would help "
            "the agent start from a known workflow shape, including the expected checks and "
            "handoff points, instead of reconstructing the approach from memory."
        )
    return (
        "When planning what to improve next, this candidate would help connect scattered "
        "session evidence to a concrete product or workflow bet that deserves a scoped human "
        "decision."
    )


def _helper_family_strategy_lines(
    family: str,
    candidates: list[dict[str, Any]],
) -> list[str]:
    if family == "bespoke_review":
        dedicated_helper = "maybe, only after another run proves this is not a router preset"
        recommendation = (
            "Keep as review evidence for now; do not create a dedicated helper until the "
            "friction repeats with a stable parameter shape."
        )
    else:
        dedicated_helper = "no"
        recommendation = (
            "Prefer a shared helper family or preset over a one-off script. Add this under "
            f"the {family} family if the same parameter shape keeps recurring."
        )
    average_confidence = sum(candidate["confidence"] for candidate in candidates) / len(candidates)
    return [
        "Helper strategy:",
        f"- helper family: {family}",
        f"- candidate count: {len(candidates)}",
        f"- max impact: {max(candidate['impact_score'] for candidate in candidates)}",
        f"- average confidence: {average_confidence:.2f}",
        f"- reuse recommendation: {recommendation}",
        f"- dedicated helper: {dedicated_helper}",
        (
            "- telemetry plan: if implemented, record family-level helper telemetry for "
            "invocations, bypasses, failures, runtime, agent retry count, and before/after "
            "friction recurrence."
        ),
        (
            "- removal review: promote the family as a removal candidate when telemetry shows "
            "neutral or negative value, rising failure rates, or repeated manual bypasses."
        ),
        "",
    ]


def _implementation_telemetry_contract_lines() -> list[str]:
    return [
        "## Implementation Telemetry Contract",
        "",
        (
            "Measure whether implemented candidates reduce repeated friction, workflow time, "
            "agent retries, and manual intervention without increasing failures, bypasses, or "
            "maintenance cost."
        ),
        "",
        "- required before implementation: define baseline friction evidence and expected benefit",
        "- required during use: record invocation count, success/failure, bypass count, latency, and affected candidate or helper family",
        "- required after review: compare measured benefit against the original candidate claim before keeping it as default behavior",
        "",
    ]


def _removal_candidate_lines(implementations: list[dict[str, Any]]) -> list[str]:
    lines = [
        "## Removal Candidates",
        "",
    ]
    removal_candidates = [
        implementation
        for implementation in implementations
        if implementation["removal_status"] == "removal_candidate"
    ]
    if removal_candidates:
        lines.extend(["### active removal candidates", ""])
        for implementation in removal_candidates:
            lines.extend(_implementation_review_lines(implementation))
    else:
        lines.extend(["No implemented helpers currently meet removal thresholds.", ""])
    if implementations:
        lines.extend(["### monitored implemented helpers", ""])
        for implementation in implementations:
            lines.extend(_implementation_review_lines(implementation))
    else:
        lines.extend(
            [
                "No implemented candidate telemetry is available yet.",
                "",
                (
                    "Future daily scans should list implemented helpers, skills, or workflows whose "
                    "telemetry shows neutral value, negative value, stale usage, repeated bypasses, or "
                    "higher failure/maintenance cost than the original manual path."
                ),
                "",
            ]
        )
    return lines


def _implementation_review_lines(implementation: dict[str, Any]) -> list[str]:
    helper_family = implementation["helper_family"]
    return [
        (
            f"- {helper_family}: {implementation['removal_status']}; "
            f"{implementation['telemetry_status']}; candidates covered: "
            f"{implementation['candidate_count']}"
        ),
        f"  - artifact: {implementation['implemented_artifact_ref']}",
        f"  - removal basis: {implementation['removal_reason']}",
        "",
    ]


def _candidate_helper_family(candidate: dict[str, Any]) -> str:
    haystack = " ".join(
        [
            candidate["title"],
            candidate["summary"],
            candidate["proposed_next_action"],
            " ".join(
                evidence.get("summary", "") for evidence in candidate["redacted_evidence"][:5]
            ),
        ]
    ).lower()
    if any(token in haystack for token in ("git status", "git diff", "worktree", "rev-parse")):
        return "repo_state"
    if any(token in haystack for token in ("git log", "git show", "rev-list", "tag")):
        return "git_history"
    if any(token in haystack for token in ("vercel deploy", "deploy --prod", "deployment")):
        return "deployment_flow"
    if any(token in haystack for token in (".csv", ".json", "manifest", "counter")) or re.search(
        r"\brows?\b", haystack
    ):
        return "artifact_probe"
    if any(token in haystack for token in ("sed -n", "nl -ba", "read_text", ".md")):
        return "doc_excerpt"
    if any(token in haystack for token in ("pnpm", "npm", "pytest", "ruff", "node -e")):
        return "package_check"
    return "bespoke_review"


def _candidate_implementation_family(candidate: dict[str, Any]) -> str:
    if candidate["lane"] == "friction_tool":
        return _candidate_helper_family(candidate)
    return str(candidate["lane"])


def _implementation_id(lane: str, helper_family: str) -> str:
    return f"session-intel-implementation-{lane}-{helper_family}"


def _implementation_candidate_ids(conn: sqlite3.Connection, implementation_id: str) -> list[str]:
    row = conn.execute(
        """
        SELECT candidate_ids_json
        FROM session_intelligence_implementations
        WHERE id = ?
        """,
        (implementation_id,),
    ).fetchone()
    if row is None:
        return []
    try:
        loaded = json.loads(row["candidate_ids_json"])
    except json.JSONDecodeError:
        return []
    if not isinstance(loaded, list):
        return []
    return [str(candidate_id) for candidate_id in loaded]


def _implementation_removal_reason(helper_family: str) -> str:
    preset = HELPER_FAMILY_PRESETS.get(helper_family, "Session intelligence helper preset.")
    return (
        f"{preset} Track usage, bypasses, failures, and before/after friction recurrence "
        "before deciding whether to keep, narrow, or remove this implementation."
    )


def _implementation_row_to_dict(row: sqlite3.Row | None) -> dict[str, Any]:
    if row is None:
        raise ValueError("Missing session intelligence implementation row")
    return {
        "id": row["id"],
        "lane": row["lane"],
        "helper_family": row["helper_family"],
        "candidate_ids": json.loads(row["candidate_ids_json"]),
        "candidate_count": row["candidate_count"],
        "implementation_status": row["implementation_status"],
        "telemetry_status": row["telemetry_status"],
        "removal_status": row["removal_status"],
        "removal_reason": row["removal_reason"],
        "implemented_artifact_type": row["implemented_artifact_type"],
        "implemented_artifact_ref": row["implemented_artifact_ref"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


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
