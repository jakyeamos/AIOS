# ruff: noqa: E402

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.peer_trace import (  # noqa: E402
    end_peer_session,
    get_peer_session_detail,
    list_peer_sessions,
    record_peer_trace,
    start_peer_session,
)


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
    return conn


def test_start_peer_session_returns_session_id() -> None:
    conn = _connect()

    session_id = start_peer_session(
        conn,
        anonymous_peer_id="peer-hash",
        harness_used="codex",
        repo_language="python",
        repo_framework="pytest",
    )

    row = conn.execute("SELECT * FROM peer_sessions WHERE id = ?", (session_id,)).fetchone()
    assert row["anonymous_peer_id"] == "peer-hash"
    assert row["context_profile"] == "peer_repo_only"
    assert row["harness_used"] == "codex"


def test_end_peer_session_sets_ended_at() -> None:
    conn = _connect()
    session_id = start_peer_session(conn, anonymous_peer_id="peer-hash")

    end_peer_session(conn, session_id)

    row = conn.execute("SELECT ended_at FROM peer_sessions WHERE id = ?", (session_id,)).fetchone()
    assert row["ended_at"] is not None


def test_record_peer_trace_redacts_notes_and_does_not_store_prompt_text() -> None:
    conn = _connect()
    session_id = start_peer_session(conn, anonymous_peer_id="peer-hash")

    trace_id = record_peer_trace(
        conn,
        session_id=session_id,
        task_category="feature",
        prompt_length=120,
        turn_count=4,
        tool_call_count=7,
        failed_command_count=1,
        duration_ms=5000,
        files_changed_count=3,
        tests_run=2,
        final_status="success",
        peer_rating=5,
        notes="api_key=supersecretvalue1234567890",
    )

    row = conn.execute("SELECT * FROM peer_traces WHERE id = ?", (trace_id,)).fetchone()
    session = conn.execute(
        "SELECT total_tasks_observed FROM peer_sessions WHERE id = ?", (session_id,)
    ).fetchone()
    assert "[REDACTED]" in row["notes"]
    assert row["store_prompt_text"] == 0
    assert session["total_tasks_observed"] == 1


def test_list_peer_sessions_and_get_detail() -> None:
    conn = _connect()
    session_id = start_peer_session(conn, anonymous_peer_id="peer-hash")
    record_peer_trace(
        conn,
        session_id=session_id,
        task_category="debug",
        prompt_length=80,
        turn_count=2,
        tool_call_count=3,
        failed_command_count=0,
        duration_ms=1000,
        files_changed_count=1,
        tests_run=1,
        final_status="success",
    )

    sessions = list_peer_sessions(conn)
    detail = get_peer_session_detail(conn, session_id)

    assert [session["id"] for session in sessions] == [session_id]
    assert detail["traces"][0]["task_category"] == "debug"
