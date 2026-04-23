from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.aios_cli import EXIT_OK, run_cli  # noqa: E402


def _seed_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE projects (id TEXT PRIMARY KEY, name TEXT, status TEXT);
        CREATE TABLE sessions (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            status TEXT,
            started_at TEXT,
            ended_at TEXT,
            cwd TEXT
        );
        CREATE TABLE bug_log (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            symptom TEXT,
            status TEXT,
            created_at TEXT
        );
        CREATE TABLE orchestration_runs (
            id TEXT PRIMARY KEY,
            status TEXT
        );
        CREATE TABLE orchestration_run_events (
            id TEXT PRIMARY KEY,
            run_id TEXT,
            to_status TEXT,
            summary TEXT,
            reason_json TEXT,
            created_at TEXT
        );
        CREATE TABLE workflow_execution_reports (
            id TEXT PRIMARY KEY,
            run_id TEXT,
            invocation_id TEXT,
            workflow_key TEXT,
            status TEXT,
            artifact_path TEXT,
            created_at TEXT
        );
        """
    )
    conn.execute("INSERT INTO projects (id, name, status) VALUES ('p1', 'AIOS', 'active')")
    conn.execute(
        """
        INSERT INTO sessions (id, project_id, status, started_at, ended_at, cwd)
        VALUES ('s1', 'p1', 'closed', '2026-04-23T00:00:00Z', '2026-04-23T00:10:00Z', '/repo')
        """
    )
    conn.execute(
        """
        INSERT INTO bug_log (id, project_id, symptom, status, created_at)
        VALUES ('b1', 'p1', 'TypeError: boom', 'open', '2026-04-23T00:20:00Z')
        """
    )
    conn.execute("INSERT INTO orchestration_runs (id, status) VALUES ('run-1', 'failed')")
    conn.execute(
        """
        INSERT INTO orchestration_run_events (id, run_id, to_status, summary, reason_json, created_at)
        VALUES ('e1', 'run-1', 'failed', 'Run failed', '{}', '2026-04-23T00:30:00Z')
        """
    )
    conn.execute(
        """
        INSERT INTO workflow_execution_reports (
            id, run_id, invocation_id, workflow_key, status, artifact_path, created_at
        )
        VALUES (
            'wr-1', 'run-1', 'inv-1', 'academic_paper_v1', 'completed',
            '/tmp/workflow-report.json', '2026-04-23T00:35:00Z'
        )
        """
    )
    conn.commit()
    conn.close()


def test_status_and_recent_failures_json(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "aios.db"
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    (logs_dir / "hooks.log").write_text(
        "2026-04-23T00:40:00Z [hook] error: failed example\n",
        encoding="utf-8",
    )
    _seed_db(db_path)

    status_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "status",
        ]
    )
    assert status_exit == EXIT_OK
    status_output = json.loads(capsys.readouterr().out)
    assert status_output["ok"] is True
    assert status_output["command"] == "status"
    assert status_output["data"]["projects_active"] == 1

    failures_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "recent-failures",
            "--last",
            "5",
        ]
    )
    assert failures_exit == EXIT_OK
    failures_output = json.loads(capsys.readouterr().out)
    assert failures_output["ok"] is True
    assert failures_output["command"] == "recent-failures"
    assert failures_output["data"]["count"] >= 2


def test_metadata_and_skills_refresh_flow(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "aios.db"
    logs_dir = tmp_path / "logs"
    config_root = tmp_path / "config"
    vault_root = tmp_path / "vault"
    logs_dir.mkdir()
    config_root.mkdir()
    vault_root.mkdir()

    _seed_db(db_path)

    arch_dir = config_root / "architecture-enforcement"
    arch_dir.mkdir()
    (arch_dir / "projects.json").write_text(
        json.dumps(
            {
                "projects": [
                    {
                        "id": "aios",
                        "name": "AIOS",
                        "path": str(tmp_path),
                        "proof_target": True,
                        "profile_bindings": [{"profile_id": "python-service-v1"}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    source_file = tmp_path / "source.md"
    source_file.write_text("hello from source\n", encoding="utf-8")
    (config_root / "instruction-registry.json").write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "id": "global",
                        "project_id": None,
                        "source": str(source_file),
                        "target": "06 Knowledge/Claude-Context/global.md",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    criteria_dir = config_root / "success-criteria"
    criteria_dir.mkdir()
    (criteria_dir / "registry.json").write_text(
        json.dumps(
            {
                "criteria": [
                    {
                        "id": "code-simplicity",
                        "title": "Protect Simplicity and Comprehension",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    workflows_dir = config_root / "workflows"
    workflows_dir.mkdir()
    (workflows_dir / "registry.json").write_text(
        json.dumps(
            {
                "workflows": [
                    {
                        "key": "academic_paper_v1",
                        "name": "Academic Paper v1",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE success_criteria_evaluations (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            run_id TEXT,
            session_id TEXT,
            pass_count INTEGER,
            warning_count INTEGER,
            blocker_count INTEGER,
            summary TEXT,
            created_at TEXT
        )
        """
    )
    conn.execute(
        """
        INSERT INTO success_criteria_evaluations (
            id, project_id, run_id, session_id, pass_count, warning_count, blocker_count, summary, created_at
        )
        VALUES ('eval-1', 'p1', 'run-1', 's1', 3, 1, 0, 'latest criteria summary', '2026-04-23T00:50:00Z')
        """
    )
    conn.commit()
    conn.close()

    metadata_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "--config-root",
            str(config_root),
            "--vault-root",
            str(vault_root),
            "metadata",
        ]
    )
    assert metadata_exit == EXIT_OK
    metadata_output = json.loads(capsys.readouterr().out)
    assert metadata_output["ok"] is True
    assert metadata_output["data"]["linked_projects"]["count"] == 1
    assert metadata_output["data"]["instructions"]["summary"]["missing_target"] == 1
    assert metadata_output["data"]["success_criteria"]["catalog"]["count"] == 1
    assert metadata_output["data"]["success_criteria"]["latest_evaluation"]["id"] == "eval-1"
    assert metadata_output["data"]["workflow_orchestration"]["registry"]["count"] == 1
    assert metadata_output["data"]["workflow_orchestration"]["latest_execution_report"]["id"] == "wr-1"

    dry_run_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "--config-root",
            str(config_root),
            "--vault-root",
            str(vault_root),
            "skills",
            "refresh",
        ]
    )
    assert dry_run_exit == EXIT_OK
    dry_run_output = json.loads(capsys.readouterr().out)
    assert dry_run_output["data"]["pending_count"] == 1
    assert dry_run_output["data"]["updated_count"] == 0

    apply_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "--config-root",
            str(config_root),
            "--vault-root",
            str(vault_root),
            "skills",
            "refresh",
            "--apply",
        ]
    )
    assert apply_exit == EXIT_OK
    apply_output = json.loads(capsys.readouterr().out)
    assert apply_output["data"]["updated_count"] == 1

    status_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "--config-root",
            str(config_root),
            "--vault-root",
            str(vault_root),
            "skills",
            "status",
        ]
    )
    assert status_exit == EXIT_OK
    status_output = json.loads(capsys.readouterr().out)
    assert status_output["data"]["summary"]["in_sync"] == 1
