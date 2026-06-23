from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_LOG_RELATIVE_PATH = Path(".aios") / "native-command-metadata.jsonl"


def native_command_metadata(
    *,
    command_name: str,
    repo_root: Path,
    scope: dict[str, Any],
    safety_class: str,
    status: str,
    read_only: bool,
    modifying: bool,
    reviewer_lanes: list[str] | None = None,
    files_touched: list[str] | None = None,
    tests_run: list[str] | None = None,
    user_confirmation_required: bool = False,
    user_confirmation_received: bool = False,
    model: str | None = None,
    reasoning_level: str | None = None,
    token_cost_estimate: float | None = None,
    runtime_ms: int | None = None,
    run_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    root = repo_root.resolve()
    return {
        "command_name": command_name,
        "timestamp": datetime.now(UTC).isoformat(),
        "repo_root": str(root),
        "project": root.name,
        "branch": _git_branch(root),
        "scope": scope,
        "safety_class": safety_class,
        "read_only": read_only,
        "modifying": modifying,
        "model": model,
        "reasoning_level": reasoning_level,
        "reviewer_lanes": reviewer_lanes or [],
        "files_touched": files_touched or [],
        "tests_run": tests_run or [],
        "status": status,
        "user_confirmation_required": user_confirmation_required,
        "user_confirmation_received": user_confirmation_received,
        "token_cost_estimate": token_cost_estimate,
        "runtime_ms": runtime_ms,
        "run_id": run_id,
        "session_id": session_id,
        "telemetry": "local_jsonl_only",
    }


def write_native_command_metadata(
    record: dict[str, Any],
    *,
    repo_root: Path,
    log_path: Path | None = None,
) -> Path:
    destination = _resolve_log_path(repo_root=repo_root, log_path=log_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    return destination


def _resolve_log_path(*, repo_root: Path, log_path: Path | None) -> Path:
    root = repo_root.resolve()
    destination = root / DEFAULT_LOG_RELATIVE_PATH if log_path is None else log_path
    if not destination.is_absolute():
        destination = root / destination
    resolved = destination.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("Native command metadata log path must stay inside the repo root.")
    return resolved


def _git_branch(repo_root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return None
    branch = result.stdout.strip()
    return branch or None
