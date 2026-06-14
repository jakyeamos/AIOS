from __future__ import annotations

import json
import re
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from services.eval_run_service import ensure_eval_schema

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY_PATH = REPO_ROOT / "config" / "peer-eval" / "peer-trace-policy.json"
SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^,\s]+"),
    re.compile(r"\b[A-Za-z0-9_=-]{24,}\b"),
)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"


def load_peer_trace_policy(policy_path: Path = DEFAULT_POLICY_PATH) -> dict[str, Any]:
    if not policy_path.exists():
        return {}
    return json.loads(policy_path.read_text(encoding="utf-8"))


def _redact_notes(notes: str | None, *, policy: dict[str, Any]) -> str | None:
    if notes is None:
        return None
    if not policy.get("secretRedactionAlwaysOn", True):
        return notes
    redacted = notes
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def ensure_peer_trace_schema(conn: sqlite3.Connection) -> None:
    ensure_eval_schema(conn)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS peer_sessions (
          id TEXT PRIMARY KEY,
          anonymous_peer_id TEXT NOT NULL,
          started_at TEXT,
          ended_at TEXT,
          context_profile TEXT NOT NULL DEFAULT 'peer_repo_only',
          harness_used TEXT,
          repo_language TEXT,
          repo_framework TEXT,
          total_tasks_observed INTEGER DEFAULT 0,
          created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS peer_traces (
          id TEXT PRIMARY KEY,
          peer_session_id TEXT REFERENCES peer_sessions(id),
          task_category TEXT,
          prompt_length INTEGER,
          turn_count INTEGER,
          tool_call_count INTEGER,
          failed_command_count INTEGER,
          duration_ms INTEGER,
          files_changed_count INTEGER,
          tests_run INTEGER,
          final_status TEXT,
          peer_rating INTEGER,
          notes TEXT,
          store_prompt_text INTEGER DEFAULT 0,
          created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS shadow_candidates (
          id TEXT PRIMARY KEY,
          task_id TEXT REFERENCES eval_tasks(id),
          peer_session_id TEXT REFERENCES peer_sessions(id),
          peer_trace_id TEXT REFERENCES peer_traces(id),
          score REAL NOT NULL,
          recommendation TEXT NOT NULL,
          reasons_json TEXT,
          blockers_json TEXT,
          automation_state TEXT NOT NULL DEFAULT 'TRACE_ONLY',
          state_updated_at TEXT,
          created_at TEXT
        );
        """
    )


def start_peer_session(
    conn: sqlite3.Connection,
    *,
    anonymous_peer_id: str,
    harness_used: str | None = None,
    repo_language: str | None = None,
    repo_framework: str | None = None,
) -> str:
    ensure_peer_trace_schema(conn)
    policy = load_peer_trace_policy()
    session_id = _new_id("peer-session")
    now = _now_iso()
    conn.execute(
        """
        INSERT INTO peer_sessions (
          id, anonymous_peer_id, started_at, context_profile, harness_used,
          repo_language, repo_framework, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            anonymous_peer_id,
            now,
            str(policy.get("contextProfile", "peer_repo_only")),
            harness_used,
            repo_language,
            repo_framework,
            now,
        ),
    )
    return session_id


def end_peer_session(conn: sqlite3.Connection, session_id: str) -> None:
    ensure_peer_trace_schema(conn)
    conn.execute(
        "UPDATE peer_sessions SET ended_at = ? WHERE id = ?",
        (_now_iso(), session_id),
    )


def record_peer_trace(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    task_category: str,
    prompt_length: int,
    turn_count: int,
    tool_call_count: int,
    failed_command_count: int,
    duration_ms: int,
    files_changed_count: int,
    tests_run: int,
    final_status: str,
    peer_rating: int | None = None,
    notes: str | None = None,
) -> str:
    ensure_peer_trace_schema(conn)
    policy = load_peer_trace_policy()
    trace_id = _new_id("peer-trace")
    conn.execute(
        """
        INSERT INTO peer_traces (
          id, peer_session_id, task_category, prompt_length, turn_count,
          tool_call_count, failed_command_count, duration_ms, files_changed_count,
          tests_run, final_status, peer_rating, notes, store_prompt_text, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            trace_id,
            session_id,
            task_category,
            prompt_length,
            turn_count,
            tool_call_count,
            failed_command_count,
            duration_ms,
            files_changed_count,
            tests_run,
            final_status,
            peer_rating,
            _redact_notes(notes, policy=policy),
            int(bool(policy.get("storePromptText", False))),
            _now_iso(),
        ),
    )
    conn.execute(
        """
        UPDATE peer_sessions
        SET total_tasks_observed = total_tasks_observed + 1
        WHERE id = ?
        """,
        (session_id,),
    )
    return trace_id


def list_peer_sessions(conn: sqlite3.Connection, limit: int = 50) -> list[dict[str, Any]]:
    ensure_peer_trace_schema(conn)
    rows = conn.execute(
        "SELECT * FROM peer_sessions ORDER BY created_at DESC LIMIT ?",
        (max(1, int(limit)),),
    ).fetchall()
    return [dict(row) for row in rows]


def get_peer_session_detail(conn: sqlite3.Connection, session_id: str) -> dict[str, Any]:
    ensure_peer_trace_schema(conn)
    row = conn.execute("SELECT * FROM peer_sessions WHERE id = ?", (session_id,)).fetchone()
    if row is None:
        raise ValueError(f"Peer session not found: {session_id}")
    detail = dict(row)
    detail["traces"] = [
        dict(trace)
        for trace in conn.execute(
            "SELECT * FROM peer_traces WHERE peer_session_id = ? ORDER BY created_at",
            (session_id,),
        ).fetchall()
    ]
    return detail
