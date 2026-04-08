#!/usr/bin/env python3
"""
AIOS: contradict-pattern.py
Record a contradiction event. Demotes rule → hypothesis immediately.
Updates confidence downward. Never silent — logs to vault and maintenance log.

Usage:
  python3 contradict-pattern.py --id <pattern_id> [--session <id>] --note "what contradicted it"
  python3 contradict-pattern.py --title-contains "prisma decimal" --note "..."
"""

import argparse
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

DB = os.path.expanduser("~/AIOS/data/aios.db")
CONTRADICTION_LOG = os.path.expanduser("~/AIOS/logs/contradictions.log")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_contradiction(title: str, old_state: str, new_state: str, note: str) -> None:
    ts = now()
    try:
        with open(CONTRADICTION_LOG, "a") as f:
            f.write(f"{ts}  [{old_state}→{new_state}]  {title[:80]}\n  note: {note}\n\n")
    except Exception:
        pass


def contradict(conn: sqlite3.Connection, pid: str, session_id: str | None, note: str) -> None:
    if not note:
        print("Error: --note is required. Contradictions must be documented.")
        return

    conn.row_factory = sqlite3.Row
    row = dict(conn.execute("SELECT * FROM patterns WHERE id=?", (pid,)).fetchone() or {})
    conn.row_factory = None

    if not row:
        print(f"Pattern not found: {pid}")
        return

    old_state = row["state"]
    if old_state == "dormant":
        print(f"Pattern is dormant — cannot contradict. Use confirm-pattern.py to reactivate first.")
        return

    new_count = (row["contradiction_count"] or 0) + 1
    new_conf = max((row["confidence"] or 0.5) - 0.15, 0.10)

    # Rules get demoted to hypothesis on any contradiction (immediate)
    new_state = old_state
    if old_state == "rule":
        new_state = "hypothesis"

    conn.execute(
        """UPDATE patterns
           SET contradiction_count=?, confidence=?, last_contradicted_at=?,
               state=?, human_approved=CASE WHEN ? = 'hypothesis' THEN 0 ELSE human_approved END
           WHERE id=?""",
        (new_count, new_conf, now(), new_state, new_state, pid),
    )

    conn.execute(
        """INSERT INTO pattern_events
           (id, pattern_id, event_type, session_id, source_type, notes, event_time)
           VALUES (?, ?, 'contradiction', ?, 'manual', ?, ?)""",
        (str(uuid.uuid4()), pid, session_id, note, now()),
    )
    conn.commit()

    log_contradiction(row["title"], old_state, new_state, note)

    print(f"Contradiction recorded: '{row['title'][:60]}'")
    print(f"  {old_state} → {new_state}  confidence={new_conf:.2f}  contradiction_count={new_count}")

    if new_state == "hypothesis":
        print("  Rule demoted. human_approved reset to 0. Re-approve after re-confirmation.")
    if new_conf <= 0.25:
        print("  Warning: confidence very low. Consider discarding via review-observations.py.")


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
    parser.add_argument("--id", help="Pattern ID to contradict")
    parser.add_argument("--title-contains", help="Find pattern by title fragment")
    parser.add_argument("--session", help="Session ID where contradiction occurred")
    parser.add_argument("--note", default="", help="Required: what contradicted this pattern")
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

    contradict(conn, pid, args.session, args.note)
    conn.close()


if __name__ == "__main__":
    main()
