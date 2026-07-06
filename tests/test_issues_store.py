# ruff: noqa: E402

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services import issues_store


def test_write_issue_creates_schema_and_round_trips(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "aios.db"
    monkeypatch.setattr(issues_store, "AIOS_DB", db_path)

    issue_id = issues_store.write_issue(
        title="User can reset password",
        description="Vertical slice through form, action, token storage, and email stub.",
        acceptance_criteria=[
            "Given a known email, when reset is requested, then a token is stored.",
            "Given an unknown email, when reset is requested, then the response is generic.",
        ],
        afk_hitl="AFK",
        dependencies=["Auth session exists"],
        linked_run_id="run-123",
        source_file="docs/prd.md",
        project="BidCamp",
    )

    rows = issues_store.list_issues("BidCamp")

    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == issue_id
    assert row["project"] == "BidCamp"
    assert row["title"] == "User can reset password"
    assert row["afk_hitl"] == "AFK"
    assert json.loads(str(row["acceptance_criteria"])) == [
        "Given a known email, when reset is requested, then a token is stored.",
        "Given an unknown email, when reset is requested, then the response is generic.",
    ]
    assert json.loads(str(row["dependencies"])) == ["Auth session exists"]
    assert row["linked_run_id"] == "run-123"
    assert row["source_file"] == "docs/prd.md"
    assert row["status"] == "open"
    assert row["created_at"]


def test_list_issues_filters_by_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(issues_store, "AIOS_DB", tmp_path / "aios.db")

    issues_store.write_issue(
        title="A",
        description="",
        acceptance_criteria=[],
        afk_hitl="AFK",
        dependencies=[],
        linked_run_id=None,
        source_file=None,
        project="one",
    )
    issues_store.write_issue(
        title="B",
        description="",
        acceptance_criteria=[],
        afk_hitl="HITL",
        dependencies=[],
        linked_run_id=None,
        source_file=None,
        project="two",
    )

    assert [row["title"] for row in issues_store.list_issues("one")] == ["A"]
    assert [row["title"] for row in issues_store.list_issues()] == ["A", "B"]


def test_write_issue_rejects_invalid_afk_hitl(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(issues_store, "AIOS_DB", tmp_path / "aios.db")

    with pytest.raises(ValueError, match="afk_hitl"):
        issues_store.write_issue(
            title="Bad",
            description="",
            acceptance_criteria=[],
            afk_hitl="MAYBE",
            dependencies=[],
            linked_run_id=None,
            source_file=None,
            project="one",
        )


def test_schema_sql_contains_issues_table() -> None:
    schema = (ROOT / "schema.sql").read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS issues" in schema
    assert "afk_hitl TEXT" in schema
    assert "linked_run_id TEXT" in schema
