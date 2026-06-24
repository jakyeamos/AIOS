from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.expert_rubric_remediation import (  # noqa: E402
    AUDIT_REPORT_SCHEMA,
    REMEDIATION_PLAN_SCHEMA,
    RUBRIC_SCHEMA,
    build_audit_report,
    build_implementation_handoff,
    build_remediation_plan,
    synthesize_rubric,
    validate_audit_report,
    validate_remediation_plan,
    validate_rubric,
    write_review_artifacts,
)


def _visual_packet() -> dict[str, object]:
    return {
        "schema": "tmcp-runtime-packet-v0.1",
        "task_id": "visual_polish",
        "objective": "Review Soundscape UI polish and create a remediation plan",
        "project_path": "/tmp/soundscape-app",
        "selected_nodes": [
            "@task:visual_polish",
            "@module:saas_interaction_architecture",
            "@module:visual_polish_system",
            "@module:enterprise_saas_visual_polish",
            "@module:data_realism_polish",
        ],
        "skipped_nodes": [
            {"node": "@module:print_report_design", "reason": "No PDF/report export scope."}
        ],
        "behavior_atoms": ["ui_quality", "visual_verification"],
        "source_hashes": {},
        "candidate_scores": {},
        "traversal_fingerprint": "visual-fingerprint",
    }


def test_synthesize_rubric_preserves_tmcp_provenance() -> None:
    rubric = synthesize_rubric(
        packet=_visual_packet(),
        run_id="review-run-1",
        objective="Review Soundscape UI polish and create a remediation plan",
    )

    assert rubric["schema"] == RUBRIC_SCHEMA
    assert rubric["run_id"] == "review-run-1"
    assert len(rubric["dimensions"]) >= 5
    assert {dimension["id"] for dimension in rubric["dimensions"]} >= {
        "surface_hierarchy",
        "data_realism",
        "interaction_architecture",
    }
    assert all(dimension["source_nodes"] for dimension in rubric["dimensions"])
    assert validate_rubric(rubric)["passed"] is True


def test_validate_audit_report_rejects_finding_without_evidence() -> None:
    report = {
        "schema": AUDIT_REPORT_SCHEMA,
        "run_id": "review-run-1",
        "rubric": "rubric.json",
        "scores": [],
        "findings": [
            {
                "id": "finding-1",
                "severity": "blocker",
                "dimension_id": "data_realism",
                "summary": "Waveform bars are random during render.",
                "evidence": [],
                "recommended_fix": "Make waveform heights deterministic from stable input.",
            }
        ],
    }

    result = validate_audit_report(report)

    assert result["passed"] is False
    assert "finding-1 is missing evidence" in result["issues"]


def test_remediation_plan_requires_verification() -> None:
    plan = {
        "schema": REMEDIATION_PLAN_SCHEMA,
        "run_id": "review-run-1",
        "slices": [
            {
                "id": "slice-1",
                "title": "Stabilize feed waveform",
                "scope": ["packages/web/src/components/feed/FeedItem.tsx"],
                "rationale": "Random visual data undermines trust and can cause hydration drift.",
                "expected_impact": "Stable rating card rendering.",
                "risk": "Low; local UI rendering behavior.",
                "verification": [],
                "follow_up_workflow": "implementation-delivery",
            }
        ],
        "deferred_scope": [],
    }

    result = validate_remediation_plan(plan)

    assert result["passed"] is False
    assert "slice-1 is missing verification" in result["issues"]


def test_write_review_artifacts_creates_expected_files(tmp_path: Path) -> None:
    packet = _visual_packet()
    rubric = synthesize_rubric(
        packet=packet,
        run_id="review-run-1",
        objective=str(packet["objective"]),
    )
    audit = {
        "schema": AUDIT_REPORT_SCHEMA,
        "run_id": "review-run-1",
        "rubric": "rubric.json",
        "scores": [
            {
                "dimension_id": "data_realism",
                "score": 1,
                "confidence": "high",
                "evidence": ["packages/web/src/components/feed/FeedItem.tsx:427"],
                "gaps": [],
            }
        ],
        "findings": [
            {
                "id": "finding-data-realism-1",
                "severity": "blocker",
                "dimension_id": "data_realism",
                "summary": "Feed waveform uses Math.random during render.",
                "evidence": ["packages/web/src/components/feed/FeedItem.tsx:427"],
                "recommended_fix": "Derive waveform heights from stable rating data.",
            }
        ],
    }
    remediation = build_remediation_plan(audit_report=audit, run_id="review-run-1")

    paths = write_review_artifacts(
        output_dir=tmp_path,
        expertise_packet=packet,
        rubric=rubric,
        audit_report=audit,
        remediation_plan=remediation,
        implementation_handoff=None,
    )

    assert paths["expertise_packet"].name == "expertise-packet.json"
    assert paths["rubric_json"].exists()
    assert paths["rubric_markdown"].exists()
    assert paths["audit_report_json"].exists()
    assert paths["remediation_plan_markdown"].exists()
    assert json.loads(paths["rubric_json"].read_text(encoding="utf-8"))["schema"] == RUBRIC_SCHEMA


def test_soundscape_fixture_builds_evidence_backed_audit_and_plan() -> None:
    fixture_path = (
        ROOT
        / "tests"
        / "fixtures"
        / "expert-rubric-remediation"
        / "soundscape-visual-polish-evidence.json"
    )
    evidence_items = json.loads(fixture_path.read_text(encoding="utf-8"))
    packet = _visual_packet()
    rubric = synthesize_rubric(
        packet=packet,
        run_id="soundscape-review",
        objective=str(packet["objective"]),
    )

    audit = build_audit_report(
        rubric=rubric,
        evidence_items=evidence_items,
        run_id="soundscape-review",
    )
    remediation = build_remediation_plan(audit_report=audit, run_id="soundscape-review")
    handoff = build_implementation_handoff(
        remediation_plan=remediation,
        run_id="soundscape-review",
        selected_slice_id="slice-1",
    )

    assert validate_audit_report(audit)["passed"] is True
    assert validate_remediation_plan(remediation)["passed"] is True
    assert audit["findings"][0]["evidence"] == ["packages/web/src/components/feed/FeedItem.tsx:427"]
    assert remediation["slices"][0]["follow_up_workflow"] == "implementation-delivery"
    assert handoff["selected_slice_id"] == "slice-1"
    assert handoff["requires_user_approval"] is True
    assert handoff["artifact_inputs"] == [
        "expertise-packet.json",
        "rubric.json",
        "audit-report.json",
        "remediation-plan.json",
    ]
