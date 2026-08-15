from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from services.aios_cli import EXIT_NOT_FOUND, EXIT_OK, run_cli
from services.standards_health_mutations import update_standards_backfill_task


def _seed_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE standards_backfill_tasks (
          id TEXT PRIMARY KEY,
          snapshot_id TEXT NOT NULL,
          project_id TEXT NOT NULL,
          delta_item_id TEXT NOT NULL,
          standard_id TEXT NOT NULL,
          title TEXT NOT NULL,
          problem_statement TEXT NOT NULL,
          expected_state TEXT NOT NULL,
          acceptance_criteria_json TEXT NOT NULL,
          effort REAL NOT NULL,
          dependency_chain_json TEXT NOT NULL,
          expected_health_impact REAL NOT NULL,
          owner TEXT,
          blocked_reason TEXT,
          due_at TEXT,
          review_at TEXT,
          priority_score REAL NOT NULL,
          priority_bucket TEXT NOT NULL,
          blocked INTEGER NOT NULL,
          status TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        INSERT INTO standards_backfill_tasks (
          id, snapshot_id, project_id, delta_item_id, standard_id, title,
          problem_statement, expected_state, acceptance_criteria_json, effort,
          dependency_chain_json, expected_health_impact, owner, blocked_reason,
          due_at, review_at, priority_score, priority_bucket, blocked, status,
          created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "task-1",
            "snapshot-1",
            "project-1",
            "delta-1",
            "testing.coverage",
            "Add coverage",
            "The core flow lacks coverage.",
            "The core flow is covered.",
            "[]",
            1.0,
            '["upstream"]',
            0.7,
            None,
            None,
            None,
            None,
            2.5,
            "high_leverage",
            0,
            "open",
            "2026-07-14T00:00:00+00:00",
            "2026-07-14T00:00:00+00:00",
        ),
    )
    conn.commit()
    conn.close()


def test_update_standards_backfill_task_preserves_omitted_fields(tmp_path: Path) -> None:
    path = tmp_path / "aios.db"
    _seed_db(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row

    result = update_standards_backfill_task(
        conn,
        {
            "taskId": "task-1",
            "status": "blocked",
            "blocked": True,
            "blockedReason": "Waiting for upstream.",
            "priorityBucket": "blocked",
        },
    )

    assert result["status"] == "blocked"
    assert result["blocked"] is True
    assert result["blocked_reason"] == "Waiting for upstream."
    assert result["owner"] is None
    assert result["priority_bucket"] == "blocked"
    conn.close()


def test_update_standards_backfill_task_rejects_invalid_state(tmp_path: Path) -> None:
    path = tmp_path / "aios.db"
    _seed_db(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row

    with pytest.raises(ValueError, match="status must be one of"):
        update_standards_backfill_task(conn, {"taskId": "task-1", "status": "unknown"})
    conn.close()


def test_cli_standards_backfill_update_uses_python_owner(tmp_path: Path, capsys) -> None:
    path = tmp_path / "aios.db"
    _seed_db(path)

    exit_code = run_cli(
        [
            "--json",
            "--db",
            str(path),
            "standards-backfill-update",
            "--payload-json",
            json.dumps({"taskId": "task-1", "status": "done", "blocked": False}),
        ]
    )

    assert exit_code == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["id"] == "task-1"
    assert payload["data"]["status"] == "done"


def test_cli_standards_backfill_update_reports_missing_task(tmp_path: Path, capsys) -> None:
    path = tmp_path / "aios.db"
    _seed_db(path)

    exit_code = run_cli(
        [
            "--json",
            "--db",
            str(path),
            "standards-backfill-update",
            "--payload-json",
            json.dumps({"taskId": "missing", "status": "done"}),
        ]
    )

    assert exit_code == EXIT_NOT_FOUND
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"]["code"] == "backfill-task-not-found"
