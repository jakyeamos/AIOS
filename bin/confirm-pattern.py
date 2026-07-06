#!/usr/bin/env python3
"""
AIOS: confirm-pattern.py
Record a confirmation event for a pattern. Updates count and confidence.
Checks if hypothesis threshold is met (flags but does not auto-promote).

Usage:
  python3 confirm-pattern.py --id <pattern_id> [--session <session_id>] [--note "text"]
  python3 confirm-pattern.py --title-contains "prisma decimal"
"""

import argparse
import os
import sqlite3
import uuid
from datetime import UTC, datetime

DB = os.path.expanduser("~/AIOS/data/aios.db")

CLASS_THRESHOLDS = {
    "bug_fix": 2,
    "failure": 2,
    "architecture": 3,
    "workflow": 3,
    "assumption": 3,
    "prompt": 4,
}


def now() -> str:
    return datetime.now(UTC).isoformat()


def confirm(conn: sqlite3.Connection, pid: str, session_id: str | None, note: str) -> None:
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM patterns WHERE id=?", (pid,)).fetchone()
    conn.row_factory = None

    if not row:
        print(f"Pattern not found: {pid}")
        return

    row = dict(row)
    if row["state"] not in ("hypothesis", "knowledge", "rule", "observation"):
        print(f"Cannot confirm pattern in state '{row['state']}'")
        return

    # Update counts and confidence
    new_count = (row["confirmation_count"] or 0) + 1
    new_conf = min((row["confidence"] or 0.5) + 0.05, 0.95)

    conn.execute(
        """UPDATE patterns
           SET confirmation_count=?, confidence=?, last_confirmed_at=?,
               state=CASE WHEN state='knowledge' THEN 'hypothesis' ELSE state END
           WHERE id=?""",
        (new_count, new_conf, now(), pid),
    )

    conn.execute(
        """INSERT INTO pattern_events
           (id, pattern_id, event_type, session_id, source_type, notes, event_time)
           VALUES (?, ?, 'confirmation', ?, 'manual', ?, ?)""",
        (str(uuid.uuid4()), pid, session_id, note or "manual confirmation", now()),
    )
    conn.commit()

    # Reload updated state
    conn.row_factory = sqlite3.Row
    updated = dict(conn.execute("SELECT * FROM patterns WHERE id=?", (pid,)).fetchone())
    conn.row_factory = None

    threshold = CLASS_THRESHOLDS.get(row["class"] or "", 3)
    print(f"Confirmed: '{row['title'][:60]}'")
    print(f"  count={new_count}  confidence={new_conf:.2f}  state={updated['state']}")

    if updated["state"] == "hypothesis" and new_count >= threshold:
        print(
            f"  Threshold met ({new_count}/{threshold}). Run approve-pattern.py --id {pid} to promote to rule."
        )
    elif updated["state"] == "hypothesis":
        print(f"  Progress: {new_count}/{threshold} confirmations needed for rule promotion.")


def find_by_title(conn: sqlite3.Connection, fragment: str) -> list[dict]:
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM patterns WHERE title LIKE ? ORDER BY confidence DESC LIMIT 10",
        (f"%{fragment}%",),
    ).fetchall()
    conn.row_factory = None
    return [dict(r) for r in rows]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", help="Pattern ID to confirm")
    parser.add_argument("--title-contains", help="Find pattern by title fragment")
    parser.add_argument("--session", help="Session ID that produced the confirmation")
    parser.add_argument("--note", default="", help="Optional context note")
    args = parser.parse_args()

    conn = sqlite3.connect(DB)

    pid = args.id
    if not pid and args.title_contains:
        matches = find_by_title(conn, args.title_contains)
        if not matches:
            print(f"No patterns found matching '{args.title_contains}'")
            conn.close()
            return
        if len(matches) == 1:
            pid = matches[0]["id"]
            print(f"Found: {matches[0]['title']}")
        else:
            print("Multiple matches:")
            for r in matches:
                print(f"  {r['id']}  {r['title'][:60]}")
            print("Re-run with --id <id>")
            conn.close()
            return

    if not pid:
        parser.print_help()
        conn.close()
        return

    confirm(conn, pid, args.session, args.note)
    conn.close()


if __name__ == "__main__":
    main()
