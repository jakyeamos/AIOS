from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.next_action import get_next_actions  # noqa: E402


def test_next_action_reads_canonical_success_criteria_schema() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE orchestration_runs (
          id TEXT PRIMARY KEY,
          project_id TEXT,
          objective TEXT,
          status TEXT,
          created_at TEXT,
          updated_at TEXT
        );
        CREATE TABLE success_criteria_evaluations (
          id TEXT PRIMARY KEY,
          project_id TEXT,
          run_id TEXT,
          summary TEXT,
          created_at TEXT
        );
        CREATE TABLE success_criteria_findings (
          id TEXT PRIMARY KEY,
          evaluation_id TEXT NOT NULL,
          criterion_id TEXT NOT NULL,
          criterion_title TEXT NOT NULL,
          criterion_scope TEXT NOT NULL,
          level TEXT NOT NULL,
          summary TEXT NOT NULL,
          resolution_status TEXT NOT NULL DEFAULT 'open',
          created_at TEXT NOT NULL
        );
        """
    )
    conn.execute(
        """
        INSERT INTO orchestration_runs (id, project_id, objective, status, created_at, updated_at)
        VALUES ('run-1', 'project-1', 'Fix login bug', 'completed',
                '2026-06-23T00:00:00Z', '2026-06-23T00:01:00Z')
        """
    )
    conn.execute(
        """
        INSERT INTO success_criteria_evaluations (id, project_id, run_id, summary, created_at)
        VALUES ('eval-1', 'project-1', 'run-1', 'Found blocker', '2026-06-23T00:01:00Z')
        """
    )
    conn.execute(
        """
        INSERT INTO success_criteria_findings (
          id, evaluation_id, criterion_id, criterion_title, criterion_scope, level, summary,
          resolution_status, created_at
        )
        VALUES (
          'finding-1', 'eval-1', 'agent-claim-verification', 'Agent Claim Verification',
          'global', 'blocker', 'Missing verification evidence', 'open',
          '2026-06-23T00:02:00Z'
        )
        """
    )

    actions = get_next_actions(conn, project_id="project-1")

    blocker_actions = [action for action in actions if action.kind == "resolve_open_blocker"]
    assert len(blocker_actions) == 1
    assert blocker_actions[0].project_id == "project-1"
    assert blocker_actions[0].evidence_ids == ("finding-1", "run-1")
    assert blocker_actions[0].drill_down_path == "/runs/run-1?finding=finding-1"
