# ruff: noqa: E402

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.aios_cli import _ensure_start_work_schema, _recent_duplicate_run
from services.run_hygiene import reap_stale_runs


def _seed_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _ensure_start_work_schema(conn)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS orchestration_run_events (
            id TEXT PRIMARY KEY,
            run_id TEXT,
            project_id TEXT,
            session_id TEXT,
            event_type TEXT,
            from_status TEXT,
            to_status TEXT,
            summary TEXT,
            reason_json TEXT,
            metadata_json TEXT,
            created_at TEXT
        )
        """
    )
    return conn


def _insert_run(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    objective: str = "Ship the fix",
    project_id: str = "proj-1",
    status: str = "ready",
    created_at: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO orchestration_runs (
            id, project_id, session_id, objective, workflow_key, agent_key, status,
            backend_key, route_id, route_status, route_result_json, active_invocation_id,
            packet_id, created_at, updated_at
        )
        VALUES (?, ?, 'session-1', ?, 'implementation-delivery', 'implementation-lead', ?,
                'codex', 'route-1', 'ready', '{"route_id": "route-1"}', 'invoke-1',
                'packet-1', ?, ?)
        """,
        (
            run_id,
            project_id,
            objective,
            status,
            created_at or datetime.now(UTC).isoformat(),
            created_at or datetime.now(UTC).isoformat(),
        ),
    )


def test_reaper_cancels_stale_ready_runs_and_records_events() -> None:
    conn = _seed_conn()
    stale = (datetime.now(UTC) - timedelta(days=10)).isoformat()
    _insert_run(conn, run_id="run-stale", created_at=stale)
    _insert_run(conn, run_id="run-fresh")
    _insert_run(conn, run_id="run-active", status="in_progress", created_at=stale)

    result = reap_stale_runs(conn, max_age_days=7)

    assert result["count"] == 1
    assert result["reaped"][0]["run_id"] == "run-stale"
    statuses = dict(conn.execute("SELECT id, status FROM orchestration_runs").fetchall())
    assert statuses == {
        "run-stale": "canceled",
        "run-fresh": "ready",
        "run-active": "in_progress",
    }
    event = conn.execute(
        "SELECT event_type, from_status, to_status FROM orchestration_run_events"
    ).fetchone()
    assert event["event_type"] == "stale_run_reaped"
    assert event["from_status"] == "ready"
    assert event["to_status"] == "canceled"
    reason = json.loads(
        str(
            conn.execute(
                "SELECT status_reason_json FROM orchestration_runs WHERE id='run-stale'"
            ).fetchone()[0]
        )
    )
    assert reason["kind"] == "stale-run-reaper"


def test_reaper_dry_run_changes_nothing() -> None:
    conn = _seed_conn()
    stale = (datetime.now(UTC) - timedelta(days=10)).isoformat()
    _insert_run(conn, run_id="run-stale", created_at=stale)

    result = reap_stale_runs(conn, max_age_days=7, dry_run=True)

    assert result["count"] == 1
    assert result["dry_run"] is True
    row = conn.execute("SELECT status FROM orchestration_runs").fetchone()
    assert row["status"] == "ready"
    assert conn.execute("SELECT COUNT(*) FROM orchestration_run_events").fetchone()[0] == 0


def test_recent_duplicate_run_returns_existing_payload() -> None:
    conn = _seed_conn()
    _insert_run(conn, run_id="run-original")
    conn.execute(
        """
        INSERT INTO briefing_packets (
            id, run_id, project_id, objective, workflow_key, agent_key,
            packet_markdown, sections_json, created_at
        )
        VALUES ('packet-1', 'run-original', 'proj-1', 'Ship the fix',
                'implementation-delivery', 'implementation-lead',
                '# Packet', '[]', ?)
        """,
        (datetime.now(UTC).isoformat(),),
    )

    payload = _recent_duplicate_run(conn, objective="Ship the fix", project_id="proj-1")

    assert payload is not None
    assert payload["deduplicated"] is True
    assert payload["run"]["id"] == "run-original"
    assert payload["packet"]["id"] == "packet-1"
    assert payload["packet"]["markdown"] == "# Packet"


def test_recent_duplicate_ignores_old_terminal_and_other_project_runs() -> None:
    conn = _seed_conn()
    old = (datetime.now(UTC) - timedelta(minutes=30)).isoformat()
    _insert_run(conn, run_id="run-old", created_at=old)
    _insert_run(conn, run_id="run-done", status="completed")
    _insert_run(conn, run_id="run-other", project_id="proj-2")

    assert _recent_duplicate_run(conn, objective="Ship the fix", project_id="proj-1") is None
