from __future__ import annotations

from services.external_benchmark_adapter import (
    normalize_external_result,
    to_swe_bench_format,
    to_terminal_bench_format,
)


def test_to_swe_bench_format_maps_required_fields() -> None:
    result = to_swe_bench_format(
        {
            "id": "task-1",
            "repo_id": "owner/repo",
            "prompt_summary": "Fix the bug.",
            "start_sha": "abc123",
            "fail_to_pass": ["test_bug"],
            "pass_to_pass": ["test_existing"],
        }
    )

    assert result == {
        "repo": "owner/repo",
        "instance_id": "task-1",
        "problem_statement": "Fix the bug.",
        "base_commit": "abc123",
        "FAIL_TO_PASS": ["test_bug"],
        "PASS_TO_PASS": ["test_existing"],
    }


def test_to_terminal_bench_format_maps_required_fields() -> None:
    result = to_terminal_bench_format(
        {
            "id": "task-1",
            "command": "pytest tests/test_bug.py",
            "expected_exit_code": 0,
            "setup_commands": ["uv sync"],
            "timeout_seconds": 120,
        }
    )

    assert result["task_id"] == "task-1"
    assert result["command"] == "pytest tests/test_bug.py"
    assert result["expected_exit_code"] == 0
    assert result["setup_commands"] == ["uv sync"]
    assert result["timeout_seconds"] == 120


def test_normalize_external_result_sets_external_clean_room() -> None:
    result = normalize_external_result(
        {"passed": True, "tests_run": ["pytest"], "duration_ms": 1000},
        eval_task_id="task-1",
        harness="swe-bench",
        model="gpt-5",
    )

    assert result["mode"] == "external"
    assert result["context_profile"] == "external_clean_room"
    assert result["final_status"] == "success"


def test_normalize_external_result_derives_failed_status() -> None:
    result = normalize_external_result(
        {"passed": False},
        eval_task_id="task-1",
        harness="terminal-bench",
        model="gpt-5",
    )

    assert result["final_status"] == "failed"
