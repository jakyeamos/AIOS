# ruff: noqa: E402

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.aios_cli import EXIT_OK, run_cli  # noqa: E402
from services.peer_trace import record_peer_trace  # noqa: E402


def test_peer_trace_cli_start_stop_list_and_shadow_score(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "aios.db"
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    sqlite3.connect(db_path).close()

    start_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "peer-trace",
            "start",
            "--peer-id",
            "peer-hash",
            "--harness",
            "codex",
        ]
    )
    assert start_exit == EXIT_OK
    start_output = json.loads(capsys.readouterr().out)
    session_id = start_output["data"]["session_id"]

    list_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "peer-trace",
            "list",
        ]
    )
    assert list_exit == EXIT_OK
    list_output = json.loads(capsys.readouterr().out)
    assert list_output["data"]["count"] == 1

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    trace_id = record_peer_trace(
        conn,
        session_id=session_id,
        task_category="feature",
        prompt_length=120,
        turn_count=5,
        tool_call_count=8,
        failed_command_count=0,
        duration_ms=6000,
        files_changed_count=4,
        tests_run=3,
        final_status="success",
    )
    conn.commit()
    conn.close()

    score_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "shadow",
            "score",
            "--trace-id",
            trace_id,
        ]
    )
    assert score_exit == EXIT_OK
    score_output = json.loads(capsys.readouterr().out)
    assert score_output["data"]["candidate_id"].startswith("shadow-candidate-")

    stop_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "peer-trace",
            "stop",
            "--session-id",
            session_id,
        ]
    )
    assert stop_exit == EXIT_OK
    stop_output = json.loads(capsys.readouterr().out)
    assert stop_output["data"]["ended"] is True
