from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

RUN_STATUSES = {
    "planned",
    "ready",
    "in_progress",
    "blocked",
    "waiting_for_user",
    "waiting_for_tool",
    "failed_validation",
    "completed",
    "failed",
    "canceled",
    "superseded",
}


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _table_has_column(
    conn: sqlite3.Connection,
    table_name: str,
    column_name: str,
) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row[1] == column_name for row in rows)


def ensure_column(
    conn: sqlite3.Connection,
    table_name: str,
    column_name: str,
    definition: str,
) -> None:
    if not _table_has_column(conn, table_name, column_name):
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table_name,),
    ).fetchone()
    return row is not None


def ensure_runtime_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS orchestration_runs (
            id TEXT PRIMARY KEY,
            project_id TEXT REFERENCES projects(id),
            session_id TEXT REFERENCES sessions(id),
            objective TEXT NOT NULL,
            workflow_key TEXT NOT NULL,
            agent_key TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'planned',
            rationale TEXT NOT NULL,
            assumptions_json TEXT NOT NULL DEFAULT '[]',
            context_trace_json TEXT NOT NULL DEFAULT '[]',
            packet_id TEXT,
            memory_update_id TEXT,
            result_summary TEXT,
            completed_at TEXT,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS improvement_writebacks (
            id TEXT PRIMARY KEY,
            run_id TEXT REFERENCES orchestration_runs(id),
            project_id TEXT REFERENCES projects(id),
            layer_type TEXT NOT NULL,
            layer_key TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            evidence_json TEXT NOT NULL DEFAULT '[]',
            proposed_change_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'proposed',
            requires_approval INTEGER NOT NULL DEFAULT 0,
            approval_reason TEXT,
            token_regressive INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS orchestration_invocations (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL REFERENCES orchestration_runs(id),
            backend_key TEXT NOT NULL,
            backend_label TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued',
            handshake_token TEXT NOT NULL,
            session_id TEXT REFERENCES sessions(id),
            pid INTEGER,
            command_json TEXT NOT NULL DEFAULT '[]',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            started_at TEXT,
            ended_at TEXT,
            updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_orchestration_invocations_run
          ON orchestration_invocations(run_id, created_at DESC)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS orchestration_run_events (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL REFERENCES orchestration_runs(id),
            project_id TEXT REFERENCES projects(id),
            session_id TEXT REFERENCES sessions(id),
            invocation_id TEXT REFERENCES orchestration_invocations(id),
            event_type TEXT NOT NULL,
            from_status TEXT,
            to_status TEXT,
            summary TEXT NOT NULL,
            reason_json TEXT NOT NULL DEFAULT '{}',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_orchestration_run_events_run
          ON orchestration_run_events(run_id, created_at DESC)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS improvement_writeback_events (
            id TEXT PRIMARY KEY,
            writeback_id TEXT NOT NULL REFERENCES improvement_writebacks(id),
            run_id TEXT REFERENCES orchestration_runs(id),
            event_type TEXT NOT NULL,
            from_status TEXT,
            to_status TEXT,
            actor TEXT NOT NULL DEFAULT 'system',
            note TEXT,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_improvement_writeback_events_writeback
          ON improvement_writeback_events(writeback_id, created_at DESC)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS workflow_learning_events (
            id TEXT PRIMARY KEY,
            run_id TEXT REFERENCES orchestration_runs(id),
            evidence_type TEXT NOT NULL,
            proposal_target TEXT,
            confidence REAL NOT NULL DEFAULT 0.5,
            approval_state TEXT NOT NULL DEFAULT 'not_required',
            rationale TEXT NOT NULL,
            source_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_workflow_learning_events_run
          ON workflow_learning_events(run_id, created_at DESC)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS workflow_execution_reports (
            id TEXT PRIMARY KEY,
            run_id TEXT REFERENCES orchestration_runs(id),
            invocation_id TEXT REFERENCES orchestration_invocations(id),
            workflow_key TEXT NOT NULL,
            status TEXT NOT NULL,
            report_json TEXT NOT NULL DEFAULT '{}',
            artifact_path TEXT,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_workflow_execution_reports_run
          ON workflow_execution_reports(run_id, created_at DESC)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS consistency_evaluations (
            id TEXT PRIMARY KEY,
            project_id TEXT REFERENCES projects(id),
            run_id TEXT REFERENCES orchestration_runs(id),
            packet_id TEXT REFERENCES briefing_packets(id),
            invocation_id TEXT REFERENCES orchestration_invocations(id),
            trigger_kind TEXT NOT NULL,
            evaluator_version TEXT NOT NULL,
            summary TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_consistency_evaluations_project
          ON consistency_evaluations(project_id, created_at DESC)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS consistency_findings (
            id TEXT PRIMARY KEY,
            evaluation_id TEXT NOT NULL REFERENCES consistency_evaluations(id),
            project_id TEXT REFERENCES projects(id),
            run_id TEXT REFERENCES orchestration_runs(id),
            packet_id TEXT REFERENCES briefing_packets(id),
            topic_slug TEXT,
            finding_kind TEXT NOT NULL,
            severity TEXT NOT NULL,
            rule_key TEXT NOT NULL,
            summary TEXT NOT NULL,
            provenance_json TEXT NOT NULL DEFAULT '[]',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            resolution_status TEXT NOT NULL DEFAULT 'open',
            resolution_actor TEXT,
            resolution_rationale TEXT,
            resolution_evidence_json TEXT NOT NULL DEFAULT '[]',
            resolved_at TEXT,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_consistency_findings_project
          ON consistency_findings(project_id, created_at DESC)
        """
    )

    ensure_column(conn, "sessions", "run_id", "TEXT REFERENCES orchestration_runs(id)")
    ensure_column(
        conn,
        "sessions",
        "invocation_id",
        "TEXT REFERENCES orchestration_invocations(id)",
    )
    ensure_column(
        conn,
        "sessions",
        "runtime_metadata_json",
        "TEXT NOT NULL DEFAULT '{}'",
    )

    ensure_column(conn, "orchestration_runs", "backend_key", "TEXT")
    ensure_column(
        conn,
        "orchestration_runs",
        "active_invocation_id",
        "TEXT REFERENCES orchestration_invocations(id)",
    )
    ensure_column(conn, "orchestration_runs", "started_at", "TEXT")
    ensure_column(conn, "orchestration_runs", "failed_at", "TEXT")
    ensure_column(conn, "orchestration_runs", "canceled_at", "TEXT")
    ensure_column(conn, "orchestration_runs", "superseded_by_run_id", "TEXT")
    ensure_column(
        conn,
        "orchestration_runs",
        "status_reason_json",
        "TEXT NOT NULL DEFAULT '{}'",
    )

    ensure_column(conn, "improvement_writebacks", "impact_scope", "TEXT NOT NULL DEFAULT 'scoped'")
    ensure_column(conn, "improvement_writebacks", "decision_note", "TEXT")
    ensure_column(conn, "improvement_writebacks", "decision_actor", "TEXT")
    ensure_column(conn, "improvement_writebacks", "decision_at", "TEXT")
    ensure_column(
        conn,
        "improvement_writebacks",
        "updated_at",
        "TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))",
    )
    ensure_column(conn, "consistency_findings", "resolution_status", "TEXT NOT NULL DEFAULT 'open'")
    ensure_column(conn, "consistency_findings", "resolution_actor", "TEXT")
    ensure_column(conn, "consistency_findings", "resolution_rationale", "TEXT")
    ensure_column(conn, "consistency_findings", "resolution_evidence_json", "TEXT NOT NULL DEFAULT '[]'")
    ensure_column(conn, "consistency_findings", "resolved_at", "TEXT")


def get_run_row(conn: sqlite3.Connection, run_id: str) -> sqlite3.Row | None:
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        """
        SELECT *
        FROM orchestration_runs
        WHERE id = ?
        LIMIT 1
        """,
        (run_id,),
    ).fetchone()
    conn.row_factory = None
    return row


def record_run_event(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    event_type: str,
    summary: str,
    to_status: str | None = None,
    from_status: str | None = None,
    reason: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    project_id: str | None = None,
    session_id: str | None = None,
    invocation_id: str | None = None,
    created_at: str | None = None,
) -> None:
    ensure_runtime_schema(conn)

    if not project_id:
        row = conn.execute(
            "SELECT project_id FROM orchestration_runs WHERE id = ? LIMIT 1",
            (run_id,),
        ).fetchone()
        project_id = row[0] if row else None

    conn.execute(
        """
        INSERT INTO orchestration_run_events (
            id,
            run_id,
            project_id,
            session_id,
            invocation_id,
            event_type,
            from_status,
            to_status,
            summary,
            reason_json,
            metadata_json,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"run-event-{uuid.uuid4()}",
            run_id,
            project_id,
            session_id,
            invocation_id,
            event_type,
            from_status,
            to_status,
            summary,
            _json(reason or {}),
            _json(metadata or {}),
            created_at or now_iso(),
        ),
    )


def transition_run(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    to_status: str,
    event_type: str,
    summary: str,
    reason: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    session_id: str | None = None,
    invocation_id: str | None = None,
    result_summary: str | None = None,
    memory_update_id: str | None = None,
    created_at: str | None = None,
    superseded_by_run_id: str | None = None,
) -> None:
    ensure_runtime_schema(conn)
    if to_status not in RUN_STATUSES:
        raise ValueError(f"Unsupported run status: {to_status}")

    current = conn.execute(
        """
        SELECT status, project_id, session_id, active_invocation_id, started_at
        FROM orchestration_runs
        WHERE id = ?
        LIMIT 1
        """,
        (run_id,),
    ).fetchone()
    if current is None:
        raise ValueError(f"Unknown run: {run_id}")

    event_time = created_at or now_iso()
    active_invocation_id = invocation_id or current[3]
    active_session_id = session_id or current[2]

    updates = {
        "status": to_status,
        "updated_at": event_time,
        "status_reason_json": _json(reason or {}),
        "session_id": active_session_id,
        "active_invocation_id": active_invocation_id,
    }

    if to_status == "in_progress" and not current[4]:
        updates["started_at"] = event_time
    if to_status == "completed":
        updates["completed_at"] = event_time
    if to_status == "failed":
        updates["failed_at"] = event_time
    if to_status == "canceled":
        updates["canceled_at"] = event_time
    if to_status == "superseded" and superseded_by_run_id:
        updates["superseded_by_run_id"] = superseded_by_run_id
    if result_summary is not None:
        updates["result_summary"] = result_summary
    if memory_update_id is not None:
        updates["memory_update_id"] = memory_update_id

    assignments = ", ".join(f"{column} = ?" for column in updates)
    conn.execute(
        f"UPDATE orchestration_runs SET {assignments} WHERE id = ?",
        (*updates.values(), run_id),
    )

    record_run_event(
        conn,
        run_id=run_id,
        event_type=event_type,
        from_status=current[0],
        to_status=to_status,
        summary=summary,
        reason=reason,
        metadata=metadata,
        project_id=current[1],
        session_id=active_session_id,
        invocation_id=active_invocation_id,
        created_at=event_time,
    )


def create_invocation(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    backend_key: str,
    backend_label: str,
    command: list[str],
    metadata: dict[str, Any] | None = None,
    status: str = "queued",
    invocation_id: str | None = None,
    handshake_token: str | None = None,
    pid: int | None = None,
) -> str:
    ensure_runtime_schema(conn)
    created_at = now_iso()
    invocation_id = invocation_id or f"invoke-{uuid.uuid4()}"
    handshake_token = handshake_token or run_id

    conn.execute(
        """
        INSERT INTO orchestration_invocations (
            id,
            run_id,
            backend_key,
            backend_label,
            status,
            handshake_token,
            pid,
            command_json,
            metadata_json,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            invocation_id,
            run_id,
            backend_key,
            backend_label,
            status,
            handshake_token,
            pid,
            _json(command),
            _json(metadata or {}),
            created_at,
            created_at,
        ),
    )
    return invocation_id


def update_invocation(
    conn: sqlite3.Connection,
    *,
    invocation_id: str,
    status: str,
    session_id: str | None = None,
    pid: int | None = None,
    metadata: dict[str, Any] | None = None,
    started_at: str | None = None,
    ended_at: str | None = None,
) -> None:
    ensure_runtime_schema(conn)
    current = conn.execute(
        """
        SELECT metadata_json
        FROM orchestration_invocations
        WHERE id = ?
        LIMIT 1
        """,
        (invocation_id,),
    ).fetchone()
    if current is None:
        return

    current_metadata = json.loads(current[0] or "{}")
    if metadata:
        current_metadata.update(metadata)

    fields = {
        "status": status,
        "updated_at": now_iso(),
        "metadata_json": _json(current_metadata),
    }
    if session_id is not None:
        fields["session_id"] = session_id
    if pid is not None:
        fields["pid"] = pid
    if started_at is not None:
        fields["started_at"] = started_at
    if ended_at is not None:
        fields["ended_at"] = ended_at

    assignments = ", ".join(f"{key} = ?" for key in fields)
    conn.execute(
        f"UPDATE orchestration_invocations SET {assignments} WHERE id = ?",
        (*fields.values(), invocation_id),
    )


def link_session_runtime(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    run_id: str | None,
    invocation_id: str | None,
    runtime_metadata: dict[str, Any] | None = None,
    objective: str | None = None,
) -> None:
    ensure_runtime_schema(conn)
    payload = runtime_metadata or {}
    conn.execute(
        """
        UPDATE sessions
        SET run_id = COALESCE(?, run_id),
            invocation_id = COALESCE(?, invocation_id),
            objective = COALESCE(?, objective),
            runtime_metadata_json = ?
        WHERE id = ?
        """,
        (run_id, invocation_id, objective, _json(payload), session_id),
    )


def insert_workflow_execution_report(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    invocation_id: str,
    workflow_key: str,
    status: str,
    report: dict[str, Any],
    artifact_path: str | None = None,
) -> str:
    ensure_runtime_schema(conn)
    report_id = f"workflow-report-{uuid.uuid4()}"
    conn.execute(
        """
        INSERT INTO workflow_execution_reports (
            id,
            run_id,
            invocation_id,
            workflow_key,
            status,
            report_json,
            artifact_path,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            report_id,
            run_id,
            invocation_id,
            workflow_key,
            status,
            _json(report),
            artifact_path,
            now_iso(),
        ),
    )
    return report_id


def resolve_run_linkage(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    payload_run_id: str | None = None,
    payload_invocation_id: str | None = None,
    legacy_matcher: Any | None = None,
    project_id: str | None = None,
    objective: str | None = None,
) -> tuple[str | None, str | None, str | None, bool]:
    ensure_runtime_schema(conn)

    if payload_run_id:
        row = conn.execute(
            """
            SELECT id, packet_id, active_invocation_id
            FROM orchestration_runs
            WHERE id = ?
            LIMIT 1
            """,
            (payload_run_id,),
        ).fetchone()
        if row:
            return row[0], row[1], payload_invocation_id or row[2], False

    session_row = conn.execute(
        """
        SELECT run_id, invocation_id
        FROM sessions
        WHERE id = ?
        LIMIT 1
        """,
        (session_id,),
    ).fetchone()
    if session_row and session_row[0]:
        row = conn.execute(
            """
            SELECT id, packet_id, active_invocation_id
            FROM orchestration_runs
            WHERE id = ?
            LIMIT 1
            """,
            (session_row[0],),
        ).fetchone()
        if row:
            return row[0], row[1], payload_invocation_id or session_row[1] or row[2], False

    if payload_invocation_id:
        row = conn.execute(
            """
            SELECT run_id, session_id
            FROM orchestration_invocations
            WHERE id = ?
            LIMIT 1
            """,
            (payload_invocation_id,),
        ).fetchone()
        if row:
            packet = conn.execute(
                "SELECT packet_id FROM orchestration_runs WHERE id = ? LIMIT 1",
                (row[0],),
            ).fetchone()
            return row[0], packet[0] if packet else None, payload_invocation_id, False

    if legacy_matcher:
        legacy_run_id, legacy_packet_id = legacy_matcher(conn, project_id, objective)
        if legacy_run_id:
            return legacy_run_id, legacy_packet_id, payload_invocation_id, True

    return None, None, payload_invocation_id, False


def record_writeback_event(
    conn: sqlite3.Connection,
    *,
    writeback_id: str,
    run_id: str | None,
    event_type: str,
    from_status: str | None,
    to_status: str | None,
    actor: str,
    note: str | None,
    metadata: dict[str, Any] | None = None,
) -> None:
    ensure_runtime_schema(conn)
    conn.execute(
        """
        INSERT INTO improvement_writeback_events (
            id,
            writeback_id,
            run_id,
            event_type,
            from_status,
            to_status,
            actor,
            note,
            metadata_json,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"writeback-event-{uuid.uuid4()}",
            writeback_id,
            run_id,
            event_type,
            from_status,
            to_status,
            actor,
            note,
            _json(metadata or {}),
            now_iso(),
        ),
    )


def insert_writeback(
    conn: sqlite3.Connection,
    *,
    run_id: str | None,
    project_id: str | None,
    layer_type: str,
    layer_key: str,
    title: str,
    summary: str,
    evidence: list[str],
    proposed_change: dict[str, Any] | None = None,
    impact_scope: str = "scoped",
    requires_approval: bool = False,
    approval_reason: str | None = None,
    token_regressive: bool = False,
    status: str | None = None,
) -> str:
    ensure_runtime_schema(conn)
    writeback_id = f"writeback-{uuid.uuid4()}"
    target_status = status or ("pending_approval" if requires_approval else "proposed")
    conn.execute(
        """
        INSERT INTO improvement_writebacks (
            id,
            run_id,
            project_id,
            layer_type,
            layer_key,
            title,
            summary,
            evidence_json,
            proposed_change_json,
            impact_scope,
            status,
            requires_approval,
            approval_reason,
            token_regressive,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            writeback_id,
            run_id,
            project_id,
            layer_type,
            layer_key,
            title,
            summary,
            _json(evidence),
            _json(proposed_change or {}),
            impact_scope,
            target_status,
            1 if requires_approval else 0,
            approval_reason,
            1 if token_regressive else 0,
            now_iso(),
            now_iso(),
        ),
    )
    record_writeback_event(
        conn,
        writeback_id=writeback_id,
        run_id=run_id,
        event_type="proposed",
        from_status=None,
        to_status=target_status,
        actor="system",
        note=summary,
        metadata={
            "requires_approval": requires_approval,
            "impact_scope": impact_scope,
            "token_regressive": token_regressive,
        },
    )
    return writeback_id


def tokenize(text: str | None) -> set[str]:
    if not text:
        return set()
    stop = {
        "this",
        "that",
        "with",
        "from",
        "into",
        "then",
        "than",
        "what",
        "when",
        "where",
        "which",
        "task",
        "work",
        "aios",
        "project",
        "system",
        "should",
        "would",
        "could",
    }
    return {
        token
        for token in re.findall(r"[a-z0-9]{4,}", text.lower())
        if token not in stop
    }


def _extract_section_items(content: str, heading: str) -> list[str]:
    match = re.search(rf"^##\s+{re.escape(heading)}\s*\n([\s\S]*?)(?=^##\s+|\Z)", content, re.M)
    if not match:
        return []
    return [
        line.strip()[2:].strip()
        for line in match.group(1).splitlines()
        if line.strip().startswith("- ")
    ]


def _load_project_truth(repo_path: str | None) -> dict[str, Any]:
    if not repo_path:
        return {"path": None, "missing": [], "guardrails": [], "last_updated": None}
    project_truth = Path(repo_path) / "PROJECT.md"
    if not project_truth.exists():
        return {"path": None, "missing": [], "guardrails": [], "last_updated": None}

    content = project_truth.read_text()
    last_updated_match = re.search(r"^Last updated:\s+(.+)$", content, re.M)
    return {
        "path": str(project_truth),
        "missing": _extract_section_items(content, "Still Missing"),
        "guardrails": _extract_section_items(content, "Guardrails"),
        "last_updated": last_updated_match.group(1).strip() if last_updated_match else None,
    }


def _load_packet_context(conn: sqlite3.Connection, packet_id: str | None) -> dict[str, Any]:
    if not packet_id:
        return {"policy_mode": None, "token_budget": None, "sections": []}
    row = conn.execute(
        """
        SELECT policy_mode, token_budget, sections_json
        FROM briefing_packets
        WHERE id = ?
        LIMIT 1
        """,
        (packet_id,),
    ).fetchone()
    if not row:
        return {"policy_mode": None, "token_budget": None, "sections": []}
    try:
        sections = json.loads(row[2] or "[]")
    except Exception:
        sections = []
    return {
        "policy_mode": row[0],
        "token_budget": row[1],
        "sections": sections,
    }


def _load_latest_memory(conn: sqlite3.Connection, run_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT id, summary, changes_json, risks_json, open_questions_json, created_at
        FROM memory_updates
        WHERE run_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (run_id,),
    ).fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "summary": row[1],
        "changes": json.loads(row[2] or "[]"),
        "risks": json.loads(row[3] or "[]"),
        "open_questions": json.loads(row[4] or "[]"),
        "created_at": row[5],
    }


def _load_recent_runs(conn: sqlite3.Connection, project_id: str, run_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id, objective, status, result_summary, completed_at, created_at
        FROM orchestration_runs
        WHERE project_id = ?
          AND id <> ?
        ORDER BY COALESCE(completed_at, created_at) DESC
        LIMIT 8
        """,
        (project_id, run_id),
    ).fetchall()
    return [
        {
            "id": row[0],
            "objective": row[1],
            "status": row[2],
            "result_summary": row[3],
            "completed_at": row[4],
            "created_at": row[5],
        }
        for row in rows
    ]


def _load_project_topics(conn: sqlite3.Connection, project_id: str | None) -> list[dict[str, Any]]:
    if not project_id:
        return []
    rows = conn.execute(
        """
        SELECT slug, title, summary
        FROM knowledge_topics
        WHERE project_id = ?
        ORDER BY updated_at DESC
        LIMIT 8
        """,
        (project_id,),
    ).fetchall()
    return [{"slug": row[0], "title": row[1], "summary": row[2]} for row in rows]


def _load_run_artifacts(conn: sqlite3.Connection, run_id: str, session_id: str | None) -> list[str]:
    if not table_exists(conn, "artifacts"):
        return []
    rows = conn.execute(
        """
        SELECT path
        FROM artifacts
        WHERE (? IS NOT NULL AND session_id = ?)
           OR metadata_json LIKE ?
        ORDER BY created_at DESC
        LIMIT 80
        """,
        (session_id, session_id, f"%{run_id}%"),
    ).fetchall()
    return sorted({str(row[0]) for row in rows if row[0]})


def _packet_file_mentions(packet: dict[str, Any]) -> list[str]:
    matches: set[str] = set()
    for section in packet["sections"]:
        for item in section.get("items", []):
            for match in re.findall(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+\\.[A-Za-z0-9]+", str(item)):
                matches.add(match)
    return sorted(matches)


def _latest_standards_signal(conn: sqlite3.Connection, project_id: str | None) -> dict[str, Any] | None:
    if not project_id or not table_exists(conn, "standards_health_snapshots"):
        return None
    row = conn.execute(
        """
        SELECT id, overall_score, critical_delta_count, unknown_count, evaluation_confidence
        FROM standards_health_snapshots
        WHERE project_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (project_id,),
    ).fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "overall_score": row[1],
        "critical_delta_count": row[2],
        "unknown_count": row[3],
        "evaluation_confidence": row[4],
    }


def evaluate_run_consistency(
    conn: sqlite3.Connection,
    run_id: str,
    *,
    invocation_id: str | None = None,
    trigger_kind: str = "terminal_run",
) -> str:
    ensure_runtime_schema(conn)
    row = conn.execute(
        """
        SELECT r.id, r.project_id, r.objective, r.workflow_key, r.agent_key, r.status,
               r.result_summary, r.packet_id, p.repo_path, r.session_id
        FROM orchestration_runs r
        LEFT JOIN projects p ON p.id = r.project_id
        WHERE r.id = ?
        LIMIT 1
        """,
        (run_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Unknown run: {run_id}")

    project_id = row[1]
    packet_id = row[7]
    session_id = row[9]
    truth = _load_project_truth(row[8])
    packet = _load_packet_context(conn, packet_id)
    memory = _load_latest_memory(conn, run_id)
    recent_runs = _load_recent_runs(conn, project_id, run_id) if project_id else []
    topics = _load_project_topics(conn, project_id)
    artifacts = _load_run_artifacts(conn, run_id, session_id)
    packet_mentions = _packet_file_mentions(packet)
    standards_signal = _latest_standards_signal(conn, project_id)

    evidence_text = " ".join(
        [
            row[2] or "",
            row[6] or "",
            memory["summary"] if memory else "",
            " ".join(memory["changes"]) if memory else "",
            " ".join(memory["risks"]) if memory else "",
            " ".join(memory["open_questions"]) if memory else "",
            " ".join(item for section in packet["sections"] for item in section.get("items", []))
            if packet["sections"]
            else "",
            " ".join(topic["title"] for topic in topics),
        ]
    )
    evidence_tokens = tokenize(evidence_text)

    evaluation_id = f"evaluation-{uuid.uuid4()}"
    conn.execute(
        """
        INSERT INTO consistency_evaluations (
            id,
            project_id,
            run_id,
            packet_id,
            invocation_id,
            trigger_kind,
            evaluator_version,
            summary,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, 'v1', ?, ?)
        """,
        (
            evaluation_id,
            project_id,
            run_id,
            packet_id,
            invocation_id,
            trigger_kind,
            f"Evaluating {row[2]} against project truth, memory, recent runs, packet policy, and indexed topics.",
            now_iso(),
        ),
    )

    findings: list[dict[str, Any]] = []

    for missing_item in truth["missing"]:
        overlap = tokenize(missing_item) & evidence_tokens
        if overlap and row[5] == "completed":
            findings.append(
                {
                    "finding_kind": "likely_stale",
                    "severity": "warning",
                    "rule_key": "project_truth.missing_vs_completed_run",
                    "summary": (
                        f"Project truth still lists '{missing_item}' as missing, but run '{row[2]}' "
                        "records it as completed."
                    ),
                    "provenance": [
                        {"source_kind": "project_truth", "path": truth["path"], "value": missing_item},
                        {"source_kind": "run", "run_id": run_id, "status": row[5]},
                        {"source_kind": "memory", "memory_id": memory["id"] if memory else None},
                    ],
                    "metadata": {"matched_terms": sorted(overlap)},
                }
            )

    current_tokens = tokenize(row[2])
    for prior_run in recent_runs:
        overlap = current_tokens & tokenize(prior_run["objective"])
        if overlap and {row[5], prior_run["status"]} & {"completed"} and {row[5], prior_run["status"]} & {"failed", "canceled"}:
            findings.append(
                {
                    "finding_kind": "direct_contradiction",
                    "severity": "error",
                    "rule_key": "recent_runs.conflicting_outcomes",
                    "summary": (
                        f"Run '{row[2]}' has a conflicting recent outcome with '{prior_run['objective']}' "
                        f"({prior_run['status']})."
                    ),
                    "provenance": [
                        {"source_kind": "run", "run_id": run_id, "status": row[5]},
                        {
                            "source_kind": "recent_run",
                            "run_id": prior_run["id"],
                            "status": prior_run["status"],
                            "objective": prior_run["objective"],
                        },
                    ],
                    "metadata": {"matched_terms": sorted(overlap)},
                }
            )
            break

    compact_guardrail = any("compact ranked" in guardrail.lower() for guardrail in truth["guardrails"])
    if compact_guardrail and (
        packet["policy_mode"] == "explore"
        or (packet["token_budget"] or 0) > 1000
    ):
        findings.append(
            {
                "finding_kind": "soft_tension",
                "severity": "info",
                "rule_key": "policy.compact_ranked_default",
                "summary": (
                    "Packet execution diverged from the compact-ranked default policy and may need "
                    "either approval or a truth-file update."
                ),
                "provenance": [
                    {"source_kind": "project_truth", "path": truth["path"], "value": truth["guardrails"]},
                    {
                        "source_kind": "packet",
                        "packet_id": packet_id,
                        "policy_mode": packet["policy_mode"],
                        "token_budget": packet["token_budget"],
                    },
                    {"source_kind": "workflow_policy", "workflow_key": row[3], "agent_key": row[4]},
                ],
                "metadata": {
                    "policy_mode": packet["policy_mode"],
                    "token_budget": packet["token_budget"],
                },
            }
        )

    if row[5] == "completed":
        workflow_report_count = 0
        if table_exists(conn, "workflow_execution_reports"):
            workflow_report_count = int(
                conn.execute(
                    "SELECT COUNT(*) FROM workflow_execution_reports WHERE run_id = ?",
                    (run_id,),
                ).fetchone()[0]
            )
        if workflow_report_count == 0:
            findings.append(
                {
                    "finding_kind": "workflow_state_gap",
                    "severity": "error",
                    "rule_key": "workflow.completed_without_execution_report",
                    "summary": "Run is completed but no workflow execution report is linked.",
                    "provenance": [
                        {"source_kind": "run", "run_id": run_id, "status": row[5]},
                        {"source_kind": "workflow_execution_reports", "count": workflow_report_count},
                    ],
                    "metadata": {"workflow_key": row[3], "agent_key": row[4]},
                }
            )

    if artifacts:
        unpredicted = [
            artifact
            for artifact in artifacts
            if packet_mentions
            and not any(artifact.endswith(mention) or mention in artifact for mention in packet_mentions)
        ]
        if packet_mentions and unpredicted:
            findings.append(
                {
                    "finding_kind": "packet_result_delta",
                    "severity": "warning",
                    "rule_key": "packet.predicted_files_vs_artifacts",
                    "summary": (
                        f"{len(unpredicted)} touched artifacts were not forecast by the packet file hints."
                    ),
                    "provenance": [
                        {"source_kind": "packet", "packet_id": packet_id, "mentioned_files": packet_mentions},
                        {"source_kind": "artifacts", "paths": unpredicted[:12]},
                    ],
                    "metadata": {"unpredicted_count": len(unpredicted)},
                }
            )
        if not packet_mentions:
            findings.append(
                {
                    "finding_kind": "file_topic_delta",
                    "severity": "info",
                    "rule_key": "packet.no_file_predictions_for_artifacts",
                    "summary": "Artifacts were recorded but the packet did not include file-level predictions.",
                    "provenance": [
                        {"source_kind": "packet", "packet_id": packet_id},
                        {"source_kind": "artifacts", "paths": artifacts[:12]},
                    ],
                    "metadata": {"artifact_count": len(artifacts)},
                }
            )

    if standards_signal and (
        int(standards_signal["critical_delta_count"] or 0) > 0
        or int(standards_signal["unknown_count"] or 0) > 0
    ):
        findings.append(
            {
                "finding_kind": "standards_evidence_gap",
                "severity": "warning"
                if int(standards_signal["critical_delta_count"] or 0) == 0
                else "error",
                "rule_key": "standards.unresolved_project_health_delta",
                "summary": (
                    "Latest standards health snapshot has unresolved critical or unknown standards."
                ),
                "provenance": [
                    {"source_kind": "standards_health_snapshot", **standards_signal},
                ],
                "metadata": standards_signal,
            }
        )

    for finding in findings:
        conn.execute(
            """
            INSERT INTO consistency_findings (
                id,
                evaluation_id,
                project_id,
                run_id,
                packet_id,
                topic_slug,
                finding_kind,
                severity,
                rule_key,
                summary,
                provenance_json,
                metadata_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"finding-{uuid.uuid4()}",
                evaluation_id,
                project_id,
                run_id,
                packet_id,
                f"project-{project_id}" if project_id else None,
                finding["finding_kind"],
                finding["severity"],
                finding["rule_key"],
                finding["summary"],
                _json(finding["provenance"]),
                _json(finding["metadata"]),
                now_iso(),
            ),
        )

    record_run_event(
        conn,
        run_id=run_id,
        event_type="evaluation_recorded",
        to_status=row[5],
        summary=f"Structured evaluator recorded {len(findings)} findings.",
        metadata={"evaluation_id": evaluation_id, "finding_count": len(findings)},
        invocation_id=invocation_id,
    )

    return evaluation_id


def default_db_path() -> str:
    return os.path.expanduser("~/AIOS/data/aios.db")
