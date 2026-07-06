"""handoff-store service for local aios-db cross-session handoff records."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from pathlib import Path

AIOS_DB = Path.home() / "AIOS" / "data" / "aios.db"

HANDOFFS_DDL = """
CREATE TABLE IF NOT EXISTS handoffs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT,
  project TEXT NOT NULL,
  focus TEXT,
  suggested_skills TEXT NOT NULL DEFAULT '[]',
  source_run_id TEXT,
  content_path TEXT,
  redacted INTEGER NOT NULL DEFAULT 0 CHECK(redacted IN (0, 1)),
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_handoffs_project_created ON handoffs(project, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_handoffs_source_run ON handoffs(source_run_id);
"""

HandoffRow = dict[str, object]


def _json_list(values: Sequence[str] | None) -> str:
    return json.dumps(list(values or []), sort_keys=True)


def _connect() -> sqlite3.Connection:
    AIOS_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(AIOS_DB)
    conn.row_factory = sqlite3.Row
    conn.executescript(HANDOFFS_DDL)
    conn.commit()
    return conn


def _row_to_dict(row: sqlite3.Row) -> HandoffRow:
    return dict(zip(row.keys(), row, strict=False))


def write_handoff(
    session_id: str | None,
    project: str,
    focus: str | None,
    suggested_skills: Sequence[str] | None = None,
    source_run_id: str | None = None,
    content_path: str | Path | None = None,
    redacted: bool = False,
) -> int:
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO handoffs (
              session_id, project, focus, suggested_skills, source_run_id, content_path, redacted
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                project,
                focus,
                _json_list(suggested_skills),
                source_run_id,
                str(content_path) if content_path is not None else None,
                int(redacted),
            ),
        )
        conn.commit()
        row_id = cursor.lastrowid
        assert row_id is not None  # set after a successful INSERT
        return int(row_id)


def list_handoffs(project: str | None = None, limit: int = 10) -> list[HandoffRow]:
    bounded_limit = max(1, min(limit, 100))
    with _connect() as conn:
        if project is not None:
            rows = conn.execute(
                "SELECT * FROM handoffs WHERE project = ? ORDER BY id DESC LIMIT ?",
                (project, bounded_limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM handoffs ORDER BY id DESC LIMIT ?",
                (bounded_limit,),
            ).fetchall()
    return [_row_to_dict(row) for row in rows]
