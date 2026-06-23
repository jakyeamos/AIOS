from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.planning_context import create_planning_context, with_execution_results  # noqa: E402


def test_create_planning_context_normalizes_required_fields() -> None:
    context = create_planning_context(
        source_invocation="natural_language",
        raw_invocation="Plan the billing API migration",
        workflow="aios",
        phase="planning",
        task_type="api_change",
        complexity="High-Risk",
        selected_lenses=("testing", "Testing", "rollback safety"),
    )

    payload = context.to_json()

    assert payload["complexity"] == "high_risk"
    assert payload["risk_level"] == "high_risk"
    assert payload["selected_lenses"] == ["testing", "rollback-safety"]
    assert payload["validation_depth"] == "full_with_independent_review"
    assert payload["sub_agent_strategy"] == "delegate_when_parallel_or_specialized"
    assert payload["model_strategy"] == "highest_reliable_reasoning"
    assert context.requires_tmcp_packet is True


def test_planning_context_allows_pending_execution_results() -> None:
    context = create_planning_context(
        source_invocation="slash_command",
        raw_invocation="/gsdplanphase 20",
        workflow="gsd",
        phase="plan",
        task_type="gsd_plan_phase",
        complexity="moderate",
        selected_lenses=("executor-readiness",),
        output_format="gsd_ready_plan",
    )

    payload = context.to_json()

    assert payload["execution_result"] is None
    assert payload["validation_result"] is None
    assert payload["rework_required"] is None


def test_planning_context_can_attach_execution_results_later() -> None:
    context = create_planning_context(
        source_invocation="natural_language",
        raw_invocation="Create a plan",
        workflow="aios",
        phase="planning",
        task_type="implementation_plan",
        complexity="moderate",
    )

    updated = with_execution_results(
        context,
        execution_result="completed",
        validation_result="passed",
        rework_required=False,
        notes=("No rework needed.",),
    )

    assert updated.execution_result == "completed"
    assert updated.validation_result == "passed"
    assert updated.rework_required is False
    assert updated.notes == ("No rework needed.",)
    assert context.execution_result is None
