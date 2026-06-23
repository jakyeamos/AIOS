from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from services.session_providers.base import WritebackCandidate
from services.session_summarizer import SessionSummary

SUMMARY_DIR = Path.home() / "AIOS" / "logs" / "summaries"


def emit_writeback_candidates(
    session_id: str,
    summary: SessionSummary,
    *,
    conn: sqlite3.Connection | None = None,
    summary_dir: Path = SUMMARY_DIR,
) -> list[WritebackCandidate]:
    """Emit proposal-only writeback candidates; never mutate the vault directly."""

    if summary.writeback_proposal_status == "held_redaction_incomplete":
        return []

    candidates: list[WritebackCandidate] = []
    if summary.should_create_obsidian_note and summary.confidence >= 0.6:
        candidate = WritebackCandidate(
            session_id=session_id,
            candidate_type="obsidian_session_note",
            destination="logs/summaries",
            payload=_candidate_payload(summary),
        )
        _write_summary_json(summary_dir, session_id, candidate.payload)
        candidates.append(candidate)

    if summary.should_update_truth_file and summary.confidence >= 0.8:
        candidates.append(
            WritebackCandidate(
                session_id=session_id,
                candidate_type="truth_update",
                destination="project_truth",
                payload=_candidate_payload(summary),
            )
        )

    if conn is not None:
        candidates.extend(_skillification_candidates(conn, session_id, summary))
        _record_candidates(conn, candidates)

    return candidates


def _candidate_payload(summary: SessionSummary) -> dict[str, Any]:
    payload = summary.to_dict()
    payload.pop("source_provenance", None)
    payload["source_provenance"] = summary.source_provenance
    payload["raw_transcript_included"] = False
    return payload


def _write_summary_json(summary_dir: Path, session_id: str, payload: dict[str, Any]) -> None:
    summary_dir.mkdir(parents=True, exist_ok=True)
    safe_name = session_id.replace("/", "_").replace(":", "_")
    path = summary_dir / f"{safe_name}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _record_candidates(conn: sqlite3.Connection, candidates: list[WritebackCandidate]) -> None:
    if not candidates:
        return
    _ensure_memory_writeback_schema(conn)
    created_at = datetime.now(UTC).isoformat()
    for candidate in candidates:
        conn.execute(
            """
            INSERT INTO memory_writeback_proposals (
              id, source_run_id, target_scope, proposal_type, proposed_content,
              rationale, evidence_json, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'proposed', ?)
            """,
            (
                f"writeback-{uuid.uuid4()}",
                candidate.session_id,
                candidate.destination,
                candidate.candidate_type,
                json.dumps(candidate.payload, sort_keys=True),
                "Session provider structured summary proposal",
                json.dumps([candidate.session_id]),
                created_at,
            ),
        )
    conn.commit()


def _ensure_memory_writeback_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS memory_writeback_proposals (
          id TEXT PRIMARY KEY,
          source_run_id TEXT NOT NULL,
          target_scope TEXT NOT NULL,
          proposal_type TEXT NOT NULL,
          proposed_content TEXT NOT NULL,
          rationale TEXT NOT NULL,
          evidence_json TEXT NOT NULL DEFAULT '[]',
          status TEXT NOT NULL DEFAULT 'proposed',
          created_at TEXT NOT NULL,
          reviewed_at TEXT,
          reviewed_by TEXT
        )
        """
    )


def _skillification_candidates(
    conn: sqlite3.Connection,
    session_id: str,
    summary: SessionSummary,
) -> list[WritebackCandidate]:
    if not summary.reusable_patterns:
        return []
    threshold_date = (datetime.now(UTC) - timedelta(days=30)).isoformat()
    try:
        rows = conn.execute(
            """
            SELECT proposed_content
            FROM memory_writeback_proposals
            WHERE proposal_type IN ('obsidian_session_note', 'skillification_candidate')
              AND created_at >= ?
            """,
            (threshold_date,),
        ).fetchall()
    except sqlite3.OperationalError:
        rows = []

    counts = {pattern: 1 for pattern in summary.reusable_patterns}
    for row in rows:
        try:
            payload = json.loads(str(row[0]))
        except json.JSONDecodeError:
            continue
        for pattern in payload.get("reusable_patterns", []):
            if pattern in counts:
                counts[pattern] += 1

    candidates: list[WritebackCandidate] = []
    for pattern, count in counts.items():
        if count >= 3:
            candidates.append(
                WritebackCandidate(
                    session_id=session_id,
                    candidate_type="skillification_candidate",
                    destination="skill_registry",
                    payload={
                        "pattern": pattern,
                        "observed_count_30d": count,
                        "summary": asdict(summary),
                    },
                )
            )
    return candidates
