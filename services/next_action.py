from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from typing import Any, Final, Literal, get_args

logger = logging.getLogger(__name__)

NextActionKind = Literal[
    "launch_remediation_workflow",
    "approve_pending_writeback",
    "resolve_open_blocker",
    "review_learning_proposal",
    "fix_terminal_run_gap",
    "promote_candidate_asset",
    "investigate_regressed_metric",
    "complete_backfill_task",
]
PriorityBucket = Literal[
    "foundational", "high_leverage", "quick_wins", "blocked", "waived_deferred"
]

NEXT_ACTION_KINDS: tuple[NextActionKind, ...] = get_args(NextActionKind)
PRIORITY_BUCKETS: tuple[PriorityBucket, ...] = get_args(PriorityBucket)
DEFAULT_LIMIT: Final[int] = 10
MAX_LIMIT: Final[int] = 50
BUCKET_WEIGHTS: Final[dict[PriorityBucket, int]] = {
    "foundational": 0,
    "high_leverage": 1,
    "quick_wins": 2,
    "blocked": 3,
    "waived_deferred": 4,
}


@dataclass(frozen=True)
class NextAction:
    kind: NextActionKind
    title: str
    rationale: str
    project_id: str | None
    priority_bucket: PriorityBucket
    recommended_workflow_key: str | None
    evidence_ids: tuple[str, ...]
    drill_down_path: str
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)


def _bucket_weight(bucket: PriorityBucket) -> int:
    return BUCKET_WEIGHTS.get(bucket, 99)


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


def _normalize_bucket(value: Any) -> PriorityBucket:
    bucket = str(value or "quick_wins")
    if bucket in PRIORITY_BUCKETS:
        return bucket  # type: ignore[return-value]
    return "quick_wins"


def _json_dict(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _drill_down_for(
    kind: str,
    *,
    id_: str,
    project_id: str | None = None,
    run_id: str | None = None,
) -> str:
    if kind == "delta_item":
        return f"/projects/{project_id}?delta={id_}" if project_id else f"/projects?delta={id_}"
    if kind == "writeback":
        return f"/writebacks#{id_}"
    if kind == "finding":
        return f"/runs/{run_id or id_}?finding={id_}"
    if kind == "run":
        return f"/runs/{id_}"
    if kind == "backfill_task":
        return (
            f"/projects/{project_id}?backfill={id_}" if project_id else f"/projects?backfill={id_}"
        )
    if kind == "promotion_lifecycle_item":
        return f"/workflows?promotion={id_}"
    if kind == "learning_pattern":
        return f"/control?pattern={id_}"
    return f"/control?item={id_}"


def _from_health_deltas(conn: sqlite3.Connection, *, project_id: str | None) -> list[NextAction]:
    if not _safe_table_exists(conn, "standards_delta_items"):
        logger.debug("next_action: standards_delta_items missing; skipping")
        return []
    columns = _table_columns(conn, "standards_delta_items")
    where = []
    params: list[Any] = []
    if "status" in columns:
        where.append("status IN ('open', 'pending')")
    if project_id and "project_id" in columns:
        where.append("project_id = ?")
        params.append(project_id)
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    rows = conn.execute(
        f"""
        SELECT id,
               {_selectable(columns, "project_id")},
               {_selectable(columns, "domain", "''")},
               {_selectable(columns, "priority_bucket", "'quick_wins'")},
               {_selectable(columns, "severity", "5")},
               {_selectable(columns, "summary", "''")},
               {_selectable(columns, "remediation_playbook_json", "'{}'")}
        FROM standards_delta_items
        {where_sql}
        ORDER BY priority_bucket, severity DESC
        LIMIT 20
        """,
        params,
    ).fetchall()
    actions = []
    for row in rows:
        row_project_id = row["project_id"]
        playbook = _json_dict(row["remediation_playbook_json"])
        severity = float(row["severity"] or 5)
        bucket = _normalize_bucket(row["priority_bucket"])
        actions.append(
            NextAction(
                kind="launch_remediation_workflow",
                title=f"Remediate {row['domain'] or row['id']}",
                rationale=str(row["summary"] or "Standards delta needs remediation."),
                project_id=row_project_id,
                priority_bucket=bucket,
                recommended_workflow_key=playbook.get("recommended_workflow_key"),
                evidence_ids=(str(row["id"]),),
                drill_down_path=_drill_down_for(
                    "delta_item", id_=str(row["id"]), project_id=row_project_id
                ),
                confidence=max(0.0, min(severity / 10.0, 1.0)),
                metadata={"domain": row["domain"]},
            )
        )
    return actions


def _from_pending_writebacks(
    conn: sqlite3.Connection, *, project_id: str | None
) -> list[NextAction]:
    if not _safe_table_exists(conn, "improvement_writebacks"):
        logger.debug("next_action: improvement_writebacks missing; skipping")
        return []
    columns = _table_columns(conn, "improvement_writebacks")
    where = ["status = 'pending_approval'", "requires_approval = 1"]
    params: list[Any] = []
    if project_id and "project_id" in columns:
        where.append("project_id = ?")
        params.append(project_id)
    rows = conn.execute(
        f"""
        SELECT id,
               {_selectable(columns, "run_id")},
               {_selectable(columns, "project_id")},
               {_selectable(columns, "layer_type", "''")},
               {_selectable(columns, "layer_key", "''")},
               {_selectable(columns, "title", "''")},
               {_selectable(columns, "summary", "''")},
               {_selectable(columns, "proposed_change_json", "'{}'")},
               {_selectable(columns, "created_at", "''")}
        FROM improvement_writebacks
        WHERE {" AND ".join(where)}
        ORDER BY created_at DESC
        LIMIT 20
        """,
        params,
    ).fetchall()
    actions = []
    for row in rows:
        proposed_change = str(row["proposed_change_json"] or "")
        is_learning = '"source": "learning_analysis"' in proposed_change
        kind: NextActionKind = (
            "review_learning_proposal" if is_learning else "approve_pending_writeback"
        )
        bucket: PriorityBucket = "high_leverage" if is_learning else "foundational"
        evidence_ids = tuple(item for item in (row["id"], row["run_id"]) if item)
        actions.append(
            NextAction(
                kind=kind,
                title=str(row["title"] or row["id"]),
                rationale=str(row["summary"] or "Pending governed writeback requires review."),
                project_id=row["project_id"],
                priority_bucket=bucket,
                recommended_workflow_key=None,
                evidence_ids=tuple(str(item) for item in evidence_ids),
                drill_down_path=_drill_down_for("writeback", id_=str(row["id"])),
                confidence=0.8 if is_learning else 0.85,
                metadata={"layer_type": row["layer_type"], "layer_key": row["layer_key"]},
            )
        )
    return actions


def _from_open_blockers(conn: sqlite3.Connection, *, project_id: str | None) -> list[NextAction]:
    if not _safe_table_exists(conn, "success_criteria_findings"):
        logger.debug("next_action: success_criteria_findings missing; skipping")
        return []
    columns = _table_columns(conn, "success_criteria_findings")
    evaluation_columns = _table_columns(conn, "success_criteria_evaluations")
    message_column = (
        "f.message" if "message" in columns else "f.summary" if "summary" in columns else "''"
    )
    has_evaluations = _safe_table_exists(conn, "success_criteria_evaluations")
    run_expr = (
        "f.run_id"
        if "run_id" in columns
        else "e.run_id"
        if has_evaluations and "run_id" in evaluation_columns
        else "NULL"
    )
    joins: list[str] = []
    if has_evaluations and "run_id" not in columns and "evaluation_id" in columns:
        joins.append("LEFT JOIN success_criteria_evaluations e ON e.id = f.evaluation_id")
    if _safe_table_exists(conn, "orchestration_runs"):
        joins.append(f"LEFT JOIN orchestration_runs r ON r.id = {run_expr}")
        project_select = (
            "COALESCE(r.project_id, e.project_id) AS project_id"
            if has_evaluations and "project_id" in evaluation_columns
            else "r.project_id AS project_id"
        )
    elif has_evaluations and "project_id" in evaluation_columns:
        project_select = "e.project_id AS project_id"
    else:
        project_select = "NULL AS project_id"
    where = ["f.level = 'blocker'", "f.resolution_status = 'open'"]
    params: list[Any] = []
    if project_id:
        where.append(f"{project_select.removesuffix(' AS project_id')} = ?")
        params.append(project_id)
    rows = conn.execute(
        f"""
        SELECT f.id, {run_expr} AS run_id, f.criterion_id, f.level, {message_column} AS message,
               {project_select}, f.created_at
        FROM success_criteria_findings f
        {" ".join(joins)}
        WHERE {" AND ".join(where)}
        ORDER BY f.created_at DESC
        LIMIT 20
        """,
        params,
    ).fetchall()
    return [
        NextAction(
            kind="resolve_open_blocker",
            title=f"Resolve blocker {row['criterion_id']}",
            rationale=str(row["message"] or "Open blocker needs resolution."),
            project_id=row["project_id"],
            priority_bucket="foundational",
            recommended_workflow_key=None,
            evidence_ids=tuple(str(item) for item in (row["id"], row["run_id"]) if item),
            drill_down_path=_drill_down_for("finding", id_=str(row["id"]), run_id=row["run_id"]),
            confidence=0.9,
            metadata={"criterion_id": row["criterion_id"]},
        )
        for row in rows
    ]


def _from_terminal_run_gaps(
    conn: sqlite3.Connection, *, project_id: str | None
) -> list[NextAction]:
    if not _safe_table_exists(conn, "orchestration_runs"):
        logger.debug("next_action: orchestration_runs missing; skipping terminal gaps")
        return []
    has_learning = _safe_table_exists(conn, "workflow_learning_events")
    join = "LEFT JOIN workflow_learning_events e ON e.run_id = r.id" if has_learning else ""
    no_event_filter = "AND e.id IS NULL" if has_learning else ""
    where = [
        "r.status IN ('completed', 'failed', 'partial', 'needs_follow_up', 'follow_up_needed')"
    ]
    params: list[Any] = []
    columns = _table_columns(conn, "orchestration_runs")
    if project_id and "project_id" in columns:
        where.append("r.project_id = ?")
        params.append(project_id)
    rows = conn.execute(
        f"""
        SELECT r.id, r.project_id, r.objective, r.status
        FROM orchestration_runs r
        {join}
        WHERE {" AND ".join(where)} {no_event_filter}
        ORDER BY COALESCE(r.updated_at, r.created_at) DESC
        LIMIT 20
        """,
        params,
    ).fetchall()
    return [
        NextAction(
            kind="fix_terminal_run_gap",
            title=f"Record learning evidence for {row['id']}",
            rationale=f"Terminal run has status {row['status']} but no learning event.",
            project_id=row["project_id"],
            priority_bucket="high_leverage",
            recommended_workflow_key=None,
            evidence_ids=(str(row["id"]),),
            drill_down_path=_drill_down_for("run", id_=str(row["id"])),
            confidence=0.7,
            metadata={"status": row["status"]},
        )
        for row in rows
    ]


def _from_backfill_tasks(conn: sqlite3.Connection, *, project_id: str | None) -> list[NextAction]:
    if not _safe_table_exists(conn, "standards_backfill_tasks"):
        logger.debug("next_action: standards_backfill_tasks missing; skipping")
        return []
    columns = _table_columns(conn, "standards_backfill_tasks")
    where = []
    params: list[Any] = []
    if "status" in columns:
        where.append("status IN ('pending', 'in_progress')")
    if project_id and "project_id" in columns:
        where.append("project_id = ?")
        params.append(project_id)
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    rows = conn.execute(
        f"""
        SELECT id,
               {_selectable(columns, "project_id")},
               {_selectable(columns, "summary", "''")},
               {_selectable(columns, "status", "'pending'")},
               {_selectable(columns, "priority_bucket", "'quick_wins'")},
               {_selectable(columns, "created_at", "''")}
        FROM standards_backfill_tasks
        {where_sql}
        ORDER BY priority_bucket, created_at
        LIMIT 20
        """,
        params,
    ).fetchall()
    return [
        NextAction(
            kind="complete_backfill_task",
            title=f"Complete backfill {row['id']}",
            rationale=str(row["summary"] or "Backfill task needs completion."),
            project_id=row["project_id"],
            priority_bucket=_normalize_bucket(row["priority_bucket"]),
            recommended_workflow_key=None,
            evidence_ids=(str(row["id"]),),
            drill_down_path=_drill_down_for(
                "backfill_task", id_=str(row["id"]), project_id=row["project_id"]
            ),
            confidence=0.6,
            metadata={"status": row["status"]},
        )
        for row in rows
    ]


def _from_promotion_candidates(
    conn: sqlite3.Connection, *, project_id: str | None
) -> list[NextAction]:
    del project_id
    if not _safe_table_exists(conn, "promotion_lifecycle_items"):
        logger.debug("next_action: promotion_lifecycle_items missing; skipping")
        return []
    rows = conn.execute(
        """
        SELECT id, item_kind, item_key, status, created_at
        FROM promotion_lifecycle_items
        WHERE status = 'candidate'
        ORDER BY created_at DESC
        LIMIT 20
        """
    ).fetchall()
    return [
        NextAction(
            kind="promote_candidate_asset",
            title=f"Review candidate {row['item_kind']} {row['item_key']}",
            rationale="Candidate asset is ready for promotion review.",
            project_id=None,
            priority_bucket="quick_wins",
            recommended_workflow_key=None,
            evidence_ids=(str(row["id"]),),
            drill_down_path=_drill_down_for("promotion_lifecycle_item", id_=str(row["id"])),
            confidence=0.65,
            metadata={"item_kind": row["item_kind"], "item_key": row["item_key"]},
        )
        for row in rows
    ]


def get_next_actions(
    conn: sqlite3.Connection,
    *,
    project_id: str | None = None,
    limit: int = DEFAULT_LIMIT,
) -> list[NextAction]:
    """Return ranked, read-time next actions.

    Learning proposals are discriminated inside pending writebacks because their persisted
    approval queue is the same `improvement_writebacks` table.
    """
    if limit < 1 or limit > MAX_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_LIMIT}")
    conn.row_factory = sqlite3.Row
    actions: list[NextAction] = []
    for fetcher in (
        _from_health_deltas,
        _from_pending_writebacks,
        _from_open_blockers,
        _from_terminal_run_gaps,
        _from_backfill_tasks,
        _from_promotion_candidates,
    ):
        actions.extend(fetcher(conn, project_id=project_id))
    actions.sort(key=lambda action: (_bucket_weight(action.priority_bucket), -action.confidence))
    return actions[:limit]


__all__ = [
    "DEFAULT_LIMIT",
    "MAX_LIMIT",
    "NEXT_ACTION_KINDS",
    "NextAction",
    "NextActionKind",
    "PRIORITY_BUCKETS",
    "PriorityBucket",
    "get_next_actions",
]
