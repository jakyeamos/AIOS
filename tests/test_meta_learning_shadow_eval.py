from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.meta_learning_proposals import MetaLearningProposal  # noqa: E402
from services.meta_learning_shadow_eval import (  # noqa: E402
    REQUIRED_METRICS,
    generate_shadow_eval_plan,
    generate_shadow_eval_plans,
    promotion_gate,
    stable_eval_plan_id,
)


def _proposal(
    *,
    proposal_id: str = "meta-proposal-1",
    target_layer: str = "project",
    confidence_score: int = 6,
    risk_level: str = "medium",
) -> MetaLearningProposal:
    return MetaLearningProposal(
        proposal_id=proposal_id,
        title="Route explicit correction to project",
        summary="User correction: Always use pnpm in this repo.",
        target_layer=target_layer,
        target_file="AGENTS.md or project context packet after review",
        confidence_score=confidence_score,
        risk_level=risk_level,
        evidence=[{"session_id": "s1", "kind": "message:user", "summary": "Always use pnpm"}],
        why_this_layer="Project-specific evidence routes away from global rules.",
        proposed_patch="Review action: decide whether to add this narrowly.",
        rollback="Do not apply automatically.",
        requires_manual_approval=True,
        source_signal_id="meta-signal-1",
    )


def test_eval_plan_contains_required_comparison_metrics() -> None:
    plan = generate_shadow_eval_plan(_proposal())

    assert plan.plan_id == stable_eval_plan_id("meta-proposal-1")
    assert plan.impact_level == "medium"
    assert plan.required_for_durable_global_promotion is True
    assert set(plan.metrics) == set(REQUIRED_METRICS)
    assert "baseline" in plan.comparison.lower()
    assert "shadow" in plan.comparison.lower()


def test_global_or_high_risk_proposals_are_high_impact() -> None:
    global_plan = generate_shadow_eval_plan(_proposal(target_layer="global", risk_level="medium"))
    high_risk_plan = generate_shadow_eval_plan(_proposal(target_layer="project", risk_level="high"))

    assert global_plan.impact_level == "high"
    assert high_risk_plan.impact_level == "high"
    assert any("unrelated project" in task for task in global_plan.evaluation_tasks)


def test_low_impact_proposal_does_not_require_eval_plan() -> None:
    plan = generate_shadow_eval_plan(
        _proposal(target_layer="command", confidence_score=3, risk_level="low")
    )

    assert plan.impact_level == "low"
    assert plan.required_for_durable_global_promotion is False
    assert plan.ready_for_durable_global_promotion is True


def test_medium_high_impact_promotion_gate_needs_plan_or_exemption() -> None:
    proposal = _proposal(target_layer="global", confidence_score=8, risk_level="high")

    blocked = promotion_gate(proposal)
    plan = generate_shadow_eval_plan(proposal)
    ready_with_plan = promotion_gate(proposal, eval_plan=plan)
    ready_with_exemption = promotion_gate(
        proposal, exemption_reason="manual operator accepted risk"
    )

    assert blocked["ready_for_durable_global_promotion"] is False
    assert ready_with_plan["ready_for_durable_global_promotion"] is True
    assert ready_with_exemption["ready_for_durable_global_promotion"] is True


def test_batch_generation_includes_required_plans_and_exemptions() -> None:
    low = _proposal(proposal_id="low", target_layer="command", confidence_score=3, risk_level="low")
    medium = _proposal(proposal_id="medium", target_layer="project", confidence_score=6)

    plans = generate_shadow_eval_plans([low, medium], exemptions={"low": "documented exemption"})

    assert [plan.proposal_id for plan in plans] == ["low", "medium"]
    assert plans[0].exemption_reason == "documented exemption"
