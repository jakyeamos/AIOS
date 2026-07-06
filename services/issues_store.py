"""issues-store service for local aios-db implementation issue records."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from pathlib import Path

AIOS_DB = Path.home() / "AIOS" / "data" / "aios.db"

ISSUES_DDL = """
CREATE TABLE IF NOT EXISTS issues (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  acceptance_criteria TEXT NOT NULL DEFAULT '[]',
  afk_hitl TEXT NOT NULL CHECK(afk_hitl IN ('AFK', 'HITL')),
  dependencies TEXT NOT NULL DEFAULT '[]',
  linked_run_id TEXT,
  source_file TEXT,
  status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open', 'in_progress', 'done', 'cancelled')),
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_issues_project_status ON issues(project, status, id);
CREATE INDEX IF NOT EXISTS idx_issues_linked_run ON issues(linked_run_id);
"""

IssueRow = dict[str, object]


def _json_list(values: Sequence[str] | None) -> str:
    return json.dumps(list(values or []), sort_keys=True)


def _connect() -> sqlite3.Connection:
    AIOS_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(AIOS_DB)
    conn.row_factory = sqlite3.Row
    conn.executescript(ISSUES_DDL)
    conn.commit()
    return conn


def _row_to_dict(row: sqlite3.Row) -> IssueRow:
    return dict(zip(row.keys(), row, strict=False))


def write_issue(
    title: str,
    description: str | None,
    acceptance_criteria: Sequence[str] | str,
    afk_hitl: str,
    dependencies: Sequence[str] | None = None,
    linked_run_id: str | None = None,
    source_file: str | None = None,
    project: str = "unknown",
) -> int:
    if afk_hitl not in {"AFK", "HITL"}:
        raise ValueError("afk_hitl must be 'AFK' or 'HITL'.")
    criteria_json = (
        json.dumps([acceptance_criteria], sort_keys=True)
        if isinstance(acceptance_criteria, str)
        else _json_list(acceptance_criteria)
    )
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO issues (
              project, title, description, acceptance_criteria, afk_hitl,
              dependencies, linked_run_id, source_file
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project,
                title,
                description,
                criteria_json,
                afk_hitl,
                _json_list(dependencies),
                linked_run_id,
                source_file,
            ),
        )
        conn.commit()
        row_id = cursor.lastrowid
        assert row_id is not None  # set after a successful INSERT
        return int(row_id)


def list_issues(project: str | None = None) -> list[IssueRow]:
    with _connect() as conn:
        if project is not None:
            rows = conn.execute(
                "SELECT * FROM issues WHERE project = ? ORDER BY id",
                (project,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM issues ORDER BY project, id").fetchall()
    return [_row_to_dict(row) for row in rows]
