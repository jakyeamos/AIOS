from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, TypedDict

BACKFILL_PRIORITY_BUCKETS = {
    "foundational",
    "high_leverage",
    "quick_wins",
    "blocked",
    "waived_deferred",
}
BACKFILL_STATUSES = {"open", "in_progress", "blocked", "done"}
BACKFILL_MUTABLE_FIELDS = {
    "taskId",
    "owner",
    "status",
    "priorityBucket",
    "blocked",
    "blockedReason",
    "dueAt",
    "reviewAt",
}


class StandardsBackfillTask(TypedDict):
    id: str
    project_id: str
    snapshot_id: str
    delta_item_id: str
    standard_id: str
    title: str
    problem_statement: str
    expected_state: str
    acceptance_criteria_json: str
    effort: float
    dependency_chain_json: str
    expected_health_impact: float
    owner: str | None
    blocked_reason: str | None
    due_at: str | None
    review_at: str | None
    priority_score: float
    priority_bucket: str
    blocked: bool
    status: str
    updated_at: str


def _optional_string(payload: Mapping[str, object], key: str, *, max_length: int) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string or null")
    if len(value) > max_length:
        raise ValueError(f"{key} exceeds the {max_length}-character limit")
    return value


def _required_task_id(payload: Mapping[str, object]) -> str:
    value = payload.get("taskId")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("taskId is required")
    if len(value) > 200:
        raise ValueError("taskId exceeds the 200-character limit")
    return value


def _validate_payload(payload: Mapping[str, object]) -> str:
    unknown = set(payload) - BACKFILL_MUTABLE_FIELDS
    if unknown:
        names = ", ".join(sorted(str(name) for name in unknown))
        raise ValueError(f"Unsupported standards backfill fields: {names}")

    task_id = _required_task_id(payload)
    owner = _optional_string(payload, "owner", max_length=120)
    blocked_reason = _optional_string(payload, "blockedReason", max_length=400)
    due_at = _optional_string(payload, "dueAt", max_length=40)
    review_at = _optional_string(payload, "reviewAt", max_length=40)
    del owner, blocked_reason, due_at, review_at

    status = payload.get("status")
    if status is not None and (not isinstance(status, str) or status not in BACKFILL_STATUSES):
        raise ValueError("status must be one of open, in_progress, blocked, or done")

    priority_bucket = payload.get("priorityBucket")
    if priority_bucket is not None and (
        not isinstance(priority_bucket, str) or priority_bucket not in BACKFILL_PRIORITY_BUCKETS
    ):
        raise ValueError("priorityBucket is not a recognized standards backfill bucket")

    blocked = payload.get("blocked")
    if blocked is not None and not isinstance(blocked, bool):
        raise ValueError("blocked must be a boolean")
    return task_id


def _row_payload(row: sqlite3.Row) -> StandardsBackfillTask:
    return {
        "id": str(row["id"]),
        "project_id": str(row["project_id"]),
        "snapshot_id": str(row["snapshot_id"]),
        "delta_item_id": str(row["delta_item_id"]),
        "standard_id": str(row["standard_id"]),
        "title": str(row["title"]),
        "problem_statement": str(row["problem_statement"]),
        "expected_state": str(row["expected_state"]),
        "acceptance_criteria_json": str(row["acceptance_criteria_json"]),
        "effort": float(row["effort"]),
        "dependency_chain_json": str(row["dependency_chain_json"]),
        "expected_health_impact": float(row["expected_health_impact"]),
        "owner": str(row["owner"]) if row["owner"] is not None else None,
        "blocked_reason": (
            str(row["blocked_reason"]) if row["blocked_reason"] is not None else None
        ),
        "due_at": str(row["due_at"]) if row["due_at"] is not None else None,
        "review_at": str(row["review_at"]) if row["review_at"] is not None else None,
        "priority_score": float(row["priority_score"]),
        "priority_bucket": str(row["priority_bucket"]),
        "blocked": bool(row["blocked"]),
        "status": str(row["status"]),
        "updated_at": str(row["updated_at"]),
    }


def update_standards_backfill_task(
    conn: sqlite3.Connection,
    payload: Mapping[str, object],
) -> StandardsBackfillTask:
    """Apply one standards backfill state transition as the Python owner."""

    task_id = _validate_payload(payload)
    current = conn.execute(
        "SELECT id FROM standards_backfill_tasks WHERE id = ? LIMIT 1",
        (task_id,),
    ).fetchone()
    if current is None:
        raise LookupError("Standards backfill task not found")

    updates: list[str] = []
    values: list[Any] = []
    columns = {
        "owner": "owner",
        "status": "status",
        "priorityBucket": "priority_bucket",
        "blocked": "blocked",
        "blockedReason": "blocked_reason",
        "dueAt": "due_at",
        "reviewAt": "review_at",
    }
    for payload_key, column in columns.items():
        if payload_key not in payload:
            continue
        value = payload[payload_key]
        if payload_key == "blocked":
            value = int(bool(value))
        updates.append(f"{column} = ?")
        values.append(value)

    if not updates:
        raise ValueError("At least one standards backfill field must be provided")

    updates.append("updated_at = ?")
    values.append(datetime.now(UTC).isoformat())
    values.append(task_id)
    with conn:
        conn.execute(
            f"UPDATE standards_backfill_tasks SET {', '.join(updates)} WHERE id = ?",
            values,
        )
        row = conn.execute(
            "SELECT * FROM standards_backfill_tasks WHERE id = ? LIMIT 1",
            (task_id,),
        ).fetchone()
    if row is None:
        raise RuntimeError("Standards backfill task was updated but could not be reloaded")
    return _row_payload(row)
