# ruff: noqa: E402

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.aios_cli import EXIT_OK, run_cli  # noqa: E402


class _Completed:
    def __init__(self, stdout: str = "") -> None:
        self.stdout = stdout


def test_shadow_create_worktree_and_cleanup_cli_json(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "aios.db"
    logs_dir = tmp_path / "logs"
    repo = tmp_path / "repo"
    logs_dir.mkdir()
    repo.mkdir()
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE eval_tasks (
          id TEXT PRIMARY KEY,
          repo_id TEXT,
          source TEXT,
          start_sha TEXT NOT NULL,
          context_profile TEXT NOT NULL,
          task_type TEXT,
          prompt_summary TEXT,
          acceptance_criteria_json TEXT,
          success_criteria_files_json TEXT,
          created_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()

    with patch("services.shadow_branch_runner.subprocess.run") as run:
        run.side_effect = [_Completed(str(repo)), _Completed("")]
        exit_code = run_cli(
            [
                "--json",
                "--db",
                str(db_path),
                "--logs-dir",
                str(logs_dir),
                "shadow",
                "create-worktree",
                "--task-id",
                "Shadow Task",
                "--start-sha",
                "abc123",
                "--condition",
                "full-aios",
                "--repo-path",
                str(repo),
            ]
        )

    assert exit_code == EXIT_OK
    output = json.loads(capsys.readouterr().out)
    assert output["data"]["branch_name"] == "aios/eval/shadow-task/full-aios"
    assert output["data"]["contamination_check_passed"] is False

    with patch("services.shadow_branch_runner.subprocess.run") as run:
        run.return_value = _Completed("")
        cleanup_exit = run_cli(
            [
                "--json",
                "--db",
                str(db_path),
                "--logs-dir",
                str(logs_dir),
                "shadow",
                "cleanup",
                "--worktree-path",
                output["data"]["worktree_path"],
                "--repo-path",
                str(repo),
            ]
        )

    assert cleanup_exit == EXIT_OK
    cleanup_output = json.loads(capsys.readouterr().out)
    assert cleanup_output["data"]["removed"] is True
