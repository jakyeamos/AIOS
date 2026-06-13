# ruff: noqa: E402

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.aios_cli import EXIT_OK, run_cli  # noqa: E402
from services.eval_run_service import (  # noqa: E402
    create_eval_run,
    create_eval_task,
    record_eval_score,
)
from services.second_brain_eval import record_retrieval, register_gold_set_task  # noqa: E402


def test_eval_second_brain_cli_commands_json(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "aios.db"
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    task_id = create_eval_task(
        conn,
        repo_id="p1",
        source="gold-set",
        start_sha="abc123",
        context_profile="jakye_repo_only",
        task_type="feature",
        prompt_summary="Measure second brain lift.",
        acceptance_criteria=["uses project truth"],
        success_criteria_files=["tests/test_second_brain_eval_cli.py"],
    )
    full_run_id = create_eval_run(
        conn,
        task_id=task_id,
        condition="full-second-brain",
        mode="controlled",
        harness="pytest",
        model="gpt-5",
        context_profile="jakye_second_brain_full",
        final_status="success",
    )
    repo_only_run_id = create_eval_run(
        conn,
        task_id=task_id,
        condition="repo-only",
        mode="controlled",
        harness="pytest",
        model="gpt-5",
        context_profile="jakye_repo_only",
        final_status="success",
    )
    record_eval_score(conn, run_id=full_run_id, overall_score=0.9)
    record_eval_score(conn, run_id=repo_only_run_id, overall_score=0.6)
    gold_task_id = register_gold_set_task(
        conn,
        task_id=task_id,
        required_sources=[{"source_id": "PROJECT.md", "source_type": "project_truth"}],
        known_correct_outcome="Uses project truth.",
    )
    record_retrieval(
        conn,
        run_id=full_run_id,
        source_type="project_truth",
        source_id="PROJECT.md",
        source_path=".planning/PROJECT.md",
        was_needed=True,
    )
    conn.commit()
    conn.close()

    lift_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "eval",
            "second-brain-lift",
            "--full-run-id",
            full_run_id,
            "--repo-only-run-id",
            repo_only_run_id,
        ]
    )
    assert lift_exit == EXIT_OK
    lift_output = json.loads(capsys.readouterr().out)
    assert lift_output["data"]["available"] is True
    assert lift_output["data"]["overall_lift"] == 0.30000000000000004

    metrics_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "eval",
            "retrieval-metrics",
            "--run-id",
            full_run_id,
        ]
    )
    assert metrics_exit == EXIT_OK
    metrics_output = json.loads(capsys.readouterr().out)
    assert metrics_output["data"]["precision"] == 1.0
    assert metrics_output["data"]["count_total"] == 1

    gold_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "eval",
            "gold-set-run",
            "--run-id",
            full_run_id,
            "--gold-task-id",
            gold_task_id,
        ]
    )
    assert gold_exit == EXIT_OK
    gold_output = json.loads(capsys.readouterr().out)
    assert gold_output["data"]["recall"] == 1.0
    assert gold_output["data"]["missed_sources"] == []
