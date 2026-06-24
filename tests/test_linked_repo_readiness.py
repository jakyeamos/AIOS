from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.linked_repo_readiness import (  # noqa: E402
    DEFAULT_EXCLUDED_PROJECT_IDS,
    phase24_readiness_report,
    phase24_target_projects,
)
from services.quality_pipeline import ensure_quality_pipeline_schema, record_quality_pipeline_run  # noqa: E402


def _write_config(path: Path) -> Path:
    payload = {
        "standard": {
            "version": "2026-04-26",
            "gates": [
                {"key": "lint", "label": "Lint", "required": True, "applicability": ["all"]},
                {"key": "ci", "label": "CI", "required": True, "applicability": ["all"]},
            ],
        },
        "projects": [
            {
                "project_id": "soundscape-app",
                "repo_class": "production_public_web_app",
                "strict_readiness_status": "evidence_required",
                "gates": {
                    "lint": {"command": "pnpm lint", "working_directory": "."},
                    "ci": {"command": ".github/workflows/pr-checks.yml", "working_directory": "."},
                },
            },
            {
                "project_id": "portfolio",
                "repo_class": "production_public_web_app",
                "strict_readiness_status": "blocked",
                "gates": {
                    "lint": {"command": "pnpm lint", "working_directory": "."},
                },
                "maturation_blockers": ["missing CI proof"],
            },
            {
                "project_id": "video-pipeline",
                "repo_class": "developer_tool_package",
                "strict_readiness_status": "blocked",
                "gates": {
                    "lint": {"command": "pnpm lint", "working_directory": "."},
                },
            },
            {
                "project_id": "agent-router",
                "repo_class": "developer_tool_package",
                "strict_readiness_status": "blocked",
                "gates": {
                    "lint": {"command": "pnpm lint", "working_directory": "."},
                },
            },
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _conn(tmp_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE projects (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          repo_path TEXT NOT NULL,
          obsidian_path TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'active'
        )
        """
    )
    for project_id in ("soundscape-app", "portfolio", "video-pipeline", "agent-router"):
        repo_path = tmp_path / project_id
        repo_path.mkdir()
        conn.execute(
            """
            INSERT INTO projects (id, name, repo_path, obsidian_path, status)
            VALUES (?, ?, ?, '.', 'active')
            """,
            (project_id, project_id, str(repo_path)),
        )
    ensure_quality_pipeline_schema(conn)
    return conn


def test_phase24_targets_exclude_deprecated_projects(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path / "quality-pipeline.json")

    targets = phase24_target_projects(config_path=config_path)

    assert DEFAULT_EXCLUDED_PROJECT_IDS == ("agent-router", "video-pipeline", "manga-sync")
    assert [target["project_id"] for target in targets] == ["soundscape-app", "portfolio"]


def test_missing_required_gate_evidence_blocks_readiness(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path / "quality-pipeline.json")
    conn = _conn(tmp_path)
    run_id = record_quality_pipeline_run(
        conn,
        project_id="soundscape-app",
        gate_key="lint",
        command="pnpm lint",
        status="pass",
        source="test",
        completed_at="2026-06-24T00:00:00Z",
        evidence=["lint ok"],
    )
    conn.commit()

    report = phase24_readiness_report(conn, config_path=config_path)
    soundscape = next(project for project in report["projects"] if project["project_id"] == "soundscape-app")

    assert soundscape["verdict"] == "evidence_required"
    assert soundscape["missing_gate_keys"] == ["ci"]
    assert soundscape["latest_evidence_ids"] == {"lint": run_id}


def test_missing_ci_without_exception_records_blocker(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path / "quality-pipeline.json")
    conn = _conn(tmp_path)

    report = phase24_readiness_report(conn, config_path=config_path)
    portfolio = next(project for project in report["projects"] if project["project_id"] == "portfolio")

    assert portfolio["verdict"] == "blocked"
    assert "ci_default_proof_missing" in portfolio["blockers"]
    assert "ci" in portfolio["missing_gate_keys"]


def test_non_remote_ci_exception_requires_local_ci_evidence(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path / "quality-pipeline.json")
    payload = json.loads(config_path.read_text())
    portfolio = next(project for project in payload["projects"] if project["project_id"] == "portfolio")
    portfolio["non_remote_ci_exception"] = {
        "owner": "jakyeamos",
        "reason": "GitHub Actions credits are constrained.",
        "review_date": "2026-06-24",
        "local_proof_command": "python3 scripts/linked-repo-quality-runner.py --project portfolio --gate ci",
        "replacement_path": "quality_pipeline_runs.ci",
    }
    config_path.write_text(json.dumps(payload), encoding="utf-8")
    conn = _conn(tmp_path)

    report = phase24_readiness_report(conn, config_path=config_path)
    portfolio = next(project for project in report["projects"] if project["project_id"] == "portfolio")

    assert portfolio["verdict"] == "blocked"
    assert "ci_default_proof_missing" not in portfolio["blockers"]
    assert "ci" in portfolio["missing_gate_keys"]


def test_runner_rejects_agent_router_and_unknown_projects(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path / "quality-pipeline.json")
    script = ROOT / "scripts" / "linked-repo-quality-runner.py"

    excluded = subprocess.run(
        [
            sys.executable,
            str(script),
            "--project",
            "agent-router",
            "--gate",
            "lint",
            "--dry-run",
            "--config",
            str(config_path),
        ],
        check=False,
        text=True,
        capture_output=True,
    )
    unknown = subprocess.run(
        [
            sys.executable,
            str(script),
            "--project",
            "unknown",
            "--gate",
            "lint",
            "--dry-run",
            "--config",
            str(config_path),
        ],
        check=False,
        text=True,
        capture_output=True,
    )

    assert excluded.returncode == 2
    assert "excluded from Phase 24" in excluded.stderr
    assert unknown.returncode == 2
    assert "Unknown project" in unknown.stderr


def test_runner_dry_run_uses_aios_owned_config_command(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path / "quality-pipeline.json")
    db_path = tmp_path / "aios.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE projects (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          repo_path TEXT NOT NULL,
          obsidian_path TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'active'
        )
        """
    )
    repo_path = tmp_path / "soundscape-app"
    repo_path.mkdir()
    conn.execute(
        """
        INSERT INTO projects (id, name, repo_path, obsidian_path, status)
        VALUES ('soundscape-app', 'soundscape-app', ?, '.', 'active')
        """,
        (str(repo_path),),
    )
    conn.commit()
    conn.close()
    script = ROOT / "scripts" / "linked-repo-quality-runner.py"

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--project",
            "soundscape-app",
            "--gate",
            "lint",
            "--dry-run",
            "--config",
            str(config_path),
            "--db",
            str(db_path),
        ],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["project_id"] == "soundscape-app"
    assert payload["gate_key"] == "lint"
    assert payload["command"] == "pnpm lint"
    assert payload["source"] == "config/quality-pipeline.json"
    assert payload["working_directory"] == str(repo_path)
    assert ".aios-quality-gate.json" not in result.stdout


def test_readiness_report_real_config_has_20_targets_and_deprecated_repos_excluded() -> None:
    conn = sqlite3.connect(":memory:")

    report = phase24_readiness_report(conn)

    assert report["target_count"] == 20
    assert report["excluded_count"] == 3
    assert report["excluded_projects"] == [
        {"project_id": "video-pipeline", "reason": "excluded_by_phase24_scope"},
        {"project_id": "manga-sync", "reason": "excluded_by_phase24_scope"},
        {"project_id": "agent-router", "reason": "excluded_by_phase24_scope"},
    ]
    placeholder_rows = conn.execute("SELECT COUNT(*) FROM projects WHERE repo_path = ''").fetchone()[0]
    assert placeholder_rows == 0
    assert all("ci_default_proof_missing" not in project["blockers"] for project in report["projects"])
    assert all("ci" in project["missing_gate_keys"] for project in report["projects"])
