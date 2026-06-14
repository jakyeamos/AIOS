# ruff: noqa: E402

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.ablation_runner import (  # noqa: E402
    compare_ablation_suite,
    load_ablation_policy,
    run_ablation_suite,
)
from services.eval_run_service import (  # noqa: E402
    create_eval_run,
    create_eval_task,
    record_eval_score,
)


class _Completed:
    returncode = 0
    stdout = ""
    stderr = ""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
    return conn


def _task(conn: sqlite3.Connection) -> str:
    return create_eval_task(
        conn,
        repo_id="p1",
        source="ablation",
        start_sha="abc123",
        context_profile="jakye_repo_only",
        task_type="feature",
        prompt_summary="Run ablation.",
        acceptance_criteria=[],
        success_criteria_files=[],
    )


def _run(conn: sqlite3.Connection, *, task_id: str, condition: str, score: float) -> str:
    run_id = create_eval_run(
        conn,
        task_id=task_id,
        condition=condition,
        mode="controlled",
        harness="pytest",
        model="gpt-5",
        context_profile="peer_repo_only" if condition == "peer_repo_only" else "jakye_repo_only",
        final_status="success",
    )
    record_eval_score(conn, run_id=run_id, overall_score=score)
    return run_id


def test_load_ablation_policy_reads_json() -> None:
    policy = load_ablation_policy(
        ROOT / "config" / "agent-eval" / "ablation-policies" / "no-context-packets.json"
    )

    assert policy["condition"] == "aios_no_context_packets"
    assert "context_packet_assembly" in policy["disable_features"]


def test_run_ablation_suite_creates_one_eval_run_per_policy(tmp_path: Path) -> None:
    conn = _connect()
    task_id = _task(conn)
    policies = [
        ROOT / "config" / "agent-eval" / "ablation-policies" / "no-context-packets.json",
        ROOT / "config" / "agent-eval" / "ablation-policies" / "no-model-routing.json",
    ]

    with (
        patch("services.ablation_runner.create_shadow_worktree") as create_worktree,
        patch("services.ablation_runner.cleanup_shadow_worktree"),
        patch("services.ablation_runner.subprocess.run") as run,
    ):
        create_worktree.side_effect = [str(tmp_path / "wt1"), str(tmp_path / "wt2")]
        run.return_value = _Completed()
        run_ids = run_ablation_suite(
            conn,
            task_id=task_id,
            start_sha="abc123",
            policy_paths=policies,
            repo_path=tmp_path,
        )

    rows = conn.execute("SELECT condition FROM eval_runs ORDER BY created_at").fetchall()
    assert len(run_ids) == 2
    assert {row["condition"] for row in rows} == {
        "aios_no_context_packets",
        "aios_no_model_routing",
    }


def test_compare_ablation_suite_positive_and_negative_lift() -> None:
    conn = _connect()
    task_id = _task(conn)
    base_run_id = _run(conn, task_id=task_id, condition="full-aios", score=0.8)
    _run(conn, task_id=task_id, condition="aios_no_context_packets", score=0.5)
    _run(conn, task_id=task_id, condition="aios_no_model_routing", score=0.9)

    result = compare_ablation_suite(conn, task_id=task_id, base_run_id=base_run_id)

    assert result["feature_lift"]["aios_no_context_packets"] == 0.30000000000000004
    assert result["feature_lift"]["aios_no_model_routing"] == -0.09999999999999998


def test_compare_ablation_suite_portability_gap_none_without_peer_run() -> None:
    conn = _connect()
    task_id = _task(conn)
    base_run_id = _run(conn, task_id=task_id, condition="full-aios", score=0.8)
    _run(conn, task_id=task_id, condition="aios_no_context_packets", score=0.5)

    result = compare_ablation_suite(conn, task_id=task_id, base_run_id=base_run_id)

    assert result["portability_gap"] is None
