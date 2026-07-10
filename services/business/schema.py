from __future__ import annotations

import sqlite3

from services.memory_layers import ensure_memory_layer_schema


def _ensure_column(
    conn: sqlite3.Connection,
    table: str,
    column: str,
    definition: str,
) -> None:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    if any(row[1] == column for row in rows):
        return
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def ensure_business_memory_schema(conn: sqlite3.Connection) -> None:
    """Idempotent schema for business memory ingest + FTS."""
    ensure_memory_layer_schema(conn)

    business_columns = [
        ("external_id", "TEXT"),
        ("author_name", "TEXT"),
        ("author_handle", "TEXT"),
        ("occurred_at", "TEXT"),
        ("channel_or_thread", "TEXT"),
        ("subject_or_title", "TEXT"),
        ("body_text", "TEXT"),
        ("url", "TEXT"),
        ("attachments_json", "TEXT"),
        ("tags_json", "TEXT"),
        ("content_hash", "TEXT"),
        ("privacy_level", "TEXT"),
        ("raw_path", "TEXT"),
        ("normalized_json_path", "TEXT"),
        ("ingest_run_id", "TEXT"),
        ("compiled_at", "TEXT"),
    ]
    for column, definition in business_columns:
        _ensure_column(conn, "memory_raw_sources", column, definition)

    conn.executescript(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_memory_raw_sources_content_hash
          ON memory_raw_sources(content_hash)
          WHERE content_hash IS NOT NULL;

        CREATE INDEX IF NOT EXISTS idx_memory_raw_sources_business_ingest
          ON memory_raw_sources(source_type, occurred_at DESC);

        CREATE INDEX IF NOT EXISTS idx_memory_raw_sources_uncompiled
          ON memory_raw_sources(compiled_at)
          WHERE compiled_at IS NULL;

        CREATE TABLE IF NOT EXISTS business_ingest_runs (
          id TEXT PRIMARY KEY,
          source_type TEXT NOT NULL,
          started_at TEXT NOT NULL,
          finished_at TEXT,
          status TEXT NOT NULL,
          records_fetched INTEGER DEFAULT 0,
          records_new INTEGER DEFAULT 0,
          records_duplicate INTEGER DEFAULT 0,
          error_summary TEXT,
          config_snapshot_json TEXT
        );

        CREATE TABLE IF NOT EXISTS business_compile_runs (
          id TEXT PRIMARY KEY,
          started_at TEXT NOT NULL,
          finished_at TEXT,
          since_cursor TEXT,
          sources_processed INTEGER DEFAULT 0,
          pages_created INTEGER DEFAULT 0,
          pages_updated INTEGER DEFAULT 0,
          llm_enabled INTEGER DEFAULT 0,
          lint_findings INTEGER DEFAULT 0,
          status TEXT NOT NULL
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS business_sources_fts USING fts5(
          source_id UNINDEXED,
          body_text,
          subject_or_title,
          author_name,
          channel_or_thread,
          tokenize='porter unicode61'
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS business_wiki_fts USING fts5(
          vault_path UNINDEXED,
          title,
          body,
          tags,
          tokenize='porter unicode61'
        );
        """
    )
    _ensure_knowledge_graph_tables(conn)


def _ensure_knowledge_graph_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS knowledge_topics (
          id TEXT PRIMARY KEY,
          slug TEXT NOT NULL UNIQUE,
          title TEXT NOT NULL,
          kind TEXT NOT NULL,
          summary TEXT NOT NULL,
          confidence REAL NOT NULL DEFAULT 0.5,
          freshness TEXT NOT NULL DEFAULT 'Unknown',
          project_id TEXT,
          canonical_href TEXT NOT NULL,
          tags_json TEXT NOT NULL DEFAULT '[]',
          metadata_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_knowledge_topics_kind
          ON knowledge_topics(kind, updated_at);
        CREATE TABLE IF NOT EXISTS knowledge_references (
          id TEXT PRIMARY KEY,
          topic_id TEXT NOT NULL REFERENCES knowledge_topics(id),
          source_kind TEXT NOT NULL,
          source_id TEXT,
          project_id TEXT,
          label TEXT NOT NULL,
          href TEXT NOT NULL,
          excerpt TEXT NOT NULL,
          freshness TEXT NOT NULL,
          confidence REAL NOT NULL DEFAULT 0.5,
          metadata_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_knowledge_references_topic
          ON knowledge_references(topic_id, created_at);
        """
    )
