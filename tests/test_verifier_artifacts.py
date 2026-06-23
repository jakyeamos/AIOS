from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services import verifier_artifacts  # noqa: E402


def test_missing_verifier_blocks_implementation_closeout() -> None:
    conn = sqlite3.connect(":memory:")

    result = verifier_artifacts.validate_closeout_verification(
        conn,
        task_id="run-1",
        run_id="run-1",
        session_id="session-1",
        workflow_key="implementation-delivery",
        implementation_bearing=True,
    )

    assert result["allowed"] is False
    assert result["code"] == "missing_verifier_artifact"
    assert result["recommended_next_phase"] == "human_review"


def test_pass_verifier_allows_closeout_with_evidence_refs() -> None:
    conn = sqlite3.connect(":memory:")
    verifier_artifacts.record_verifier_artifact(
        conn,
        task_id="run-1",
        run_id="run-1",
        session_id="session-1",
        verifier_agent="reviewer",
        model="gpt",
        inputs_reviewed=["task_spec", "changed_files", "evidence_artifacts"],
        checks_performed=["diff", "tests"],
        result="pass",
        evidence_refs=["evidence-artifact: ev-1 status=pass command=pytest"],
    )

    result = verifier_artifacts.validate_closeout_verification(
        conn,
        task_id="run-1",
        run_id="run-1",
        session_id="session-1",
        workflow_key="implementation-delivery",
        implementation_bearing=True,
    )

    assert result["allowed"] is True
    assert result["recommended_next_phase"] == "closeout"
    assert result["evidence_refs"]


def test_fail_and_needs_work_do_not_route_to_closeout() -> None:
    for verifier_result in ("fail", "needs_work"):
        conn = sqlite3.connect(":memory:")
        verifier_artifacts.record_verifier_artifact(
            conn,
            task_id="run-1",
            run_id="run-1",
            session_id="session-1",
            inputs_reviewed=["task_spec", "changed_files", "evidence_artifacts"],
            checks_performed=["diff"],
            result=verifier_result,  # type: ignore[arg-type]
            blocking_issues=[{"file": "services/example.py", "summary": "still broken"}],
            evidence_refs=["evidence-artifact: ev-1 status=fail command=pytest"],
        )

        result = verifier_artifacts.validate_closeout_verification(
            conn,
            task_id="run-1",
            run_id="run-1",
            session_id="session-1",
            workflow_key="implementation-delivery",
            implementation_bearing=True,
        )

        assert result["allowed"] is False
        assert result["recommended_next_phase"] in {"implementation_retry", "human_review"}


def test_stale_verifier_artifact_is_rejected_for_current_run() -> None:
    conn = sqlite3.connect(":memory:")
    verifier_artifacts.record_verifier_artifact(
        conn,
        task_id="old-run",
        run_id="old-run",
        session_id="old-session",
        inputs_reviewed=["task_spec", "changed_files", "evidence_artifacts"],
        checks_performed=["diff"],
        result="pass",
        evidence_refs=["evidence-artifact: ev-old status=pass command=pytest"],
    )

    result = verifier_artifacts.validate_closeout_verification(
        conn,
        task_id="new-run",
        run_id="new-run",
        session_id="new-session",
        workflow_key="implementation-delivery",
        implementation_bearing=True,
    )

    assert result["allowed"] is False
    assert result["code"] == "missing_verifier_artifact"


def test_pass_verifier_without_evidence_refs_is_invalid() -> None:
    conn = sqlite3.connect(":memory:")
    verifier_artifacts.record_verifier_artifact(
        conn,
        task_id="run-1",
        run_id="run-1",
        session_id="session-1",
        inputs_reviewed=["task_spec", "changed_files", "evidence_artifacts"],
        checks_performed=["diff"],
        result="pass",
        evidence_refs=[],
    )

    result = verifier_artifacts.validate_closeout_verification(
        conn,
        task_id="run-1",
        run_id="run-1",
        session_id="session-1",
        workflow_key="implementation-delivery",
        implementation_bearing=True,
    )

    assert result["allowed"] is False
    assert result["code"] == "invalid_verifier_artifact"
    assert "evidence_refs" in result["reason"]


def test_blocking_issues_must_cite_concrete_evidence() -> None:
    conn = sqlite3.connect(":memory:")
    verifier_artifacts.record_verifier_artifact(
        conn,
        task_id="run-1",
        run_id="run-1",
        session_id="session-1",
        inputs_reviewed=["task_spec", "changed_files", "evidence_artifacts"],
        checks_performed=["diff"],
        result="fail",
        blocking_issues=["bad"],
        evidence_refs=["evidence-artifact: ev-1 status=fail command=pytest"],
    )

    result = verifier_artifacts.validate_closeout_verification(
        conn,
        task_id="run-1",
        run_id="run-1",
        session_id="session-1",
        workflow_key="implementation-delivery",
        implementation_bearing=True,
    )

    assert result["allowed"] is False
    assert "blocking issues must cite" in result["reason"]


def test_exempt_workflow_requires_recorded_reason() -> None:
    conn = sqlite3.connect(":memory:")

    missing_reason = verifier_artifacts.validate_closeout_verification(
        conn,
        workflow_key="audit",
        implementation_bearing=True,
        verification_exempt=True,
    )
    with_reason = verifier_artifacts.validate_closeout_verification(
        conn,
        workflow_key="audit",
        implementation_bearing=True,
        verification_exempt=True,
        exemption_reason="read-only audit workflow",
    )

    assert missing_reason["allowed"] is False
    assert with_reason["allowed"] is True
    assert with_reason["code"] == "exempt"
