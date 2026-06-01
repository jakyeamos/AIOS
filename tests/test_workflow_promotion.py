from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.asset_lifecycle import promote_asset  # noqa: E402
from services.workflow_promotion import (  # noqa: E402
    WorkflowEffectiveness,
    compare_workflow_effectiveness,
    finalize_workflow_promotion,
    propose_workflow_promotion,
)


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE workflow_execution_reports (
          id TEXT PRIMARY KEY,
          run_id TEXT,
          invocation_id TEXT,
          workflow_key TEXT NOT NULL,
          status TEXT NOT NULL,
          report_json TEXT NOT NULL DEFAULT '{}',
          artifact_path TEXT,
          created_at TEXT NOT NULL
        );
        CREATE TABLE success_criteria_stage_findings (
          id TEXT PRIMARY KEY,
          run_id TEXT NOT NULL,
          stage_key TEXT NOT NULL,
          stage_kind TEXT NOT NULL,
          criterion_id TEXT NOT NULL,
          criterion_title TEXT NOT NULL,
          criterion_scope TEXT NOT NULL,
          level TEXT NOT NULL,
          summary TEXT NOT NULL,
          evidence_json TEXT NOT NULL DEFAULT '[]',
          metadata_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL
        );
        """
    )
    return conn


def _report(stage_count: int, blockers: int = 0) -> str:
    return json.dumps(
        {
            "stage_evaluations": [
                {
                    "stage_key": f"stage-{index}",
                    "passed_validations": 1,
                    "total_validations": 1,
                    "blocker_count": 1 if index < blockers else 0,
                    "warning_count": 0,
                    "stage_finding_ids": [],
                    "outcome": "blocked" if index < blockers else "completed",
                }
                for index in range(stage_count)
            ]
        }
    )


def _insert_report(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    workflow_key: str = "implementation-delivery",
    status: str = "completed",
    stage_count: int = 2,
    blockers: int = 0,
) -> None:
    conn.execute(
        """
        INSERT INTO workflow_execution_reports (
          id, run_id, invocation_id, workflow_key, status, report_json, artifact_path, created_at
        )
        VALUES (?, ?, NULL, ?, ?, ?, NULL, '2026-05-24T00:00:00Z')
        """,
        (f"report-{run_id}", run_id, workflow_key, status, _report(stage_count, blockers)),
    )


def test_compare_workflow_returns_metrics() -> None:
    conn = _conn()
    _insert_report(conn, run_id="r1")
    _insert_report(conn, run_id="r2")
    _insert_report(conn, run_id="r3", status="failed", blockers=1)

    result = compare_workflow_effectiveness(
        conn,
        workflow_key="implementation-delivery",
        since="2026-04-01T00:00:00Z",
    )
    assert result.run_count == 3
    assert result.completed_count == 2
    assert result.failed_count == 1
    assert result.validation_pass_rate == pytest.approx(2 / 3)
    assert result.mean_blocker_count == pytest.approx(1 / 3)


def test_compare_normalizes_per_stage_blockers() -> None:
    conn = _conn()
    _insert_report(
        conn, run_id="r1", workflow_key="implementation-delivery", stage_count=4, blockers=1
    )
    _insert_report(conn, run_id="r2", workflow_key="academic_paper_v1", stage_count=7, blockers=2)

    implementation = compare_workflow_effectiveness(
        conn,
        workflow_key="implementation-delivery",
        since="2026-04-01T00:00:00Z",
    )
    academic = compare_workflow_effectiveness(
        conn,
        workflow_key="academic_paper_v1",
        since="2026-04-01T00:00:00Z",
    )
    assert implementation.mean_blocker_count == 1
    assert implementation.mean_blockers_per_stage == pytest.approx(0.25)
    assert academic.mean_blocker_count == 2
    assert academic.mean_blockers_per_stage == pytest.approx(2 / 7)


def test_compare_includes_writeback_usefulness() -> None:
    conn = _conn()
    _insert_report(conn, run_id="r1")
    conn.execute(
        """
        CREATE TABLE improvement_writebacks (
          id TEXT PRIMARY KEY,
          proposed_change_json TEXT NOT NULL DEFAULT '{}',
          status TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO improvement_writebacks VALUES ('w1', ?, 'approved')",
        (json.dumps({"workflow_key": "implementation-delivery"}),),
    )
    conn.execute(
        "INSERT INTO improvement_writebacks VALUES ('w2', ?, 'rejected')",
        (json.dumps({"workflow_key": "implementation-delivery"}),),
    )

    result = compare_workflow_effectiveness(
        conn,
        workflow_key="implementation-delivery",
        since="2026-04-01T00:00:00Z",
    )
    assert result.writeback_usefulness == 0.5


def test_propose_workflow_promotion_writes_writeback_with_workflow_default_scope() -> None:
    conn = _conn()
    evidence = _effectiveness()
    result = propose_workflow_promotion(
        conn,
        workflow_key="implementation-delivery",
        to_state="active",
        evidence=evidence,
        actor="op",
        rationale="enough evidence",
    )
    row = conn.execute(
        """
        SELECT layer_type, impact_scope, status, requires_approval
        FROM improvement_writebacks
        WHERE id = ?
        """,
        (result["writeback_id"],),
    ).fetchone()
    assert row == ("workflow", "workflow-default", "proposed", 1)


def test_propose_workflow_promotion_records_proposed_not_target_state() -> None:
    conn = _conn()
    result = propose_workflow_promotion(
        conn,
        workflow_key="implementation-delivery",
        to_state="active",
        evidence=_effectiveness(),
        actor="op",
        rationale="enough evidence",
    )
    status = conn.execute(
        "SELECT status FROM promotion_lifecycle_items WHERE id = ?",
        (result["lifecycle_id"],),
    ).fetchone()[0]
    assert status == "proposed"


def test_finalize_workflow_promotion_requires_approved_writeback() -> None:
    conn = _conn()
    proposal = propose_workflow_promotion(
        conn,
        workflow_key="implementation-delivery",
        to_state="active",
        evidence=_effectiveness(),
        actor="op",
        rationale="enough evidence",
    )
    with pytest.raises(ValueError, match="must be 'approved'"):
        finalize_workflow_promotion(
            conn,
            lifecycle_id=proposal["lifecycle_id"],
            approval_writeback_id=proposal["writeback_id"],
            actor="op",
        )
    conn.execute(
        "UPDATE improvement_writebacks SET status = 'approved' WHERE id = ?",
        (proposal["writeback_id"],),
    )
    finalized = finalize_workflow_promotion(
        conn,
        lifecycle_id=proposal["lifecycle_id"],
        approval_writeback_id=proposal["writeback_id"],
        actor="op",
    )
    assert finalized["previous_status"] == "proposed"
    assert finalized["new_status"] == "active"


def test_promote_active_requires_writeback() -> None:
    conn = sqlite3.connect(":memory:")
    transition = promote_asset(
        conn,
        asset_kind="workflow",
        asset_key="implementation-delivery",
        from_state="approved",
        to_state="active",
        actor="op",
        rationale="direct active promotion",
    )
    assert transition.requires_approval is True
    assert conn.execute("SELECT COUNT(*) FROM improvement_writebacks").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM promotion_lifecycle_items").fetchone()[0] == 1


def _effectiveness() -> WorkflowEffectiveness:
    return WorkflowEffectiveness(
        workflow_key="implementation-delivery",
        since="2026-04-01T00:00:00Z",
        run_count=3,
        completed_count=3,
        failed_count=0,
        rework_rate=0.0,
        validation_pass_rate=1.0,
        mean_blocker_count=0.0,
        mean_blockers_per_stage=0.0,
        writeback_usefulness=1.0,
        stage_evaluations={},
    )
