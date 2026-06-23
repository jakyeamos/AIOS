from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.execution_symmetric_planner import generate_execution_symmetric_plan  # noqa: E402


def test_simple_task_is_not_over_planned() -> None:
    plan = generate_execution_symmetric_plan(
        objective="Fix a typo in README",
        complexity="simple",
    )

    assert set(plan.sections) == {"objective", "safest_next_step", "validation"}
    assert "rollback_recovery" not in plan.sections
    assert "delegation_strategy" not in plan.sections


def test_moderate_natural_language_plan_has_executor_ready_sections() -> None:
    plan = generate_execution_symmetric_plan(
        objective="Create an implementation plan for a bounded API change",
        complexity="moderate",
        task_types=("api_change",),
    )

    for section in {
        "mission",
        "scope",
        "execution_constraints",
        "assumptions",
        "selected_planning_lenses",
        "affected_areas",
        "ordered_steps",
        "validation_strategy",
        "failure_modes",
        "rollback_recovery",
        "delegation_strategy",
        "escalation_conditions",
        "definition_of_done",
    }:
        assert section in plan.sections
    assert "interface-contracts" in plan.sections["selected_planning_lenses"]
    assert plan.workflow_context.workflow == "aios"


def test_explicit_planning_lens_request_supplements_automatic_lenses() -> None:
    plan = generate_execution_symmetric_plan(
        objective="Create a migration implementation plan",
        complexity="moderate",
        task_types=("api_change",),
        requested_lenses=("observability",),
    )

    assert "interface-contracts" in plan.sections["selected_planning_lenses"]
    assert "observability" in plan.sections["selected_planning_lenses"]


def test_audit_to_implementation_prompt_generates_execution_symmetric_plan() -> None:
    plan = generate_execution_symmetric_plan(
        objective="Turn the security audit findings into implementation fixes",
        complexity="complex",
        task_types=("security_sensitive_task",),
    )

    assert plan.workflow_context.source_invocation == "audit_to_implementation_prompt"
    assert plan.workflow_context.output_format == "audit_to_implementation_plan"
    assert "rollback_recovery" in plan.sections
    assert "validation_strategy" in plan.sections


def test_gsd_ready_plan_output_uses_detected_gsd_context() -> None:
    plan = generate_execution_symmetric_plan(
        objective="Plan Phase 20",
        source_text="/gsdplanphase 20",
        complexity="complex",
        task_types=("gsd_plan_phase",),
    )

    assert plan.workflow_context.workflow == "gsd"
    assert plan.workflow_context.phase == "plan"
    assert plan.workflow_context.output_format == "gsd_ready_plan"
    assert plan.sections["gsd_ready"] is True
    assert plan.sections["handoff_target"] == "gsd"
    assert "GSD-compatible artifacts" in " ".join(plan.sections["ordered_steps"])
    assert any("GSD phase" in item for item in plan.sections["definition_of_done"])


def test_high_risk_plan_includes_rollback_and_escalation() -> None:
    plan = generate_execution_symmetric_plan(
        objective="Plan a security-sensitive secret handling change",
        complexity="high_risk",
        task_types=("security_sensitive_task",),
        risk_level="high_risk",
        skill_requests=("security review principles",),
    )

    assert "threat-modeling" in plan.sections["selected_planning_lenses"]
    assert "secrets-safety" in plan.sections["selected_planning_lenses"]
    assert any("revert path" in item for item in plan.sections["rollback_recovery"])
    assert any("Rollback path" in item for item in plan.sections["escalation_conditions"])
    assert plan.sections["skill_planning_constraints"][0]["skill_key"] == "security_review_executor"
    assert "completed_work_review" in plan.sections["skill_planning_constraints"][0][
        "disallowed_outputs"
    ]


def test_unknown_complexity_is_rejected() -> None:
    try:
        generate_execution_symmetric_plan(
            objective="Plan something",
            complexity="huge",
        )
    except ValueError as exc:
        assert "Unknown planning complexity" in str(exc)
    else:
        raise AssertionError("Expected unknown complexity to fail")
