"""Stale orchestration-run hygiene: cancel runs that never left the launchpad."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

REAPABLE_STATUSES = ("planned", "ready")


def reap_stale_runs(
    conn: sqlite3.Connection,
    *,
    max_age_days: int = 7,
    dry_run: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    moment = now or datetime.now(UTC)
    cutoff = (moment - timedelta(days=max_age_days)).isoformat()
    placeholders = ", ".join("?" for _ in REAPABLE_STATUSES)
    rows = conn.execute(
        f"""
        SELECT id, project_id, session_id, status, created_at
        FROM orchestration_runs
        WHERE status IN ({placeholders}) AND created_at < ?
        ORDER BY created_at ASC
        """,
        (*REAPABLE_STATUSES, cutoff),
    ).fetchall()

    columns = {row[1] for row in conn.execute("PRAGMA table_info(orchestration_runs)")}
    timestamp = moment.strftime("%Y-%m-%dT%H:%M:%SZ")
    reaped: list[dict[str, Any]] = []
    for row in rows:
        run_id, project_id, session_id, status, created_at = (
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
        )
        reaped.append(
            {
                "run_id": str(run_id),
                "previous_status": str(status),
                "created_at": str(created_at),
            }
        )
        if dry_run:
            continue
        reason = json.dumps(
            {
                "kind": "stale-run-reaper",
                "previous_status": str(status),
                "max_age_days": max_age_days,
            }
        )
        assignments = ["status = 'canceled'", "status_reason_json = ?", "updated_at = ?"]
        values: list[Any] = [reason, timestamp]
        if "canceled_at" in columns:
            assignments.append("canceled_at = ?")
            values.append(timestamp)
        conn.execute(
            f"UPDATE orchestration_runs SET {', '.join(assignments)} WHERE id = ?",
            (*values, run_id),
        )
        conn.execute(
            """
            INSERT INTO orchestration_run_events (
                id, run_id, project_id, session_id, event_type, from_status,
                to_status, summary, reason_json, metadata_json, created_at
            )
            VALUES (?, ?, ?, ?, 'stale_run_reaped', ?, 'canceled', ?, ?, '{}', ?)
            """,
            (
                f"run-event-{uuid.uuid4()}",
                run_id,
                project_id,
                session_id,
                status,
                f"Run stale in {status} for over {max_age_days} day(s); canceled by reaper.",
                reason,
                timestamp,
            ),
        )

    return {
        "count": len(reaped),
        "reaped": reaped,
        "cutoff": cutoff,
        "max_age_days": max_age_days,
        "dry_run": dry_run,
    }
