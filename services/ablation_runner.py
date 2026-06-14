from __future__ import annotations

import json
import sqlite3
import subprocess
from pathlib import Path
from typing import Any

from services.eval_run_service import create_eval_run, get_eval_run_detail, record_eval_score
from services.shadow_branch_runner import cleanup_shadow_worktree, create_shadow_worktree


def load_ablation_policy(policy_path: str | Path) -> dict[str, Any]:
    path = Path(policy_path)
    policy = json.loads(path.read_text(encoding="utf-8"))
    if "condition" not in policy:
        raise ValueError(f"Ablation policy missing condition: {path}")
    return policy


def _disabled_values(policy: dict[str, Any]) -> list[str]:
    values = policy.get("disable_features", policy.get("disable_sources", []))
    return [str(value) for value in values]


def run_ablation_suite(
    conn: sqlite3.Connection,
    *,
    task_id: str,
    start_sha: str,
    policy_paths: list[str | Path],
    repo_path: str | Path,
    base_run_id: str | None = None,
) -> list[str]:
    run_ids: list[str] = []
    repo = Path(repo_path)
    for policy_path in policy_paths:
        policy = load_ablation_policy(policy_path)
        condition = str(policy["condition"])
        branch_name = f"aios/eval/{task_id}/{condition}"
        worktree_path = create_shadow_worktree(
            repo_path=repo,
            start_sha=start_sha,
            branch_name=branch_name,
        )
        disabled = _disabled_values(policy)
        try:
            command = [
                "pnpm",
                "context:compile",
                "--task",
                f"ablation:{task_id}:{condition}",
            ]
            if disabled:
                command.extend(["--disable-features", ",".join(disabled)])
            result = subprocess.run(
                command,
                cwd=worktree_path,
                check=False,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                override_path = Path(worktree_path) / "config" / "ablation-override.json"
                override_path.parent.mkdir(parents=True, exist_ok=True)
                override_path.write_text(json.dumps(policy, indent=2, sort_keys=True), encoding="utf-8")
        finally:
            cleanup_shadow_worktree(worktree_path=worktree_path, repo_path=repo)
        run_id = create_eval_run(
            conn,
            task_id=task_id,
            condition=condition,
            mode="ablation",
            harness="aios-ablation",
            model=None,
            context_profile="jakye_repo_only",
            branch_name=branch_name,
            final_status="partial",
        )
        record_eval_score(conn, run_id=run_id, overall_score=0.0, reviewer_notes=base_run_id)
        run_ids.append(run_id)
    return run_ids


def compare_ablation_suite(
    conn: sqlite3.Connection,
    *,
    task_id: str,
    base_run_id: str,
) -> dict[str, Any]:
    base = get_eval_run_detail(conn, base_run_id)
    if not base["scores"]:
        raise ValueError(f"Base run has no score: {base_run_id}")
    base_score = float(base["scores"][0]["overall_score"])
    rows = conn.execute(
        """
        SELECT id, condition, context_profile
        FROM eval_runs
        WHERE task_id = ? AND id != ?
        ORDER BY created_at
        """,
        (task_id, base_run_id),
    ).fetchall()
    comparisons = []
    feature_lift: dict[str, float] = {}
    portability_gap: float | None = None
    for row in rows:
        detail = get_eval_run_detail(conn, str(row["id"]))
        if not detail["scores"]:
            continue
        score = float(detail["scores"][0]["overall_score"])
        delta = base_score - score
        comparisons.append({"run_id": row["id"], "condition": row["condition"], "delta": delta})
        feature_lift[str(row["condition"])] = delta
        if row["context_profile"] == "peer_repo_only":
            portability_gap = delta
    return {
        "task_id": task_id,
        "base_run_id": base_run_id,
        "feature_lift": feature_lift,
        "comparisons": comparisons,
        "portability_gap": portability_gap,
    }
