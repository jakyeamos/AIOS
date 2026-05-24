from __future__ import annotations

import importlib.util
import io
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.session_effectiveness import (  # noqa: E402
    build_session_effectiveness_receipt,
    load_activity_snapshot,
    write_session_effectiveness_receipt,
)


def _load_module(module_name: str, relative_path: str):
    module_path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
    conn.execute(
        """
        INSERT INTO projects (id, name, repo_path, obsidian_path, status)
        VALUES ('p1', 'AIOS', '/tmp/aios', '', 'active')
        """
    )
    conn.execute(
        """
        INSERT INTO sessions (
            id, project_id, tool, started_at, objective, run_id, invocation_id,
            status, cwd, summary_candidate_path, handoff_path
        )
        VALUES (
            's1', 'p1', 'claude-code', '2026-05-24T00:00:00Z',
            'Measure session usefulness', 'r1', 'i1', 'closed', '/tmp/aios',
            '/tmp/summary.json', '/tmp/handoff.md'
        )
        """
    )
    conn.execute(
        """
        INSERT INTO prompts_used (
            id, session_id, prompt_text, classification, reusable_candidate
        )
        VALUES ('prompt-1', 's1', 'Build it', 'implementation', 1)
        """
    )
    conn.execute(
        """
        INSERT INTO artifacts (id, session_id, artifact_type, path)
        VALUES ('artifact-1', 's1', 'patch', '/tmp/file.py')
        """
    )
    conn.execute(
        """
        INSERT INTO tool_events (id, session_id, source_tool, event_type, event_time, payload_json)
        VALUES ('event-1', 's1', 'claude-code', 'PostToolUse', '2026-05-24T00:01:00Z', '{}')
        """
    )
    conn.execute(
        """
        INSERT INTO rtk_compression_events (
            id, session_id, source_kind, mode, effective_mode, raw_chars,
            compressed_chars, estimated_raw_tokens, estimated_compressed_tokens,
            token_reduction_percent
        )
        VALUES ('rtk-1', 's1', 'test', 'compressed', 'compressed', 1000, 600, 250, 100, 60)
        """
    )
    conn.commit()
    return conn


def test_build_session_effectiveness_receipt_scores_working_session() -> None:
    conn = _conn()
    snapshot = load_activity_snapshot(conn, "s1")
    assert snapshot is not None

    receipt = build_session_effectiveness_receipt(snapshot, generated_at="2026-05-24T00:02:00Z")

    assert receipt["score"] == 100
    assert receipt["rating"] == "working"
    assert receipt["activity_lights"]["capture"]["state"] == "green"
    assert receipt["activity_lights"]["governance"]["state"] == "green"
    assert receipt["measures"]["rtk_tokens_saved"] == 150
    conn.close()


def test_write_session_effectiveness_receipt_persists_row_and_json(tmp_path: Path) -> None:
    conn = _conn()

    receipt = write_session_effectiveness_receipt(conn, "s1", receipt_dir=tmp_path)
    conn.commit()

    assert receipt is not None
    receipt_path = tmp_path / "s1.json"
    assert receipt_path.exists()
    row = conn.execute(
        "SELECT rating, score, receipt_path FROM session_effectiveness_receipts WHERE session_id = 's1'"
    ).fetchone()
    assert row == ("working", 100.0, str(receipt_path))
    assert json.loads(receipt_path.read_text(encoding="utf-8"))["session_id"] == "s1"
    conn.close()


def test_statusline_renders_live_activity(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "aios.db"
    source = _conn()
    backup = sqlite3.connect(db_path)
    source.backup(backup)
    source.close()
    backup.close()
    statusline = _load_module("aios_statusline", "bin/aios-statusline.py")

    monkeypatch.setattr(statusline, "DB", str(db_path))
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            json.dumps(
                {
                    "session_id": "s1",
                    "columns": 120,
                    "model": {"display_name": "Claude Sonnet"},
                    "context_window": {"used_percentage": 12.4},
                }
            )
        ),
    )
    captured = io.StringIO()
    monkeypatch.setattr(sys, "stdout", captured)

    statusline.main()

    output = captured.getvalue()
    assert "AIOS s1 live working:100" in output
    assert "cap:G" in output
    assert "q:G" in output
    assert "Sonnet ctx:12%" in output
