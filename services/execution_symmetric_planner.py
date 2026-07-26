from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from services.planning_lenses import PlanningLens, select_planning_lenses
from services.planning_skill_lenses import SkillPlanningLens, select_skill_planning_lenses
from services.planning_workflow_detection import (
    PlanningWorkflowDetection,
    detect_planning_workflow,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COMPLEXITY_POLICY = ROOT / "config" / "planning" / "execution-symmetric-planning.json"


@dataclass(frozen=True)
class ExecutionSymmetricPlan:
    objective: str
    complexity: str
    workflow_context: PlanningWorkflowDetection
    selected_lenses: tuple[PlanningLens, ...]
    skill_lenses: tuple[SkillPlanningLens, ...]
    sections: dict[str, Any]

    def to_json(self) -> dict[str, Any]:
        return {
            "objective": self.objective,
            "complexity": self.complexity,
            "workflow_context": self.workflow_context.to_json(),
            "selected_lenses": [lens.to_json() for lens in self.selected_lenses],
            "skill_lenses": [lens.to_json() for lens in self.skill_lenses],
            "sections": self.sections,
        }


def generate_execution_symmetric_plan(
    *,
    objective: str,
    complexity: str,
    task_types: tuple[str, ...] = (),
    risk_level: str | None = None,
    requested_lenses: tuple[str, ...] = (),
    skill_requests: tuple[str, ...] = (),
    source_text: str | None = None,
    complexity_policy_path: Path | None = None,
) -> ExecutionSymmetricPlan:
    policy = _load_complexity_policy(complexity_policy_path)
    normalized_complexity = _normalize_complexity(complexity)
    if normalized_complexity not in _complexity_levels(policy):
        raise ValueError(f"Unknown planning complexity: {complexity}")

    workflow_context = detect_planning_workflow(source_text or objective)
    lens_selection = select_planning_lenses(
        task_types=task_types,
        workflow=workflow_context.workflow,
        phase=workflow_context.phase,
        risk_level=risk_level or normalized_complexity,
        requested_lenses=requested_lenses,
    )
    skill_selection = select_skill_planning_lenses(skill_requests) if skill_requests else None
    skill_lenses = skill_selection.lenses if skill_selection else ()

    if normalized_complexity in {"trivial", "simple"}:
        sections = _simple_sections(objective)
    else:
        sections = _full_sections(
            objective=objective,
            complexity=normalized_complexity,
            workflow_context=workflow_context,
            lenses=lens_selection.lenses,
            skill_lenses=skill_lenses,
            policy=policy,
        )

    return ExecutionSymmetricPlan(
        objective=objective,
        complexity=normalized_complexity,
        workflow_context=workflow_context,
        selected_lenses=lens_selection.lenses,
        skill_lenses=skill_lenses,
        sections=sections,
    )


def _load_complexity_policy(path: Path | None = None) -> dict[str, Any]:
    policy_path = path or DEFAULT_COMPLEXITY_POLICY
    with policy_path.open(encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, dict):
        raise ValueError("Execution-symmetric planning policy must be a JSON object.")
    if not _complexity_levels(loaded):
        raise ValueError("Execution-symmetric planning policy must define complexity_levels.")
    return loaded


def _complexity_levels(policy: dict[str, Any]) -> dict[str, Any]:
    levels = policy.get("complexity_levels", {})
    return levels if isinstance(levels, dict) else {}


def _normalize_complexity(value: str) -> str:
    return value.strip().lower().replace("-", "_")


def _simple_sections(objective: str) -> dict[str, Any]:
    return {
        "objective": objective,
        "safest_next_step": "Make the smallest scoped change or response that satisfies the objective.",
        "validation": "Verify the direct result with the narrowest relevant check.",
    }


def _full_sections(
    *,
    objective: str,
    complexity: str,
    workflow_context: PlanningWorkflowDetection,
    lenses: tuple[PlanningLens, ...],
    skill_lenses: tuple[SkillPlanningLens, ...],
    policy: dict[str, Any],
) -> dict[str, Any]:
    is_gsd_ready = workflow_context.output_format.startswith("gsd_ready")
    lens_keys = [lens.key for lens in lenses]
    skill_constraints = [
        constraint for skill_lens in skill_lenses for constraint in skill_lens.constraints
    ]
    required_sections = _complexity_levels(policy)[complexity].get("required_sections", [])
    sections: dict[str, Any] = {
        "mission": objective,
        "scope": _scope(workflow_context, is_gsd_ready),
        "execution_constraints": _constraints(lenses, skill_constraints),
        "assumptions": [
            "The objective text is the source of task intent until a narrower artifact overrides it.",
            "Existing GSD and slash command behavior must be preserved.",
        ],
        "selected_planning_lenses": lens_keys,
        "affected_areas": _affected_areas(workflow_context, lens_keys),
        "ordered_steps": _ordered_steps(is_gsd_ready, bool(skill_lenses)),
        "validation_strategy": _validation_strategy(lenses, skill_lenses),
        "failure_modes": _failure_modes(lenses, skill_lenses),
        "rollback_recovery": _rollback_recovery(complexity, lens_keys),
        "delegation_strategy": _delegation_strategy(complexity, workflow_context),
        "escalation_conditions": _escalation_conditions(complexity),
        "definition_of_done": _definition_of_done(is_gsd_ready),
        "required_policy_sections": required_sections,
        "output_format": workflow_context.output_format,
    }
    if skill_lenses:
        sections["skill_planning_constraints"] = [
            {
                "skill_key": lens.skill_key,
                "planning_behavior": lens.planning_behavior,
                "validation_gates": list(lens.validation_gates),
                "reviewable_artifacts": list(lens.reviewable_artifacts),
                "disallowed_outputs": list(lens.disallowed_outputs),
            }
            for lens in skill_lenses
        ]
    if is_gsd_ready:
        sections["gsd_ready"] = True
        sections["handoff_target"] = workflow_context.handoff_target
        sections["planning_quality_contract"] = _planning_quality_contract(lenses)
        sections["acceptance_criteria_contract"] = _acceptance_criteria_contract()
        sections["evidence_contract"] = _evidence_contract(lenses)
        sections["verification_handoff"] = _verification_handoff(workflow_context)
    return sections


def _scope(workflow_context: PlanningWorkflowDetection, is_gsd_ready: bool) -> list[str]:
    scope = [
        f"Workflow: {workflow_context.workflow}",
        f"Phase: {workflow_context.phase}",
        "Generate a plan only; do not implement while planning.",
    ]
    if is_gsd_ready:
        scope.append("Keep output compatible with GSD phase artifacts and execution.")
    return scope


def _constraints(lenses: tuple[PlanningLens, ...], skill_constraints: list[str]) -> list[str]:
    constraints = [lens.purpose for lens in lenses if lens.purpose]
    constraints.extend(skill_constraints)
    return constraints or ["Preserve user intent and existing project constraints."]


def _affected_areas(workflow_context: PlanningWorkflowDetection, lens_keys: list[str]) -> list[str]:
    areas = [workflow_context.workflow, workflow_context.phase]
    areas.extend(lens_keys[:6])
    return list(dict.fromkeys(item for item in areas if item and item != "unknown"))


def _ordered_steps(is_gsd_ready: bool, has_skill_lenses: bool) -> list[str]:
    steps = [
        "Confirm scope, non-scope, assumptions, and affected files or artifacts.",
        "Map selected planning lenses to concrete plan constraints.",
        "Write ordered implementation tasks with validation attached to each task.",
        "Run or record the validation strategy before claiming completion.",
    ]
    if has_skill_lenses:
        steps.insert(2, "Convert selected skill principles into planning constraints.")
    if is_gsd_ready:
        steps.append(
            "Write GSD-compatible artifacts and update phase state only after verification."
        )
    return steps


def _validation_strategy(
    lenses: tuple[PlanningLens, ...], skill_lenses: tuple[SkillPlanningLens, ...]
) -> list[str]:
    gates = ["Run the narrowest automated checks that cover changed behavior."]
    for lens in lenses:
        if "validation" in lens.key or lens.key in {"testing", "regression-safety"}:
            gates.append(f"Validate lens `{lens.key}` with concrete command or evidence.")
    for skill_lens in skill_lenses:
        gates.extend(
            f"Skill gate `{gate}` must be planned." for gate in skill_lens.validation_gates
        )
    return list(dict.fromkeys(gates))


def _failure_modes(
    lenses: tuple[PlanningLens, ...], skill_lenses: tuple[SkillPlanningLens, ...]
) -> list[str]:
    modes = [
        "Plan omits a required constraint or selected lens.",
        "Validation evidence is too narrow for the changed behavior.",
    ]
    if any(lens.key in {"security", "threat-modeling", "secrets-safety"} for lens in lenses):
        modes.append(
            "Security-sensitive behavior changes without threat or secret handling review."
        )
    for skill_lens in skill_lenses:
        modes.extend(skill_lens.source_failure_conditions)
    return list(dict.fromkeys(modes))


def _rollback_recovery(complexity: str, lens_keys: list[str]) -> list[str]:
    if complexity == "high_risk" or "rollback-safety" in lens_keys:
        return [
            "Define the exact revert path before implementation.",
            "Record owner/action for recovery if validation or review fails.",
        ]
    return ["Revert the scoped diff or supersede the generated artifact if validation fails."]


def _delegation_strategy(complexity: str, workflow_context: PlanningWorkflowDetection) -> list[str]:
    if complexity in {"complex", "high_risk"}:
        return [
            "Use explicit executor/reviewer roles when work crosses files, layers, or risk domains.",
            f"Preserve workflow handoff target `{workflow_context.handoff_target}`.",
        ]
    return ["Inline execution is acceptable unless scope expands."]


def _escalation_conditions(complexity: str) -> list[str]:
    conditions = [
        "Required context or acceptance criteria are missing.",
        "Validation cannot be run or produces ambiguous evidence.",
    ]
    if complexity == "high_risk":
        conditions.extend(
            [
                "Security, privacy, data, deployment, or governance risk is unresolved.",
                "Rollback path is not explicit before implementation.",
            ]
        )
    return conditions


def _definition_of_done(is_gsd_ready: bool) -> list[str]:
    done = [
        "All planned artifacts exist or are explicitly marked not applicable.",
        "Validation strategy has passing evidence or accepted blockers.",
        "Follow-up, rollback, or handoff notes are recorded when needed.",
    ]
    if is_gsd_ready:
        done.append("GSD phase summary/state updates reflect the completed plan.")
    return done


def _planning_quality_contract(lenses: tuple[PlanningLens, ...]) -> list[str]:
    standards = [
        ref
        for lens in lenses
        for ref in lens.standard_refs
        if ref.startswith("global.") or "." in ref
    ]
    return [
        "Surface standards before execution starts; do not defer quality constraints to closeout.",
        "Keep the plan scoped to the requested GSD planning artifact and explicit non-goals.",
        "Selected standards: " + ", ".join(dict.fromkeys(standards[:8]))
        if standards
        else "Selected standards: none recorded.",
    ]


def _acceptance_criteria_contract() -> list[str]:
    return [
        "Every planned task must carry acceptance criteria that would fail if the behavior regresses.",
        "Acceptance criteria must name the command, file check, or evidence artifact that proves completion.",
        "Planning output must keep blockers and accepted tradeoffs visible rather than folding them into success claims.",
    ]


def _evidence_contract(lenses: tuple[PlanningLens, ...]) -> list[str]:
    lens_keys = ", ".join(lens.key for lens in lenses[:8]) or "none"
    return [
        f"Evidence must cover selected planning lenses: {lens_keys}.",
        "Record validation commands and expected artifacts before implementation work starts.",
        "Preserve route, packet, and summary evidence for later verification.",
    ]


def _verification_handoff(workflow_context: PlanningWorkflowDetection) -> list[str]:
    return [
        f"Hand off to `{workflow_context.handoff_target}` only after the plan lists verification commands.",
        "Verifier must check actual artifacts and command results, not just SUMMARY.md claims.",
        "Do not mark the plan complete while blocker-level criteria fail without accepted tradeoff metadata.",
    ]
