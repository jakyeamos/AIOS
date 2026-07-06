#!/usr/bin/env python3
"""
AIOS: migrate-lab-integration.py
Add lab integration columns and tables to aios.db.
Safe to run multiple times (idempotent).
"""

import os
import sqlite3
from datetime import UTC, datetime

DB = os.path.expanduser("~/AIOS/data/aios.db")


def col_exists(conn: sqlite3.Connection, table: str, col: str) -> bool:
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    return col in cols


def main() -> None:
    conn = sqlite3.connect(DB)

    # --- patterns: add lab summary columns ---
    lab_cols = [
        ("lab_dispatched_at", "TEXT"),
        ("lab_status", "TEXT"),
        ("last_lab_run_id", "TEXT"),
    ]
    for col, typedef in lab_cols:
        if not col_exists(conn, "patterns", col):
            conn.execute(f"ALTER TABLE patterns ADD COLUMN {col} {typedef}")
            print(f"  added patterns.{col}")
        else:
            print(f"  skip (exists): patterns.{col}")

    # --- lab_runs: append-only experiment history ---
    conn.execute("""
        CREATE TABLE IF NOT EXISTS lab_runs (
            id                TEXT PRIMARY KEY,
            pattern_id        TEXT NOT NULL REFERENCES patterns(id),
            rule_text_snapshot TEXT NOT NULL,
            bundle_id         TEXT,
            patch_type        TEXT NOT NULL,
            patch_payload     TEXT NOT NULL DEFAULT '{}',
            baseline_score    REAL,
            candidate_score   REAL,
            score_delta       REAL,
            pass_delta        REAL,
            holdout_delta     REAL,
            simplicity_delta  REAL,
            micro_delta       REAL,
            outcome           TEXT,
            commit_hash       TEXT,
            notes             TEXT,
            created_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
    """)
    print("  lab_runs table ready")

    # --- rule_eval_bundles: rule artifact + task manifest ---
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rule_eval_bundles (
            id                  TEXT PRIMARY KEY,
            pattern_id          TEXT NOT NULL REFERENCES patterns(id),
            rule_text           TEXT NOT NULL,
            failure_class       TEXT,
            capability_class    TEXT NOT NULL,
            generation_strategy TEXT NOT NULL DEFAULT 'template',
            task_manifest_json  TEXT NOT NULL DEFAULT '[]',
            artifact_path       TEXT,
            created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
    """)
    print("  rule_eval_bundles table ready")

    conn.commit()
    conn.close()
    print(f"\nMigration complete — {datetime.now(UTC).isoformat()}")


if __name__ == "__main__":
    main()
