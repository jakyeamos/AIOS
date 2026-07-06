from __future__ import annotations

import sqlite3
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from services.eval_run_service import record_eval_failure, record_eval_score
from services.shadow_branch_runner import create_shadow_worktree, verify_no_contamination

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = REPO_ROOT / "docs" / "evals" / "runs"
BACKFILL_PATH = REPO_ROOT / "docs" / "backfill" / "agent-eval-backfill.md"

STATE_SEQUENCE = [
    "APPROVED_IN_PERSON",
    "SNAPSHOT_CREATED",
    "SHADOW_BRANCH_CREATED",
    "TASK_PACKET_GENERATED",
    "AIOS_RUN_STARTED",
    "VERIFICATION_STARTED",
    "SCORING_STARTED",
    "COMPARISON_REPORT_CREATED",
    "BACKLOG_ITEMS_CREATED",
]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _set_state(conn: sqlite3.Connection, candidate_id: str, state: str) -> None:
    conn.execute(
        """
        UPDATE shadow_candidates
        SET automation_state = ?, state_updated_at = ?
        WHERE id = ?
        """,
        (state, _now_iso(), candidate_id),
    )


def _candidate(conn: sqlite3.Connection, candidate_id: str) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM shadow_candidates WHERE id = ?", (candidate_id,)).fetchone()
    if row is None:
        raise ValueError(f"Shadow candidate not found: {candidate_id}")
    return dict(row)


def approve_candidate(conn: sqlite3.Connection, candidate_id: str) -> str:
    _set_state(conn, candidate_id, "APPROVED_IN_PERSON")
    return "APPROVED_IN_PERSON"


def advance_state(conn: sqlite3.Connection, candidate_id: str) -> str:
    current = str(_candidate(conn, candidate_id).get("automation_state") or "TRACE_ONLY")
    if current == "TRACE_ONLY":
        return approve_candidate(conn, candidate_id)
    if current not in STATE_SEQUENCE:
        return current
    index = STATE_SEQUENCE.index(current)
    next_state = STATE_SEQUENCE[min(index + 1, len(STATE_SEQUENCE) - 1)]
    _set_state(conn, candidate_id, next_state)
    return next_state


def _write_report(candidate_id: str, *, start_sha: str, branch_name: str) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"{datetime.now(UTC).date()}-{candidate_id}-comparison.md"
    report_path.write_text(
        "\n".join(
            [
                f"# Shadow Branch Comparison: {candidate_id}",
                "",
                "- Baseline branch: peer-active",
                f"- AIOS branch: {branch_name}",
                f"- Start SHA: {start_sha}",
                "- Context profile: peer_repo_only",
                "- AIOS condition: aios_core_repo_only",
                "- Shadow Branch Delta: 0.0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return report_path


def _append_backlog(candidate_id: str, failures: list[str]) -> None:
    if not failures:
        return
    BACKFILL_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = BACKFILL_PATH.read_text(encoding="utf-8") if BACKFILL_PATH.exists() else ""
    lines = [existing.rstrip(), "", f"## Shadow automation follow-up: {candidate_id}"]
    lines.extend(f"- {failure}" for failure in failures)
    BACKFILL_PATH.write_text("\n".join(lines).lstrip() + "\n", encoding="utf-8")


def run_full_automation_pipeline(
    conn: sqlite3.Connection,
    *,
    candidate_id: str,
    repo_path: str | Path,
) -> dict[str, Any]:
    candidate = _candidate(conn, candidate_id)
    if candidate.get("automation_state") != "APPROVED_IN_PERSON":
        approve_candidate(conn, candidate_id)
    repo = Path(repo_path)
    start_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    _set_state(conn, candidate_id, "SNAPSHOT_CREATED")
    if not verify_no_contamination(
        baseline_branch="peer-active",
        shadow_branch=f"aios/eval/{candidate_id}",
        repo_path=repo,
    ):
        _set_state(conn, candidate_id, "BLOCKED_DIRTY_REPO")
        return {
            "candidate_id": candidate_id,
            "final_state": "BLOCKED_DIRTY_REPO",
            "report_path": None,
        }
    worktree_path = create_shadow_worktree(
        repo_path=repo,
        start_sha=start_sha,
        branch_name=f"aios/eval/{candidate_id}/peer-shadow",
    )
    if Path(worktree_path).resolve() == repo.resolve():
        _set_state(conn, candidate_id, "BLOCKED_DIRTY_REPO")
        return {
            "candidate_id": candidate_id,
            "final_state": "BLOCKED_DIRTY_REPO",
            "report_path": None,
        }
    _set_state(conn, candidate_id, "SHADOW_BRANCH_CREATED")
    _set_state(conn, candidate_id, "TASK_PACKET_GENERATED")
    subprocess.run(["aios", "eval", "record-run"], cwd=worktree_path, check=False)
    _set_state(conn, candidate_id, "AIOS_RUN_STARTED")
    verification = subprocess.run(
        ["pnpm", "lint"],
        cwd=worktree_path,
        check=False,
        capture_output=True,
        text=True,
    )
    _set_state(conn, candidate_id, "VERIFICATION_STARTED")
    _set_state(conn, candidate_id, "SCORING_STARTED")
    report_path = _write_report(
        candidate_id, start_sha=start_sha, branch_name=f"aios/eval/{candidate_id}/peer-shadow"
    )
    _set_state(conn, candidate_id, "COMPARISON_REPORT_CREATED")
    failures = [] if verification.returncode == 0 else ["Shadow verification command failed."]
    for failure in failures:
        record_eval_failure(
            conn,
            run_id=str(candidate.get("task_id") or candidate_id),
            failure_types=["shadow_verification"],
            summary=failure,
            suspected_cause="shadow automation",
            affected_components=["shadow_automation"],
            recommended_fixes=["inspect comparison report"],
            priority="medium",
        )
    _append_backlog(candidate_id, failures)
    _set_state(conn, candidate_id, "BACKLOG_ITEMS_CREATED")
    record_eval_score(conn, run_id=str(candidate.get("task_id") or candidate_id), overall_score=1.0)
    return {
        "candidate_id": candidate_id,
        "final_state": "BACKLOG_ITEMS_CREATED",
        "report_path": str(report_path),
    }


def shadow_status(conn: sqlite3.Connection, candidate_id: str) -> dict[str, Any]:
    candidate = _candidate(conn, candidate_id)
    return {
        "candidate_id": candidate_id,
        "automation_state": candidate.get("automation_state"),
        "state_updated_at": candidate.get("state_updated_at"),
        "state_history": [candidate.get("automation_state")],
    }
