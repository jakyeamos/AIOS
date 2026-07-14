#!/usr/bin/env python3
"""
Safely abandon stale open sessions that never captured prompts.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "bin") not in sys.path:
    sys.path.insert(0, str(ROOT / "bin"))

from hook_lifecycle import current_session_id  # noqa: E402

from services.storage import connect as connect_storage  # noqa: E402


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def cutoff_iso(days: int) -> str:
    return (datetime.now(UTC) - timedelta(days=days)).isoformat()


def stale_sessions(
    conn: sqlite3.Connection,
    *,
    older_than_days: int,
    current_id: str | None,
) -> list[sqlite3.Row]:
    rows = conn.execute(
        """
        SELECT s.id, s.project_id, s.started_at, s.cwd, s.objective
        FROM sessions s
        WHERE s.status = 'open'
          AND s.started_at < ?
          AND (? IS NULL OR s.id != ?)
          AND NOT EXISTS (
              SELECT 1 FROM prompts_used p WHERE p.session_id = s.id
          )
          AND NOT EXISTS (
              SELECT 1 FROM tool_events te
              WHERE te.session_id = s.id AND te.event_type != 'SessionStart'
          )
          AND s.run_id IS NULL
          AND s.invocation_id IS NULL
        ORDER BY s.started_at
        """,
        (cutoff_iso(older_than_days), current_id, current_id),
    ).fetchall()
    return list(rows)


def abandon_sessions(conn: sqlite3.Connection, rows: list[sqlite3.Row], *, reason: str) -> None:
    ended_at = now_iso()
    for row in rows:
        session_id = str(row["id"])
        conn.execute(
            """
            UPDATE sessions
            SET status = 'abandoned',
                ended_at = COALESCE(ended_at, ?)
            WHERE id = ? AND status = 'open'
            """,
            (ended_at, session_id),
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO tool_events (id, session_id, source_tool, event_type, event_time, payload_json)
            VALUES (?, ?, 'aios-repair', 'SessionAbandonedBackfill', ?, ?)
            """,
            (
                f"{session_id}-abandoned-backfill",
                session_id,
                ended_at,
                json.dumps({"reason": reason, "started_at": row["started_at"], "cwd": row["cwd"]}),
            ),
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=os.environ.get("AIOS_DB", str(ROOT / "data" / "aios.db")))
    parser.add_argument("--logs-dir", default=str(ROOT / "logs"))
    parser.add_argument("--older-than-days", type=int, default=2)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    conn = connect_storage(args.db)
    current_id = current_session_id(args.logs_dir)
    rows = stale_sessions(conn, older_than_days=args.older_than_days, current_id=current_id)

    result = {
        "apply": args.apply,
        "current_session": current_id,
        "older_than_days": args.older_than_days,
        "candidate_count": len(rows),
        "candidates": [
            {
                "id": row["id"],
                "started_at": row["started_at"],
                "cwd": row["cwd"],
                "objective": row["objective"],
            }
            for row in rows
        ],
    }

    if args.apply and rows:
        abandon_sessions(
            conn,
            rows,
            reason="stale open session with no prompt/tool activity beyond SessionStart",
        )
        conn.commit()
        result["abandoned_count"] = len(rows)
    else:
        result["abandoned_count"] = 0

    conn.close()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
