#!/usr/bin/env python3
"""
AIOS: migrate-patterns.py
One-time schema migration for the knowledge layer.

What this does:
  1. ALTER TABLE patterns — adds new columns (backward-safe, all have defaults)
  2. CREATE TABLE pattern_events — append-only provenance log
  3. CREATE VIEWs — active_rules, active_hypotheses, domain_stats
  4. Migrate existing row data (status → state, quarantine all human_approved)
  5. CREATE new indexes

Safe to run multiple times — uses IF NOT EXISTS and checks before ALTER.
"""

import os
import sqlite3
from datetime import datetime, timezone

DB = os.path.expanduser("~/AIOS/data/aios.db")


def column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


def migrate(conn: sqlite3.Connection) -> None:
    ts = datetime.now(timezone.utc).isoformat()

    # -----------------------------------------------------------------------
    # Step 1: Extend patterns table (backward-safe ALTER TABLE)
    # -----------------------------------------------------------------------
    new_columns = [
        ("domain",                "TEXT DEFAULT 'unclassified'"),
        ("state",                 "TEXT DEFAULT 'observation'"),
        ("body",                  "TEXT"),
        ("source_type",           "TEXT DEFAULT 'bigram'"),
        ("confirmation_count",    "INTEGER DEFAULT 0"),
        ("contradiction_count",   "INTEGER DEFAULT 0"),
        ("last_confirmed_at",     "TEXT"),
        ("last_contradicted_at",  "TEXT"),
        ("first_observed_at",     "TEXT"),
        ("human_approved",        "INTEGER DEFAULT 0"),
        ("project_id",            "TEXT"),
    ]

    added = []
    for col, defn in new_columns:
        if not column_exists(conn, "patterns", col):
            conn.execute(f"ALTER TABLE patterns ADD COLUMN {col} {defn}")
            added.append(col)

    print(f"Added {len(added)} columns to patterns: {added or '(none — already present)'}")

    # -----------------------------------------------------------------------
    # Step 2: Migrate existing data
    # -----------------------------------------------------------------------
    # Map old status → new state
    conn.execute("UPDATE patterns SET state = 'rule'        WHERE status = 'promoted' AND state = 'observation'")
    conn.execute("UPDATE patterns SET state = 'observation' WHERE status IN ('candidate', 'discarded') AND state = 'observation'")

    # Quarantine everything — nothing injects as a rule until manually approved
    conn.execute("UPDATE patterns SET human_approved = 0")

    # Backfill first_observed_at from created_at
    conn.execute("UPDATE patterns SET first_observed_at = created_at WHERE first_observed_at IS NULL")

    # Domain classification based on class
    domain_map = [
        ("bug_fix",      "debugging"),
        ("failure",      "debugging"),
        ("prompt",       "prompting"),
        ("architecture", "architecture"),
        ("refactor",     "architecture"),
        ("workflow",     "workflow"),
        ("assumption",   "workflow"),
    ]
    for class_, domain in domain_map:
        conn.execute(
            "UPDATE patterns SET domain = ? WHERE class = ? AND domain = 'unclassified'",
            (domain, class_),
        )

    stats = conn.execute(
        "SELECT state, COUNT(*) FROM patterns GROUP BY state"
    ).fetchall()
    print("Post-migration state distribution:", dict(stats))

    domain_stats = conn.execute(
        "SELECT domain, COUNT(*) FROM patterns GROUP BY domain"
    ).fetchall()
    print("Domain distribution:", dict(domain_stats))

    # -----------------------------------------------------------------------
    # Step 3: Create pattern_events table
    # -----------------------------------------------------------------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pattern_events (
            id            TEXT PRIMARY KEY,
            pattern_id    TEXT NOT NULL REFERENCES patterns(id),
            event_type    TEXT NOT NULL,
            session_id    TEXT REFERENCES sessions(id),
            source_type   TEXT NOT NULL DEFAULT 'manual',
            source_id     TEXT,
            source_path   TEXT,
            notes         TEXT,
            event_time    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pevents_pattern ON pattern_events(pattern_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pevents_type ON pattern_events(event_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pevents_time ON pattern_events(event_time)")
    print("Created pattern_events table and indexes")

    # -----------------------------------------------------------------------
    # Step 4: Create views
    # -----------------------------------------------------------------------
    conn.execute("DROP VIEW IF EXISTS active_rules")
    conn.execute("""
        CREATE VIEW active_rules AS
            SELECT * FROM patterns
            WHERE state = 'rule' AND human_approved = 1
            ORDER BY confidence DESC
    """)

    conn.execute("DROP VIEW IF EXISTS active_hypotheses")
    conn.execute("""
        CREATE VIEW active_hypotheses AS
            SELECT *,
                (CASE class
                    WHEN 'bug_fix'      THEN 2
                    WHEN 'failure'      THEN 2
                    WHEN 'architecture' THEN 3
                    WHEN 'workflow'     THEN 3
                    WHEN 'assumption'   THEN 3
                    WHEN 'prompt'       THEN 4
                    ELSE 3
                END - confirmation_count) AS confirmations_needed
            FROM patterns
            WHERE state = 'hypothesis'
            ORDER BY confirmations_needed ASC
    """)

    conn.execute("DROP VIEW IF EXISTS domain_stats")
    conn.execute("""
        CREATE VIEW domain_stats AS
            SELECT
                domain,
                SUM(CASE WHEN state='rule'        THEN 1 ELSE 0 END) AS rule_count,
                SUM(CASE WHEN state='hypothesis'  THEN 1 ELSE 0 END) AS hypothesis_count,
                SUM(CASE WHEN state='knowledge'   THEN 1 ELSE 0 END) AS knowledge_count,
                SUM(CASE WHEN state='observation' THEN 1 ELSE 0 END) AS observation_count,
                MAX(last_confirmed_at) AS last_activity
            FROM patterns GROUP BY domain
    """)
    print("Created views: active_rules, active_hypotheses, domain_stats")

    # -----------------------------------------------------------------------
    # Step 5: New indexes on patterns
    # -----------------------------------------------------------------------
    conn.execute("CREATE INDEX IF NOT EXISTS idx_patterns_domain ON patterns(domain)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_patterns_state ON patterns(state)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_patterns_confidence ON patterns(confidence)")
    print("Created indexes on patterns(domain, state, confidence)")


def main() -> None:
    print(f"Migrating {DB}")
    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA foreign_keys = ON")

    migrate(conn)
    conn.commit()
    conn.close()

    print("Migration complete.")


if __name__ == "__main__":
    main()
