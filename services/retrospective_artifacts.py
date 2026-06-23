from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any

from services.workflow_learning import retrospective_artifact_learning_proposal

OUTCOMES = {"success", "partial", "failure"}
RISKS = {"low", "medium", "high"}
SHOULD_BECOME = {
    "rule",
    "check",
    "playbook",
    "benchmark",
    "memory",
    "model_routing_update",
    "doc",
}
ROOT_CAUSE_CATEGORIES = {
    "missing_context",
    "wrong_model",
    "bad_decomposition",
    "weak_verification",
    "missing_test",
    "unclear_acceptance_criteria",
    "tool_failure",
    "bad_retrieval",
    "overbroad_edit",
    "architecture_misunderstanding",
    "second_brain_miss",
    "prompt_template_flaw",
    "deterministic_harness_gap",
}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def ensure_retrospective_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS retrospective_artifacts (
          id TEXT PRIMARY KEY,
          task_id TEXT NOT NULL,
          outcome TEXT NOT NULL,
          failed_phase TEXT,
          root_cause_category TEXT NOT NULL,
          evidence_refs_json TEXT NOT NULL DEFAULT '[]',
          harness_gap TEXT NOT NULL,
          proposed_change TEXT NOT NULL,
          target_file_or_component TEXT NOT NULL,
          risk TEXT NOT NULL,
          auto_apply INTEGER NOT NULL DEFAULT 0,
          should_become TEXT NOT NULL,
          learning_proposal_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_retrospective_artifacts_task
          ON retrospective_artifacts(task_id, created_at DESC)
        """
    )


def _require_member(value: str, allowed: set[str], field: str) -> str:
    if value not in allowed:
        raise ValueError(f"Unsupported {field}: {value}")
    return value


def record_retrospective_artifact(
    conn: sqlite3.Connection,
    *,
    task_id: str,
    outcome: str,
    failed_phase: str | None,
    root_cause_category: str,
    evidence_refs: list[dict[str, Any]],
    harness_gap: str,
    proposed_change: str,
    target_file_or_component: str,
    risk: str,
    should_become: str,
) -> str:
    ensure_retrospective_schema(conn)
    artifact_id = f"retro-{uuid.uuid4()}"
    artifact = {
        "id": artifact_id,
        "task_id": task_id,
        "outcome": _require_member(outcome, OUTCOMES, "outcome"),
        "failed_phase": failed_phase,
        "root_cause_category": _require_member(
            root_cause_category, ROOT_CAUSE_CATEGORIES, "root_cause_category"
        ),
        "evidence_refs": evidence_refs,
        "harness_gap": harness_gap,
        "proposed_change": proposed_change,
        "target_file_or_component": target_file_or_component,
        "risk": _require_member(risk, RISKS, "risk"),
        "auto_apply": False,
        "should_become": _require_member(should_become, SHOULD_BECOME, "should_become"),
    }
    learning_proposal = retrospective_artifact_learning_proposal(artifact)
    conn.execute(
        """
        INSERT INTO retrospective_artifacts (
          id, task_id, outcome, failed_phase, root_cause_category, evidence_refs_json,
          harness_gap, proposed_change, target_file_or_component, risk, auto_apply,
          should_become, learning_proposal_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
        """,
        (
            artifact_id,
            artifact["task_id"],
            artifact["outcome"],
            artifact["failed_phase"],
            artifact["root_cause_category"],
            json.dumps(evidence_refs, sort_keys=True),
            artifact["harness_gap"],
            artifact["proposed_change"],
            artifact["target_file_or_component"],
            artifact["risk"],
            artifact["should_become"],
            json.dumps(learning_proposal, sort_keys=True),
            _now_iso(),
        ),
    )
    return artifact_id


def list_retrospective_artifacts(
    conn: sqlite3.Connection, *, task_id: str | None = None
) -> list[dict[str, Any]]:
    ensure_retrospective_schema(conn)
    params: tuple[str, ...] = ()
    where = ""
    if task_id:
        where = "WHERE task_id = ?"
        params = (task_id,)
    return [
        {
            **dict(row),
            "evidence_refs": json.loads(row["evidence_refs_json"] or "[]"),
            "learning_proposal": json.loads(row["learning_proposal_json"] or "{}"),
            "auto_apply": bool(row["auto_apply"]),
        }
        for row in conn.execute(
            f"""
            SELECT *
            FROM retrospective_artifacts
            {where}
            ORDER BY created_at DESC
            LIMIT 100
            """,
            params,
        ).fetchall()
    ]
