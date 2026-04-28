from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_extract_module():
    module_path = ROOT / "bin" / "extract-patterns.py"
    bin_path = str(ROOT / "bin")
    if bin_path not in sys.path:
        sys.path.insert(0, bin_path)
    spec = importlib.util.spec_from_file_location("extract_patterns", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE patterns (
          id TEXT PRIMARY KEY,
          class TEXT NOT NULL,
          title TEXT NOT NULL,
          evidence TEXT NOT NULL DEFAULT '[]',
          confidence REAL DEFAULT 0.5,
          status TEXT DEFAULT 'candidate',
          domain TEXT DEFAULT 'unclassified',
          state TEXT DEFAULT 'observation',
          body TEXT,
          source_type TEXT DEFAULT 'bigram',
          human_approved INTEGER DEFAULT 0,
          first_observed_at TEXT,
          created_at TEXT,
          frequency_count INTEGER DEFAULT 0,
          source_sessions INTEGER DEFAULT 0,
          last_seen_at TEXT
        );
        CREATE TABLE sessions (
          id TEXT PRIMARY KEY,
          started_at TEXT,
          ended_at TEXT,
          status TEXT,
          objective TEXT
        );
        CREATE TABLE prompts_used (
          id TEXT PRIMARY KEY,
          session_id TEXT NOT NULL,
          classification TEXT,
          prompt_text TEXT
        );
        CREATE TABLE tool_events (
          id TEXT PRIMARY KEY,
          session_id TEXT NOT NULL,
          source_tool TEXT NOT NULL,
          event_type TEXT NOT NULL,
          event_time TEXT NOT NULL,
          payload_json TEXT NOT NULL
        );
        """
    )
    return conn


def _seed_session(conn: sqlite3.Connection, session_id: str, classification: str, tool_events: int) -> None:
    conn.execute(
        """
        INSERT INTO sessions (id, started_at, ended_at, status, objective)
        VALUES (?, '2026-04-28T00:00:00Z', '2026-04-28T00:05:00Z', 'closed', ?)
        """,
        (session_id, f"{classification} session"),
    )
    conn.execute(
        "INSERT INTO prompts_used (id, session_id, classification, prompt_text) VALUES (?, ?, ?, ?)",
        (f"prompt-{session_id}", session_id, classification, f"please {classification} this"),
    )
    for index in range(tool_events):
        conn.execute(
            """
            INSERT INTO tool_events (id, session_id, source_tool, event_type, event_time, payload_json)
            VALUES (?, ?, 'codex', 'PostToolUse', '2026-04-28T00:01:00Z', '{}')
            """,
            (f"tool-{session_id}-{index}", session_id),
        )


def test_extract_workflow_patterns_from_repeated_session_traces() -> None:
    module = _load_extract_module()
    conn = _conn()
    for index in range(3):
        _seed_session(conn, f"debug-{index}", "debug", 4)

    inserted = module.extract_workflow_patterns(conn, set())

    assert inserted == [
        {
            "class": "workflow",
            "title": "Captured workflow: debug fix failing behavior",
            "count": 3,
            "tool_events": 12,
        }
    ]
    row = conn.execute(
        """
        SELECT class, title, status, domain, source_type, source_sessions, frequency_count, body
        FROM patterns
        """
    ).fetchone()
    assert row[:7] == (
        "workflow",
        "Captured workflow: debug fix failing behavior",
        "candidate",
        "workflow",
        "session-workflow",
        3,
        3,
    )
    assert "observed across 3 sessions" in row[7]


def test_extract_workflow_patterns_skips_single_session_noise() -> None:
    module = _load_extract_module()
    conn = _conn()
    _seed_session(conn, "debug-1", "debug", 12)

    inserted = module.extract_workflow_patterns(conn, set())

    assert inserted == []
    assert conn.execute("SELECT COUNT(*) FROM patterns").fetchone()[0] == 0
