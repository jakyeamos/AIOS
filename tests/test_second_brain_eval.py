# ruff: noqa: E402

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.eval_run_service import create_eval_run, create_eval_task, record_eval_score
from services.second_brain_eval import (
    compute_retrieval_metrics,
    compute_second_brain_lift,
    evaluate_gold_set_run,
    record_retrieval,
    register_gold_set_task,
)


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
    return conn


def _create_task(conn: sqlite3.Connection) -> str:
    return create_eval_task(
        conn,
        repo_id="p1",
        source="gold-set",
        start_sha="abc123",
        context_profile="jakye_repo_only",
        task_type="feature",
        prompt_summary="Measure second brain lift.",
        acceptance_criteria=["uses required context"],
        success_criteria_files=["tests/test_second_brain_eval.py"],
    )


def _create_run(
    conn: sqlite3.Connection,
    *,
    task_id: str,
    condition: str = "full-second-brain",
) -> str:
    return create_eval_run(
        conn,
        task_id=task_id,
        condition=condition,
        mode="controlled",
        harness="pytest",
        model="gpt-5",
        context_profile="jakye_second_brain_full",
        final_status="success",
    )


def test_record_retrieval_round_trip() -> None:
    conn = _connect()
    task_id = _create_task(conn)
    run_id = _create_run(conn, task_id=task_id)

    retrieval_id = record_retrieval(
        conn,
        run_id=run_id,
        source_type="project_truth",
        source_id="PROJECT.md",
        source_path=".planning/PROJECT.md",
        was_needed=True,
        relevance_score=0.95,
    )

    row = conn.execute(
        "SELECT * FROM eval_second_brain_retrievals WHERE id = ?", (retrieval_id,)
    ).fetchone()
    assert row is not None
    assert row["run_id"] == run_id
    assert row["source_type"] == "project_truth"
    assert row["was_needed"] == 1
    assert row["relevance_score"] == 0.95


def test_compute_retrieval_metrics_precision_recall_and_staleness() -> None:
    conn = _connect()
    task_id = _create_task(conn)
    run_id = _create_run(conn, task_id=task_id)
    record_retrieval(
        conn,
        run_id=run_id,
        source_type="project_truth",
        source_id="PROJECT.md",
        source_path=None,
        was_needed=True,
    )
    record_retrieval(
        conn,
        run_id=run_id,
        source_type="prior_task_history",
        source_id="old-summary",
        source_path=None,
        was_needed=False,
        was_stale=True,
        stale_reason="superseded",
    )

    metrics = compute_retrieval_metrics(conn, run_id)

    assert metrics["precision"] == 0.5
    assert metrics["recall"] == 0.5
    assert metrics["staleness_rate"] == 0.5
    assert metrics["count_total"] == 2
    assert metrics["count_needed"] == 1
    assert metrics["count_stale"] == 1


def test_evaluate_gold_set_run_identifies_missed_required_sources() -> None:
    conn = _connect()
    task_id = _create_task(conn)
    run_id = _create_run(conn, task_id=task_id)
    gold_task_id = register_gold_set_task(
        conn,
        task_id=task_id,
        required_sources=[
            {"source_id": "PROJECT.md", "source_type": "project_truth"},
            {"source_id": "missing-note", "source_type": "obsidian_notes"},
        ],
        known_correct_outcome="Implementation uses the current project truth.",
    )
    record_retrieval(
        conn,
        run_id=run_id,
        source_type="project_truth",
        source_id="PROJECT.md",
        source_path=".planning/PROJECT.md",
        was_needed=True,
    )

    result = evaluate_gold_set_run(conn, run_id=run_id, gold_task_id=gold_task_id)

    assert result["recall"] == 0.5
    assert result["precision"] == 1.0
    assert result["missed_sources"] == [
        {"source_id": "missing-note", "source_type": "obsidian_notes"}
    ]


def test_compute_second_brain_lift_returns_positive_lift() -> None:
    conn = _connect()
    task_id = _create_task(conn)
    full_run_id = _create_run(conn, task_id=task_id, condition="full-second-brain")
    repo_only_run_id = _create_run(conn, task_id=task_id, condition="repo-only")
    record_eval_score(
        conn,
        run_id=full_run_id,
        overall_score=0.9,
        task_success=1.0,
        second_brain_effectiveness=0.8,
    )
    record_eval_score(
        conn,
        run_id=repo_only_run_id,
        overall_score=0.6,
        task_success=0.7,
        second_brain_effectiveness=0.2,
    )

    lift = compute_second_brain_lift(
        conn,
        full_run_id=full_run_id,
        repo_only_run_id=repo_only_run_id,
    )

    assert lift["available"] is True
    assert lift["overall_lift"] == 0.30000000000000004
    assert lift["dimensions"]["task_success"] == 0.30000000000000004
    assert lift["dimensions"]["second_brain_effectiveness"] == 0.6000000000000001


def test_compute_second_brain_lift_returns_unavailable_when_repo_run_missing() -> None:
    conn = _connect()
    task_id = _create_task(conn)
    full_run_id = _create_run(conn, task_id=task_id)
    record_eval_score(conn, run_id=full_run_id, overall_score=0.9)

    lift = compute_second_brain_lift(
        conn,
        full_run_id=full_run_id,
        repo_only_run_id="missing-run",
    )

    assert lift == {"available": False, "missing_condition": "missing-run"}


def test_ablation_policy_json_files_have_required_keys() -> None:
    policy_dir = ROOT / "config" / "agent-eval" / "ablation-policies"
    expected_files = {
        "no-second-brain.json",
        "no-personal-corpus.json",
        "no-project-truth.json",
        "no-prior-task-history.json",
    }

    for file_name in expected_files:
        policy = json.loads((policy_dir / file_name).read_text(encoding="utf-8"))
        assert isinstance(policy["condition"], str)
        assert isinstance(policy["description"], str)
        assert isinstance(policy["disable_sources"], list)
        assert policy["portability_impact"] in {"high", "medium", "low"}
