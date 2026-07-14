# ruff: noqa: E402

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.eval_run_service import (
    create_eval_pair,
    create_eval_run,
    create_eval_task,
    finalize_eval_pair,
    get_eval_pair,
    get_eval_run_detail,
    get_eval_summary,
    list_eval_pairs,
    list_eval_runs,
    record_eval_failure,
    record_eval_score,
)


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
    return conn


def _create_task(
    conn: sqlite3.Connection, *, repo_id: str = "p1", start_sha: str = "abc123"
) -> str:
    return create_eval_task(
        conn,
        repo_id=repo_id,
        source="controlled_benchmark",
        start_sha=start_sha,
        context_profile="jakye_repo_only",
        task_type="feature",
        prompt_summary="Implement eval recording.",
        acceptance_criteria=["records runs", "lists runs"],
        success_criteria_files=["tests/test_eval_run_service.py"],
    )


def _create_run(
    conn: sqlite3.Connection,
    *,
    task_id: str,
    condition: str = "full-aios",
    context_profile: str = "jakye_repo_only",
    final_status: str = "success",
) -> str:
    return create_eval_run(
        conn,
        task_id=task_id,
        condition=condition,
        mode="controlled",
        harness="pytest",
        model="gpt-5",
        context_profile=context_profile,
        branch_name="codex/eval",
        duration_ms=1200,
        total_tokens=3456,
        estimated_cost_usd=0.42,
        tool_calls=7,
        failed_commands=1,
        files_changed=3,
        tests_run=["uv run pytest -q tests/test_eval_run_service.py"],
        final_status=final_status,
    )


PAIR_SHA = "a" * 40
TASK_HASH = "b" * 64
PROMPT_HASH = "c" * 64
CONTEXT_HASH = "d" * 64


def _pair_metadata() -> dict[str, object]:
    return {
        "model": "gpt-5.6",
        "effort": "high",
        "tools": ["terminal"],
        "budget": {"tokens": 20_000, "seconds": 900},
    }


def test_create_eval_task_round_trip() -> None:
    conn = _connect()
    task_id = _create_task(conn)

    row = conn.execute("SELECT * FROM eval_tasks WHERE id = ?", (task_id,)).fetchone()

    assert row is not None
    assert row["repo_id"] == "p1"
    assert row["source"] == "controlled_benchmark"
    assert row["start_sha"] == "abc123"
    assert row["context_profile"] == "jakye_repo_only"
    assert row["acceptance_criteria_json"] == '["records runs", "lists runs"]'
    assert row["success_criteria_files_json"] == '["tests/test_eval_run_service.py"]'


def test_create_eval_run_with_required_and_optional_fields() -> None:
    conn = _connect()
    task_id = _create_task(conn)
    run_id = _create_run(conn, task_id=task_id)

    row = conn.execute("SELECT * FROM eval_runs WHERE id = ?", (run_id,)).fetchone()

    assert row is not None
    assert row["task_id"] == task_id
    assert row["condition"] == "full-aios"
    assert row["mode"] == "controlled"
    assert row["harness"] == "pytest"
    assert row["model"] == "gpt-5"
    assert row["context_profile"] == "jakye_repo_only"
    assert row["final_status"] == "success"
    assert row["duration_ms"] == 1200
    assert row["total_tokens"] == 3456
    assert row["estimated_cost_usd"] == 0.42
    assert row["tool_calls"] == 7
    assert row["failed_commands"] == 1
    assert row["files_changed"] == 3
    assert row["tests_run_json"] == '["uv run pytest -q tests/test_eval_run_service.py"]'


def test_create_eval_run_rejects_unknown_task() -> None:
    conn = _connect()

    with pytest.raises(ValueError, match="Eval task not found"):
        create_eval_run(
            conn,
            task_id="missing-task",
            condition="full-aios",
            mode="controlled",
            harness="pytest",
            model="gpt-5",
            context_profile="jakye_repo_only",
            final_status="partial",
        )


def test_record_eval_score_allows_partial_fields() -> None:
    conn = _connect()
    task_id = _create_task(conn)
    run_id = _create_run(conn, task_id=task_id)

    score_id = record_eval_score(conn, run_id=run_id, task_success=1.0, autonomy=0.5)

    row = conn.execute("SELECT * FROM eval_scores WHERE id = ?", (score_id,)).fetchone()
    assert row is not None
    assert row["task_success"] == 1.0
    assert row["quality_adherence"] is None
    assert row["autonomy"] == 0.5
    assert row["overall_score"] == 0.75


def test_record_eval_failure_validates_priority() -> None:
    conn = _connect()
    task_id = _create_task(conn)
    run_id = _create_run(conn, task_id=task_id, final_status="failed")

    failure_id = record_eval_failure(
        conn,
        run_id=run_id,
        failure_types=["verification_gap"],
        summary="Verifier missed the service contract.",
        suspected_cause="static reasoning",
        affected_components=["services/eval_run_service.py"],
        recommended_fixes=["add round-trip tests"],
        priority="high",
    )

    row = conn.execute("SELECT * FROM eval_failures WHERE id = ?", (failure_id,)).fetchone()
    assert row is not None
    assert row["priority"] == "high"
    assert row["failure_types_json"] == '["verification_gap"]'

    with pytest.raises(ValueError, match="Invalid priority"):
        record_eval_failure(
            conn,
            run_id=run_id,
            failure_types=[],
            summary=None,
            suspected_cause=None,
            affected_components=[],
            recommended_fixes=[],
            priority="urgent",
        )


def test_list_eval_runs_filters_by_condition_and_context_profile() -> None:
    conn = _connect()
    task_id = _create_task(conn)
    _create_run(conn, task_id=task_id, condition="full-aios", context_profile="jakye_repo_only")
    _create_run(
        conn,
        task_id=task_id,
        condition="portable",
        context_profile="peer_portable_context_packet",
    )

    by_condition = list_eval_runs(conn, condition="portable")
    by_profile = list_eval_runs(conn, context_profile="jakye_repo_only")

    assert [run["condition"] for run in by_condition] == ["portable"]
    assert [run["context_profile"] for run in by_profile] == ["jakye_repo_only"]
    assert by_condition[0]["tests_run"] == ["uv run pytest -q tests/test_eval_run_service.py"]


def test_get_eval_run_detail_returns_joined_fields_scores_and_failures() -> None:
    conn = _connect()
    task_id = _create_task(conn)
    run_id = _create_run(conn, task_id=task_id)
    record_eval_score(conn, run_id=run_id, overall_score=0.9, reviewer_notes="solid")
    record_eval_failure(
        conn,
        run_id=run_id,
        failure_types=["minor"],
        summary="Small issue",
        suspected_cause="coverage",
        affected_components=["tests"],
        recommended_fixes=["add case"],
        priority="low",
    )

    detail = get_eval_run_detail(conn, run_id)

    assert detail["id"] == run_id
    assert detail["repo_id"] == "p1"
    assert detail["start_sha"] == "abc123"
    assert detail["acceptance_criteria"] == ["records runs", "lists runs"]
    assert detail["success_criteria_files"] == ["tests/test_eval_run_service.py"]
    assert detail["scores"][0]["overall_score"] == 0.9
    assert detail["failures"][0]["failure_types"] == ["minor"]
    assert detail["failures"][0]["affected_components"] == ["tests"]
    assert detail["failures"][0]["recommended_fixes"] == ["add case"]


def test_get_eval_summary_returns_counts_and_average_score() -> None:
    conn = _connect()
    first_task_id = _create_task(conn, repo_id="p1")
    second_task_id = _create_task(conn, repo_id="p2")
    first_run_id = _create_run(conn, task_id=first_task_id, final_status="success")
    second_run_id = _create_run(conn, task_id=second_task_id, final_status="failed")
    record_eval_score(conn, run_id=first_run_id, overall_score=0.8)
    record_eval_score(conn, run_id=second_run_id, overall_score=0.4)

    all_summary = get_eval_summary(conn)
    project_summary = get_eval_summary(conn, project_id="p1")

    assert all_summary["run_count"] == 2
    assert all_summary["task_count"] == 2
    assert all_summary["average_score"] == 0.6000000000000001
    assert all_summary["by_status"] == {"failed": 1, "success": 1}
    assert project_summary["run_count"] == 1
    assert project_summary["average_score"] == 0.8


def test_get_eval_summary_counts_runs_once_with_multiple_scores() -> None:
    conn = _connect()
    task_id = _create_task(conn, repo_id="p1")
    run_id = _create_run(conn, task_id=task_id, final_status="success")
    record_eval_score(conn, run_id=run_id, overall_score=0.2)
    record_eval_score(conn, run_id=run_id, overall_score=0.8)

    summary = get_eval_summary(conn, project_id="p1")

    assert summary["run_count"] == 1
    assert summary["task_count"] == 1
    assert summary["average_score"] == 0.8


def test_context_profile_validation_raises_value_error() -> None:
    conn = _connect()

    with pytest.raises(ValueError, match="Invalid context_profile.*Use one of"):
        create_eval_task(
            conn,
            repo_id="p1",
            source="controlled_benchmark",
            start_sha="abc123",
            context_profile="everything",
            task_type="feature",
            prompt_summary=None,
            acceptance_criteria=[],
            success_criteria_files=[],
        )


def test_final_status_validation_raises_value_error() -> None:
    conn = _connect()
    task_id = _create_task(conn)

    with pytest.raises(ValueError, match="Invalid final_status"):
        _create_run(conn, task_id=task_id, final_status="done")


def test_eval_pair_round_trip_records_scores_and_defer_decision() -> None:
    conn = _connect()
    task_id = _create_task(conn, start_sha=PAIR_SHA)
    control_run_id = _create_run(conn, task_id=task_id, condition="baseline_repo_only")
    treatment_run_id = _create_run(conn, task_id=task_id, condition="aios_workflow_governed")
    record_eval_score(conn, run_id=control_run_id, overall_score=0.4)
    record_eval_score(conn, run_id=treatment_run_id, overall_score=0.9)

    pair_id = create_eval_pair(
        conn,
        task_id=task_id,
        control_run_id=control_run_id,
        treatment_run_id=treatment_run_id,
        protected_start_sha=PAIR_SHA,
        task_hash=TASK_HASH,
        prompt_hash=PROMPT_HASH,
        context_hash=CONTEXT_HASH,
        parity_metadata=_pair_metadata(),
    )
    finalized = finalize_eval_pair(
        conn,
        pair_id=pair_id,
        decision="defer",
        contamination_status="failed",
        contamination_evidence={"reason": "dirty baseline"},
        independent_review_status="not_run",
        limitations=["fixture-only"],
    )

    assert finalized["status"] == "insufficient_evidence"
    assert finalized["control_score"] == 0.4
    assert finalized["treatment_score"] == 0.9
    assert finalized["delta"] == 0.5
    assert finalized["parity_metadata"] == _pair_metadata()
    assert finalized["contamination_evidence"] == {"reason": "dirty baseline"}
    assert finalized["limitations"] == ["fixture-only"]
    assert [event["event_type"] for event in finalized["events"]] == ["created", "finalized"]
    assert get_eval_pair(conn, pair_id)["decision"] == "defer"
    assert (
        list_eval_pairs(conn, task_id=task_id, status="insufficient_evidence")[0]["id"]
        == pair_id
    )


def test_eval_pair_rejects_mismatched_runs_and_incomplete_metadata() -> None:
    conn = _connect()
    task_id = _create_task(conn, start_sha=PAIR_SHA)
    other_task_id = _create_task(conn, repo_id="p2", start_sha=PAIR_SHA)
    control_run_id = _create_run(conn, task_id=task_id, condition="baseline_repo_only")
    treatment_run_id = _create_run(conn, task_id=other_task_id, condition="aios_workflow_governed")

    with pytest.raises(ValueError, match="Both eval runs must belong to task_id"):
        create_eval_pair(
            conn,
            task_id=task_id,
            control_run_id=control_run_id,
            treatment_run_id=treatment_run_id,
            protected_start_sha=PAIR_SHA,
            task_hash=TASK_HASH,
            prompt_hash=PROMPT_HASH,
            context_hash=CONTEXT_HASH,
            parity_metadata=_pair_metadata(),
        )

    treatment_run_id = _create_run(conn, task_id=task_id, condition="aios_workflow_governed")
    with pytest.raises(ValueError, match="missing required fields"):
        create_eval_pair(
            conn,
            task_id=task_id,
            control_run_id=control_run_id,
            treatment_run_id=treatment_run_id,
            protected_start_sha=PAIR_SHA,
            task_hash=TASK_HASH,
            prompt_hash=PROMPT_HASH,
            context_hash=CONTEXT_HASH,
            parity_metadata={"model": "gpt-5.6"},
        )


def test_eval_pair_promotion_fails_closed_until_scores_contamination_and_review_pass() -> None:
    conn = _connect()
    task_id = _create_task(conn, start_sha=PAIR_SHA)
    control_run_id = _create_run(conn, task_id=task_id, condition="baseline_repo_only")
    treatment_run_id = _create_run(conn, task_id=task_id, condition="aios_workflow_governed")
    pair_id = create_eval_pair(
        conn,
        task_id=task_id,
        control_run_id=control_run_id,
        treatment_run_id=treatment_run_id,
        protected_start_sha=PAIR_SHA,
        task_hash=TASK_HASH,
        prompt_hash=PROMPT_HASH,
        context_hash=CONTEXT_HASH,
        parity_metadata=_pair_metadata(),
    )

    with pytest.raises(ValueError, match="requires scores"):
        finalize_eval_pair(
            conn,
            pair_id=pair_id,
            decision="promote",
            contamination_status="passed",
            independent_review_status="passed",
        )

    record_eval_score(conn, run_id=control_run_id, overall_score=0.6)
    record_eval_score(conn, run_id=treatment_run_id, overall_score=0.8)
    with pytest.raises(ValueError, match="independent_review_status=passed"):
        finalize_eval_pair(
            conn,
            pair_id=pair_id,
            decision="promote",
            contamination_status="passed",
            independent_review_status="pending",
        )

    finalized = finalize_eval_pair(
        conn,
        pair_id=pair_id,
        decision="promote",
        contamination_status="passed",
        independent_review_status="passed",
        independent_review_ref="review-1",
    )
    assert finalized["decision"] == "promote"
    assert finalized["delta"] == 0.2


def test_service_initializes_eval_tables_without_other_phase_11_tables() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    task_id = _create_task(conn)
    run_id = _create_run(conn, task_id=task_id)

    assert list_eval_runs(conn, task_id=task_id)[0]["id"] == run_id
