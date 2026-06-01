from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from services.asset_lifecycle import (
    AssetKind,
    AssetLifecycleState,
    promote_asset,
    writeback_approval_policy_shim,
)
from services.workflow_orchestration import load_workflow_registry


@dataclass(frozen=True)
class WorkflowEffectiveness:
    workflow_key: str
    since: str
    run_count: int
    completed_count: int
    failed_count: int
    rework_rate: float
    validation_pass_rate: float
    mean_blocker_count: float
    mean_blockers_per_stage: float
    writeback_usefulness: float
    stage_evaluations: dict[str, dict[str, float]]
    rework_rate_unavailable: bool = True


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


def _json_dict(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table,),
    ).fetchone()
    return row is not None


def ensure_workflow_promotion_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS improvement_writebacks (
          id TEXT PRIMARY KEY,
          run_id TEXT,
          project_id TEXT,
          layer_type TEXT NOT NULL,
          layer_key TEXT NOT NULL,
          title TEXT NOT NULL,
          summary TEXT NOT NULL,
          evidence_json TEXT NOT NULL DEFAULT '[]',
          proposed_change_json TEXT NOT NULL DEFAULT '{}',
          impact_scope TEXT NOT NULL DEFAULT 'scoped',
          status TEXT NOT NULL DEFAULT 'proposed',
          requires_approval INTEGER NOT NULL DEFAULT 0,
          approval_reason TEXT,
          token_regressive INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          decision_note TEXT,
          decision_actor TEXT,
          decision_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS promotion_lifecycle_items (
          id TEXT PRIMARY KEY,
          item_kind TEXT NOT NULL,
          item_key TEXT NOT NULL,
          source_run_id TEXT,
          status TEXT NOT NULL,
          evidence_json TEXT NOT NULL DEFAULT '[]',
          status_reason TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          metadata_json TEXT NOT NULL DEFAULT '{}'
        )
        """
    )


def _stage_rows(report_json: str | None) -> list[dict[str, Any]]:
    report = _json_dict(report_json)
    rows = report.get("stage_evaluations", [])
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def compare_workflow_effectiveness(
    conn: sqlite3.Connection,
    *,
    workflow_key: str,
    since: str,
) -> WorkflowEffectiveness:
    if not _table_exists(conn, "workflow_execution_reports"):
        return WorkflowEffectiveness(workflow_key, since, 0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, {})
    rows = conn.execute(
        """
        SELECT id, run_id, status, report_json, created_at
        FROM workflow_execution_reports
        WHERE workflow_key = ? AND created_at >= ?
        """,
        (workflow_key, since),
    ).fetchall()
    run_count = len(rows)
    completed_count = len([row for row in rows if row[2] == "completed"])
    failed_count = run_count - completed_count
    total_blockers = 0
    total_stages = 0
    stage_acc: dict[str, dict[str, float]] = {}
    for _, _, _, report_json, _ in rows:
        stages = _stage_rows(report_json)
        total_stages += len(stages)
        for stage in stages:
            stage_key = str(stage.get("stage_key", "unknown"))
            total = float(stage.get("total_validations") or 0)
            passed = float(stage.get("passed_validations") or 0)
            blockers = float(stage.get("blocker_count") or 0)
            warnings = float(stage.get("warning_count") or 0)
            total_blockers += int(blockers)
            acc = stage_acc.setdefault(
                stage_key,
                {"runs": 0.0, "passed": 0.0, "total": 0.0, "blockers": 0.0, "warnings": 0.0},
            )
            acc["runs"] += 1
            acc["passed"] += passed
            acc["total"] += total
            acc["blockers"] += blockers
            acc["warnings"] += warnings

    if _table_exists(conn, "success_criteria_stage_findings"):
        blocker_row = conn.execute(
            """
            SELECT COUNT(*)
            FROM success_criteria_stage_findings
            WHERE level = 'blocker'
              AND run_id IN (
                SELECT run_id FROM workflow_execution_reports
                WHERE workflow_key = ? AND created_at >= ?
              )
            """,
            (workflow_key, since),
        ).fetchone()
        table_blockers = int(blocker_row[0]) if blocker_row else 0
        total_blockers = max(total_blockers, table_blockers)

    writeback_usefulness = _writeback_usefulness(conn, workflow_key)
    stage_evaluations = {
        key: {
            "passed_validation_rate": values["passed"] / values["total"]
            if values["total"]
            else 0.0,
            "blocker_rate": values["blockers"] / values["runs"] if values["runs"] else 0.0,
            "warning_rate": values["warnings"] / values["runs"] if values["runs"] else 0.0,
        }
        for key, values in stage_acc.items()
    }
    return WorkflowEffectiveness(
        workflow_key=workflow_key,
        since=since,
        run_count=run_count,
        completed_count=completed_count,
        failed_count=failed_count,
        rework_rate=0.0,
        validation_pass_rate=completed_count / run_count if run_count else 0.0,
        mean_blocker_count=total_blockers / run_count if run_count else 0.0,
        mean_blockers_per_stage=total_blockers / total_stages if total_stages else 0.0,
        writeback_usefulness=writeback_usefulness,
        stage_evaluations=stage_evaluations,
    )


def _writeback_usefulness(conn: sqlite3.Connection, workflow_key: str) -> float:
    if not _table_exists(conn, "improvement_writebacks"):
        return 0.0
    rows = conn.execute(
        """
        SELECT status
        FROM improvement_writebacks
        WHERE proposed_change_json LIKE ?
        """,
        (f'%"{workflow_key}"%',),
    ).fetchall()
    if not rows:
        return 0.0
    approved = len([row for row in rows if row[0] == "approved"])
    return approved / len(rows)


def _insert_workflow_promotion_writeback(
    conn: sqlite3.Connection,
    *,
    workflow_key: str,
    proposed_change: dict[str, Any],
    rationale: str,
    actor: str,
    policy: dict[str, Any],
) -> str:
    ensure_workflow_promotion_schema(conn)
    now = _now_iso()
    writeback_id = f"writeback-{uuid.uuid4()}"
    conn.execute(
        """
        INSERT INTO improvement_writebacks (
          id, run_id, project_id, layer_type, layer_key, title, summary,
          evidence_json, proposed_change_json, impact_scope, status, requires_approval,
          approval_reason, token_regressive, created_at, updated_at
        )
        VALUES (?, NULL, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
        """,
        (
            writeback_id,
            "workflow",
            workflow_key,
            f"Promote workflow {workflow_key}",
            rationale,
            _json([]),
            _json({**proposed_change, "actor": actor, "approval_policy": policy}),
            "workflow-default",
            "proposed",
            1 if policy["requires_approval"] else 0,
            policy.get("reason"),
            now,
            now,
        ),
    )
    return writeback_id


def propose_workflow_promotion(
    conn: sqlite3.Connection,
    *,
    workflow_key: str,
    to_state: AssetLifecycleState,
    evidence: WorkflowEffectiveness,
    actor: str,
    rationale: str,
) -> dict[str, Any]:
    ensure_workflow_promotion_schema(conn)
    evidence_summary = asdict(evidence)
    proposed_change = {
        "workflow_key": workflow_key,
        "to_state": to_state,
        "evidence_summary": evidence_summary,
    }
    policy = writeback_approval_policy_shim(
        layer_type="workflow",
        impact_scope="workflow-default",
        proposed_change=proposed_change,
    )
    writeback_id = _insert_workflow_promotion_writeback(
        conn,
        workflow_key=workflow_key,
        proposed_change=proposed_change,
        rationale=rationale,
        actor=actor,
        policy=policy,
    )
    workflows = load_workflow_registry()
    workflow = workflows.get(workflow_key)
    from_state = workflow.lifecycle_state if workflow is not None else None
    lifecycle_id = f"workflow-promotion-{uuid.uuid4()}"
    now = _now_iso()
    conn.execute(
        """
        INSERT INTO promotion_lifecycle_items (
          id, item_kind, item_key, source_run_id, status, evidence_json, status_reason,
          created_at, updated_at, metadata_json
        )
        VALUES (?, 'workflow', ?, NULL, 'proposed', ?, ?, ?, ?, ?)
        """,
        (
            lifecycle_id,
            workflow_key,
            _json(evidence_summary),
            rationale,
            now,
            now,
            _json(
                {
                    "actor": actor,
                    "target_state": to_state,
                    "approval_writeback_id": writeback_id,
                    "from_state": from_state,
                }
            ),
        ),
    )
    return {
        "writeback_id": writeback_id,
        "lifecycle_id": lifecycle_id,
        "requires_approval": bool(policy["requires_approval"]),
        "rationale": policy.get("reason"),
    }


def propose_asset_promotion(
    conn: sqlite3.Connection,
    *,
    asset_kind: AssetKind,
    asset_key: str,
    to_state: AssetLifecycleState,
    evidence: dict[str, Any],
    actor: str,
    rationale: str | None = None,
) -> dict[str, Any]:
    ensure_workflow_promotion_schema(conn)
    summary = rationale or f"Promote {asset_kind} {asset_key} to {to_state}"
    proposed_change = {
        "asset_kind": asset_kind,
        "asset_key": asset_key,
        "to_state": to_state,
        "evidence": evidence,
    }
    policy = writeback_approval_policy_shim(
        layer_type=asset_kind,
        impact_scope=f"{asset_kind}-default",
        proposed_change=proposed_change,
    )
    writeback_id = f"writeback-{uuid.uuid4()}"
    now = _now_iso()
    conn.execute(
        """
        INSERT INTO improvement_writebacks (
          id, run_id, project_id, layer_type, layer_key, title, summary,
          evidence_json, proposed_change_json, impact_scope, status, requires_approval,
          approval_reason, token_regressive, created_at, updated_at
        )
        VALUES (?, NULL, NULL, ?, ?, ?, ?, ?, ?, ?, 'proposed', ?, ?, 0, ?, ?)
        """,
        (
            writeback_id,
            asset_kind,
            asset_key,
            f"Promote {asset_kind} {asset_key}",
            summary,
            _json(evidence),
            _json({**proposed_change, "actor": actor, "approval_policy": policy}),
            f"{asset_kind}-default",
            1 if policy["requires_approval"] else 0,
            policy.get("reason"),
            now,
            now,
        ),
    )
    lifecycle_id = f"{asset_kind}-promotion-{uuid.uuid4()}"
    conn.execute(
        """
        INSERT INTO promotion_lifecycle_items (
          id, item_kind, item_key, source_run_id, status, evidence_json, status_reason,
          created_at, updated_at, metadata_json
        )
        VALUES (?, ?, ?, ?, 'proposed', ?, ?, ?, ?, ?)
        """,
        (
            lifecycle_id,
            asset_kind,
            asset_key,
            evidence.get("run_id")
            or evidence.get("divergent_run_id")
            or evidence.get("experiment_id"),
            _json(evidence),
            summary,
            now,
            now,
            _json(
                {
                    "actor": actor,
                    "target_state": to_state,
                    "approval_writeback_id": writeback_id,
                    "source": evidence.get("source"),
                }
            ),
        ),
    )
    return {
        "writeback_id": writeback_id,
        "lifecycle_id": lifecycle_id,
        "requires_approval": bool(policy["requires_approval"]),
        "rationale": policy.get("reason"),
    }


def finalize_workflow_promotion(
    conn: sqlite3.Connection,
    *,
    lifecycle_id: str,
    approval_writeback_id: str,
    actor: str,
) -> dict[str, Any]:
    ensure_workflow_promotion_schema(conn)
    writeback = conn.execute(
        "SELECT status FROM improvement_writebacks WHERE id = ?",
        (approval_writeback_id,),
    ).fetchone()
    status = str(writeback[0]) if writeback else "missing"
    if status != "approved":
        raise ValueError(
            f"Cannot finalize promotion: writeback {approval_writeback_id} is {status!r}, must be 'approved'"
        )
    row = conn.execute(
        """
        SELECT status, status_reason, metadata_json
        FROM promotion_lifecycle_items
        WHERE id = ?
        """,
        (lifecycle_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Unknown lifecycle item: {lifecycle_id}")
    metadata = _json_dict(row[2])
    target_state = str(metadata.get("target_state", ""))
    if not target_state:
        raise ValueError(f"Lifecycle item {lifecycle_id} has no target_state metadata")
    previous_status = str(row[0])
    finalized_at = _now_iso()
    conn.execute(
        """
        UPDATE promotion_lifecycle_items
        SET status = ?,
            status_reason = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            target_state,
            f"{row[1]} | finalized by {actor}",
            finalized_at,
            lifecycle_id,
        ),
    )
    return {
        "lifecycle_id": lifecycle_id,
        "previous_status": previous_status,
        "new_status": target_state,
        "finalized_at": finalized_at,
    }


__all__ = [
    "WorkflowEffectiveness",
    "compare_workflow_effectiveness",
    "finalize_workflow_promotion",
    "promote_asset",
    "propose_asset_promotion",
    "propose_workflow_promotion",
]
