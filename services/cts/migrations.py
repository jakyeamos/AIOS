from __future__ import annotations

import sqlite3

MIGRATIONS: list[tuple[int, str]] = [
    (
        1,
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        );

        CREATE TABLE IF NOT EXISTS repos (
            repo_id TEXT PRIMARY KEY,
            repo_path TEXT NOT NULL,
            name TEXT NOT NULL,
            current_commit TEXT,
            last_full_build_at TEXT,
            last_incremental_at TEXT,
            index_status TEXT NOT NULL DEFAULT 'empty',
            coverage_pct REAL NOT NULL DEFAULT 0.0,
            node_count INTEGER NOT NULL DEFAULT 0,
            edge_count INTEGER NOT NULL DEFAULT 0,
            language_breakdown TEXT NOT NULL DEFAULT '{}',
            index_updated_at TEXT,
            updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        );

        CREATE TABLE IF NOT EXISTS nodes (
            id TEXT PRIMARY KEY,
            repo_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            name TEXT NOT NULL,
            qualified_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            line_start INTEGER NOT NULL,
            line_end INTEGER NOT NULL,
            language TEXT NOT NULL,
            parent_qualified TEXT,
            params TEXT,
            return_type TEXT,
            modifiers TEXT NOT NULL DEFAULT '[]',
            is_test INTEGER NOT NULL DEFAULT 0,
            file_hash TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 1.0,
            extraction_method TEXT NOT NULL,
            last_verified_at TEXT,
            is_stale INTEGER NOT NULL DEFAULT 0,
            unresolved_call_count INTEGER NOT NULL DEFAULT 0,
            extra TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            UNIQUE(repo_id, qualified_name)
        );

        CREATE TABLE IF NOT EXISTS edges (
            id TEXT PRIMARY KEY,
            repo_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            source_qualified TEXT NOT NULL,
            target_qualified TEXT NOT NULL,
            file_path TEXT NOT NULL,
            line INTEGER NOT NULL,
            confidence REAL NOT NULL DEFAULT 1.0,
            resolution_method TEXT NOT NULL,
            extraction_method TEXT NOT NULL,
            last_verified_at TEXT,
            is_stale INTEGER NOT NULL DEFAULT 0,
            extra TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        );

        CREATE INDEX IF NOT EXISTS idx_nodes_repo_file ON nodes(repo_id, file_path);
        CREATE INDEX IF NOT EXISTS idx_nodes_repo_kind ON nodes(repo_id, kind);
        CREATE INDEX IF NOT EXISTS idx_nodes_repo_conf ON nodes(repo_id, confidence);
        CREATE INDEX IF NOT EXISTS idx_nodes_repo_stale ON nodes(repo_id, is_stale);
        CREATE INDEX IF NOT EXISTS idx_edges_repo_file ON edges(repo_id, file_path);
        CREATE INDEX IF NOT EXISTS idx_edges_repo_source ON edges(repo_id, source_qualified);
        CREATE INDEX IF NOT EXISTS idx_edges_repo_target ON edges(repo_id, target_qualified);
        CREATE INDEX IF NOT EXISTS idx_edges_repo_kind ON edges(repo_id, kind);
        """,
    ),
    (
        2,
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
            repo_id UNINDEXED,
            qualified_name,
            name,
            kind,
            file_path,
            content,
            tokenize='porter unicode61'
        );
        """,
    ),
]


def current_version(conn: sqlite3.Connection) -> int:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """
    )
    row = conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_migrations").fetchone()
    return int(row[0]) if row else 0


def apply_migrations(conn: sqlite3.Connection) -> int:
    version_before = current_version(conn)
    for version, sql in MIGRATIONS:
        if version <= version_before:
            continue
        conn.executescript(sql)
        conn.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version,))
    conn.commit()
    return current_version(conn)
