from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.aios_cli import EXIT_OK, run_cli  # noqa: E402
from services.harness import (  # noqa: E402
    brief_task,
    replay_session,
    shadow_evaluate_session,
    simulate_fixture,
)


def _apply_schema(conn: sqlite3.Connection) -> None:
    conn.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))


def _seed_project(conn: sqlite3.Connection, repo_path: Path) -> None:
    conn.execute(
        """
        INSERT INTO projects (id, name, repo_path, obsidian_path, status)
        VALUES ('project-aios', 'AIOS', ?, ?, 'active')
        """,
        (str(repo_path), str(repo_path)),
    )


def _seed_db(path: Path, repo_path: Path) -> None:
    conn = sqlite3.connect(path)
    _apply_schema(conn)
    _seed_project(conn, repo_path)
    conn.commit()
    conn.close()


def test_brief_task_combines_context_and_success_criteria(tmp_path: Path) -> None:
    db_path = tmp_path / "aios.db"
    _seed_db(db_path, ROOT)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    briefing = brief_task(
        conn,
        task="Add OIDC federation policy to AIOS global secret handling rules.",
        project_id="project-aios",
        context_root=ROOT / "aios" / "context",
    )

    selected_ids = {item["id"] for item in briefing["selected_context_packets"]}
    criteria_ids = {item["id"] for item in briefing["success_criteria"]}
    conn.close()

    assert "global.security" in selected_ids
    assert "packets.security.oidc-secrets" in selected_ids
    assert "packets.ui.command-center" not in selected_ids
    assert "security-review" in criteria_ids
    assert "global_standards_change" in briefing["approval_requirements"]


def test_simulate_fixture_blocks_claimed_completion_after_failed_tests(tmp_path: Path) -> None:
    db_path = tmp_path / "aios.db"
    _seed_db(db_path, ROOT)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    report = simulate_fixture(
        conn,
        fixture_path=ROOT / "tests" / "fixtures" / "harness" / "failed-claimed-complete.json",
        context_root=ROOT / "aios" / "context",
    )

    run = conn.execute(
        "SELECT status FROM orchestration_runs WHERE id = ?",
        (report["run_id"],),
    ).fetchone()
    writebacks = conn.execute("SELECT COUNT(*) FROM improvement_writebacks").fetchone()[0]
    conn.close()

    assert run["status"] == "failed_validation"
    assert report["evaluation"]["completion_status"] == "not_complete"
    assert "tests_failed" in report["evaluation"]["violations"]
    assert "claimed_complete_after_failed_gate" in report["evaluation"]["violations"]
    assert report["evaluation"]["health_delta"]["direction"] == "negative"
    assert report["evaluation"]["writeback_proposal_eligible"] is False
    assert writebacks == 0


def test_simulate_fixture_allows_completed_when_gates_pass(tmp_path: Path) -> None:
    db_path = tmp_path / "aios.db"
    _seed_db(db_path, ROOT)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    report = simulate_fixture(
        conn,
        fixture_path=ROOT / "tests" / "fixtures" / "harness" / "passing-complete.json",
        context_root=ROOT / "aios" / "context",
    )

    run = conn.execute(
        "SELECT status FROM orchestration_runs WHERE id = ?",
        (report["run_id"],),
    ).fetchone()
    conn.close()

    assert run["status"] == "completed"
    assert report["evaluation"]["completion_status"] == "complete"
    assert report["evaluation"]["violations"] == []
    assert report["evaluation"]["health_delta"]["direction"] == "positive"
    assert report["evaluation"]["approval_eligible"] is True


def test_replay_session_converts_existing_records_to_stable_events(tmp_path: Path) -> None:
    db_path = tmp_path / "aios.db"
    _seed_db(db_path, ROOT)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        INSERT INTO sessions (id, project_id, tool, started_at, ended_at, objective, status, cwd)
        VALUES (
            'session-replay', 'project-aios', 'claude-code',
            '2026-05-14T00:00:00Z', '2026-05-14T00:10:00Z',
            'Replay an old harness run', 'closed', ?
        )
        """,
        (str(ROOT),),
    )
    conn.execute(
        """
        INSERT INTO tool_events (id, session_id, source_tool, event_type, event_time, payload_json)
        VALUES (
            'tool-1', 'session-replay', 'claude-code', 'PostToolUse',
            '2026-05-14T00:02:00Z', '{"tool":"Bash","command":"uv run pytest","exit_code":1}'
        )
        """
    )
    conn.execute(
        """
        INSERT INTO artifacts (id, session_id, artifact_type, path, metadata_json)
        VALUES ('artifact-1', 'session-replay', 'patch', 'services/harness.py', '{}')
        """
    )
    conn.commit()

    first = replay_session(conn, session_id="session-replay")
    second = replay_session(conn, session_id="session-replay")
    conn.close()

    assert first == second
    assert [event["type"] for event in first["events"]] == [
        "task_created",
        "agent_started",
        "tests_failed",
        "file_changed",
        "run_closed_failed",
    ]


def test_shadow_evaluate_latest_session_is_read_only_report(tmp_path: Path) -> None:
    db_path = tmp_path / "aios.db"
    _seed_db(db_path, ROOT)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        INSERT INTO sessions (id, project_id, tool, started_at, objective, status, cwd)
        VALUES (
            'session-shadow', 'project-aios', 'codex',
            '2026-05-14T00:00:00Z', 'Shadow evaluate current work', 'open', ?
        )
        """,
        (str(ROOT),),
    )
    conn.commit()

    report = shadow_evaluate_session(conn, session_id="latest")
    run_count = conn.execute("SELECT COUNT(*) FROM orchestration_runs").fetchone()[0]
    conn.close()

    assert report["mode"] == "shadow"
    assert report["session_id"] == "session-shadow"
    assert report["evaluation"]["completion_status"] == "not_complete"
    assert run_count == 0


def test_harness_cli_commands_emit_json(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "aios.db"
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    _seed_db(db_path, ROOT)

    brief_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "harness-brief",
            "--task",
            "Add OIDC federation policy to AIOS global secret handling rules.",
            "--project",
            "project-aios",
        ]
    )
    assert brief_exit == EXIT_OK
    brief = json.loads(capsys.readouterr().out)
    assert (
        brief["data"]["task"] == "Add OIDC federation policy to AIOS global secret handling rules."
    )

    simulate_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "harness-simulate",
            "--fixture",
            str(ROOT / "tests" / "fixtures" / "harness" / "failed-claimed-complete.json"),
        ]
    )
    assert simulate_exit == EXIT_OK
    simulated = json.loads(capsys.readouterr().out)
    assert simulated["data"]["evaluation"]["completion_status"] == "not_complete"
