# ruff: noqa: E402

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services import evidence_artifacts


def test_record_evidence_artifact_hashes_output_and_round_trips(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    stdout = tmp_path / "stdout.log"
    stdout.write_text("tests passed\n", encoding="utf-8")

    evidence_id = evidence_artifacts.record_evidence_artifact(
        conn,
        task_id="task-1",
        run_id="run-1",
        session_id="session-1",
        phase="verify",
        agent="codex",
        model="gpt",
        command="uv run pytest -q",
        exit_code=0,
        stdout_path=stdout,
        parsed_summary="7 passed",
        status="pass",
    )

    rows = evidence_artifacts.list_evidence_artifacts(conn, run_id="run-1")

    assert rows[0]["evidence_id"] == evidence_id
    assert rows[0]["status"] == "pass"
    assert rows[0]["output_hash"] == hashlib.sha256(b"tests passed\n").hexdigest()
    assert json.loads(str(rows[0]["caveats_json"])) == []


def test_empty_marker_pass_is_downgraded_to_unknown() -> None:
    conn = sqlite3.connect(":memory:")

    evidence_artifacts.record_evidence_artifact(
        conn,
        task_id="task-1",
        run_id="run-1",
        session_id="session-1",
        phase="verify",
        status="pass",
        parsed_summary="tests passed",
    )

    row = evidence_artifacts.list_evidence_artifacts(conn, run_id="run-1")[0]
    validation = evidence_artifacts.validate_fresh_evidence(
        conn,
        run_id="run-1",
        session_id="session-1",
    )

    assert row["status"] == "unknown"
    assert "empty-marker" in json.loads(str(row["caveats_json"]))
    assert validation["usable"] is False
    assert validation["unknown_count"] == 1


def test_freshness_requires_active_run_and_session(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    stdout = tmp_path / "stdout.log"
    stdout.write_text("ok\n", encoding="utf-8")
    evidence_artifacts.record_evidence_artifact(
        conn,
        task_id="task-1",
        run_id="old-run",
        session_id="old-session",
        phase="verify",
        command="pnpm test",
        exit_code=0,
        stdout_path=stdout,
        status="pass",
    )

    validation = evidence_artifacts.validate_fresh_evidence(
        conn,
        run_id="new-run",
        session_id="new-session",
    )

    assert validation["usable"] is False
    assert validation["stale_count"] == 1


def test_query_helpers_filter_run_and_session(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    stdout = tmp_path / "stdout.log"
    stdout.write_text("ok\n", encoding="utf-8")

    evidence_artifacts.record_evidence_artifact(
        conn,
        task_id="task-1",
        run_id="run-1",
        session_id="session-1",
        phase="verify",
        command="pytest",
        exit_code=0,
        stdout_path=stdout,
        status="pass",
    )
    evidence_artifacts.record_evidence_artifact(
        conn,
        task_id="task-2",
        run_id="run-2",
        session_id="session-2",
        phase="verify",
        command="pytest",
        exit_code=1,
        stdout_path=stdout,
        status="fail",
    )

    assert len(evidence_artifacts.list_evidence_artifacts(conn, run_id="run-1")) == 1
    assert len(evidence_artifacts.list_evidence_artifacts(conn, session_id="session-2")) == 1


def test_command_pass_without_exit_code_is_downgraded_to_unknown() -> None:
    conn = sqlite3.connect(":memory:")

    evidence_artifacts.record_evidence_artifact(
        conn,
        run_id="run-1",
        session_id="session-1",
        phase="tool-use",
        command="pytest -q",
        exit_code=None,
        status="pass",
        caveats=["output-absent:inline-output"],
    )

    row = evidence_artifacts.list_evidence_artifacts(conn, run_id="run-1")[0]

    assert row["status"] == "unknown"
    assert "exit-code-unavailable" in json.loads(str(row["caveats_json"]))


def test_command_pass_with_nonzero_exit_code_is_forced_to_fail() -> None:
    conn = sqlite3.connect(":memory:")

    evidence_artifacts.record_evidence_artifact(
        conn,
        run_id="run-1",
        session_id="session-1",
        phase="tool-use",
        command="pytest -q",
        exit_code=2,
        status="pass",
        caveats=["output-absent:inline-output"],
    )

    row = evidence_artifacts.list_evidence_artifacts(conn, run_id="run-1")[0]

    assert row["status"] == "fail"
    assert "status-exit-code-mismatch" in json.loads(str(row["caveats_json"]))


def test_command_pass_with_zero_exit_code_stays_pass() -> None:
    conn = sqlite3.connect(":memory:")

    evidence_artifacts.record_evidence_artifact(
        conn,
        run_id="run-1",
        session_id="session-1",
        phase="tool-use",
        command="pytest -q",
        exit_code=0,
        status="pass",
        caveats=["output-absent:inline-output"],
    )

    row = evidence_artifacts.list_evidence_artifacts(conn, run_id="run-1")[0]

    assert row["status"] == "pass"
