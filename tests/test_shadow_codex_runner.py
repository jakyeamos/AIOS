# ruff: noqa: E402

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.shadow_branch_runner import (  # noqa: E402
    record_shadow_branch_run,
)
from services.shadow_codex_runner import (  # noqa: E402
    build_codex_exec_command,
    launch_codex_shadow,
    score_codex_shadow_candidate,
    should_auto_run,
    skip_codex_shadow,
)


class _Process:
    pid = 4242


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
    return conn


def _shadow_run(conn: sqlite3.Connection, tmp_path: Path) -> str:
    worktree = tmp_path / "shadow"
    worktree.mkdir()
    return record_shadow_branch_run(
        conn,
        task_id="task-1",
        condition="full-aios",
        start_sha="abc123",
        aios_branch="codex/aios-shadow-task-1",
        worktree_path=str(worktree),
        no_evidence_reason="shadow lane created; implementation has not run yet",
        contamination_check_passed=True,
    )


def test_codex_exec_command_uses_sandbox_and_never_approval(tmp_path: Path) -> None:
    command = build_codex_exec_command(
        worktree_path=tmp_path,
        prompt="Do the task",
        final_message_path=tmp_path / "final.md",
    )

    assert command[:2] == ["codex", "exec"]
    assert command[command.index("--sandbox") + 1] == "workspace-write"
    assert command[command.index("--ask-for-approval") + 1] == "never"
    assert "--dangerously-bypass-approvals-and-sandbox" not in command


def test_good_candidate_is_auto_runnable(tmp_path: Path) -> None:
    score = score_codex_shadow_candidate(
        objective="Implement a multi-file release workflow with tests and verification proof",
        shadow={
            "worktree_path": str(tmp_path),
            "branch_name": "codex/aios-shadow-release-workflow",
        },
        route={"run_id": "run-1"},
        baseline_dirty=False,
    )

    assert score["recommendation"] in {"good_shadow_candidate", "excellent_shadow_candidate"}
    assert should_auto_run(score)


def test_blocked_candidate_does_not_auto_run(tmp_path: Path) -> None:
    score = score_codex_shadow_candidate(
        objective="fix typo",
        shadow={
            "worktree_path": str(tmp_path),
            "branch_name": "codex/aios-shadow-typo",
        },
        route={"run_id": "run-1"},
        baseline_dirty=False,
    )

    assert score["recommendation"] == "trace_only"
    assert not should_auto_run(score)
    assert "too_small" in score["blockers"]


def test_skip_records_shadow_execution_metadata(tmp_path: Path) -> None:
    conn = _connect()
    shadow_run_id = _shadow_run(conn, tmp_path)

    execution = skip_codex_shadow(
        conn,
        shadow_run_id=shadow_run_id,
        score={"recommendation": "trace_only", "blockers": ["too_small"]},
    )

    row = conn.execute(
        "SELECT execution_status, failure_classification, execution_metadata_json FROM shadow_branch_runs WHERE id = ?",
        (shadow_run_id,),
    ).fetchone()
    assert execution["status"] == "skipped"
    assert row["execution_status"] == "skipped"
    assert row["failure_classification"] == "shadow_execution_skipped"
    assert json.loads(row["execution_metadata_json"])["skip_reason"] == "blocked: too_small"


def test_launch_records_pid_and_artifact_paths(tmp_path: Path) -> None:
    conn = _connect()
    shadow_run_id = _shadow_run(conn, tmp_path)
    logs_dir = tmp_path / "logs"

    with patch("services.shadow_codex_runner.subprocess.Popen", return_value=_Process()) as popen:
        execution = launch_codex_shadow(
            conn,
            shadow_run_id=shadow_run_id,
            objective="Implement a multi-file workflow",
            run_id="run-1",
            packet_id="packet-1",
            route_id="route-1",
            logs_dir=logs_dir,
        )

    command = popen.call_args.args[0]
    assert execution["status"] == "running"
    assert execution["pid"] == 4242
    assert command[:2] == ["codex", "exec"]
    assert "--dangerously-bypass-approvals-and-sandbox" not in command
    assert str(logs_dir / shadow_run_id / "codex-exec.jsonl") == execution["output_jsonl_path"]

    row = conn.execute(
        "SELECT execution_status, execution_pid, execution_command_json FROM shadow_branch_runs WHERE id = ?",
        (shadow_run_id,),
    ).fetchone()
    assert row["execution_status"] == "running"
    assert row["execution_pid"] == 4242
    assert json.loads(row["execution_command_json"]) == command
