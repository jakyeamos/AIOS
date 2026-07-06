# ruff: noqa: E402

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.peer_trace import ensure_peer_trace_schema  # noqa: E402
from services.shadow_automation import (  # noqa: E402
    advance_state,
    approve_candidate,
    run_full_automation_pipeline,
)


class _Completed:
    def __init__(self, stdout: str = "", returncode: int = 0) -> None:
        self.stdout = stdout
        self.stderr = ""
        self.returncode = returncode


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    ensure_peer_trace_schema(conn)
    return conn


def _candidate(conn: sqlite3.Connection, candidate_id: str = "candidate-1") -> str:
    conn.execute(
        """
        INSERT INTO shadow_candidates (
          id, score, recommendation, reasons_json, blockers_json, automation_state, created_at
        )
        VALUES (?, 90, 'excellent_shadow_candidate', '[]', '[]', 'TRACE_ONLY', '2026-06-13T00:00:00Z')
        """,
        (candidate_id,),
    )
    return candidate_id


def test_approve_candidate_sets_approved_in_person() -> None:
    conn = _connect()
    candidate_id = _candidate(conn)

    state = approve_candidate(conn, candidate_id)

    row = conn.execute(
        "SELECT automation_state FROM shadow_candidates WHERE id = ?", (candidate_id,)
    ).fetchone()
    assert state == "APPROVED_IN_PERSON"
    assert row["automation_state"] == "APPROVED_IN_PERSON"


def test_advance_state_follows_approved_to_snapshot() -> None:
    conn = _connect()
    candidate_id = _candidate(conn)
    approve_candidate(conn, candidate_id)

    state = advance_state(conn, candidate_id)

    assert state == "SNAPSHOT_CREATED"


def test_contamination_detection_blocks_pipeline(tmp_path: Path) -> None:
    conn = _connect()
    candidate_id = _candidate(conn)
    approve_candidate(conn, candidate_id)

    with (
        patch("services.shadow_automation.subprocess.run") as run,
        patch("services.shadow_automation.verify_no_contamination") as verify,
    ):
        run.return_value = _Completed("abc123\n")
        verify.return_value = False
        result = run_full_automation_pipeline(conn, candidate_id=candidate_id, repo_path=tmp_path)

    assert result["final_state"] == "BLOCKED_DIRTY_REPO"


def test_pipeline_creates_comparison_report(tmp_path: Path) -> None:
    conn = _connect()
    candidate_id = _candidate(conn)
    approve_candidate(conn, candidate_id)

    with (
        patch("services.shadow_automation.REPORT_DIR", tmp_path / "reports"),
        patch("services.shadow_automation.BACKFILL_PATH", tmp_path / "backfill.md"),
        patch("services.shadow_automation.subprocess.run") as run,
        patch("services.shadow_automation.verify_no_contamination") as verify,
        patch("services.shadow_automation.create_shadow_worktree") as create_worktree,
    ):
        run.side_effect = [_Completed("abc123\n"), _Completed("", 0), _Completed("", 0)]
        verify.return_value = True
        create_worktree.return_value = str(tmp_path / "worktree")
        result = run_full_automation_pipeline(conn, candidate_id=candidate_id, repo_path=tmp_path)

    assert result["final_state"] == "BACKLOG_ITEMS_CREATED"
    assert Path(result["report_path"]).exists()


def test_pipeline_appends_backlog_for_failed_verification(tmp_path: Path) -> None:
    conn = _connect()
    candidate_id = _candidate(conn)
    approve_candidate(conn, candidate_id)
    backfill = tmp_path / "backfill.md"

    with (
        patch("services.shadow_automation.REPORT_DIR", tmp_path / "reports"),
        patch("services.shadow_automation.BACKFILL_PATH", backfill),
        patch("services.shadow_automation.subprocess.run") as run,
        patch("services.shadow_automation.verify_no_contamination") as verify,
        patch("services.shadow_automation.create_shadow_worktree") as create_worktree,
    ):
        run.side_effect = [_Completed("abc123\n"), _Completed("", 0), _Completed("", 1)]
        verify.return_value = True
        create_worktree.return_value = str(tmp_path / "worktree")
        run_full_automation_pipeline(conn, candidate_id=candidate_id, repo_path=tmp_path)

    assert "Shadow verification command failed." in backfill.read_text(encoding="utf-8")
