from __future__ import annotations

import os
import signal
import sqlite3
import subprocess
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from services.shadow_branch_runner import (
    get_shadow_run,
    update_shadow_execution_metadata,
)
from services.shadow_candidate_scorer import score_shadow_candidate

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOGS_DIR = REPO_ROOT / "logs" / "shadow-codex"
ELIGIBLE_RECOMMENDATIONS = {"good_shadow_candidate", "excellent_shadow_candidate"}
BLOCKER_TERMS = {
    "secret_risk": ("secret", "token", "credential", "api key", "password"),
    "private_external_system": (
        "stripe",
        "production",
        "prod database",
        "customer account",
        "bank",
    ),
}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _paths(logs_dir: Path, shadow_run_id: str) -> dict[str, str]:
    run_dir = logs_dir / shadow_run_id
    return {
        "run_dir": str(run_dir),
        "output_jsonl_path": str(run_dir / "codex-exec.jsonl"),
        "stderr_path": str(run_dir / "codex-exec.stderr.log"),
        "final_message_path": str(run_dir / "final-message.md"),
    }


def build_shadow_prompt(
    *,
    objective: str,
    run_id: str | None,
    packet_id: str | None,
    route_id: str | None,
) -> str:
    route_lines = [
        "You are running the AIOS shadow lane in an isolated git worktree.",
        "",
        f"Objective: {objective}",
    ]
    if run_id:
        route_lines.append(f"AIOS run id: {run_id}")
    if packet_id:
        route_lines.append(f"AIOS packet id: {packet_id}")
    if route_id:
        route_lines.append(f"AIOS route id: {route_id}")
    route_lines.extend(
        [
            "",
            "Rules:",
            "- Implement only inside this shadow worktree.",
            "- Do not merge, push, or copy changes back to the baseline workspace.",
            "- Keep normal repository quality expectations: inspect first, make scoped edits, run relevant checks.",
            "- Finish with a concise closeout listing changed files, checks run, unresolved deltas, and whether AIOS context helped.",
        ]
    )
    return "\n".join(route_lines)


def build_codex_exec_command(
    *,
    worktree_path: str | Path,
    prompt: str,
    final_message_path: str | Path,
) -> list[str]:
    return [
        "codex",
        "exec",
        "--cd",
        str(Path(worktree_path)),
        "--sandbox",
        "workspace-write",
        "--ask-for-approval",
        "never",
        "--json",
        "-o",
        str(Path(final_message_path)),
        prompt,
    ]


def score_codex_shadow_candidate(
    *,
    objective: str,
    shadow: dict[str, Any] | None,
    route: dict[str, Any] | None = None,
    baseline_dirty: bool = False,
) -> dict[str, Any]:
    blockers: list[str] = []
    normalized = objective.lower()
    word_count = len([word for word in normalized.split() if word.strip()])
    if baseline_dirty:
        blockers.append("dirty_repo")
    if not shadow or not shadow.get("worktree_path"):
        blockers.append("no_start_sha")
    if len(objective) > 4000:
        blockers.append("too_large")
    if word_count < 6 and not any(
        term in normalized for term in ("implement", "refactor", "release")
    ):
        blockers.append("too_small")
    for blocker, terms in BLOCKER_TERMS.items():
        if any(term in normalized for term in terms):
            blockers.append(blocker)

    complexity = min(100, max(0, word_count * 7))
    if any(
        term in normalized
        for term in ("implement", "refactor", "architecture", "release", "workflow", "multi-file")
    ):
        complexity = max(complexity, 85)
    measurability = (
        80
        if any(
            term in normalized
            for term in ("test", "check", "verify", "quality", "release", "proof")
        )
        else 60
    )
    reproducibility = (
        90 if shadow and shadow.get("worktree_path") and shadow.get("branch_name") else 40
    )
    trace_record = {
        "components": {
            "complexity": complexity,
            "measurability": measurability,
            "reproducibility": reproducibility,
            "aios_relevance": 90 if route else 70,
            "learning_value": 85 if "aios" in normalized or "shadow" in normalized else 70,
            "safety": 90 if not blockers else 20,
            "benchmark_coverage_need": 75
            if "release" in normalized or "workflow" in normalized
            else 55,
        },
        "blockers": blockers,
    }
    return score_shadow_candidate(trace_record)


def should_auto_run(score: dict[str, Any]) -> bool:
    return str(score.get("recommendation")) in ELIGIBLE_RECOMMENDATIONS and not score.get(
        "blockers"
    )


def launch_codex_shadow(
    conn: sqlite3.Connection,
    *,
    shadow_run_id: str,
    objective: str,
    run_id: str | None = None,
    packet_id: str | None = None,
    route_id: str | None = None,
    logs_dir: str | Path = DEFAULT_LOGS_DIR,
) -> dict[str, Any]:
    shadow = get_shadow_run(conn, shadow_run_id)
    worktree_path = shadow.get("worktree_path")
    if not worktree_path:
        update_shadow_execution_metadata(
            conn,
            shadow_run_id=shadow_run_id,
            execution_status="failed",
            execution_backend="codex-exec",
            execution_ended_at=_now_iso(),
            execution_metadata={"error": "shadow run has no worktree_path"},
            failure_classification="shadow_execution_launch_failed",
            replay_unavailable_reason="shadow run has no worktree path",
        )
        return _execution_payload(conn, shadow_run_id)

    paths = _paths(Path(logs_dir), shadow_run_id)
    Path(paths["run_dir"]).mkdir(parents=True, exist_ok=True)
    prompt = build_shadow_prompt(
        objective=objective,
        run_id=run_id,
        packet_id=packet_id,
        route_id=route_id,
    )
    command = build_codex_exec_command(
        worktree_path=str(worktree_path),
        prompt=prompt,
        final_message_path=paths["final_message_path"],
    )
    started_at = _now_iso()
    try:
        with (
            Path(paths["output_jsonl_path"]).open("w", encoding="utf-8") as stdout_file,
            Path(paths["stderr_path"]).open("w", encoding="utf-8") as stderr_file,
        ):
            process = subprocess.Popen(
                command,
                cwd=str(worktree_path),
                stdout=stdout_file,
                stderr=stderr_file,
                text=True,
                start_new_session=True,
            )
    except OSError as exc:
        update_shadow_execution_metadata(
            conn,
            shadow_run_id=shadow_run_id,
            execution_status="failed",
            execution_backend="codex-exec",
            execution_command=command,
            output_jsonl_path=paths["output_jsonl_path"],
            stderr_path=paths["stderr_path"],
            final_message_path=paths["final_message_path"],
            execution_started_at=started_at,
            execution_ended_at=_now_iso(),
            execution_metadata={"error": str(exc)},
            failure_classification="shadow_execution_launch_failed",
            replay_unavailable_reason=str(exc),
        )
        return _execution_payload(conn, shadow_run_id)

    update_shadow_execution_metadata(
        conn,
        shadow_run_id=shadow_run_id,
        execution_status="running",
        execution_backend="codex-exec",
        execution_pid=process.pid,
        execution_command=command,
        output_jsonl_path=paths["output_jsonl_path"],
        stderr_path=paths["stderr_path"],
        final_message_path=paths["final_message_path"],
        execution_started_at=started_at,
        execution_metadata={"mode": "headless", "approval_policy": "never"},
        replay_command=" ".join(command),
    )
    return _execution_payload(conn, shadow_run_id)


def skip_codex_shadow(
    conn: sqlite3.Connection,
    *,
    shadow_run_id: str,
    score: dict[str, Any],
) -> dict[str, Any]:
    reason = _skip_reason(score)
    update_shadow_execution_metadata(
        conn,
        shadow_run_id=shadow_run_id,
        execution_status="skipped",
        execution_backend="codex-exec",
        execution_ended_at=_now_iso(),
        execution_metadata={"candidate_score": score, "skip_reason": reason},
        failure_classification="shadow_execution_skipped",
        replay_unavailable_reason=reason,
    )
    return _execution_payload(conn, shadow_run_id)


def shadow_execution_status(conn: sqlite3.Connection, *, shadow_run_id: str) -> dict[str, Any]:
    payload = _execution_payload(conn, shadow_run_id)
    pid = payload.get("pid")
    if payload["status"] == "running" and isinstance(pid, int) and not _pid_is_running(pid):
        update_shadow_execution_metadata(
            conn,
            shadow_run_id=shadow_run_id,
            execution_status="completed",
            execution_ended_at=_now_iso(),
            execution_metadata={
                **dict(payload.get("metadata") or {}),
                "completion_detected_by": "status_probe",
            },
        )
        payload = _execution_payload(conn, shadow_run_id)
    return payload


def cancel_shadow_execution(conn: sqlite3.Connection, *, shadow_run_id: str) -> dict[str, Any]:
    payload = _execution_payload(conn, shadow_run_id)
    pid = payload.get("pid")
    if payload["status"] == "running" and isinstance(pid, int) and _pid_is_running(pid):
        with suppress(ProcessLookupError):
            os.killpg(pid, signal.SIGTERM)
    update_shadow_execution_metadata(
        conn,
        shadow_run_id=shadow_run_id,
        execution_status="canceled",
        execution_ended_at=_now_iso(),
        execution_metadata={
            **dict(payload.get("metadata") or {}),
            "canceled_by": "aios shadow cancel",
        },
        failure_classification="shadow_execution_canceled",
        replay_unavailable_reason="shadow execution was canceled",
    )
    return _execution_payload(conn, shadow_run_id)


def _skip_reason(score: dict[str, Any]) -> str:
    blockers = score.get("blockers") or []
    if blockers:
        return f"blocked: {', '.join(str(blocker) for blocker in blockers)}"
    return f"candidate recommendation is {score.get('recommendation', 'unknown')}"


def _pid_is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _execution_payload(conn: sqlite3.Connection, shadow_run_id: str) -> dict[str, Any]:
    row = get_shadow_run(conn, shadow_run_id)
    metadata = row.get("execution_metadata") or {}
    return {
        "mode": "headless-codex-exec",
        "status": row.get("execution_status") or "not_started",
        "backend": row.get("execution_backend"),
        "command": row.get("execution_command") or [],
        "pid": row.get("execution_pid"),
        "started_at": row.get("execution_started_at"),
        "ended_at": row.get("execution_ended_at"),
        "output_jsonl_path": row.get("output_jsonl_path"),
        "stderr_path": row.get("stderr_path"),
        "final_message_path": row.get("final_message_path"),
        "skip_reason": metadata.get("skip_reason"),
        "metadata": metadata,
    }
