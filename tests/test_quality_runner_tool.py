from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from services.quality_runner_tool import (
    quality_runner_rollout_command,
    run_quality_runner_rollout,
)


def test_quality_runner_command_defaults_to_refreshing_remote_source(monkeypatch) -> None:
    monkeypatch.delenv("QUALITY_RUNNER_MODE", raising=False)
    monkeypatch.delenv("QUALITY_RUNNER_REPO", raising=False)
    command = quality_runner_rollout_command(
        repo_list_path=Path("repo-list.txt"),
        repos=["/tmp/one"],
        run_id_prefix="audit",
        output_dir=Path("artifacts"),
        profile="jakyeamos",
        ci_status_json=None,
        timeout_seconds=120,
        workflow_timeout_seconds=None,
        verify_timeout_seconds=180,
        workflow_timeout_reason=None,
        total_timeout_seconds=300,
        total_timeout_reason="fleet deadline",
        checkout_most_advanced_branch=True,
        allow_mutating_gates=False,
    )

    assert command[:5] == [
        "uvx",
        "--refresh",
        "--from",
        "git+https://github.com/jakyeamos/quality-runner.git",
        "quality-runner",
    ]
    assert command[5:] == [
        "rollout",
        str(Path("repo-list.txt").resolve()),
        "--repo",
        str(Path("/tmp/one").resolve()),
        "--run-id-prefix",
        "audit",
        "--output-dir",
        str(Path("artifacts").resolve()),
        "--profile",
        "jakyeamos",
        "--timeout-seconds",
        "120",
        "--verify-timeout-seconds",
        "180",
        "--total-timeout-seconds",
        "300",
        "--total-timeout-reason",
        "fleet deadline",
        "--checkout-most-advanced-branch",
        "--json",
    ]


def test_quality_runner_command_supports_local_checkout(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUALITY_RUNNER_MODE", "local")
    monkeypatch.setenv("QUALITY_RUNNER_REPO", str(tmp_path / "quality-runner"))

    command = quality_runner_rollout_command(
        repo_list_path=None,
        repos=[],
        run_id_prefix=None,
        output_dir=None,
        profile=None,
        ci_status_json=None,
        timeout_seconds=120,
        workflow_timeout_seconds=None,
        verify_timeout_seconds=None,
        workflow_timeout_reason=None,
        total_timeout_seconds=None,
        total_timeout_reason=None,
        checkout_most_advanced_branch=False,
        allow_mutating_gates=False,
    )

    assert command == [
        "uv",
        "run",
        "--project",
        str((tmp_path / "quality-runner").resolve()),
        "quality-runner",
        "rollout",
        "--timeout-seconds",
        "120",
        "--json",
    ]


def test_run_quality_runner_rollout_parses_json(monkeypatch) -> None:
    completed = subprocess.CompletedProcess(
        args=["uvx"],
        returncode=0,
        stdout='{"status":"completed"}',
        stderr="",
    )
    monkeypatch.setattr(
        "services.quality_runner_tool.subprocess.run", lambda *args, **kwargs: completed
    )

    result = run_quality_runner_rollout(
        repo_list_path=None,
        repos=["/tmp/demo"],
        run_id_prefix="demo",
        output_dir=None,
        profile=None,
        ci_status_json=None,
        timeout_seconds=120,
        workflow_timeout_seconds=None,
        verify_timeout_seconds=None,
        workflow_timeout_reason=None,
        total_timeout_seconds=None,
        total_timeout_reason=None,
        checkout_most_advanced_branch=False,
        allow_mutating_gates=False,
    )

    assert result == {"status": "completed"}


def test_run_quality_runner_rollout_rejects_failed_tool(monkeypatch) -> None:
    completed = subprocess.CompletedProcess(
        args=["uvx"],
        returncode=2,
        stdout="",
        stderr="runner failed",
    )
    monkeypatch.setattr(
        "services.quality_runner_tool.subprocess.run", lambda *args, **kwargs: completed
    )

    with pytest.raises(RuntimeError, match="runner failed"):
        run_quality_runner_rollout(
            repo_list_path=None,
            repos=["/tmp/demo"],
            run_id_prefix="demo",
            output_dir=None,
            profile=None,
            ci_status_json=None,
            timeout_seconds=120,
            workflow_timeout_seconds=None,
            verify_timeout_seconds=None,
            workflow_timeout_reason=None,
            total_timeout_seconds=None,
            total_timeout_reason=None,
            checkout_most_advanced_branch=False,
            allow_mutating_gates=False,
        )
