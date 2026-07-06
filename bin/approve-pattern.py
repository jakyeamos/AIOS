#!/usr/bin/env python3
"""
AIOS: approve-pattern.py
Set human_approved=1 on a knowledge pattern, validate all 4 promotion gates,
and promote it to 'rule' state if gates pass.

Gates (all four must pass):
  1. confirmation_count >= class_threshold
  2. first_observed_at is at least 14 days ago
  3. Confirmations span at least 2 distinct session IDs
  4. human_approved = 1 (this script sets it)

Usage:
  python3 approve-pattern.py --list               # show approvable patterns
  python3 approve-pattern.py --id <pattern_id>    # approve a specific pattern
  python3 approve-pattern.py --all-knowledge      # interactive approval of all knowledge patterns
"""

import argparse
import os
import sqlite3
import uuid
from datetime import UTC, datetime

DB = os.path.expanduser("~/AIOS/data/aios.db")

CLASS_THRESHOLDS = {
    "bug_fix": 2, "failure": 2,
    "architecture": 3, "workflow": 3, "assumption": 3,
    "prompt": 4,
}


def now() -> str:
    return datetime.now(UTC).isoformat()


def check_gates(conn: sqlite3.Connection, row: dict) -> tuple[bool, list[str]]:
    """Return (all_pass, list_of_failed_gate_messages)."""
    failures = []
    class_ = row["class"] or ""
    threshold = CLASS_THRESHOLDS.get(class_, 3)

    # Gate 1: confirmation count
    if (row["confirmation_count"] or 0) < threshold:
        failures.append(
            f"Gate 1 FAIL: confirmation_count={row['confirmation_count'] or 0} < {threshold} required for class '{class_}'"
        )

    # Gate 2: age >= 14 days
    first = row["first_observed_at"]
    if first:
        try:
            observed = datetime.fromisoformat(first.replace("Z", "+00:00"))
            age_days = (datetime.now(UTC) - observed).days
            if age_days < 14:
                failures.append(f"Gate 2 FAIL: only {age_days} days old, need 14+")
        except ValueError:
            failures.append(f"Gate 2 FAIL: unparseable first_observed_at='{first}'")
    else:
        failures.append("Gate 2 FAIL: first_observed_at is NULL")

    # Gate 3: confirmations from >= 2 distinct sessions
    distinct = conn.execute(
        """SELECT COUNT(DISTINCT session_id) FROM pattern_events
           WHERE pattern_id=? AND event_type='confirmation' AND session_id IS NOT NULL""",
        (row["id"],),
    ).fetchone()[0]
    if distinct < 2:
        failures.append(f"Gate 3 FAIL: only {distinct} distinct confirming session(s), need 2+")

    return (len(failures) == 0, failures)


def list_approvable(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        """SELECT id, class, domain, title, confidence, confirmation_count, first_observed_at
           FROM patterns WHERE state='knowledge' ORDER BY confidence DESC"""
    ).fetchall()
    if not rows:
        print("No patterns in 'knowledge' state. Run review-observations.py first.")
        return
    print(f"\n{'ID':36}  {'domain':12} {'class':12} {'conf':5} {'cnt':3}  title")
    print("-" * 100)
    for r in rows:
        pid, class_, domain, title, conf, cnt, first = r
        print(f"{pid}  {(domain or '?'):12} {(class_ or '?'):12} {conf:.2f}  {cnt or 0:3}  {title[:50]}")


def approve_one(conn: sqlite3.Connection, pid: str, force: bool = False) -> None:
    row = conn.execute("SELECT * FROM patterns WHERE id=?", (pid,)).fetchone()
    if not row:
        print(f"Pattern not found: {pid}")
        return

    conn.row_factory = sqlite3.Row
    row_dict = dict(conn.execute("SELECT * FROM patterns WHERE id=?", (pid,)).fetchone())
    conn.row_factory = None

    if row_dict["state"] not in ("knowledge", "hypothesis"):
        print(f"Pattern is in state '{row_dict['state']}', not 'knowledge'. Cannot approve.")
        return

    all_pass, failures = check_gates(conn, row_dict)

    if not all_pass and not force:
        print(f"\nGate failures for '{row_dict['title'][:60]}':")
        for f in failures:
            print(f"  {f}")
        print("\nPattern not approved. Use --force to override gate checks (document reason).")
        return

    if not all_pass and force:
        print("\nForce-approving despite gate failures:")
        for f in failures:
            print(f"  {f}")

    conn.execute(
        """UPDATE patterns
           SET human_approved=1, state='rule'
           WHERE id=?""",
        (pid,),
    )
    conn.execute(
        """INSERT INTO pattern_events
           (id, pattern_id, event_type, source_type, notes, event_time)
           VALUES (?, ?, 'promotion', 'manual', 'knowledge→rule via approve-pattern.py', ?)""",
        (str(uuid.uuid4()), pid, now()),
    )
    conn.commit()
    print(f"Approved: '{row_dict['title'][:70]}' → rule")


def interactive_approve(conn: sqlite3.Connection) -> None:
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM patterns WHERE state='knowledge' ORDER BY confidence DESC"
    ).fetchall()
    conn.row_factory = None

    if not rows:
        print("No knowledge patterns to approve.")
        return

    approved = skipped = 0
    for row in rows:
        r = dict(row)
        all_pass, failures = check_gates(conn, r)
        print(f"\n{'='*60}")
        print(f"  {r['domain']} / {r['class']}")
        print(f"  {r['title']}")
        print(f"  confidence={r['confidence']:.2f}  confirmations={r['confirmation_count'] or 0}")
        if r.get("body"):
            print(f"  body: {r['body']}")
        if all_pass:
            print("  Gates: ALL PASS")
        else:
            for f in failures:
                print(f"  ⚠ {f}")
        print("\n  (a) approve  (s) skip  (q) quit")
        choice = input("  > ").strip().lower()
        if choice == "q":
            break
        elif choice == "a":
            approve_one(conn, r["id"])
            approved += 1
        else:
            skipped += 1

    print(f"\nApproved: {approved}  Skipped: {skipped}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", action="store_true", help="List patterns in knowledge state")
    parser.add_argument("--id", help="Approve a specific pattern by ID")
    parser.add_argument("--all-knowledge", action="store_true", help="Interactive approval of all knowledge patterns")
    parser.add_argument("--force", action="store_true", help="Skip gate checks (document reason manually)")
    args = parser.parse_args()

    conn = sqlite3.connect(DB)

    if args.list:
        list_approvable(conn)
    elif args.id:
        approve_one(conn, args.id, force=args.force)
    elif args.all_knowledge:
        interactive_approve(conn)
    else:
        parser.print_help()

    conn.close()


if __name__ == "__main__":
    main()
