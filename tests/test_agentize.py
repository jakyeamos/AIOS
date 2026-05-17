from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.agentize import (  # noqa: E402
    AgentizedTaskPacket,
    TaskClassification,
    agentize_request,
    ensure_agentize_schema,
    record_agentize_evaluation,
)
from services.workflow_orchestration import (  # noqa: E402
    WorkflowExecutionContext,
    execute_workflow,
    load_skill_registry,
    load_workflow_registry,
    validate_workflow_bindings,
)


def test_basic_transformation_returns_structured_packet() -> None:
    packet = agentize_request("Clean up this repo and make the workflow docs easier to trust.")

    assert isinstance(packet, AgentizedTaskPacket)
    assert packet.original_request == "Clean up this repo and make the workflow docs easier to trust."
    assert packet.normalized_objective == "Clean up this repo and make the workflow docs easier to trust."
    assert packet.task_classifications
    assert packet.execution_mode.reasoning
    assert packet.output_contract.summary_required is True
    assert "original_request" in packet.to_json()


def test_task_classification_covers_core_request_families() -> None:
    cases = {
        "audit this feature for security risk": TaskClassification.AUDIT,
        "implement this PRD": TaskClassification.IMPLEMENT,
        "audit and then fix the failing route": TaskClassification.DEBUG,
        "make this UI better": TaskClassification.UI_UX_IMPROVEMENT,
        "write tests for the parser": TaskClassification.TEST_GENERATION,
        "refactor this without breaking behavior": TaskClassification.REFACTOR,
        "research this library": TaskClassification.RESEARCH,
        "turn this idea into a plan": TaskClassification.PLANNING,
    }

    for request, expected in cases.items():
        packet = agentize_request(request)
        assert expected in packet.task_classifications


def test_execution_mode_selection_uses_request_risk_and_complexity() -> None:
    assert agentize_request("rename this one variable").execution_mode.mode == "single_agent_execution"
    assert (
        agentize_request("audit the whole repo architecture and implement the migration").execution_mode.mode
        == "sub_agent_driven_development"
    )
    assert (
        agentize_request("change the authentication architecture and security policy").execution_mode.mode
        == "approval_gated_mode"
    )
    assert agentize_request("write tests first for this parser feature").execution_mode.mode == "tdd_first_implementation"


def test_context_plan_is_targeted_and_includes_truth_and_success_criteria_when_relevant() -> None:
    packet = agentize_request("implement this AIOS workflow change with project truth updates")
    paths = [item.path for item in packet.required_context]

    assert "PROJECT.md" in paths
    assert "AGENTS.md" in paths
    assert "spec/success-criteria/index.md" in paths
    assert all(item.reason for item in packet.required_context)
    assert not any(item.path == "." for item in packet.required_context)


def test_standards_attachment_matches_task_family() -> None:
    security = agentize_request("audit auth token handling for security bugs")
    ui = agentize_request("make this UI better and easier to scan")
    refactor = agentize_request("refactor this service without changing behavior")

    assert "security" in security.relevant_standards
    assert {"ui_polish", "accessibility"} <= set(ui.relevant_standards)
    assert {"maintainability", "testing", "preserve_existing_behavior"} <= set(refactor.relevant_standards)


def test_verification_plan_matches_execution_risk() -> None:
    implementation = agentize_request("implement the feature and update docs")
    audit = agentize_request("audit the feature only")
    risky = agentize_request("migrate authentication and database schema")

    assert {"unit_tests", "lint", "typecheck", "build"} <= {
        step.kind for step in implementation.verification_plan
    }
    assert {"evidence_review", "recommendation_review"} <= {step.kind for step in audit.verification_plan}
    assert "rollback_plan" in {step.kind for step in risky.verification_plan}


def test_prompt_library_is_evidence_not_required_static_mapping() -> None:
    packet = agentize_request("clean up this repo")

    assert packet.prompt_pattern_evidence
    assert packet.prompt_library_role == "supporting_pattern_corpus"
    assert packet.experiment_metadata["requires_static_template_mapping"] is False


def test_agentize_evaluation_records_outcome_without_promoting_learning() -> None:
    conn = sqlite3.connect(":memory:")
    ensure_agentize_schema(conn)
    packet = agentize_request("write tests for the workflow router")

    record = record_agentize_evaluation(
        conn,
        packet=packet,
        outcome_quality=4,
        tests_passed=True,
        user_correction=None,
        follow_up_required=False,
        major_repair_required=False,
    )

    assert record["packet_id"] == packet.packet_id
    row = conn.execute(
        "SELECT selected_execution_mode, outcome_quality, tests_passed FROM agentize_evaluations"
    ).fetchone()
    assert row == ("tdd_first_implementation", 4, 1)


def test_agentize_workflow_and_skill_registry_bindings_are_valid() -> None:
    workflows = load_workflow_registry(ROOT / "config" / "workflows" / "registry.json")
    skills = load_skill_registry(ROOT / "config" / "workflows" / "skills.json")

    assert "agentize" in workflows
    assert "agentize_intent_compiler" in skills
    assert validate_workflow_bindings(workflows, skills) == []


def test_agentize_workflow_executes_and_emits_packet_artifact() -> None:
    report = execute_workflow(
        WorkflowExecutionContext(
            objective="Agentize this request: audit the workflow router and propose tests",
            workflow_key="agentize",
        )
    )

    packet = report["artifacts"]["agentized_task_packet"]

    assert report["status"] == "completed"
    assert packet["prompt_library_role"] == "supporting_pattern_corpus"
    assert packet["execution_mode"]["reasoning"]
    assert packet["verification_plan"]
