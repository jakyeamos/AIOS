from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Sequence
from pathlib import Path

DEFAULT_QUALITY_RUNNER_GIT_URL = "git+https://github.com/jakyeamos/quality-runner.git"


def run_quality_runner_rollout(
    *,
    repo_list_path: Path | None,
    repos: list[str],
    run_id_prefix: str | None,
    output_dir: Path | None,
    profile: str | None,
    ci_status_json: Path | None,
    timeout_seconds: int,
    workflow_timeout_seconds: int | None,
    verify_timeout_seconds: int | None,
    workflow_timeout_reason: str | None,
    total_timeout_seconds: int | None,
    total_timeout_reason: str | None,
    checkout_most_advanced_branch: bool,
    allow_mutating_gates: bool,
) -> dict[str, object]:
    command = quality_runner_rollout_command(
        repo_list_path=repo_list_path,
        repos=repos,
        run_id_prefix=run_id_prefix,
        output_dir=output_dir,
        profile=profile,
        ci_status_json=ci_status_json,
        timeout_seconds=timeout_seconds,
        workflow_timeout_seconds=workflow_timeout_seconds,
        verify_timeout_seconds=verify_timeout_seconds,
        workflow_timeout_reason=workflow_timeout_reason,
        total_timeout_seconds=total_timeout_seconds,
        total_timeout_reason=total_timeout_reason,
        checkout_most_advanced_branch=checkout_most_advanced_branch,
        allow_mutating_gates=allow_mutating_gates,
    )
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
        )
    except OSError as error:
        raise RuntimeError(f"Could not launch Quality Runner tool: {error}") from error
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "no output"
        raise RuntimeError(
            f"Quality Runner tool exited with status {completed.returncode}: {detail}"
        )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError("Quality Runner tool returned invalid JSON") from error
    if not isinstance(payload, dict):
        raise RuntimeError("Quality Runner tool returned a non-object JSON payload")
    return payload


def quality_runner_rollout_command(
    *,
    repo_list_path: Path | None,
    repos: Sequence[str],
    run_id_prefix: str | None,
    output_dir: Path | None,
    profile: str | None,
    ci_status_json: Path | None,
    timeout_seconds: int,
    workflow_timeout_seconds: int | None,
    verify_timeout_seconds: int | None,
    workflow_timeout_reason: str | None,
    total_timeout_seconds: int | None,
    total_timeout_reason: str | None,
    checkout_most_advanced_branch: bool,
    allow_mutating_gates: bool,
) -> list[str]:
    command = _quality_runner_entrypoint()
    if repo_list_path is not None:
        command.append(str(repo_list_path.expanduser().resolve()))
    for repo in repos:
        command.extend(["--repo", str(Path(repo).expanduser().resolve())])
    _append_option(command, "--run-id-prefix", run_id_prefix)
    _append_option(command, "--output-dir", _resolved_path(output_dir))
    _append_option(command, "--profile", profile)
    _append_option(command, "--ci-status-json", _resolved_path(ci_status_json))
    _append_option(command, "--timeout-seconds", str(timeout_seconds))
    _append_option(command, "--workflow-timeout-seconds", _optional_int(workflow_timeout_seconds))
    _append_option(command, "--verify-timeout-seconds", _optional_int(verify_timeout_seconds))
    _append_option(command, "--workflow-timeout-reason", workflow_timeout_reason)
    _append_option(command, "--total-timeout-seconds", _optional_int(total_timeout_seconds))
    _append_option(command, "--total-timeout-reason", total_timeout_reason)
    if checkout_most_advanced_branch:
        command.append("--checkout-most-advanced-branch")
    if allow_mutating_gates:
        command.append("--allow-mutating-gates")
    command.append("--json")
    return command


def _quality_runner_entrypoint() -> list[str]:
    mode = os.environ.get("QUALITY_RUNNER_MODE", "latest").strip().lower()
    if mode in {"latest", "remote"}:
        git_url = os.environ.get("QUALITY_RUNNER_GIT_URL", DEFAULT_QUALITY_RUNNER_GIT_URL)
        return ["uvx", "--refresh", "--from", git_url, "quality-runner", "rollout"]
    if mode == "local":
        repo = os.environ.get("QUALITY_RUNNER_REPO", "").strip()
        if not repo:
            raise RuntimeError("QUALITY_RUNNER_REPO is required when QUALITY_RUNNER_MODE=local")
        return [
            "uv",
            "run",
            "--project",
            str(Path(repo).expanduser().resolve()),
            "quality-runner",
            "rollout",
        ]
    raise RuntimeError("QUALITY_RUNNER_MODE must be latest, remote, or local")


def _append_option(command: list[str], option: str, value: str | None) -> None:
    if value:
        command.extend([option, value])


def _optional_int(value: int | None) -> str | None:
    return str(value) if value is not None else None


def _resolved_path(path: Path | None) -> str | None:
    return str(path.expanduser().resolve()) if path is not None else None
