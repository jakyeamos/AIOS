#!/usr/bin/env python3
"""
AIOS: purge-noise-patterns.py
Discard low-signal pattern backlog (kb-architecture audit Phase 0).

Targets patterns with class in personal, observation, or error that were never
human-approved. Idempotent — safe to re-run.

Usage:
  python3 ~/AIOS/bin/purge-noise-patterns.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.storage import connect as connect_storage  # noqa: E402

DB = Path(os.environ.get("AIOS_DB", str(Path.home() / "AIOS" / "data" / "aios.db"))).expanduser()
LOG = Path(os.path.expanduser("~/AIOS/logs/purge-noise-patterns-latest.json"))

NOISE_CLASSES = ("personal", "observation", "error")


def _count_candidates(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        f"""
        SELECT class, status, state, COUNT(*) AS n
        FROM patterns
        WHERE class IN ({",".join("?" * len(NOISE_CLASSES))})
          AND human_approved = 0
          AND status != 'discarded'
        GROUP BY class, status, state
        ORDER BY n DESC
        """,
        NOISE_CLASSES,
    ).fetchall()
    return [{"class": row[0], "status": row[1], "state": row[2], "count": row[3]} for row in rows]


def purge_noise_patterns(conn: sqlite3.Connection, *, dry_run: bool = False) -> dict:
    before = _count_candidates(conn)
    total_before = sum(item["count"] for item in before)

    if dry_run:
        return {
            "dry_run": True,
            "would_discard": total_before,
            "breakdown_before": before,
        }

    cursor = conn.execute(
        f"""
        UPDATE patterns
        SET status = 'discarded',
            state = 'discarded'
        WHERE class IN ({",".join("?" * len(NOISE_CLASSES))})
          AND human_approved = 0
          AND status != 'discarded'
        """,
        NOISE_CLASSES,
    )
    conn.commit()
    after = _count_candidates(conn)
    purged_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    return {
        "dry_run": False,
        "discarded": cursor.rowcount,
        "breakdown_before": before,
        "remaining_non_discarded": after,
        "purged_at": purged_at,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not DB.exists():
        print(json.dumps({"ok": False, "error": f"database not found: {DB}"}, indent=2))
        return 1

    conn = connect_storage(DB)
    try:
        result = purge_noise_patterns(conn, dry_run=args.dry_run)
    finally:
        conn.close()

    result["ok"] = True
    result["db_path"] = str(DB)
    if not args.dry_run:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        LOG.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        result["log_path"] = str(LOG)

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
