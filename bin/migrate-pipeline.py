#!/usr/bin/env python3
"""
AIOS: migrate-pipeline.py
Schema migration + state rename for notice→hypothesis→rule pipeline.

Safe to run multiple times (idempotent).
"""

import os
import sqlite3
from datetime import UTC, datetime

DB = os.path.expanduser("~/AIOS/data/aios.db")


def col_exists(conn, table, col):
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    return col in cols


def main():
    conn = sqlite3.connect(DB)

    # 1. Add new columns (idempotent)
    new_cols = [
        ("frequency_score", "REAL    DEFAULT 0"),
        ("impact_score", "REAL    DEFAULT 0"),
        ("frequency_count", "INTEGER DEFAULT 0"),
        ("source_sessions", "INTEGER DEFAULT 0"),
        ("last_seen_at", "TEXT"),
    ]
    for col, typedef in new_cols:
        if not col_exists(conn, "patterns", col):
            conn.execute(f"ALTER TABLE patterns ADD COLUMN {col} {typedef}")
            print(f"  added column: {col}")
        else:
            print(f"  skip (exists): {col}")

    # 2. Rename states
    renamed = conn.execute("UPDATE patterns SET state='notice' WHERE state='observation'").rowcount
    print(f"  observation → notice: {renamed} rows")

    renamed = conn.execute(
        "UPDATE patterns SET state='hypothesis' WHERE state='knowledge'"
    ).rowcount
    print(f"  knowledge → hypothesis: {renamed} rows")

    # 3. Recreate active_rules view (still state='rule')
    conn.execute("DROP VIEW IF EXISTS active_rules")
    conn.execute("""
        CREATE VIEW active_rules AS
        SELECT * FROM patterns
        WHERE state = 'rule' AND human_approved = 1
        ORDER BY confidence DESC
    """)
    print("  active_rules view refreshed")

    # 4. Create processed_files table for idempotent extraction tracking
    conn.execute("""
        CREATE TABLE IF NOT EXISTS processed_files (
            path        TEXT PRIMARY KEY,
            processed_at TEXT NOT NULL
        )
    """)
    print("  processed_files table ready")

    conn.commit()
    conn.close()
    print(f"\nMigration complete — {datetime.now(UTC).isoformat()}")


if __name__ == "__main__":
    main()
