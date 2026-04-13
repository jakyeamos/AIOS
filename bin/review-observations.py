#!/usr/bin/env python3
"""
AIOS: review-observations.py
Interactive CLI for reviewing patterns in 'observation' state.

For each observation you can:
  (k) keep as observation — skip for now
  (n) promote to knowledge — marks ready for human approval pass
  (d) discard — mark as noise
  (b) add body — annotate with description before promoting
  (q) quit

Usage:
  python3 review-observations.py [--domain <name>] [--limit N]
"""

import argparse
import os
import sqlite3
import uuid
from datetime import UTC, datetime

DB = os.path.expanduser("~/AIOS/data/aios.db")


def now() -> str:
    return datetime.now(UTC).isoformat()


def review(conn: sqlite3.Connection, domain: str | None, limit: int) -> None:
    query = """
        SELECT id, class, domain, title, confidence, evidence, source_type, first_observed_at
        FROM patterns
        WHERE state = 'observation' AND status != 'discarded'
    """
    params: list = []
    if domain:
        query += " AND domain = ?"
        params.append(domain)
    query += " ORDER BY confidence DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    total = conn.execute(
        "SELECT COUNT(*) FROM patterns WHERE state='observation' AND status != 'discarded'"
    ).fetchone()[0]

    if not rows:
        print("No observations to review.")
        return

    print(f"\n{'='*60}")
    print(f"Reviewing {len(rows)} of {total} total observations")
    print(f"{'='*60}\n")

    promoted = discarded = skipped = annotated = 0

    for i, row in enumerate(rows, 1):
        pid, class_, dom, title, confidence, evidence, source_type, first_observed = row

        print(f"\n[{i}/{len(rows)}] {dom} / {class_}")
        print(f"  Title    : {title}")
        print(f"  Confidence: {confidence:.2f}  Source: {source_type or 'bigram'}")
        print(f"  Observed : {first_observed or 'unknown'}")
        print()
        print("  (k) keep  (n) → knowledge  (d) discard  (b) add body + promote  (q) quit")

        while True:
            try:
                choice = input("  > ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                print("\nInterrupted.")
                conn.commit()
                _print_summary(promoted, discarded, skipped, annotated)
                return

            if choice == "q":
                conn.commit()
                _print_summary(promoted, discarded, skipped, annotated)
                return

            elif choice == "k":
                skipped += 1
                break

            elif choice == "n":
                conn.execute(
                    "UPDATE patterns SET state='knowledge', status='promoted' WHERE id=?",
                    (pid,),
                )
                conn.execute(
                    """INSERT INTO pattern_events
                       (id, pattern_id, event_type, source_type, notes, event_time)
                       VALUES (?, ?, 'promotion', 'manual', 'observation→knowledge via review', ?)""",
                    (str(uuid.uuid4()), pid, now()),
                )
                promoted += 1
                print("  → knowledge")
                break

            elif choice == "d":
                conn.execute(
                    "UPDATE patterns SET state='observation', status='discarded' WHERE id=?",
                    (pid,),
                )
                conn.execute(
                    """INSERT INTO pattern_events
                       (id, pattern_id, event_type, source_type, notes, event_time)
                       VALUES (?, ?, 'demotion', 'manual', 'discarded via review', ?)""",
                    (str(uuid.uuid4()), pid, now()),
                )
                discarded += 1
                print("  → discarded")
                break

            elif choice == "b":
                print("  Enter body text (one line, or press Enter to skip):")
                try:
                    body = input("  body> ").strip()
                except (KeyboardInterrupt, EOFError):
                    body = ""
                if body:
                    conn.execute(
                        "UPDATE patterns SET body=?, state='knowledge', status='promoted' WHERE id=?",
                        (body, pid),
                    )
                else:
                    conn.execute(
                        "UPDATE patterns SET state='knowledge', status='promoted' WHERE id=?",
                        (pid,),
                    )
                conn.execute(
                    """INSERT INTO pattern_events
                       (id, pattern_id, event_type, source_type, notes, event_time)
                       VALUES (?, ?, 'promotion', 'manual', 'observation→knowledge with body annotation', ?)""",
                    (str(uuid.uuid4()), pid, now()),
                )
                annotated += 1
                promoted += 1
                print("  → knowledge (with body)")
                break

            else:
                print("  Invalid. Use k/n/d/b/q")

    conn.commit()
    _print_summary(promoted, discarded, skipped, annotated)


def _print_summary(promoted: int, discarded: int, skipped: int, annotated: int) -> None:
    print(f"\n{'='*40}")
    print("Session summary:")
    print(f"  → knowledge : {promoted} ({annotated} with body)")
    print(f"  discarded   : {discarded}")
    print(f"  kept        : {skipped}")
    print()
    print("Run approve-pattern.py to promote knowledge → rule.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", help="Filter by domain (debugging|prompting|architecture|workflow|system)")
    parser.add_argument("--limit", type=int, default=25, help="Max patterns to review per session (default 25)")
    args = parser.parse_args()

    conn = sqlite3.connect(DB)
    try:
        review(conn, args.domain, args.limit)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
