# ruff: noqa: E402

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bin"))

from aios_orchestration_runtime import insert_writeback

from services.evidence_artifacts import record_evidence_artifact
from services.governed_effects import (
    authorize_effect,
    evaluate_governed_closeout,
    transition_writeback,
)
from services.verifier_artifacts import record_verifier_artifact


def _db(tmp_path: Path) -> sqlite3.Connection:
    path = tmp_path / "aios.db"
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
    conn.execute(
        "INSERT INTO projects (id, name, repo_path, obsidian_path, status) VALUES ('p1', 'AIOS', ?, '', 'active')",
        (str(ROOT),),
    )
    conn.execute(
        """
        INSERT INTO orchestration_runs (
          id, project_id, objective, workflow_key, agent_key, status, rationale,
          resume_snapshot_json
        )
        VALUES ('run-1', 'p1', 'M5 test', 'implementation-delivery', 'codex', 'partial', 'test', ?)
        """,
        (json.dumps({"next_recommended_action": "Review the governed closeout."}),),
    )
    conn.commit()
    return conn


def _verification(conn: sqlite3.Connection) -> dict[str, object]:
    record_evidence_artifact(
        conn,
        run_id="run-1",
        phase="verification",
        command="pytest -q",
        exit_code=0,
        output_hash="evidence-hash",
        status="pass",
    )
    record_verifier_artifact(
        conn,
        run_id="run-1",
        verifier_agent="test",
        inputs_reviewed=["task_spec", "changed_files", "evidence_artifacts"],
        checks_performed=["pytest"],
        result="pass",
        evidence_refs=["evidence-artifact: evidence-hash"],
    )
    return {"allowed": True, "code": "passed"}


def test_authorize_effect_blocks_capability_loopback_and_egress() -> None:
    assert authorize_effect(capability="unknown")["code"] == "capability_denied"
    assert authorize_effect(capability="run.closeout", origin="remote")["code"] == "loopback_required"
    assert authorize_effect(
        capability="run.closeout", egress_target="https://example.test"
    )["code"] == "egress_target_denied"
    assert authorize_effect(
        capability="run.closeout", egress_target="loopback", redaction_status="incomplete"
    )["code"] == "redaction_incomplete"


def test_writeback_transition_requires_governed_approval_and_is_terminal(tmp_path: Path) -> None:
    conn = _db(tmp_path)
    writeback_id = insert_writeback(
        conn,
        run_id="run-1",
        project_id="p1",
        layer_type="workflow",
        layer_key="implementation-delivery",
        title="Review workflow",
        summary="Requires review",
        evidence=["run-1"],
        impact_scope="workflow-default",
    )
    with pytest.raises(PermissionError, match="loopback-only"):
        transition_writeback(
            conn,
            writeback_id=writeback_id,
            to_status="approved",
            actor="remote",
            origin="remote",
        )
    assert conn.execute(
        "SELECT status FROM improvement_writebacks WHERE id = ?", (writeback_id,)
    ).fetchone()[0] == "pending_approval"
    transition_writeback(
        conn,
        writeback_id=writeback_id,
        to_status="approved",
        actor="operator",
        note="Reviewed locally.",
    )
    transition_writeback(
        conn,
        writeback_id=writeback_id,
        to_status="applied",
        actor="operator",
        note="Applied with rollback reference.",
        capability="writeback.apply",
        rollback_ref="backup:run-1",
    )
    assert conn.execute(
        "SELECT status FROM improvement_writebacks WHERE id = ?", (writeback_id,)
    ).fetchone()[0] == "applied"
    with pytest.raises(ValueError, match="terminal"):
        transition_writeback(
            conn,
            writeback_id=writeback_id,
            to_status="approved",
            actor="operator",
        )
    event_count = conn.execute(
        "SELECT COUNT(*) FROM governed_effect_events WHERE effect_id = ?", (writeback_id,)
    ).fetchone()[0]
    assert event_count == 3


def test_closeout_blocks_pending_approval_then_closes_after_approval(tmp_path: Path) -> None:
    conn = _db(tmp_path)
    writeback_id = insert_writeback(
        conn,
        run_id="run-1",
        project_id="p1",
        layer_type="workflow",
        layer_key="implementation-delivery",
        title="Review workflow",
        summary="Requires review",
        evidence=["run-1"],
        impact_scope="workflow-default",
    )
    blocked = evaluate_governed_closeout(
        conn,
        run_id="run-1",
        verification=_verification(conn),
    )
    assert blocked["allowed"] is False
    assert "approval_required" in blocked["blockers"]
    assert conn.execute("SELECT status FROM orchestration_runs WHERE id = 'run-1'").fetchone()[0] == "partial"

    transition_writeback(
        conn,
        writeback_id=writeback_id,
        to_status="approved",
        actor="operator",
        note="Approved after review.",
    )
    allowed = evaluate_governed_closeout(
        conn,
        run_id="run-1",
        verification={"allowed": True, "code": "passed"},
    )
    assert allowed["allowed"] is True
    assert allowed["status"] == "closed"
    assert allowed["changed_artifact_count"] == 1
