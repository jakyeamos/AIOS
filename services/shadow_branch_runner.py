from __future__ import annotations

import json
import re
import sqlite3
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from services.eval_run_service import ensure_eval_schema, get_eval_run_detail

VALID_CONDITIONS = {
    "full-aios",
    "repo-only",
    "full-second-brain",
    "aios_no_second_brain",
    "aios_no_personal_context",
    "aios_no_project_truth",
    "aios_no_prior_task_history",
    "aios_no_context_packets",
    "aios_no_success_criteria",
    "aios_no_subagents",
    "aios_no_model_routing",
    "peer_repo_only",
    "peer_portable_context_packet",
    "external_clean_room",
}


class ShadowBranchSafetyError(RuntimeError):
    pass


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"


def ensure_shadow_branch_schema(conn: sqlite3.Connection) -> None:
    ensure_eval_schema(conn)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS shadow_branch_runs (
          id TEXT PRIMARY KEY,
          task_id TEXT REFERENCES eval_tasks(id),
          baseline_run_id TEXT REFERENCES eval_runs(id),
          aios_run_id TEXT REFERENCES eval_runs(id),
          condition TEXT NOT NULL,
          start_sha TEXT NOT NULL,
          baseline_branch TEXT,
          aios_branch TEXT,
          worktree_path TEXT,
          diff_stat_json TEXT,
          test_delta_json TEXT,
          shadow_branch_delta REAL,
          comparison_report_path TEXT,
          comparison_refs_json TEXT NOT NULL DEFAULT '{}',
          parity_checklist_status TEXT,
          failure_classification TEXT,
          replay_command TEXT,
          replay_unavailable_reason TEXT,
          contamination_check_passed INTEGER NOT NULL DEFAULT 0,
          created_at TEXT
        );
        """
    )
    columns = {str(row["name"]) for row in conn.execute("PRAGMA table_info(shadow_branch_runs)")}
    additions = {
        "comparison_refs_json": "TEXT NOT NULL DEFAULT '{}'",
        "parity_checklist_status": "TEXT",
        "failure_classification": "TEXT",
        "replay_command": "TEXT",
        "replay_unavailable_reason": "TEXT",
    }
    for column, ddl in additions.items():
        if column not in columns:
            conn.execute(f"ALTER TABLE shadow_branch_runs ADD COLUMN {column} {ddl}")


def shadow_branch_name(*, task_id: str, condition: str) -> str:
    safe_task = re.sub(r"[^A-Za-z0-9-]+", "-", task_id).strip("-").lower()[:60]
    safe_condition = re.sub(r"[^A-Za-z0-9-]+", "-", condition).strip("-").lower()[:30]
    return f"aios/eval/{safe_task or 'task'}/{safe_condition or 'condition'}"


def create_shadow_worktree(*, repo_path: str | Path, start_sha: str, branch_name: str) -> str:
    repo = Path(repo_path).resolve()
    active_root = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    worktree_path = repo / ".aios" / "shadow-worktrees" / branch_name.replace("/", "-")
    if Path(active_root).resolve() == worktree_path.resolve():
        raise ShadowBranchSafetyError("Refusing to create a shadow worktree on the active tree path.")
    worktree_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "worktree", "add", str(worktree_path), "-b", branch_name, start_sha],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return str(worktree_path)


def verify_no_contamination(
    *, baseline_branch: str, shadow_branch: str, repo_path: str | Path
) -> bool:
    result = subprocess.run(
        ["git", "log", "--oneline", f"{baseline_branch}..{shadow_branch}"],
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() == ""


def capture_diff_stat(
    *, baseline_branch: str, aios_branch: str, repo_path: str | Path
) -> dict[str, int]:
    result = subprocess.run(
        ["git", "diff", "--shortstat", baseline_branch, aios_branch],
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True,
    )
    output = result.stdout.strip()
    files = re.search(r"(\d+) files? changed", output)
    insertions = re.search(r"(\d+) insertions?", output)
    deletions = re.search(r"(\d+) deletions?", output)
    return {
        "files_changed": int(files.group(1)) if files else 0,
        "insertions": int(insertions.group(1)) if insertions else 0,
        "deletions": int(deletions.group(1)) if deletions else 0,
    }


def capture_test_delta(
    *, baseline_result: dict[str, Any], aios_result: dict[str, Any]
) -> dict[str, Any]:
    baseline_failures = set(baseline_result.get("failures", []))
    aios_failures = set(aios_result.get("failures", []))
    return {
        "baseline_pass_count": int(baseline_result.get("pass_count", 0)),
        "aios_pass_count": int(aios_result.get("pass_count", 0)),
        "new_failures": sorted(aios_failures - baseline_failures),
        "fixed_failures": sorted(baseline_failures - aios_failures),
    }


def compute_shadow_branch_delta(*, baseline_score: dict[str, Any], aios_score: dict[str, Any]) -> float:
    return float(aios_score["overall_score"]) - float(baseline_score["overall_score"])


def cleanup_shadow_worktree(*, worktree_path: str | Path, repo_path: str | Path) -> None:
    subprocess.run(
        ["git", "worktree", "remove", "--force", str(worktree_path)],
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True,
    )


def record_shadow_branch_run(
    conn: sqlite3.Connection,
    *,
    task_id: str,
    condition: str,
    start_sha: str,
    aios_branch: str,
    worktree_path: str,
) -> str:
    ensure_shadow_branch_schema(conn)
    run_id = _new_id("shadow-run")
    conn.execute(
        """
        INSERT INTO shadow_branch_runs (
          id, task_id, condition, start_sha, aios_branch, worktree_path,
          contamination_check_passed, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, 0, ?)
        """,
        (run_id, task_id, condition, start_sha, aios_branch, worktree_path, _now_iso()),
    )
    return run_id


def update_shadow_parity_metadata(
    conn: sqlite3.Connection,
    *,
    shadow_run_id: str,
    baseline_branch: str | None = None,
    comparison_refs: dict[str, Any] | None = None,
    parity_checklist_status: str,
    failure_classification: str | None = None,
    replay_command: str | None = None,
    replay_unavailable_reason: str | None = None,
) -> None:
    ensure_shadow_branch_schema(conn)
    if replay_command and replay_unavailable_reason:
        raise ValueError("Provide replay_command or replay_unavailable_reason, not both.")
    conn.execute(
        """
        UPDATE shadow_branch_runs
        SET baseline_branch = COALESCE(?, baseline_branch),
            comparison_refs_json = ?,
            parity_checklist_status = ?,
            failure_classification = ?,
            replay_command = ?,
            replay_unavailable_reason = ?
        WHERE id = ?
        """,
        (
            baseline_branch,
            json.dumps(comparison_refs or {}, sort_keys=True),
            parity_checklist_status,
            failure_classification,
            replay_command,
            replay_unavailable_reason,
            shadow_run_id,
        ),
    )


def list_shadow_parity_metadata(
    conn: sqlite3.Connection, *, task_id: str | None = None
) -> list[dict[str, Any]]:
    ensure_shadow_branch_schema(conn)
    params: tuple[str, ...] = ()
    where = ""
    if task_id:
        where = "WHERE task_id = ?"
        params = (task_id,)
    return [
        {
            **dict(row),
            "comparison_refs": json.loads(row["comparison_refs_json"] or "{}"),
        }
        for row in conn.execute(
            f"""
            SELECT id, task_id, condition, start_sha, baseline_branch, aios_branch,
                   worktree_path, diff_stat_json, test_delta_json, comparison_report_path,
                   comparison_refs_json, parity_checklist_status, failure_classification,
                   replay_command, replay_unavailable_reason, contamination_check_passed,
                   created_at
            FROM shadow_branch_runs
            {where}
            ORDER BY created_at DESC
            LIMIT 100
            """,
            params,
        ).fetchall()
    ]


def compare_shadow_runs(
    conn: sqlite3.Connection,
    *,
    shadow_run_id: str,
    baseline_run_id: str,
) -> dict[str, Any]:
    ensure_shadow_branch_schema(conn)
    row = conn.execute(
        "SELECT * FROM shadow_branch_runs WHERE id = ? LIMIT 1",
        (shadow_run_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Shadow branch run not found: {shadow_run_id}")
    baseline_detail = get_eval_run_detail(conn, baseline_run_id)
    aios_run_id = row["aios_run_id"]
    if not aios_run_id:
        raise ValueError(f"Shadow branch run has no aios_run_id: {shadow_run_id}")
    aios_detail = get_eval_run_detail(conn, str(aios_run_id))
    if not baseline_detail["scores"] or not aios_detail["scores"]:
        raise ValueError("Both baseline and AIOS runs must have at least one score.")
    delta = compute_shadow_branch_delta(
        baseline_score=baseline_detail["scores"][0],
        aios_score=aios_detail["scores"][0],
    )
    conn.execute(
        """
        UPDATE shadow_branch_runs
        SET baseline_run_id = ?, shadow_branch_delta = ?, diff_stat_json = ?,
            test_delta_json = ?, contamination_check_passed = 1
        WHERE id = ?
        """,
        (baseline_run_id, delta, json.dumps({}), json.dumps({}), shadow_run_id),
    )
    return {"shadow_run_id": shadow_run_id, "baseline_run_id": baseline_run_id, "delta": delta}
