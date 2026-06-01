from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.next_action import NextAction, get_next_actions  # noqa: E402


def _make_db(*, all_tables: bool = True) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE orchestration_runs (
          id TEXT PRIMARY KEY,
          project_id TEXT,
          objective TEXT,
          workflow_key TEXT,
          status TEXT,
          created_at TEXT,
          updated_at TEXT
        );
        CREATE TABLE improvement_writebacks (
          id TEXT PRIMARY KEY,
          run_id TEXT,
          project_id TEXT,
          layer_type TEXT,
          layer_key TEXT,
          title TEXT,
          summary TEXT,
          status TEXT,
          requires_approval INTEGER,
          proposed_change_json TEXT,
          created_at TEXT
        );
        """
    )
    if not all_tables:
        return conn
    conn.executescript(
        """
        CREATE TABLE standards_delta_items (
          id TEXT PRIMARY KEY,
          project_id TEXT,
          domain TEXT,
          priority_bucket TEXT,
          severity REAL,
          summary TEXT,
          remediation_playbook_json TEXT,
          status TEXT,
          created_at TEXT
        );
        CREATE TABLE success_criteria_findings (
          id TEXT PRIMARY KEY,
          run_id TEXT,
          criterion_id TEXT,
          level TEXT,
          message TEXT,
          resolution_status TEXT,
          created_at TEXT
        );
        CREATE TABLE workflow_learning_events (
          id TEXT PRIMARY KEY,
          run_id TEXT
        );
        CREATE TABLE standards_backfill_tasks (
          id TEXT PRIMARY KEY,
          project_id TEXT,
          summary TEXT,
          status TEXT,
          priority_bucket TEXT,
          created_at TEXT
        );
        CREATE TABLE promotion_lifecycle_items (
          id TEXT PRIMARY KEY,
          item_kind TEXT,
          item_key TEXT,
          status TEXT,
          created_at TEXT
        );
        """
    )
    return conn


def _seed_delta(
    conn: sqlite3.Connection,
    *,
    id_: str = "delta-1",
    project_id: str = "p1",
    priority_bucket: str = "foundational",
    severity: float = 9,
    workflow_key: str | None = "standards-backfill",
) -> None:
    conn.execute(
        """
        INSERT INTO standards_delta_items (
          id, project_id, domain, priority_bucket, severity, summary,
          remediation_playbook_json, status, created_at
        )
        VALUES (?, ?, 'testing', ?, ?, 'Fix testing delta', ?, 'open', '2026-06-01T00:00:00Z')
        """,
        (
            id_,
            project_id,
            priority_bucket,
            severity,
            json.dumps({"recommended_workflow_key": workflow_key} if workflow_key else {}),
        ),
    )


def _seed_pending_writeback(
    conn: sqlite3.Connection,
    *,
    id_: str = "wb-1",
    project_id: str = "p1",
    learning: bool = False,
) -> None:
    source = {"metadata": {"source": "learning_analysis"}} if learning else {"source": "operator"}
    conn.execute(
        """
        INSERT INTO improvement_writebacks (
          id, run_id, project_id, layer_type, layer_key, title, summary, status,
          requires_approval, proposed_change_json, created_at
        )
        VALUES (?, 'run-1', ?, 'workflow', 'implementation-delivery', 'Review writeback',
                'Approve the governed change', 'pending_approval', 1, ?, '2026-06-01T00:00:00Z')
        """,
        (id_, project_id, json.dumps(source)),
    )


def _seed_open_blocker(conn: sqlite3.Connection, *, project_id: str = "p1") -> None:
    conn.execute(
        """
        INSERT INTO orchestration_runs (
          id, project_id, objective, workflow_key, status, created_at, updated_at
        )
        VALUES ('run-blocked', ?, 'Blocked work', 'implementation-delivery',
                'completed', '2026-06-01T00:00:00Z', '2026-06-01T00:00:00Z')
        """,
        (project_id,),
    )
    conn.execute(
        """
        INSERT INTO success_criteria_findings (
          id, run_id, criterion_id, level, message, resolution_status, created_at
        )
        VALUES ('finding-1', 'run-blocked', 'CRIT-1', 'blocker',
                'Open blocker', 'open', '2026-06-01T00:00:00Z')
        """
    )


def _seed_terminal_gap(conn: sqlite3.Connection, *, project_id: str = "p1") -> None:
    conn.execute(
        """
        INSERT INTO orchestration_runs (
          id, project_id, objective, workflow_key, status, created_at, updated_at
        )
        VALUES ('run-gap', ?, 'Completed without learning', 'implementation-delivery',
                'completed', '2026-06-01T00:00:00Z', '2026-06-01T00:00:00Z')
        """,
        (project_id,),
    )


def _seed_backfill(conn: sqlite3.Connection, *, project_id: str = "p1") -> None:
    conn.execute(
        """
        INSERT INTO standards_backfill_tasks (
          id, project_id, summary, status, priority_bucket, created_at
        )
        VALUES ('backfill-1', ?, 'Backfill standards evidence', 'pending',
                'quick_wins', '2026-06-01T00:00:00Z')
        """,
        (project_id,),
    )


def _seed_promotion_candidate(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT INTO promotion_lifecycle_items (id, item_kind, item_key, status, created_at)
        VALUES ('promotion-1', 'skill', 'review-skill', 'candidate', '2026-06-01T00:00:00Z')
        """
    )


def test_next_actions_fuse_multiple_sources() -> None:
    conn = _make_db()
    _seed_delta(conn)
    _seed_pending_writeback(conn)
    _seed_open_blocker(conn)
    _seed_terminal_gap(conn)
    _seed_backfill(conn)

    actions = get_next_actions(conn, project_id="p1")

    kinds = {action.kind for action in actions}
    assert {
        "launch_remediation_workflow",
        "approve_pending_writeback",
        "resolve_open_blocker",
        "fix_terminal_run_gap",
        "complete_backfill_task",
    } <= kinds


def test_next_action_ranking_respects_bucket_weight() -> None:
    conn = _make_db()
    _seed_delta(conn, id_="foundational", priority_bucket="foundational", severity=5)
    _seed_delta(conn, id_="high", priority_bucket="high_leverage", severity=10)

    actions = get_next_actions(conn, project_id="p1")

    assert actions[0].evidence_ids == ("foundational",)


def test_next_action_confidence_tiebreak_within_bucket() -> None:
    conn = _make_db()
    _seed_delta(conn, id_="low", priority_bucket="foundational", severity=5)
    _seed_delta(conn, id_="high", priority_bucket="foundational", severity=9)

    actions = get_next_actions(conn, project_id="p1")

    assert actions[0].evidence_ids == ("high",)


def test_remediation_action_carries_workflow_key() -> None:
    conn = _make_db()
    _seed_delta(conn, workflow_key="standards-backfill")

    action = get_next_actions(conn, project_id="p1")[0]

    assert action.kind == "launch_remediation_workflow"
    assert action.recommended_workflow_key == "standards-backfill"


def test_review_learning_proposal_kind_from_writeback() -> None:
    conn = _make_db()
    _seed_pending_writeback(conn, learning=True)

    action = get_next_actions(conn, project_id="p1")[0]

    assert action.kind == "review_learning_proposal"


def test_all_next_actions_have_drill_down_path() -> None:
    conn = _make_db()
    _seed_delta(conn)
    _seed_pending_writeback(conn, learning=True)
    _seed_open_blocker(conn)
    _seed_terminal_gap(conn)
    _seed_backfill(conn)
    _seed_promotion_candidate(conn)

    actions = get_next_actions(conn, project_id="p1")
    paths = {action.kind: action.drill_down_path for action in actions}

    assert all(path.startswith("/") for path in paths.values())
    assert paths["launch_remediation_workflow"].startswith("/projects/p1?delta=")
    assert paths["review_learning_proposal"].startswith("/writebacks#")
    assert paths["resolve_open_blocker"].startswith("/runs/run-blocked?finding=")
    assert paths["complete_backfill_task"].startswith("/projects/p1?backfill=")
    assert paths["fix_terminal_run_gap"].startswith("/runs/")
    assert paths["promote_candidate_asset"].startswith("/workflows?promotion=")


def test_next_action_tolerates_missing_tables() -> None:
    conn = _make_db(all_tables=False)
    _seed_pending_writeback(conn)
    _seed_terminal_gap(conn)

    actions = get_next_actions(conn, project_id="p1")

    assert {action.kind for action in actions} == {
        "approve_pending_writeback",
        "fix_terminal_run_gap",
    }


def test_next_action_honors_project_filter() -> None:
    conn = _make_db()
    _seed_delta(conn, id_="delta-p1", project_id="p1")
    _seed_delta(conn, id_="delta-p2", project_id="p2")
    _seed_pending_writeback(conn, id_="wb-p1", project_id="p1")
    _seed_pending_writeback(conn, id_="wb-p2", project_id="p2")
    _seed_promotion_candidate(conn)

    actions = get_next_actions(conn, project_id="p1")

    assert actions
    assert all(action.project_id in {"p1", None} for action in actions)
    evidence = {evidence_id for action in actions for evidence_id in action.evidence_ids}
    assert "delta-p2" not in evidence
    assert "wb-p2" not in evidence


def test_next_action_cross_project_when_no_filter() -> None:
    conn = _make_db()
    _seed_delta(conn, id_="delta-p1", project_id="p1")
    _seed_delta(conn, id_="delta-p2", project_id="p2")

    actions = get_next_actions(conn, project_id=None)

    assert {"p1", "p2"} <= {action.project_id for action in actions}


def test_next_action_limit_truncation() -> None:
    conn = _make_db()
    for index in range(20):
        _seed_delta(
            conn,
            id_=f"delta-{index}",
            priority_bucket="foundational" if index < 10 else "quick_wins",
            severity=float(index % 10),
        )

    actions = get_next_actions(conn, project_id="p1", limit=5)

    assert len(actions) == 5
    assert all(action.priority_bucket == "foundational" for action in actions)


def test_next_action_empty_db_returns_empty_list() -> None:
    conn = _make_db()

    assert get_next_actions(conn, project_id="p1") == []


def test_next_action_shape_is_dataclass() -> None:
    conn = _make_db()
    _seed_delta(conn)

    assert isinstance(get_next_actions(conn, project_id="p1")[0], NextAction)
