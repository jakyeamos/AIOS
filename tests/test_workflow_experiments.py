from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import services.workflow_experiments as workflow_experiments  # noqa: E402
from services.workflow_experiments import (  # noqa: E402
    queue_test_repo_experiments,
    run_workflow_skill_experiment,
    seed_paper_fixtures,
)


def _init_experiment_repo(repo: Path) -> None:
    repo.mkdir()
    subprocess.run(["git", "-C", str(repo), "init"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "switch", "-c", "test-fixture"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@example.local"], check=True
    )
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    (repo / ".pre-cr.json").write_text(
        json.dumps(
            {
                "version": 1,
                "testCommand": f"{sys.executable} scripts/pre_cr_fixture.py",
                "coveragePaths": ["coverage/lcov.info"],
                "excludePatterns": [
                    ".gitignore",
                    ".pre-cr.json",
                    "README.md",
                    "pyproject.toml",
                    "scripts/**",
                    "tests/**",
                ],
                "checks": {"coverage": False, "security": False, "checklist": False},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (repo / ".gitignore").write_text(
        ".aios/audit/\n.pytest_cache/\n__pycache__/\ncoverage/\n", encoding="utf-8"
    )
    (repo / "README.md").write_text("# Repo\n", encoding="utf-8")
    (repo / "pyproject.toml").write_text(
        "[tool.pytest.ini_options]\npythonpath = ['.']\n", encoding="utf-8"
    )
    (repo / "scripts").mkdir()
    (repo / "scripts" / "pre_cr_fixture.py").write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "",
                "import pathlib",
                "import subprocess",
                "import sys",
                "",
                "result = subprocess.run([sys.executable, '-m', 'pytest'], check=False)",
                "coverage_dir = pathlib.Path('coverage')",
                "coverage_dir.mkdir(exist_ok=True)",
                "(coverage_dir / 'lcov.info').write_text('', encoding='utf-8')",
                "raise SystemExit(result.returncode)",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (repo / "tests").mkdir()
    (repo / "tests" / "test_smoke.py").write_text(
        "def test_smoke():\n    assert True\n", encoding="utf-8"
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "add",
            ".gitignore",
            ".pre-cr.json",
            "README.md",
            "pyproject.toml",
            "scripts/pre_cr_fixture.py",
            "tests/test_smoke.py",
        ],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "init"], check=True, capture_output=True
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

    assert seeded == [{"id": "paper-fixture-paper-one", "path": str(fixtures / "paper-one.md")}]
    row = conn.execute("SELECT title, purpose, status FROM workflow_paper_fixtures").fetchone()
    assert row[0] == "Paper One"
    assert row[1].startswith("Humanizer workflow experiment fixture")
    assert row[2] == "active"


def test_python_validation_falls_back_to_executable_test_file(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    tests = repo / "tests"
    tests.mkdir(parents=True)
    (repo / "pyproject.toml").write_text("[project]\nname = 'repo'\n", encoding="utf-8")
    (tests / "test_app.py").write_text("def test_app():\n    assert True\n", encoding="utf-8")
    monkeypatch.setattr(workflow_experiments.importlib.util, "find_spec", lambda name: None)

    command = workflow_experiments._repo_validation_command(repo)

    assert command == [sys.executable, "-B", "tests/test_app.py"]


@pytest.mark.parametrize("asset_kind", ["prompt", "skill"])
def test_experiment_winner_goes_through_propose_asset_promotion_when_phase8_present(
    asset_kind: str,
) -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    workflow_experiments.ensure_workflow_experiment_schema(conn)

    result = workflow_experiments._propose_via_workflow_promotion_if_available(
        conn,
        asset_kind=asset_kind,
        asset_key=f"{asset_kind}-candidate",
        to_state="candidate",
        evidence={
            "source": "workflow_experiments",
            "experiment_id": "experiment-1",
            "baseline_score": 0.5,
            "candidate_score": 0.8,
        },
        actor="workflow_experiments",
        rationale="Experiment winner improved validation score",
    )

    assert result is not None
    writeback = conn.execute(
        """
        SELECT layer_type, layer_key, requires_approval, proposed_change_json
        FROM improvement_writebacks
        WHERE id = ?
        """,
        (result["writeback_id"],),
    ).fetchone()
    lifecycle = conn.execute(
        """
        SELECT item_kind, item_key, status, metadata_json
        FROM promotion_lifecycle_items
        WHERE id = ?
        """,
        (result["lifecycle_id"],),
    ).fetchone()
    assert writeback["layer_type"] == asset_kind
    assert writeback["requires_approval"] == 1
    assert '"source": "workflow_experiments"' in writeback["proposed_change_json"]
    assert lifecycle["item_kind"] == asset_kind
    assert lifecycle["status"] == "proposed"
    assert '"target_state": "candidate"' in lifecycle["metadata_json"]


def test_experiment_winner_falls_back_when_phase8_missing(monkeypatch, capsys) -> None:
    def unavailable(*args, **kwargs):
        print(
            "[warn] Phase 8 workflow_promotion absent; falling back to status only.",
            file=sys.stderr,
        )
        return None

    monkeypatch.setattr(
        workflow_experiments,
        "_propose_via_workflow_promotion_if_available",
        unavailable,
    )
    conn = sqlite3.connect(":memory:")

    result = workflow_experiments._propose_via_workflow_promotion_if_available(
        conn,
        asset_kind="skill",
        asset_key="candidate-skill",
        to_state="candidate",
        evidence={"source": "workflow_experiments", "experiment_id": "experiment-1"},
        actor="workflow_experiments",
        rationale="Experiment winner improved validation score",
    )

    assert result is None
    assert "Phase 8 workflow_promotion absent" in capsys.readouterr().err


def test_run_workflow_skill_experiment_records_candidate_improvement(
    tmp_path: Path, monkeypatch
) -> None:
    repo = tmp_path / "repo"
    _init_experiment_repo(repo)
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
            {
                "key": "normalize_prompt",
                "kind": "normalize_prompt",
                "required_skills": ["prompt_library_normalizer"],
            },
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
    assert result["promotion_proposal"]["requires_approval"] is True
    assert result["candidate_score"] > result["baseline_score"]
    row = conn.execute(
        "SELECT status, outcome, baseline_score, candidate_score FROM workflow_skill_experiments WHERE id='experiment-1'"
    ).fetchone()
    assert row["status"] == "completed"
    assert row["outcome"] == "promotion_ready"
    assert row["candidate_score"] > row["baseline_score"]
    details = json.loads(
        conn.execute(
            "SELECT details_json FROM workflow_skill_experiments WHERE id='experiment-1'"
        ).fetchone()[0]
    )
    assert details["baseline_validation_passed"] is True
    assert details["baseline_kind"] == "loose_workflow"
    assert details["ablation_validation_passed"] is True
    assert details["ablation_delta"] > 0
    assert details["repo_fit_score"] > 0
    assert details["repo_profile"]["has_pyproject"] is True
    assert details["candidate_validation_passed"] is True
    assert details["promotion_proposal"]["requires_approval"] is True
    assert details["validation_command"][-2:] == ["-m", "pytest"]
    assert (
        details["divergent_strategy_standard"]["standard_id"]
        == "experimentation.divergent_strategy_standard"
    )
    assert "candidate_portfolio" in details["divergent_strategy_standard"]["required_evidence"]
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
    assert '"baseline_kind": "loose_workflow"' in artifact.stdout
    assert '"ablation_report"' in artifact.stdout
    assert '"candidate_validation"' in artifact.stdout
    assert '"divergent_strategy_standard"' in artifact.stdout


def test_experiment_runtime_behavior_otherwise_unchanged(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    _init_experiment_repo(repo)
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
            {
                "key": "normalize_prompt",
                "kind": "normalize_prompt",
                "required_skills": ["prompt_library_normalizer"],
            },
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
    assert conn.execute("SELECT COUNT(*) FROM workflow_skill_experiments").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM improvement_writebacks").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM promotion_lifecycle_items").fetchone()[0] == 1
