from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from services.workflow_experiments import queue_test_repo_experiments, seed_paper_fixtures


def test_queue_test_repo_experiments_creates_one_row_per_repo(tmp_path: Path) -> None:
    test_repos = tmp_path / "test-repos.json"
    test_repos.write_text(
        json.dumps(
            {
                "test_repos": [
                    {"id": "one", "name": "One", "repo_path": "staging/one", "profile": "clean"},
                    {"id": "two", "name": "Two", "repo_path": "staging/two", "profile": "messy"},
                ]
            }
        ),
        encoding="utf-8",
    )
    conn = sqlite3.connect(":memory:")

    queued = queue_test_repo_experiments(
        conn,
        workflow_key="debug_root_cause_investigation_v1",
        skill_key="debug_root_cause_investigation_v1_executor",
        test_repos_path=test_repos,
    )

    assert [row["test_repo_id"] for row in queued] == ["one", "two"]
    rows = conn.execute(
        "SELECT workflow_key, skill_key, test_repo_id, branch_name, status FROM workflow_skill_experiments"
    ).fetchall()
    assert len(rows) == 2
    assert rows[0][0] == "debug_root_cause_investigation_v1"
    assert rows[0][1] == "debug_root_cause_investigation_v1_executor"
    assert rows[0][3].startswith("aios/experiment/debug_root_cause_investigation_v1/")
    assert rows[0][4] == "queued"

    queued_again = queue_test_repo_experiments(
        conn,
        workflow_key="debug_root_cause_investigation_v1",
        skill_key="debug_root_cause_investigation_v1_executor",
        test_repos_path=test_repos,
    )
    assert queued_again == []


def test_seed_paper_fixtures_registers_generated_papers(tmp_path: Path) -> None:
    fixtures = tmp_path / "papers"
    fixtures.mkdir()
    (fixtures / "paper-one.md").write_text("# Paper One\n", encoding="utf-8")
    conn = sqlite3.connect(":memory:")

    seeded = seed_paper_fixtures(conn, fixtures_dir=fixtures)

    assert seeded == [{"id": "paper-fixture-paper-one", "path": str((fixtures / "paper-one.md"))}]
    row = conn.execute("SELECT title, purpose, status FROM workflow_paper_fixtures").fetchone()
    assert row[0] == "Paper One"
    assert row[1].startswith("Humanizer workflow experiment fixture")
    assert row[2] == "active"
