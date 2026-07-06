from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from services.execution_symmetric_planner import ExecutionSymmetricPlan
from services.planning_context import JSONValue, PlanningContext, create_planning_context

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLANNING_LOG = ROOT / "logs" / "control-plane" / "planning" / "planning-events.jsonl"
NON_TRIVIAL_COMPLEXITIES = frozenset({"moderate", "complex", "high_risk"})


@dataclass(frozen=True)
class PlanningLogEntry:
    id: str
    recorded_at: str
    plan_kind: str
    route_trigger: str
    comparison_axes: dict[str, str]
    planning_context: PlanningContext

    def to_json(self) -> dict[str, JSONValue]:
        return {
            "id": self.id,
            "recorded_at": self.recorded_at,
            "plan_kind": self.plan_kind,
            "route_trigger": self.route_trigger,
            "comparison_axes": self.comparison_axes,
            "planning_context": self.planning_context.to_json(),
        }


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def build_plan_log_entry(
    *,
    planning_context: PlanningContext,
    plan_kind: str,
    route_trigger: str,
    entry_id: str | None = None,
    recorded_at: str | None = None,
) -> PlanningLogEntry:
    return PlanningLogEntry(
        id=entry_id or f"planning-log-{uuid.uuid4()}",
        recorded_at=recorded_at or now_iso(),
        plan_kind=plan_kind,
        route_trigger=route_trigger,
        comparison_axes=_comparison_axes(planning_context, plan_kind, route_trigger),
        planning_context=planning_context,
    )


def build_plan_log_from_execution_plan(
    *,
    plan: ExecutionSymmetricPlan,
    source_invocation: str,
    raw_invocation: str,
    task_type: str,
    route_trigger: str = "auto_routed",
    risk_level: str | None = None,
    tmcp_packet_id: str | None = None,
    tmcp_receipt_id: str | None = None,
    tmcp_bypass_reason: str | None = None,
) -> PlanningLogEntry:
    workflow_context = plan.workflow_context
    context = create_planning_context(
        source_invocation=source_invocation,
        raw_invocation=raw_invocation,
        workflow=workflow_context.workflow,
        phase=workflow_context.phase,
        task_type=task_type,
        complexity=plan.complexity,
        risk_level=risk_level or plan.complexity,
        selected_lenses=tuple(lens.key for lens in plan.selected_lenses),
        handoff_target=workflow_context.handoff_target,
        output_format=workflow_context.output_format,
        tmcp_packet_id=tmcp_packet_id,
        tmcp_receipt_id=tmcp_receipt_id,
        tmcp_bypass_reason=tmcp_bypass_reason,
    )
    return build_plan_log_entry(
        planning_context=context,
        plan_kind="execution_symmetric",
        route_trigger=route_trigger,
    )


def record_plan_log(entry: PlanningLogEntry, path: Path | None = None) -> Path:
    log_path = path or DEFAULT_PLANNING_LOG
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry.to_json(), sort_keys=True) + "\n")
    return log_path


def load_plan_logs(path: Path) -> tuple[PlanningLogEntry, ...]:
    if not path.exists():
        return ()
    entries: list[PlanningLogEntry] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entries.append(planning_log_from_json(json.loads(line)))
    return tuple(entries)


def planning_log_from_json(payload: dict[str, JSONValue]) -> PlanningLogEntry:
    context_payload = payload.get("planning_context")
    if not isinstance(context_payload, dict):
        raise ValueError("Planning log requires a planning_context object.")
    return PlanningLogEntry(
        id=str(payload.get("id") or ""),
        recorded_at=str(payload.get("recorded_at") or ""),
        plan_kind=str(payload.get("plan_kind") or ""),
        route_trigger=str(payload.get("route_trigger") or ""),
        comparison_axes=_json_object_strs(payload.get("comparison_axes")),
        planning_context=create_planning_context(
            source_invocation=str(context_payload.get("source_invocation") or ""),
            raw_invocation=str(context_payload.get("raw_invocation") or ""),
            workflow=str(context_payload.get("workflow") or ""),
            phase=str(context_payload.get("phase") or ""),
            task_type=str(context_payload.get("task_type") or ""),
            complexity=str(context_payload.get("complexity") or ""),
            risk_level=str(context_payload.get("risk_level") or ""),
            selected_lenses=tuple(
                str(item) for item in _json_list(context_payload.get("selected_lenses"))
            ),
            handoff_target=str(context_payload.get("handoff_target") or ""),
            validation_depth=str(context_payload.get("validation_depth") or ""),
            output_format=str(context_payload.get("output_format") or ""),
            sub_agent_strategy=str(context_payload.get("sub_agent_strategy") or ""),
            model_strategy=str(context_payload.get("model_strategy") or ""),
            tmcp_packet_id=_optional_str(context_payload.get("tmcp_packet_id")),
            tmcp_receipt_id=_optional_str(context_payload.get("tmcp_receipt_id")),
            tmcp_bypass_reason=_optional_str(context_payload.get("tmcp_bypass_reason")),
            execution_result=_optional_str(context_payload.get("execution_result")),
            validation_result=_optional_str(context_payload.get("validation_result")),
            rework_required=_optional_bool(context_payload.get("rework_required")),
            notes=tuple(str(item) for item in _json_list(context_payload.get("notes"))),
        ),
    )


def managed_run_tmcp_contract_metadata(
    *,
    complexity: str,
    tmcp_packet_id: str | None,
    tmcp_receipt_id: str | None,
    bypass_reason: str | None = None,
) -> dict[str, JSONValue]:
    normalized_complexity = complexity.strip().lower().replace("-", "_")
    tmcp_required = normalized_complexity in NON_TRIVIAL_COMPLEXITIES
    if not tmcp_required:
        status = "not_required"
    elif tmcp_packet_id and tmcp_receipt_id:
        status = "satisfied"
    elif bypass_reason and bypass_reason.strip():
        status = "bypassed"
    else:
        raise ValueError(
            "Non-trivial managed runs require TMCP packet and receipt evidence "
            "or an explicit bypass reason."
        )

    return {
        "tmcp_required": tmcp_required,
        "tmcp_contract_status": status,
        "tmcp_packet_id": tmcp_packet_id,
        "tmcp_receipt_id": tmcp_receipt_id,
        "tmcp_bypass_reason": bypass_reason,
    }


def _comparison_axes(
    planning_context: PlanningContext,
    plan_kind: str,
    route_trigger: str,
) -> dict[str, str]:
    return {
        "plan_family": "execution_symmetric" if plan_kind == "execution_symmetric" else "generic",
        "workflow_family": "gsd_phase"
        if planning_context.workflow == "gsd"
        else "natural_language",
        "invocation_family": "slash_command" if route_trigger == "slash_command" else "auto_routed",
        "lens_family": "with_selected_lenses"
        if planning_context.selected_lenses
        else "without_selected_lenses",
    }


def _json_list(value: JSONValue | None) -> list[JSONValue]:
    return value if isinstance(value, list) else []


def _json_object_strs(value: JSONValue | None) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key): str(item) for key, item in value.items()}


def _optional_str(value: JSONValue | None) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None


def _optional_bool(value: JSONValue | None) -> bool | None:
    return value if isinstance(value, bool) else None
