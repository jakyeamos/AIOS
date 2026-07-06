# ruff: noqa: E402

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.run_verification import RunVerificationError, verify_run
from services.verifier_artifacts import validate_closeout_verification


def _seed_db(status: str = "ready") -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE projects (id TEXT PRIMARY KEY, name TEXT)")
    conn.execute(
        """
        CREATE TABLE orchestration_runs (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            session_id TEXT,
            status TEXT,
            workflow_key TEXT,
            status_reason_json TEXT,
            updated_at TEXT,
            completed_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE orchestration_run_events (
            id TEXT PRIMARY KEY,
            run_id TEXT,
            project_id TEXT,
            session_id TEXT,
            event_type TEXT,
            from_status TEXT,
            to_status TEXT,
            summary TEXT,
            reason_json TEXT,
            metadata_json TEXT,
            created_at TEXT
        )
        """
    )
    conn.execute("INSERT INTO projects VALUES ('proj-1', 'fixture-project')")
    conn.execute(
        "INSERT INTO orchestration_runs (id, project_id, session_id, status, workflow_key)"
        " VALUES ('run-1', 'proj-1', 'session-1', ?, 'implementation-delivery')",
        (status,),
    )
    return conn


def _write_registry(tmp_path: Path, repo_root: Path, commands: list[list[str]]) -> Path:
    registry_path = tmp_path / "quality-gates.json"
    registry_path.write_text(
        json.dumps(
            {
                "version": "test",
                "knownGates": ["test_quality"],
                "projects": [
                    {
                        "projectId": "fixture-project",
                        "roots": [str(repo_root)],
                        "gates": {"test_quality": {"fullCommands": commands}},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return registry_path


def _write_contract(repo_root: Path) -> None:
    (repo_root / ".aios-quality-gate.json").write_text(
        json.dumps({"projectId": "fixture-project", "fullGates": ["test_quality"]}),
        encoding="utf-8",
    )


def test_passing_gates_complete_run_with_verifier_artifact(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_contract(repo_root)
    registry = _write_registry(tmp_path, repo_root, [["true"]])
    conn = _seed_db()

    payload = verify_run(conn, run_id="run-1", registry_path=registry)

    assert payload["result"] == "pass"
    assert payload["run_status"] == {"from": "ready", "to": "completed"}
    row = conn.execute("SELECT status, completed_at FROM orchestration_runs").fetchone()
    assert row["status"] == "completed"
    assert row["completed_at"] is not None
    evidence = conn.execute(
        "SELECT exit_code, status FROM evidence_artifacts WHERE phase='verification'"
    ).fetchone()
    assert evidence["exit_code"] == 0
    assert evidence["status"] == "pass"
    validation = validate_closeout_verification(
        conn,
        run_id="run-1",
        session_id="session-1",
        workflow_key="implementation-delivery",
        implementation_bearing=True,
    )
    assert validation["allowed"] is True


def test_failing_gate_blocks_completion_and_records_blocking_issue(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_contract(repo_root)
    registry = _write_registry(tmp_path, repo_root, [["false"]])
    conn = _seed_db()

    payload = verify_run(conn, run_id="run-1", registry_path=registry)

    assert payload["result"] == "fail"
    assert payload["run_status"] == {"from": "ready", "to": "failed_validation"}
    assert payload["blocking_issues"][0]["gate"] == "test_quality"
    row = conn.execute("SELECT status FROM orchestration_runs").fetchone()
    assert row["status"] == "failed_validation"
    event = conn.execute("SELECT event_type, to_status FROM orchestration_run_events").fetchone()
    assert event["event_type"] == "verify_run"
    assert event["to_status"] == "failed_validation"


def test_no_gates_configured_is_an_error(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    registry = _write_registry(tmp_path, repo_root, [["true"]])
    conn = _seed_db()

    with pytest.raises(RunVerificationError) as excinfo:
        verify_run(conn, run_id="run-1", registry_path=registry)

    assert excinfo.value.code == "no-gates-configured"


def test_canceled_run_cannot_be_verified(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_contract(repo_root)
    registry = _write_registry(tmp_path, repo_root, [["true"]])
    conn = _seed_db(status="canceled")

    with pytest.raises(RunVerificationError) as excinfo:
        verify_run(conn, run_id="run-1", registry_path=registry)

    assert excinfo.value.code == "run-canceled"


def test_unregistered_repo_root_is_rejected(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    other_root = tmp_path / "other"
    other_root.mkdir()
    _write_contract(repo_root)
    registry = _write_registry(tmp_path, repo_root, [["true"]])
    conn = _seed_db()

    with pytest.raises(RunVerificationError) as excinfo:
        verify_run(conn, run_id="run-1", repo_root=other_root, registry_path=registry)

    assert excinfo.value.code == "repo-root-unregistered"
