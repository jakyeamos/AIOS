from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import services.workflow_experiments as workflow_experiments
from services.workflow_experiments import (
    queue_test_repo_experiments,
    run_workflow_skill_experiment,
    seed_paper_fixtures,
)


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


def test_run_workflow_skill_experiment_records_candidate_improvement(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "-C", str(repo), "init"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.local"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    (repo / "README.md").write_text("# Repo\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "README.md"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "init"], check=True, capture_output=True)
    monkeypatch.setattr(workflow_experiments, "ROOT", tmp_path)

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE workflow_synthesis_proposals (
          id TEXT PRIMARY KEY,
          proposal_key TEXT NOT NULL,
          title TEXT NOT NULL,
          summary TEXT NOT NULL,
          source_pattern_ids_json TEXT NOT NULL DEFAULT '[]',
          workflow_spec_json TEXT NOT NULL DEFAULT '{}',
          skill_specs_json TEXT NOT NULL DEFAULT '[]',
          validation_plan_json TEXT NOT NULL DEFAULT '{}',
          evidence_json TEXT NOT NULL DEFAULT '[]',
          status TEXT NOT NULL DEFAULT 'pending_approval',
          created_at TEXT NOT NULL DEFAULT '2026-04-28T00:00:00Z',
          updated_at TEXT NOT NULL DEFAULT '2026-04-28T00:00:00Z'
        );
        """
    )
    workflow_experiments.ensure_workflow_experiment_schema(conn)
    workflow_spec = {
        "key": "debug_root_cause_investigation_v1",
        "name": "Debug",
        "purpose": "Debug workflow",
        "trigger_hints": ["debug"],
        "output_contract": ["result"],
        "required_validations": ["scope_check"],
        "stages": [
            {"key": "normalize_prompt", "kind": "normalize_prompt", "required_skills": ["prompt_library_normalizer"]},
            {
                "key": "execute_pattern",
                "kind": "generate",
                "required_skills": ["debug_root_cause_investigation_v1_executor"],
            },
            {"key": "validate", "kind": "validate", "required_skills": ["scope_check"]},
        ],
    }
    skill_specs = [
        {
            "key": "debug_root_cause_investigation_v1_executor",
            "purpose": "Execute learned debug workflow",
            "allowed_stages": ["generate"],
            "input_schema": {},
            "output_schema": {"result_text": "string"},
            "invariants": ["Use the learned pattern only when trigger evidence matches."],
            "failure_conditions": [],
            "side_effects": [],
            "execution_mode": "heuristic",
        }
    ]
    conn.execute(
        """
        INSERT INTO workflow_synthesis_proposals (
          id, proposal_key, title, summary, workflow_spec_json, skill_specs_json, status
        )
        VALUES ('proposal-1', ?, 'Debug', 'Debug', ?, ?, 'pending_approval')
        """,
        ("debug_root_cause_investigation_v1", json.dumps(workflow_spec), json.dumps(skill_specs)),
    )
    conn.execute(
        """
        INSERT INTO workflow_skill_experiments (
          id, workflow_key, skill_key, test_repo_id, test_repo_path, branch_name, experiment_kind
        )
        VALUES (
          'experiment-1',
          'debug_root_cause_investigation_v1',
          'debug_root_cause_investigation_v1_executor',
          'repo',
          'repo',
          'aios/experiment/debug/repo',
          'test_repo_branch'
        )
        """
    )

    result = run_workflow_skill_experiment(conn, "experiment-1")

    assert result["outcome"] == "promotion_ready"
    assert result["candidate_score"] > result["baseline_score"]
    row = conn.execute(
        "SELECT status, outcome, baseline_score, candidate_score FROM workflow_skill_experiments WHERE id='experiment-1'"
    ).fetchone()
    assert row["status"] == "completed"
    assert row["outcome"] == "promotion_ready"
    assert row["candidate_score"] > row["baseline_score"]
    artifact = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "show",
            "aios/experiment/debug/repo:.aios/workflow-skill-experiments/experiment-1.json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert '"outcome": "promotion_ready"' in artifact.stdout
