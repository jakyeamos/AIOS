# ruff: noqa: E402

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.eval_run_service import (  # noqa: E402
    create_eval_run,
    create_eval_task,
    record_eval_score,
)
from services.shadow_branch_runner import (  # noqa: E402
    ShadowBranchSafetyError,
    capture_diff_stat,
    capture_test_delta,
    cleanup_shadow_worktree,
    compute_shadow_branch_delta,
    create_shadow_worktree,
    shadow_branch_name,
    verify_no_contamination,
)


class _Completed:
    def __init__(self, stdout: str = "") -> None:
        self.stdout = stdout


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
    return conn


def test_create_shadow_worktree_returns_path(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    with patch("services.shadow_branch_runner.subprocess.run") as run:
        run.side_effect = [_Completed(str(repo)), _Completed("")]

        worktree_path = create_shadow_worktree(
            repo_path=repo,
            start_sha="abc123",
            branch_name="aios/eval/task/full-aios",
        )

    assert worktree_path.endswith(".aios/shadow-worktrees/aios-eval-task-full-aios")
    assert run.call_args_list[1].args[0][:3] == ["git", "worktree", "add"]


def test_create_shadow_worktree_rejects_active_tree_path(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    branch = "aios/eval/task/full-aios"
    active_path = repo / ".aios" / "shadow-worktrees" / branch.replace("/", "-")

    with patch("services.shadow_branch_runner.subprocess.run") as run:
        run.return_value = _Completed(str(active_path))
        with pytest.raises(ShadowBranchSafetyError):
            create_shadow_worktree(repo_path=repo, start_sha="abc123", branch_name=branch)


def test_verify_no_contamination_clean_and_contaminated() -> None:
    with patch("services.shadow_branch_runner.subprocess.run") as run:
        run.return_value = _Completed("")
        assert verify_no_contamination(
            baseline_branch="main",
            shadow_branch="aios/eval/task/full-aios",
            repo_path=".",
        )
        run.return_value = _Completed("abc123 changed baseline\n")
        assert not verify_no_contamination(
            baseline_branch="main",
            shadow_branch="aios/eval/task/full-aios",
            repo_path=".",
        )


def test_capture_diff_stat_parses_shortstat() -> None:
    with patch("services.shadow_branch_runner.subprocess.run") as run:
        run.return_value = _Completed(" 3 files changed, 12 insertions(+), 4 deletions(-)\n")
        diff = capture_diff_stat(
            baseline_branch="main",
            aios_branch="aios/eval/task/full-aios",
            repo_path=".",
        )

    assert diff == {"files_changed": 3, "insertions": 12, "deletions": 4}


def test_capture_test_delta_counts_new_and_fixed_failures() -> None:
    delta = capture_test_delta(
        baseline_result={"pass_count": 8, "failures": ["test_a", "test_b"]},
        aios_result={"pass_count": 9, "failures": ["test_b", "test_c"]},
    )

    assert delta == {
        "baseline_pass_count": 8,
        "aios_pass_count": 9,
        "new_failures": ["test_c"],
        "fixed_failures": ["test_a"],
    }


def test_compute_shadow_branch_delta() -> None:
    assert (
        compute_shadow_branch_delta(
            baseline_score={"overall_score": 0.55},
            aios_score={"overall_score": 0.8},
        )
        == 0.25
    )


def test_cleanup_shadow_worktree_uses_git_worktree_remove() -> None:
    with patch("services.shadow_branch_runner.subprocess.run") as run:
        run.return_value = _Completed("")
        cleanup_shadow_worktree(worktree_path="/tmp/wt", repo_path="/repo")

    assert run.call_args.args[0] == ["git", "worktree", "remove", "--force", "/tmp/wt"]


def test_shadow_branch_name_is_url_safe_and_bounded() -> None:
    branch = shadow_branch_name(
        task_id="Task With Spaces And !@# A Very Long Name That Needs Truncation",
        condition="aios_no_second_brain",
    )

    assert branch.startswith("aios/eval/task-with-spaces-and-a-very-long-name")
    assert branch.endswith("/aios-no-second-brain")


def test_shadow_branch_schema_available_with_eval_scores() -> None:
    conn = _connect()
    task_id = create_eval_task(
        conn,
        repo_id="p1",
        source="shadow",
        start_sha="abc123",
        context_profile="jakye_repo_only",
        task_type="feature",
        prompt_summary="Compare branches.",
        acceptance_criteria=[],
        success_criteria_files=[],
    )
    run_id = create_eval_run(
        conn,
        task_id=task_id,
        condition="baseline",
        mode="controlled",
        harness="pytest",
        model="gpt-5",
        context_profile="jakye_repo_only",
        final_status="success",
    )
    record_eval_score(conn, run_id=run_id, overall_score=0.7)

    row = conn.execute("SELECT overall_score FROM eval_scores WHERE run_id = ?", (run_id,)).fetchone()

    assert row["overall_score"] == 0.7
