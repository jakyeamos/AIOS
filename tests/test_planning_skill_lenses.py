from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.planning_skill_lenses import (  # noqa: E402
    build_skill_planning_lens,
    select_skill_planning_lenses,
)


def test_testing_skill_request_translates_to_planning_constraints() -> None:
    selection = select_skill_planning_lenses(("use testing principles during planning",))

    assert len(selection.lenses) == 1
    lens = selection.lenses[0]
    assert lens.skill_key == "structure_checker"
    assert "planning_constraints" in lens.output_expectations
    assert "section_presence_check" in lens.validation_gates
    assert any("Preserve skill invariant" in constraint for constraint in lens.constraints)


def test_security_review_skill_translates_to_risk_controls() -> None:
    selection = select_skill_planning_lenses(
        ("use security review principles before creating the implementation plan",)
    )

    assert len(selection.lenses) == 1
    lens = selection.lenses[0]
    assert lens.skill_key == "security_review_executor"
    assert "risk_controls" in lens.output_expectations
    assert "threat_model_check" in lens.validation_gates
    assert "secret_leak_check" in lens.validation_gates
    assert any("Plan mitigation" in constraint for constraint in lens.constraints)


def test_planning_mode_does_not_produce_completed_work_review_output() -> None:
    lens = build_skill_planning_lens("security_review_executor")

    assert lens.planning_mode_only is True
    assert "completed_work_review" in lens.disallowed_outputs
    assert "final_review_findings" in lens.disallowed_outputs
    assert "pass_fail_claim" in lens.disallowed_outputs
    assert "implementation_output" in lens.disallowed_outputs


def test_direct_skill_key_request_is_supported() -> None:
    selection = select_skill_planning_lenses(("scope_check",))

    assert len(selection.lenses) == 1
    assert selection.lenses[0].skill_key == "scope_check"
    assert "scope_constraints" in selection.lenses[0].output_expectations


def test_unknown_skill_request_is_reported() -> None:
    selection = select_skill_planning_lenses(("use nonexistent review magic",))

    assert selection.lenses == ()
    assert selection.unknown_requests == ("use nonexistent review magic",)
