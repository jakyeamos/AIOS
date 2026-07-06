"""Durable evidence artifact helpers for command-backed closeout checks."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

EvidenceStatus = Literal["pass", "fail", "unknown"]


def ensure_evidence_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS evidence_artifacts (
          evidence_id TEXT PRIMARY KEY,
          task_id TEXT,
          run_id TEXT,
          session_id TEXT,
          phase TEXT,
          timestamp TEXT NOT NULL,
          agent TEXT,
          model TEXT,
          command TEXT,
          exit_code INTEGER,
          stdout_path TEXT,
          stderr_path TEXT,
          output_hash TEXT,
          parsed_summary TEXT,
          diff_hash TEXT,
          commit_hash TEXT,
          status TEXT NOT NULL,
          caveats_json TEXT NOT NULL DEFAULT '[]',
          created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_evidence_artifacts_run
          ON evidence_artifacts(run_id, created_at DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_evidence_artifacts_session
          ON evidence_artifacts(session_id, created_at DESC)
        """
    )


def record_evidence_artifact(
    conn: sqlite3.Connection,
    *,
    task_id: str | None = None,
    run_id: str | None = None,
    session_id: str | None = None,
    phase: str | None = None,
    agent: str | None = None,
    model: str | None = None,
    command: str | None = None,
    exit_code: int | None = None,
    stdout_path: str | Path | None = None,
    stderr_path: str | Path | None = None,
    output_hash: str | None = None,
    parsed_summary: str | None = None,
    diff_hash: str | None = None,
    commit_hash: str | None = None,
    status: EvidenceStatus = "unknown",
    caveats: list[str] | None = None,
    evidence_id: str | None = None,
    timestamp: str | None = None,
) -> str:
    ensure_evidence_schema(conn)
    normalized_caveats = list(caveats or [])
    stdout_text = _path_text(stdout_path)
    stderr_text = _path_text(stderr_path)
    normalized_hash = output_hash or _output_hash(stdout_text, stderr_text)
    normalized_status: EvidenceStatus = status if status in {"pass", "fail"} else "unknown"

    has_output_reference = bool(stdout_path or stderr_path or normalized_hash)
    has_absence_reason = any(item.startswith("output-absent:") for item in normalized_caveats)
    if normalized_status == "pass" and (
        not command or not (has_output_reference or has_absence_reason)
    ):
        normalized_status = "unknown"
        if "empty-marker" not in normalized_caveats:
            normalized_caveats.append("empty-marker")

    # Command-backed pass verdicts must be provable: no exit code means unknown,
    # and a nonzero exit code can never be pass.
    if command:
        if normalized_status == "pass" and exit_code is None:
            normalized_status = "unknown"
            if "exit-code-unavailable" not in normalized_caveats:
                normalized_caveats.append("exit-code-unavailable")
        elif normalized_status == "pass" and exit_code != 0:
            normalized_status = "fail"
            if "status-exit-code-mismatch" not in normalized_caveats:
                normalized_caveats.append("status-exit-code-mismatch")

    artifact_id = evidence_id or str(uuid.uuid4())
    observed_at = timestamp or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        """
        INSERT INTO evidence_artifacts (
          evidence_id, task_id, run_id, session_id, phase, timestamp, agent, model,
          command, exit_code, stdout_path, stderr_path, output_hash, parsed_summary,
          diff_hash, commit_hash, status, caveats_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            artifact_id,
            task_id,
            run_id,
            session_id,
            phase,
            observed_at,
            agent,
            model,
            _nonempty(command),
            exit_code,
            str(stdout_path) if stdout_path else None,
            str(stderr_path) if stderr_path else None,
            normalized_hash,
            parsed_summary,
            diff_hash,
            commit_hash,
            normalized_status,
            json.dumps(normalized_caveats),
            observed_at,
        ),
    )
    return artifact_id


def list_evidence_artifacts(
    conn: sqlite3.Connection,
    *,
    run_id: str | None = None,
    session_id: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if run_id:
        clauses.append("run_id = ?")
        params.append(run_id)
    if session_id:
        clauses.append("session_id = ?")
        params.append(session_id)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    try:
        rows = conn.execute(
            f"""
            SELECT evidence_id, task_id, run_id, session_id, phase, timestamp, agent, model,
                   command, exit_code, stdout_path, stderr_path, output_hash, parsed_summary,
                   diff_hash, commit_hash, status, caveats_json, created_at
            FROM evidence_artifacts
            {where}
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (*params, max(1, min(limit, 500))),
        ).fetchall()
    except sqlite3.Error:
        return []
    columns = [
        "evidence_id",
        "task_id",
        "run_id",
        "session_id",
        "phase",
        "timestamp",
        "agent",
        "model",
        "command",
        "exit_code",
        "stdout_path",
        "stderr_path",
        "output_hash",
        "parsed_summary",
        "diff_hash",
        "commit_hash",
        "status",
        "caveats_json",
        "created_at",
    ]
    return [dict(zip(columns, row, strict=True)) for row in rows]


def validate_fresh_evidence(
    conn: sqlite3.Connection,
    *,
    run_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    rows = list_evidence_artifacts(conn, limit=500)
    fresh_rows: list[dict[str, Any]] = []
    stale_count = 0
    unknown_count = 0
    usable_rows: list[dict[str, Any]] = []
    for row in rows:
        if _is_stale(row, run_id=run_id, session_id=session_id):
            stale_count += 1
            continue
        fresh_rows.append(row)
        if row.get("status") == "unknown":
            unknown_count += 1
        if is_usable_evidence(row):
            usable_rows.append(row)
    return {
        "usable": bool(usable_rows),
        "fresh_count": len(fresh_rows),
        "usable_count": len(usable_rows),
        "unknown_count": unknown_count,
        "stale_count": stale_count,
        "evidence": [format_evidence_ref(row) for row in usable_rows],
    }


def usable_evidence_refs(
    conn: sqlite3.Connection,
    *,
    run_id: str | None = None,
    session_id: str | None = None,
    limit: int = 20,
) -> list[str]:
    rows = list_evidence_artifacts(conn, run_id=run_id, session_id=session_id, limit=limit)
    return [format_evidence_ref(row) for row in rows if is_usable_evidence(row)]


def is_usable_evidence(row: dict[str, Any]) -> bool:
    if row.get("status") not in {"pass", "fail"}:
        return False
    command = str(row.get("command") or "").strip()
    if not command:
        return False
    if row.get("output_hash") or row.get("stdout_path") or row.get("stderr_path"):
        return True
    return any(item.startswith("output-absent:") for item in _caveats(row))


def format_evidence_ref(row: dict[str, Any]) -> str:
    command = str(row.get("command") or "").strip()
    return (
        f"evidence-artifact: {row.get('evidence_id')} status={row.get('status')} "
        f"command={command[:180]}"
    )


def _is_stale(row: dict[str, Any], *, run_id: str | None, session_id: str | None) -> bool:
    row_run_id = str(row.get("run_id") or "").strip()
    row_session_id = str(row.get("session_id") or "").strip()
    if run_id and row_run_id and row_run_id != run_id:
        return True
    return bool(session_id and row_session_id and row_session_id != session_id)


def _caveats(row: dict[str, Any]) -> list[str]:
    try:
        payload = json.loads(str(row.get("caveats_json") or "[]"))
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    return [str(item) for item in payload]


def _path_text(path: str | Path | None) -> bytes | None:
    if not path:
        return None
    candidate = Path(path).expanduser()
    if not candidate.exists() or not candidate.is_file():
        return None
    return candidate.read_bytes()


def _output_hash(stdout: bytes | None, stderr: bytes | None) -> str | None:
    if stdout is None and stderr is None:
        return None
    digest = hashlib.sha256()
    if stdout is not None:
        digest.update(stdout)
    if stderr is not None:
        digest.update(stderr)
    return digest.hexdigest()


def _nonempty(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
