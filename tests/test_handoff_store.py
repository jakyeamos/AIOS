# ruff: noqa: E402

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services import handoff_store


def test_write_handoff_creates_schema_and_round_trips(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(handoff_store, "AIOS_DB", tmp_path / "aios.db")

    handoff_id = handoff_store.write_handoff(
        session_id="session-1",
        project="AIOS",
        focus="Continue Phase 15 Plan 15-08.",
        suggested_skills=["handoff", "to-issues"],
        source_run_id="run-1",
        content_path=tmp_path / "handoff.md",
        redacted=True,
    )

    rows = handoff_store.list_handoffs("AIOS", limit=5)

    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == handoff_id
    assert row["session_id"] == "session-1"
    assert row["project"] == "AIOS"
    assert row["focus"] == "Continue Phase 15 Plan 15-08."
    assert json.loads(str(row["suggested_skills"])) == ["handoff", "to-issues"]
    assert row["source_run_id"] == "run-1"
    assert row["content_path"] == str(tmp_path / "handoff.md")
    assert row["redacted"] == 1
    assert row["created_at"]


def test_list_handoffs_filters_project_and_limit(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(handoff_store, "AIOS_DB", tmp_path / "aios.db")

    handoff_store.write_handoff("s1", "one", "old", ["handoff"])
    handoff_store.write_handoff("s2", "one", "new", ["diagnose"])
    handoff_store.write_handoff("s3", "two", "other", ["to-issues"])

    assert [row["focus"] for row in handoff_store.list_handoffs("one", limit=1)] == ["new"]
    assert [row["project"] for row in handoff_store.list_handoffs(limit=2)] == ["two", "one"]


def test_schema_sql_contains_handoffs_table() -> None:
    schema = (ROOT / "schema.sql").read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS handoffs" in schema
    assert "suggested_skills TEXT" in schema
    assert "source_run_id TEXT" in schema
