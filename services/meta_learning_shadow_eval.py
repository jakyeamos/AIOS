from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from typing import Any, Literal

from services.meta_learning_proposals import MetaLearningProposal

ImpactLevel = Literal["low", "medium", "high"]

REQUIRED_METRICS = (
    "task_completion_quality",
    "user_correction_count",
    "token_usage",
    "tool_call_count",
    "wall_clock_proxy",
    "test_pass_fail",
    "context_loaded",
    "model_used",
    "user_intent_restatement_count",
)


@dataclass(frozen=True)
class ShadowEvalPlan:
    plan_id: str
    proposal_id: str
    impact_level: ImpactLevel
    baseline_condition: str
    shadow_condition: str
    metrics: list[str]
    required_for_durable_global_promotion: bool
    ready_for_durable_global_promotion: bool
    exemption_reason: str | None
    evaluation_tasks: list[str]
    comparison: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def generate_shadow_eval_plan(
    proposal: MetaLearningProposal,
    *,
    exemption_reason: str | None = None,
) -> ShadowEvalPlan:
    impact_level = proposal_impact_level(proposal)
    required = requires_shadow_eval(proposal)
    plan_id = stable_eval_plan_id(proposal.proposal_id)
    return ShadowEvalPlan(
        plan_id=plan_id,
        proposal_id=proposal.proposal_id,
        impact_level=impact_level,
        baseline_condition="Run representative task(s) without applying the proposed rule.",
        shadow_condition="Run the same task(s) in a shadow branch or isolated prompt with the proposed rule applied.",
        metrics=list(REQUIRED_METRICS),
        required_for_durable_global_promotion=required,
        ready_for_durable_global_promotion=not required or bool(exemption_reason),
        exemption_reason=exemption_reason,
        evaluation_tasks=_evaluation_tasks(proposal),
        comparison="Compare baseline behavior against shadow behavior before durable promotion.",
    )


def generate_shadow_eval_plans(
    proposals: Iterable[MetaLearningProposal],
    *,
    exemptions: dict[str, str] | None = None,
) -> list[ShadowEvalPlan]:
    exemption_map = exemptions or {}
    return [
        generate_shadow_eval_plan(
            proposal,
            exemption_reason=exemption_map.get(proposal.proposal_id),
        )
        for proposal in proposals
        if requires_shadow_eval(proposal) or proposal.proposal_id in exemption_map
    ]


def plans_to_dicts(plans: Iterable[ShadowEvalPlan]) -> list[dict[str, Any]]:
    return [plan.to_dict() for plan in plans]


def requires_shadow_eval(proposal: MetaLearningProposal) -> bool:
    return proposal_impact_level(proposal) in {"medium", "high"}


def proposal_impact_level(proposal: MetaLearningProposal) -> ImpactLevel:
    if proposal.target_layer == "global" or proposal.risk_level == "high":
        return "high"
    if proposal.target_layer in {"agent", "skill", "project"} or proposal.confidence_score >= 5:
        return "medium"
    return "low"


def promotion_gate(
    proposal: MetaLearningProposal,
    *,
    eval_plan: ShadowEvalPlan | None = None,
    exemption_reason: str | None = None,
) -> dict[str, Any]:
    required = requires_shadow_eval(proposal)
    ready = not required or eval_plan is not None or bool(exemption_reason)
    return {
        "proposal_id": proposal.proposal_id,
        "requires_eval_plan": required,
        "ready_for_durable_global_promotion": ready,
        "eval_plan_id": eval_plan.plan_id if eval_plan else None,
        "exemption_reason": exemption_reason,
    }


def stable_eval_plan_id(proposal_id: str) -> str:
    digest = hashlib.sha256(json.dumps({"proposal_id": proposal_id}, sort_keys=True).encode("utf-8"))
    return f"meta-eval-{digest.hexdigest()[:16]}"


def _evaluation_tasks(proposal: MetaLearningProposal) -> list[str]:
    tasks = [
        f"Re-run a task that previously produced signal {proposal.source_signal_id}.",
        "Measure baseline task completion without the proposed learning.",
        "Measure shadow task completion with the proposed learning applied in isolation.",
    ]
    if proposal.target_layer == "global":
        tasks.append("Include at least one unrelated project task to detect over-broad global behavior.")
    if proposal.target_layer in {"agent", "skill"}:
        tasks.append("Include one task where the target agent/skill should not trigger.")
    return tasks
