from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.workflow_orchestration import (  # noqa: E402
    _reset_validation_caches,
    load_skill_registry,
    load_workflow_registry,
    recommend_workflow_from_health,
    validate_workflow_bindings,
)

PLANNED_WORKFLOWS = {
    "audit-only",
    "audit-and-implement",
    "standards-backfill",
    "security-review",
}
PLANNED_SKILLS = {
    "audit_only_executor",
    "audit_and_implement_executor",
    "standards_backfill_executor",
    "security_review_executor",
}


def _registries():
    _reset_validation_caches()
    workflows = load_workflow_registry(ROOT / "config" / "workflows" / "registry.json")
    skills = load_skill_registry(ROOT / "config" / "workflows" / "skills.json")
    return workflows, skills


def test_audit_only_workflow_loads_and_validates() -> None:
    workflows, skills = _registries()
    workflow = workflows["audit-only"]

    assert workflow.lifecycle_state == "candidate"
    assert workflow.applicability
    assert len(workflow.stages) >= 3
    assert any(stage.validations for stage in workflow.stages)
    assert any(stage.prompt_bindings for stage in workflow.stages)
    assert validate_workflow_bindings({"audit-only": workflow}, skills) == []


def test_audit_and_implement_workflow_loads_and_validates() -> None:
    workflows, skills = _registries()
    workflow = workflows["audit-and-implement"]
    implementation = next(stage for stage in workflow.stages if stage.key == "implementation")

    assert workflow.lifecycle_state == "candidate"
    assert implementation.approval_gates[0].impact_scope == "workflow-default"
    assert implementation.approval_gates[0].condition == "on_failure"
    assert validate_workflow_bindings({"audit-and-implement": workflow}, skills) == []


def test_standards_backfill_workflow_loads_and_validates() -> None:
    workflows, skills = _registries()
    workflow = workflows["standards-backfill"]

    assert workflow.lifecycle_state == "candidate"
    assert any(stage.standards_bindings for stage in workflow.stages)
    assert validate_workflow_bindings({"standards-backfill": workflow}, skills) == []


def test_security_review_workflow_loads_and_validates() -> None:
    workflows, skills = _registries()
    workflow = workflows["security-review"]
    criterion_ids = {
        validation.criterion_id for stage in workflow.stages for validation in stage.validations
    }

    assert workflow.lifecycle_state == "candidate"
    assert "security-review" in criterion_ids
    assert validate_workflow_bindings({"security-review": workflow}, skills) == []


def test_all_four_executor_skills_resolve() -> None:
    _workflows, skills = _registries()

    assert PLANNED_SKILLS <= set(skills)
    assert all(skills[key].lifecycle_state == "draft" for key in PLANNED_SKILLS)


def test_validate_workflow_bindings_passes_for_full_registry_post_plan_05() -> None:
    workflows, skills = _registries()

    assert PLANNED_WORKFLOWS <= set(workflows)
    assert validate_workflow_bindings(workflows, skills) == []


def test_new_workflows_are_candidate_not_active() -> None:
    workflows, _skills = _registries()

    assert all(workflows[key].lifecycle_state == "candidate" for key in PLANNED_WORKFLOWS)


def test_health_recommendations_resolve_planned_workflows_in_registry() -> None:
    recommendations = recommend_workflow_from_health(
        delta_items=[
            {"domain": "security", "status": "fail", "priority_score": 8},
            {"domain": "code_quality", "status": "fail", "priority_bucket": "foundational"},
        ],
        workflow_registry_path=ROOT / "config" / "workflows" / "registry.json",
    )
    by_key = {row["workflow_key"]: row for row in recommendations}

    assert by_key["security-review"]["available_in_registry"] is True
    assert by_key["standards-backfill"]["available_in_registry"] is True
