# ruff: noqa: E402

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.aios_cli import EXIT_OK, run_cli
from services.run_verification import verify_run


def _canonical_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
    conn.execute(
        """
        INSERT INTO projects (id, name, repo_path, obsidian_path, status)
        VALUES ('p1', 'AIOS', ?, '', 'active')
        """,
        (str(ROOT),),
    )
    conn.commit()
    conn.close()


def _verification_registry(path: Path, repo_root: Path, command: str = "true") -> Path:
    registry = path / "quality-gates.json"
    registry.write_text(
        json.dumps(
            {
                "version": "m4-test",
                "knownGates": ["m4_smoke"],
                "projects": [
                    {
                        "projectId": "p1",
                        "roots": [str(repo_root)],
                        "gates": {"m4_smoke": {"fullCommands": [[command]]}},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return registry


def test_start_work_verify_and_resume_use_fk_safe_canonical_envelope(
    tmp_path: Path,
    capsys,
) -> None:
    db_path = tmp_path / "aios.db"
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    (logs_dir / "current_session").write_text("session-p1", encoding="utf-8")
    _canonical_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO sessions (id, project_id, tool, started_at, status, cwd)
        VALUES ('session-p1', 'p1', 'codex', '2026-07-14T00:00:00Z', 'open', ?)
        """,
        (str(ROOT),),
    )
    conn.commit()
    conn.close()

    start_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "start-work",
            "Audit AIOS onboarding and ship a scoped fix with tests",
            "--project",
            "p1",
        ]
    )
    assert start_exit == EXIT_OK
    start_payload = json.loads(capsys.readouterr().out)["data"]
    run_id = str(start_payload["run"]["id"])
    invocation_id = str(start_payload["invocation"]["id"])
    packet_id = str(start_payload["packet"]["id"])

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    assert (
        conn.execute(
            "SELECT active_invocation_id FROM orchestration_runs WHERE id = ?",
            (run_id,),
        ).fetchone()[0]
        == invocation_id
    )
    assert (
        conn.execute(
            "SELECT run_id FROM orchestration_invocations WHERE id = ?",
            (invocation_id,),
        ).fetchone()[0]
        == run_id
    )
    assert (
        conn.execute(
            "SELECT run_id FROM briefing_packets WHERE id = ?",
            (packet_id,),
        ).fetchone()[0]
        == run_id
    )
    event_rows = conn.execute(
        "SELECT event_type, invocation_id FROM orchestration_run_events WHERE run_id = ?",
        (run_id,),
    ).fetchall()
    assert {row[0] for row in event_rows} == {
        "planned",
        "ready",
        "strict_manual_invocation_registered",
    }
    assert any(row[1] == invocation_id for row in event_rows)

    conn.execute(
        """
        UPDATE orchestration_runs
        SET status = 'partial',
            resume_snapshot_json = ?,
            updated_at = '2026-07-14T00:00:00Z'
        WHERE id = ?
        """,
        (
            json.dumps(
                {
                    "packet_id": packet_id,
                    "current_stage": "verification",
                    "next_recommended_action": "Resume verification from the saved packet.",
                    "pending_approval_count": 0,
                    "approval_targets": [],
                    "updated_at": "2026-07-14T00:00:00Z",
                }
            ),
            run_id,
        ),
    )
    conn.commit()
    conn.close()

    status_exit = run_cli(["--json", "--db", str(db_path), "status"])
    assert status_exit == EXIT_OK
    resumable = json.loads(capsys.readouterr().out)["data"]["resumable_runs"]
    assert resumable[0]["run_id"] == run_id
    assert resumable[0]["current_stage"] == "verification"

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    registry = _verification_registry(tmp_path, repo_root)
    conn = sqlite3.connect(db_path)
    verification = verify_run(
        conn,
        run_id=run_id,
        repo_root=repo_root,
        gate_ids=["m4_smoke"],
        registry_path=registry,
    )
    assert verification["result"] == "pass"
    assert verification["run_status"] == {"from": "partial", "to": "completed"}
    assert verification["evidence_refs"]
    assert (
        conn.execute(
            "SELECT COUNT(*) FROM verifier_artifacts WHERE run_id = ?",
            (run_id,),
        ).fetchone()[0]
        == 1
    )
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    conn.close()


def test_failed_verification_preserves_a_resumable_snapshot(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "aios.db"
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    _canonical_db(db_path)
    start_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "start-work",
            "Audit AIOS onboarding and ship a scoped fix with tests",
            "--project",
            "p1",
        ]
    )
    assert start_exit == EXIT_OK
    run_id = str(json.loads(capsys.readouterr().out)["data"]["run"]["id"])
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    registry = _verification_registry(tmp_path, repo_root, command="false")

    conn = sqlite3.connect(db_path)
    verification = verify_run(
        conn,
        run_id=run_id,
        repo_root=repo_root,
        gate_ids=["m4_smoke"],
        registry_path=registry,
    )
    assert verification["result"] == "fail"
    snapshot = json.loads(
        conn.execute(
            "SELECT resume_snapshot_json FROM orchestration_runs WHERE id = ?",
            (run_id,),
        ).fetchone()[0]
    )
    assert snapshot["current_stage"] == "verification"
    assert (
        snapshot["next_recommended_action"] == "Resolve verifier blockers and resume verification."
    )
    assert snapshot["verification_result"] == "fail"
    assert snapshot["blocking_issue_count"] == 1
    conn.close()


def test_start_work_blocks_cross_project_session_linkage(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "aios.db"
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    (logs_dir / "current_session").write_text("session-p1", encoding="utf-8")
    _canonical_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO projects (id, name, repo_path, obsidian_path, status) VALUES ('p2', 'Other', '/other', '', 'active')"
    )
    conn.execute(
        """
        INSERT INTO sessions (id, project_id, tool, started_at, status, cwd)
        VALUES ('session-p1', 'p1', 'codex', '2026-07-14T00:00:00Z', 'open', ?)
        """,
        (str(ROOT),),
    )
    conn.commit()
    conn.close()

    start_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "start-work",
            "Audit AIOS onboarding and ship a scoped fix with tests",
            "--project",
            "p2",
        ]
    )
    assert start_exit != EXIT_OK
    error = json.loads(capsys.readouterr().out)["error"]
    assert error["code"] == "session-project-mismatch"
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM orchestration_runs").fetchone()[0] == 0
    conn.close()
