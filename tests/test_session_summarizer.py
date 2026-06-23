# ruff: noqa: E402
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.session_summarizer import summarize_session


def _conn(*, confidence: float, redaction_incomplete: int = 0) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE session_imports (
        stable_session_id TEXT PRIMARY KEY, provider_id TEXT, provider_session_id TEXT,
        workspace_path TEXT, workspace_id TEXT, project_id TEXT, started_at TEXT, updated_at TEXT,
        imported_at TEXT, source_files_json TEXT, source_file_mtimes_json TEXT, content_hash TEXT,
        title TEXT, participants_json TEXT, messages_json TEXT, tool_calls_json TEXT,
        file_edits_json TEXT, commands_run_json TEXT, decisions_extracted_json TEXT,
        todos_extracted_json TEXT, errors_extracted_json TEXT, summary_status TEXT,
        writeback_status TEXT, confidence REAL, provider_metadata_json TEXT, redaction_incomplete INTEGER)"""
    )
    conn.execute(
        "INSERT INTO session_imports VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "fixture:1",
            "fixture",
            "1",
            "/repo",
            None,
            "project-aios",
            None,
            None,
            "2026-06-23T00:00:00Z",
            json.dumps(["source"]),
            json.dumps({}),
            "hash",
            "Low confidence task",
            json.dumps(["user"]),
            json.dumps([{"role": "user", "text": "Low confidence task"}]),
            json.dumps([]),
            json.dumps([]),
            json.dumps([]),
            json.dumps([]),
            json.dumps([]),
            json.dumps([]),
            "pending",
            "pending",
            confidence,
            json.dumps({}),
            redaction_incomplete,
        ),
    )
    return conn


def test_low_confidence_session_does_not_propose_truth_update() -> None:
    summary = summarize_session("fixture:1", _conn(confidence=0.2))
    assert summary.should_update_truth_file is False


def test_redaction_incomplete_session_is_held() -> None:
    summary = summarize_session("fixture:1", _conn(confidence=0.8, redaction_incomplete=1))
    assert summary.writeback_proposal_status == "held_redaction_incomplete"
    assert summary.should_create_obsidian_note is False
