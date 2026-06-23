from __future__ import annotations

from dataclasses import dataclass, replace

type JSONScalar = str | int | float | bool | None
type JSONValue = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]

NON_TRIVIAL_COMPLEXITIES = frozenset({"moderate", "complex", "high_risk"})


@dataclass(frozen=True)
class PlanningContext:
    source_invocation: str
    raw_invocation: str
    workflow: str
    phase: str
    task_type: str
    complexity: str
    risk_level: str
    selected_lenses: tuple[str, ...]
    handoff_target: str
    validation_depth: str
    output_format: str
    sub_agent_strategy: str
    model_strategy: str
    execution_result: str | None = None
    validation_result: str | None = None
    rework_required: bool | None = None
    notes: tuple[str, ...] = ()
    tmcp_packet_id: str | None = None
    tmcp_receipt_id: str | None = None
    tmcp_bypass_reason: str | None = None

    @property
    def requires_tmcp_packet(self) -> bool:
        return self.complexity in NON_TRIVIAL_COMPLEXITIES

    def to_json(self) -> dict[str, JSONValue]:
        return {
            "source_invocation": self.source_invocation,
            "raw_invocation": self.raw_invocation,
            "workflow": self.workflow,
            "phase": self.phase,
            "task_type": self.task_type,
            "complexity": self.complexity,
            "risk_level": self.risk_level,
            "selected_lenses": list(self.selected_lenses),
            "handoff_target": self.handoff_target,
            "validation_depth": self.validation_depth,
            "output_format": self.output_format,
            "sub_agent_strategy": self.sub_agent_strategy,
            "model_strategy": self.model_strategy,
            "tmcp_packet_id": self.tmcp_packet_id,
            "tmcp_receipt_id": self.tmcp_receipt_id,
            "tmcp_bypass_reason": self.tmcp_bypass_reason,
            "execution_result": self.execution_result,
            "validation_result": self.validation_result,
            "rework_required": self.rework_required,
            "notes": list(self.notes),
        }


def create_planning_context(
    *,
    source_invocation: str,
    raw_invocation: str,
    workflow: str,
    phase: str,
    task_type: str,
    complexity: str,
    selected_lenses: tuple[str, ...] = (),
    risk_level: str | None = None,
    handoff_target: str | None = None,
    validation_depth: str | None = None,
    output_format: str | None = None,
    sub_agent_strategy: str | None = None,
    model_strategy: str | None = None,
    execution_result: str | None = None,
    validation_result: str | None = None,
    rework_required: bool | None = None,
    notes: tuple[str, ...] = (),
    tmcp_packet_id: str | None = None,
    tmcp_receipt_id: str | None = None,
    tmcp_bypass_reason: str | None = None,
) -> PlanningContext:
    normalized_complexity = _normalize(complexity)
    normalized_risk = _normalize(risk_level or normalized_complexity)
    return PlanningContext(
        source_invocation=_required(source_invocation, "source_invocation"),
        raw_invocation=raw_invocation.strip(),
        workflow=_required(workflow, "workflow"),
        phase=_required(phase, "phase"),
        task_type=_required(task_type, "task_type"),
        complexity=normalized_complexity,
        risk_level=normalized_risk,
        selected_lenses=tuple(dict.fromkeys(_normalize_lens(lens) for lens in selected_lenses if lens)),
        handoff_target=(handoff_target or workflow).strip() or workflow,
        validation_depth=validation_depth or _default_validation_depth(normalized_complexity),
        output_format=output_format or "execution_symmetric_plan",
        sub_agent_strategy=sub_agent_strategy or _default_sub_agent_strategy(normalized_complexity),
        model_strategy=model_strategy or _default_model_strategy(normalized_complexity),
        execution_result=execution_result,
        validation_result=validation_result,
        rework_required=rework_required,
        notes=tuple(note.strip() for note in notes if note.strip()),
        tmcp_packet_id=tmcp_packet_id,
        tmcp_receipt_id=tmcp_receipt_id,
        tmcp_bypass_reason=tmcp_bypass_reason,
    )


def with_execution_results(
    context: PlanningContext,
    *,
    execution_result: str | None,
    validation_result: str | None,
    rework_required: bool | None,
    notes: tuple[str, ...] = (),
) -> PlanningContext:
    return replace(
        context,
        execution_result=execution_result,
        validation_result=validation_result,
        rework_required=rework_required,
        notes=(*context.notes, *(note.strip() for note in notes if note.strip())),
    )


def _required(value: str, field: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"Planning context requires {field}.")
    return normalized


def _normalize(value: str) -> str:
    return value.strip().lower().replace("-", "_")


def _normalize_lens(value: str) -> str:
    return value.strip().lower().replace(" ", "-").replace("_", "-")


def _default_validation_depth(complexity: str) -> str:
    if complexity == "high_risk":
        return "full_with_independent_review"
    if complexity == "complex":
        return "full"
    if complexity == "moderate":
        return "focused"
    return "minimal"


def _default_sub_agent_strategy(complexity: str) -> str:
    if complexity in NON_TRIVIAL_COMPLEXITIES:
        return "delegate_when_parallel_or_specialized"
    return "direct_execution"


def _default_model_strategy(complexity: str) -> str:
    if complexity == "high_risk":
        return "highest_reliable_reasoning"
    if complexity == "complex":
        return "standard_plus_specialist_review"
    return "lowest_reliable_tier"
