from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Final, Literal
from urllib.parse import quote

from services.agentize import agentize_request
from services.capability_truth import Provenance
from services.next_action import get_next_actions
from services.task_routing import recommend_route_primitives

logger = logging.getLogger(__name__)

DailyFlowStepKind = Literal[
    "goal",
    "route",
    "packet",
    "run",
    "evaluation",
    "writeback",
    "unresolved_delta",
    "next_action",
]
CANONICAL_STEP_ORDER: Final[tuple[DailyFlowStepKind, ...]] = (
    "goal",
    "route",
    "packet",
    "run",
    "evaluation",
    "writeback",
    "unresolved_delta",
    "next_action",
)


@dataclass(frozen=True)
class DailyFlowStep:
    kind: DailyFlowStepKind
    summary: str
    evidence_ref: dict[str, Any]
    drill_down_path: str
    provenance: Provenance
    freshness: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DailyFlowTrace:
    project_id: str | None
    objective: str
    is_preview: bool
    steps: tuple[DailyFlowStep, ...]


def preview_from_objective(
    conn: sqlite3.Connection, *, objective: str, project_id: str | None = None
) -> DailyFlowTrace:
    normalized = " ".join(objective.strip().split())
    if not normalized:
        raise ValueError("Cannot preview an empty objective.")

    route_result = recommend_route_primitives(normalized)
    packet = agentize_request(normalized, project_id=project_id, conn=conn, dry_run=True)
    packet_json = packet.to_dict()
    required_context = packet_json.get("required_context")
    next_actions = get_next_actions(conn, project_id=project_id, limit=1)

    steps: list[DailyFlowStep] = [
        _step(
            "goal",
            summary=normalized,
            evidence_ref={"kind": "objective", "value": normalized},
            drill_down_path=_drill_down_for_step("goal", objective=normalized),
            provenance="inferred",
            metadata={"project_id": project_id},
        ),
        _step(
            "route",
            summary=_route_summary(route_result),
            evidence_ref={"table": "route_projection", "id": _route_id(route_result)},
            drill_down_path=_drill_down_for_step("route", objective=normalized),
            provenance="inferred",
            metadata={"route_result": _safe_metadata(route_result)},
        ),
        _step(
            "packet",
            summary=str(packet_json.get("normalized_objective") or normalized),
            evidence_ref={"table": "agentize_preview", "id": str(packet_json["packet_id"])},
            drill_down_path=_drill_down_for_step("packet"),
            provenance="inferred",
            metadata={
                "packet_id": packet_json["packet_id"],
                "sections_loaded": len(required_context)
                if isinstance(required_context, list)
                else 0,
                "sections_skipped": 0,
            },
        ),
        _missing_step("run", "preview - no real run yet", drill_down_path="/"),
        _missing_step(
            "evaluation",
            "preview - no success-criteria evaluation yet",
            drill_down_path="/",
        ),
        _missing_step(
            "writeback", "preview - no governed writeback yet", drill_down_path="/writebacks"
        ),
        _missing_step(
            "unresolved_delta",
            "preview - no project-scoped standards delta selected yet",
            drill_down_path=f"/projects/{quote(project_id)}" if project_id else "/projects",
        ),
        _next_action_step(next_actions[0])
        if next_actions
        else _missing_step("next_action", "no next actions available", drill_down_path="/"),
    ]
    return DailyFlowTrace(
        project_id=project_id, objective=normalized, is_preview=True, steps=tuple(steps)
    )


def replay_from_run(conn: sqlite3.Connection, *, run_id: str) -> DailyFlowTrace:
    run = _fetch_run(conn, run_id)
    if run is None:
        objective = ""
        steps = tuple(
            _missing_step(
                kind,
                "run_id not found" if kind == "run" else f"run_id not found - cannot load {kind}",
                drill_down_path=_drill_down_for_step(kind, run_id=run_id),
            )
            for kind in CANONICAL_STEP_ORDER
        )
        return DailyFlowTrace(project_id=None, objective=objective, is_preview=False, steps=steps)

    objective = str(run.get("objective") or "")
    project_id = _optional_str(run.get("project_id"))
    route_result = _json_dict(run.get("route_result_json"))
    packet = _fetch_packet(conn, run_id)
    finding = _fetch_finding(conn, run_id)
    writeback = _fetch_writeback(conn, run_id)
    delta = _fetch_delta(conn, project_id)
    next_actions = get_next_actions(conn, project_id=project_id, limit=1)

    steps = (
        _step(
            "goal",
            summary=objective,
            evidence_ref={"kind": "objective", "value": objective},
            drill_down_path=_drill_down_for_step("goal", objective=objective),
            provenance="confirmed",
            freshness=str(run.get("created_at") or _now_iso()),
            metadata={"project_id": project_id},
        ),
        _route_step_for_replay(run, route_result),
        _packet_step(packet, run_id),
        _run_step(run),
        _evaluation_step(conn, finding, run),
        _writeback_step(conn, writeback, run_id),
        _delta_step(conn, delta, project_id),
        _next_action_step(next_actions[0])
        if next_actions
        else _missing_step("next_action", "no next actions available", drill_down_path="/"),
    )
    return DailyFlowTrace(project_id=project_id, objective=objective, is_preview=False, steps=steps)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _safe_table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table_name,),
    ).fetchone()
    return row is not None


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    if not _safe_table_exists(conn, table_name):
        return set()
    return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}


def _selectable(columns: set[str], column: str, fallback: str = "NULL") -> str:
    return column if column in columns else f"{fallback} AS {column}"


def _drill_down_for_step(
    kind: DailyFlowStepKind,
    *,
    run_id: str | None = None,
    packet_id: str | None = None,
    finding_id: str | None = None,
    writeback_id: str | None = None,
    delta_id: str | None = None,
    project_id: str | None = None,
    objective: str | None = None,
    route_id: str | None = None,
) -> str:
    if kind == "goal":
        return f"/search?query={quote(objective or '')}"
    if kind == "route":
        if run_id:
            route_query = f"?route={quote(route_id)}" if route_id else ""
            return f"/runs/{quote(run_id)}{route_query}"
        return "/search"
    if kind == "packet":
        return f"/control?packet={quote(packet_id)}" if packet_id else "/control"
    if kind == "run":
        return f"/runs/{quote(run_id)}" if run_id else "/"
    if kind == "evaluation":
        if run_id and finding_id:
            return f"/runs/{quote(run_id)}?finding={quote(finding_id)}"
        return f"/runs/{quote(run_id)}" if run_id else "/"
    if kind == "writeback":
        return f"/writebacks#{quote(writeback_id)}" if writeback_id else "/writebacks"
    if kind == "unresolved_delta":
        if project_id and delta_id:
            return f"/projects/{quote(project_id)}?delta={quote(delta_id)}"
        return f"/projects/{quote(project_id)}" if project_id else "/projects"
    if kind == "next_action":
        return "/"
    return "/"


def _step(
    kind: DailyFlowStepKind,
    *,
    summary: str,
    evidence_ref: dict[str, Any],
    drill_down_path: str,
    provenance: Provenance,
    freshness: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> DailyFlowStep:
    if "table" not in evidence_ref and "kind" not in evidence_ref:
        evidence_ref = {
            "table": evidence_ref.get("table"),
            "id": evidence_ref.get("id"),
            **evidence_ref,
        }
    return DailyFlowStep(
        kind=kind,
        summary=summary,
        evidence_ref=evidence_ref,
        drill_down_path=drill_down_path or "/",
        provenance=provenance,
        freshness=freshness or _now_iso(),
        metadata=metadata or {},
    )


def _missing_step(
    kind: DailyFlowStepKind, summary: str, *, drill_down_path: str | None = None
) -> DailyFlowStep:
    return _step(
        kind,
        summary=summary,
        evidence_ref={"table": None, "id": None, "missing_reason": summary},
        drill_down_path=drill_down_path or _drill_down_for_step(kind),
        provenance="missing",
        metadata={},
    )


def _fetch_run(conn: sqlite3.Connection, run_id: str) -> dict[str, Any] | None:
    if not _safe_table_exists(conn, "orchestration_runs"):
        return None
    columns = _table_columns(conn, "orchestration_runs")
    row = conn.execute(
        f"""
        SELECT id,
               {_selectable(columns, "objective", "''")},
               {_selectable(columns, "project_id")},
               {_selectable(columns, "workflow_key")},
               {_selectable(columns, "status")},
               {_selectable(columns, "route_id")},
               {_selectable(columns, "route_result_json", "'{}'")},
               {_selectable(columns, "created_at", "''")},
               {_selectable(columns, "updated_at", "''")}
        FROM orchestration_runs
        WHERE id = ?
        LIMIT 1
        """,
        (run_id,),
    ).fetchone()
    return dict(row) if row is not None else None


def _fetch_packet(conn: sqlite3.Connection, run_id: str) -> dict[str, Any] | None:
    if not _safe_table_exists(conn, "briefing_packets"):
        return None
    columns = _table_columns(conn, "briefing_packets")
    row = conn.execute(
        f"""
        SELECT id,
               {_selectable(columns, "run_id")},
               {_selectable(columns, "project_id")},
               {_selectable(columns, "objective", "''")},
               {_selectable(columns, "route_id")},
               {_selectable(columns, "selection_trace_json", "'[]'")},
               {_selectable(columns, "created_at", "''")}
        FROM briefing_packets
        WHERE run_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (run_id,),
    ).fetchone()
    return dict(row) if row is not None else None


def _fetch_finding(conn: sqlite3.Connection, run_id: str) -> dict[str, Any] | None:
    if not _safe_table_exists(conn, "success_criteria_findings"):
        return None
    columns = _table_columns(conn, "success_criteria_findings")
    has_direct_run = "run_id" in columns
    has_evaluations = _safe_table_exists(conn, "success_criteria_evaluations")
    evaluation_columns = _table_columns(conn, "success_criteria_evaluations")
    if not has_direct_run and not (
        has_evaluations and "evaluation_id" in columns and "run_id" in evaluation_columns
    ):
        return None
    message_expr = (
        "f.message" if "message" in columns else "f.summary" if "summary" in columns else "''"
    )
    run_expr = "f.run_id" if has_direct_run else "e.run_id"
    join = (
        "LEFT JOIN success_criteria_evaluations e ON e.id = f.evaluation_id"
        if not has_direct_run
        else ""
    )
    row = conn.execute(
        f"""
        SELECT f.id,
               {run_expr} AS run_id,
               {_selectable(columns, "criterion_id")},
               {_selectable(columns, "level", "''")},
               {message_expr} AS message,
               {_selectable(columns, "resolution_status", "'open'")},
               f.created_at AS created_at
        FROM success_criteria_findings f
        {join}
        WHERE {run_expr} = ?
        ORDER BY f.created_at ASC
        LIMIT 1
        """,
        (run_id,),
    ).fetchone()
    return dict(row) if row is not None else None


def _fetch_writeback(conn: sqlite3.Connection, run_id: str) -> dict[str, Any] | None:
    if not _safe_table_exists(conn, "improvement_writebacks"):
        return None
    columns = _table_columns(conn, "improvement_writebacks")
    if "run_id" not in columns:
        return None
    row = conn.execute(
        f"""
        SELECT id,
               run_id,
               {_selectable(columns, "project_id")},
               {_selectable(columns, "layer_type", "''")},
               {_selectable(columns, "layer_key", "''")},
               {_selectable(columns, "title", "''")},
               {_selectable(columns, "summary", "''")},
               {_selectable(columns, "status", "''")},
               {_selectable(columns, "requires_approval", "0")},
               {_selectable(columns, "created_at", "''")}
        FROM improvement_writebacks
        WHERE run_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (run_id,),
    ).fetchone()
    return dict(row) if row is not None else None


def _fetch_delta(conn: sqlite3.Connection, project_id: str | None) -> dict[str, Any] | None:
    if not project_id or not _safe_table_exists(conn, "standards_delta_items"):
        return None
    columns = _table_columns(conn, "standards_delta_items")
    if "project_id" not in columns:
        return None
    row = conn.execute(
        f"""
        SELECT id,
               project_id,
               {_selectable(columns, "domain", "''")},
               {_selectable(columns, "priority_bucket", "'quick_wins'")},
               {_selectable(columns, "summary", "''")},
               {_selectable(columns, "status", "''")},
               {_selectable(columns, "updated_at", "''")}
        FROM standards_delta_items
        WHERE project_id = ? AND status IN ('open', 'pending')
        ORDER BY priority_bucket ASC
        LIMIT 1
        """,
        (project_id,),
    ).fetchone()
    return dict(row) if row is not None else None


def _route_step_for_replay(run: dict[str, Any], route_result: dict[str, Any]) -> DailyFlowStep:
    run_id = str(run["id"])
    route_id = _optional_str(run.get("route_id"))
    if not route_result:
        return _missing_step(
            "route",
            "route_result_json unavailable for run",
            drill_down_path=_drill_down_for_step("route", run_id=run_id, route_id=route_id),
        )
    return _step(
        "route",
        summary=_route_summary(route_result),
        evidence_ref={"table": "orchestration_runs", "id": run_id},
        drill_down_path=_drill_down_for_step("route", run_id=run_id, route_id=route_id),
        provenance="confirmed",
        freshness=str(run.get("created_at") or _now_iso()),
        metadata={"route_id": route_id, "route_result": _safe_metadata(route_result)},
    )


def _packet_step(packet: dict[str, Any] | None, run_id: str) -> DailyFlowStep:
    if packet is None:
        summary = (
            "source data unavailable - Phase 2 briefing_packets table not present"
            if not run_id
            else "no briefing packet found for run"
        )
        return _missing_step("packet", summary, drill_down_path=_drill_down_for_step("packet"))
    packet_id = str(packet["id"])
    return _step(
        "packet",
        summary=f"Briefing packet {packet_id}",
        evidence_ref={"table": "briefing_packets", "id": packet_id},
        drill_down_path=_drill_down_for_step("packet", packet_id=packet_id),
        provenance="confirmed",
        freshness=str(packet.get("created_at") or _now_iso()),
        metadata={"selection_trace": _json_list(packet.get("selection_trace_json"))[:5]},
    )


def _run_step(run: dict[str, Any]) -> DailyFlowStep:
    run_id = str(run["id"])
    return _step(
        "run",
        summary=f"Run {run_id} is {run.get('status') or 'unknown'}",
        evidence_ref={"table": "orchestration_runs", "id": run_id},
        drill_down_path=_drill_down_for_step("run", run_id=run_id),
        provenance="confirmed",
        freshness=str(run.get("updated_at") or run.get("created_at") or _now_iso()),
        metadata={"workflow_key": run.get("workflow_key"), "status": run.get("status")},
    )


def _evaluation_step(
    conn: sqlite3.Connection, finding: dict[str, Any] | None, run: dict[str, Any]
) -> DailyFlowStep:
    run_id = str(run["id"])
    if not _safe_table_exists(conn, "success_criteria_findings"):
        return _missing_step(
            "evaluation",
            "source data unavailable - Phase 6 success_criteria_findings table not present",
            drill_down_path=_drill_down_for_step("evaluation", run_id=run_id),
        )
    if finding is None:
        return _missing_step(
            "evaluation",
            "no success-criteria finding found for run",
            drill_down_path=_drill_down_for_step("evaluation", run_id=run_id),
        )
    provenance: Provenance = "confirmed"
    if (
        str(finding.get("level")) == "blocker"
        and str(finding.get("resolution_status")) == "open"
        and str(run.get("status")) == "completed"
    ):
        provenance = "contradictory"
    finding_id = str(finding["id"])
    return _step(
        "evaluation",
        summary=str(finding.get("message") or f"Finding {finding_id}"),
        evidence_ref={"table": "success_criteria_findings", "id": finding_id},
        drill_down_path=_drill_down_for_step("evaluation", run_id=run_id, finding_id=finding_id),
        provenance=provenance,
        freshness=str(finding.get("created_at") or _now_iso()),
        metadata={
            "criterion_id": finding.get("criterion_id"),
            "level": finding.get("level"),
            "resolution_status": finding.get("resolution_status"),
        },
    )


def _writeback_step(
    conn: sqlite3.Connection, writeback: dict[str, Any] | None, run_id: str
) -> DailyFlowStep:
    if not _safe_table_exists(conn, "improvement_writebacks"):
        return _missing_step(
            "writeback",
            "source data unavailable - Phase 5 improvement_writebacks table not present",
            drill_down_path="/writebacks",
        )
    if writeback is None:
        return _missing_step(
            "writeback", "no governed writeback found for run", drill_down_path="/writebacks"
        )
    writeback_id = str(writeback["id"])
    return _step(
        "writeback",
        summary=str(writeback.get("title") or writeback.get("summary") or writeback_id),
        evidence_ref={"table": "improvement_writebacks", "id": writeback_id},
        drill_down_path=_drill_down_for_step("writeback", writeback_id=writeback_id),
        provenance="confirmed",
        freshness=str(writeback.get("created_at") or _now_iso()),
        metadata={
            "run_id": run_id,
            "layer_type": writeback.get("layer_type"),
            "layer_key": writeback.get("layer_key"),
            "status": writeback.get("status"),
            "requires_approval": bool(writeback.get("requires_approval")),
        },
    )


def _delta_step(
    conn: sqlite3.Connection, delta: dict[str, Any] | None, project_id: str | None
) -> DailyFlowStep:
    if not _safe_table_exists(conn, "standards_delta_items"):
        return _missing_step(
            "unresolved_delta",
            "source data unavailable - Phase 7 standards_delta_items table not present",
            drill_down_path=_drill_down_for_step("unresolved_delta", project_id=project_id),
        )
    if delta is None:
        return _missing_step(
            "unresolved_delta",
            "no open standards delta found for project",
            drill_down_path=_drill_down_for_step("unresolved_delta", project_id=project_id),
        )
    delta_id = str(delta["id"])
    return _step(
        "unresolved_delta",
        summary=str(delta.get("summary") or delta_id),
        evidence_ref={"table": "standards_delta_items", "id": delta_id},
        drill_down_path=_drill_down_for_step(
            "unresolved_delta", project_id=project_id, delta_id=delta_id
        ),
        provenance="confirmed",
        freshness=str(delta.get("updated_at") or _now_iso()),
        metadata={
            "domain": delta.get("domain"),
            "priority_bucket": delta.get("priority_bucket"),
            "status": delta.get("status"),
        },
    )


def _next_action_step(action: Any) -> DailyFlowStep:
    return _step(
        "next_action",
        summary=action.title,
        evidence_ref={
            "table": "next_action_projection",
            "id": action.evidence_ids[0] if action.evidence_ids else action.kind,
        },
        drill_down_path=action.drill_down_path,
        provenance="confirmed",
        metadata={
            "kind": action.kind,
            "priority_bucket": action.priority_bucket,
            "confidence": action.confidence,
        },
    )


def _route_summary(route_result: dict[str, Any]) -> str:
    selected = route_result.get("selected_workflow")
    if isinstance(selected, dict) and selected.get("workflow_key"):
        return f"Route to {selected['workflow_key']}"
    return "No governed workflow matched strongly enough"


def _route_id(route_result: dict[str, Any]) -> str:
    selected = route_result.get("selected_workflow")
    if isinstance(selected, dict) and selected.get("workflow_key"):
        return str(selected["workflow_key"])
    return "unmatched"


def _safe_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(payload, default=str))


def _json_dict(raw: Any) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        loaded = json.loads(str(raw))
    except json.JSONDecodeError:
        logger.debug("daily_flow: malformed JSON dict ignored")
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _json_list(raw: Any) -> list[Any]:
    if not raw:
        return []
    try:
        loaded = json.loads(str(raw))
    except json.JSONDecodeError:
        logger.debug("daily_flow: malformed JSON list ignored")
        return []
    return loaded if isinstance(loaded, list) else []


def _optional_str(value: Any) -> str | None:
    return str(value) if value not in (None, "") else None
