from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from quality_evidence_contract import (  # noqa: E402
    QUALITY_FINDING_SCHEMA,
    normalize_quality_finding,
    quality_finding_counts,
    validate_quality_finding,
)

from services import success_criteria  # noqa: E402


def test_normalize_quality_finding_preserves_legacy_text_evidence() -> None:
    finding = normalize_quality_finding(
        criterion_id="testing-trust",
        criterion_title="Testing Trust",
        criterion_scope="global",
        level="blocker",
        summary="Missing behavior proof.",
        evidence=["tests/test_example.py"],
        metadata={"risk": "regression"},
        source="unit-test",
    )

    assert finding["schema"] == QUALITY_FINDING_SCHEMA
    assert finding["blocking"] is True
    assert finding["evidence_text"] == ["tests/test_example.py"]
    assert finding["evidence"][0]["summary"] == "tests/test_example.py"
    assert validate_quality_finding(finding)["passed"] is True


def test_quality_finding_counts_treats_error_as_blocker() -> None:
    findings = [
        normalize_quality_finding(
            criterion_id="a",
            level="pass",
            summary="ok",
        ),
        normalize_quality_finding(
            criterion_id="b",
            level="warning",
            summary="warn",
        ),
        normalize_quality_finding(
            criterion_id="c",
            level="critical",
            summary="critical",
        ),
    ]

    assert quality_finding_counts(findings) == {"pass": 1, "warning": 1, "blocker": 1}


def test_success_criteria_stage_findings_include_quality_contract() -> None:
    criterion = success_criteria.CriterionRecord(
        id="testing-trust",
        title="Testing Trust",
        scope="global",
        blocking=True,
        applies_when={},
        path="spec/success-criteria/testing-trust.md",
        related=[],
        evaluation_method="heuristic",
        stage_applicability=("validate",),
    )
    context = success_criteria.infer_context(
        objective="Update critical behavior",
        prompt_classifications=["implement"],
        changed_files=["services/example.py"],
        skills=[],
    )
    context["execution_evidence"] = []
    context["test_evidence"] = []

    findings = success_criteria.evaluate_stage_findings(
        criteria=[criterion],
        context=context,
        stage_key="validate",
        stage_kind="validate",
        run_state={},
    )

    assert findings[0]["quality_contract"]["schema"] == QUALITY_FINDING_SCHEMA
    assert findings[0]["quality_contract"]["criterion_id"] == "testing-trust"
    assert findings[0]["evidence"] == ["services/example.py"]


def test_success_criteria_evaluation_artifact_includes_quality_contract(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    original_artifacts_dir = success_criteria.ARTIFACTS_DIR
    success_criteria.ARTIFACTS_DIR = tmp_path
    try:
        finding = success_criteria.CriterionFinding(
            criterion_id="truth-file-consistency",
            criterion_title="Truth File Consistency",
            criterion_scope="global",
            level="warning",
            summary="Truth file needs update.",
            evidence=["PROJECT.md"],
            metadata={},
        )
        evaluation_id = success_criteria.record_evaluation(
            conn,
            project_id=None,
            run_id=None,
            session_id=None,
            packet_id=None,
            objective="Update docs",
            task_id=None,
            trigger_kind="unit-test",
            context={"changed_files": ["PROJECT.md"]},
            findings=[finding],
        )
    finally:
        success_criteria.ARTIFACTS_DIR = original_artifacts_dir

    payload = json.loads((tmp_path / f"{evaluation_id}.json").read_text(encoding="utf-8"))
    assert payload["findings"][0]["quality_contract"]["schema"] == QUALITY_FINDING_SCHEMA
