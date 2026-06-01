from __future__ import annotations

import dataclasses
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.learning_impact import (  # noqa: E402
    AssetEvidenceDelta,
    LearningImpactPerRun,
    LearningImpactRollup,
    ProposalCreated,
    _trend_from_rates,
    build_per_run_impact,
    build_rollup,
)

SINCE = "2026-06-01T00:00:00Z"
RECENT = "2026-05-21T00:00:00Z"
PRIOR = "2026-04-01T00:00:00Z"


def test_per_run_impact_returns_dataclass() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_schema(conn)
    _insert_run(conn, "r1", workflow_key="implementation-delivery")
    _insert_learning_event(conn, "e1", "r1", "weak_workflow")
    _insert_agentize_eval(conn, "a1", "r1")

    impact = build_per_run_impact(conn, run_id="r1")

    assert isinstance(impact, LearningImpactPerRun)
    assert dataclasses.is_dataclass(impact)
    assert impact.workflow_key == "implementation-delivery"
    with pytest.raises(dataclasses.FrozenInstanceError):
        impact.workflow_key = "other"  # type: ignore[misc]


def test_per_run_impact_signals_emitted_from_workflow_learning_events() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_schema(conn)
    _insert_run(conn, "r1")
    _insert_learning_event(conn, "e1", "r1", "weak_prompt")
    _insert_learning_event(conn, "e2", "r1", "weak_workflow")
    _insert_learning_event(conn, "e3", "r1", None)

    impact = build_per_run_impact(conn, run_id="r1")

    assert impact is not None
    assert impact.signals_emitted == ("weak_prompt", "weak_workflow")


def test_per_run_impact_assets_evidenced_includes_workflow() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_schema(conn)
    _insert_run(conn, "r1", workflow_key="implementation-delivery")
    _insert_agentize_eval(conn, "a1", "r1", outcome_quality=4, tests_passed=1)

    impact = build_per_run_impact(conn, run_id="r1")

    assert impact is not None
    assert impact.assets_evidenced[0] == AssetEvidenceDelta(
        asset_kind="workflow",
        asset_key="implementation-delivery",
        delta_sample_size=1,
        delta_success_count=1,
        delta_blocker_count=0,
    )


def test_per_run_impact_assets_evidenced_includes_prompts() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_schema(conn)
    _insert_run(conn, "r1")
    _insert_prompt(conn, "p1", "r1", "research", 0.8)
    _insert_prompt(conn, "p2", "r1", "coding_debug", 0.2)

    impact = build_per_run_impact(conn, run_id="r1")

    assert impact is not None
    prompt_keys = {
        asset.asset_key for asset in impact.assets_evidenced if asset.asset_kind == "prompt"
    }
    assert prompt_keys == {"research", "coding_debug"}


def test_per_run_impact_assets_evidenced_includes_skills() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_schema(conn)
    _insert_run(conn, "r1")
    _insert_agentize_eval(
        conn,
        "a1",
        "r1",
        selected_skills_json='[{"key":"agentize_intent_compiler"}]',
    )

    impact = build_per_run_impact(conn, run_id="r1")

    assert impact is not None
    assert any(
        asset.asset_kind == "skill" and asset.asset_key == "agentize_intent_compiler"
        for asset in impact.assets_evidenced
    )


def test_per_run_impact_proposals_created_links_to_improvement_writebacks() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_schema(conn)
    _insert_run(conn, "r1")
    _insert_writeback(conn, "w1", "r1", status="pending_approval", requires_approval=1)
    _insert_writeback(conn, "w2", "r1", status="proposed", requires_approval=0, signal_kind=None)

    impact = build_per_run_impact(conn, run_id="r1")

    assert impact is not None
    assert impact.proposals_created == (
        ProposalCreated("w1", "weak_workflow", True, "pending_approval"),
        ProposalCreated("w2", None, False, "proposed"),
    )


def test_per_run_impact_learning_events_persisted_count() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_schema(conn)
    _insert_run(conn, "r1")
    for index in range(5):
        _insert_learning_event(conn, f"e{index}", "r1", "weak_prompt")

    impact = build_per_run_impact(conn, run_id="r1")

    assert impact is not None
    assert impact.learning_events_persisted == 5


def test_per_run_impact_no_learning_reason_passthrough() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_schema(conn)
    _insert_run(conn, "r1", status="canceled", result_summary="")

    impact = build_per_run_impact(conn, run_id="r1")

    assert impact is not None
    assert impact.no_learning_reason == "canceled_without_signal"


def test_per_run_impact_run_not_found_returns_none_or_empty_payload() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_schema(conn)

    assert build_per_run_impact(conn, run_id="missing") is None


def test_per_run_impact_is_pure_read() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_schema(conn)
    _insert_run(conn, "r1")
    _insert_learning_event(conn, "e1", "r1", "weak_prompt")
    before = _snapshot_counts(conn)

    build_per_run_impact(conn, run_id="r1")

    assert _snapshot_counts(conn) == before


def test_rollup_returns_dataclass() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_schema(conn)
    _seed_workflow_window(conn, "implementation-delivery", 10, 2, RECENT)

    rollup = build_rollup(
        conn,
        scope="workflow",
        key="implementation-delivery",
        since=SINCE,
        project_id=None,
    )

    assert isinstance(rollup, LearningImpactRollup)
    assert dataclasses.is_dataclass(rollup)
    with pytest.raises(dataclasses.FrozenInstanceError):
        rollup.sample_size = 1  # type: ignore[misc]


def test_rollup_trend_insufficient_data() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_schema(conn)
    _seed_workflow_window(conn, "implementation-delivery", 3, 1, RECENT)

    rollup = build_rollup(
        conn,
        scope="workflow",
        key="implementation-delivery",
        since=SINCE,
        min_sample_size_for_trend=10,
    )

    assert rollup.trend == "insufficient_data"
    assert "sample_size=3" in rollup.rationale


def test_rollup_trend_improving_requires_sample_floor() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_schema(conn)
    _seed_workflow_window(conn, "implementation-delivery", 6, 1, RECENT)
    _seed_workflow_window(conn, "implementation-delivery", 6, 4, PRIOR, prefix="prior-small")

    small = build_rollup(
        conn,
        scope="workflow",
        key="implementation-delivery",
        since=SINCE,
        min_sample_size_for_trend=10,
    )

    assert small.trend == "insufficient_data"

    conn = sqlite3.connect(":memory:")
    _seed_schema(conn)
    _seed_workflow_window(conn, "implementation-delivery", 15, 1, RECENT)
    _seed_workflow_window(conn, "implementation-delivery", 15, 10, PRIOR, prefix="prior-large")

    large = build_rollup(
        conn,
        scope="workflow",
        key="implementation-delivery",
        since=SINCE,
        min_sample_size_for_trend=10,
    )

    assert large.trend == "improving"
    assert "rework_rate dropped" in large.rationale
    assert "sample_size=15" in large.rationale


def test_rollup_trend_regressing() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_schema(conn)
    _seed_workflow_window(conn, "implementation-delivery", 12, 6, RECENT)
    _seed_workflow_window(conn, "implementation-delivery", 12, 1, PRIOR, prefix="prior")

    rollup = build_rollup(conn, scope="workflow", key="implementation-delivery", since=SINCE)

    assert rollup.trend == "regressing"
    assert "sample_size=12" in rollup.rationale


def test_rollup_trend_flat() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_schema(conn)
    _seed_workflow_window(conn, "implementation-delivery", 15, 5, RECENT)
    _seed_workflow_window(conn, "implementation-delivery", 15, 5, PRIOR, prefix="prior")

    rollup = build_rollup(conn, scope="workflow", key="implementation-delivery", since=SINCE)

    assert rollup.trend == "flat"


def test_rollup_rationale_always_cites_sample_size() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_schema(conn)
    _seed_workflow_window(conn, "implementation-delivery", 15, 5, RECENT)
    _seed_workflow_window(conn, "implementation-delivery", 15, 5, PRIOR, prefix="prior")

    rollup = build_rollup(conn, scope="workflow", key="implementation-delivery", since=SINCE)

    assert f"sample_size={rollup.sample_size}" in rollup.rationale


def test_rollup_scope_prompt() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_schema(conn)
    _insert_run(conn, "r1")
    for index, score in enumerate([0.8, 0.9, 0.4, 0.7]):
        _insert_prompt(conn, f"p{index}", "r1", "research", score, created_at=RECENT)

    rollup = build_rollup(conn, scope="prompt", key="research", since=SINCE)

    assert rollup.sample_size == 4
    assert rollup.success_rate_30d == pytest.approx(0.75)
    assert rollup.blocker_rate_30d is None


def test_rollup_scope_skill() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_schema(conn)
    for index, quality in enumerate([4, 3, 2, 5]):
        run_id = f"r{index}"
        _insert_run(conn, run_id)
        _insert_agentize_eval(
            conn,
            f"a{index}",
            run_id,
            outcome_quality=quality,
            selected_skills_json='[{"key":"agentize_intent_compiler"}]',
            created_at=RECENT,
        )

    rollup = build_rollup(conn, scope="skill", key="agentize_intent_compiler", since=SINCE)

    assert rollup.sample_size == 4
    assert rollup.success_rate_30d == pytest.approx(0.75)


def test_rollup_per_project_filter() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_schema(conn)
    _seed_workflow_window(conn, "implementation-delivery", 10, 2, RECENT, project_id="p1")
    _seed_workflow_window(
        conn, "implementation-delivery", 10, 8, RECENT, project_id="p2", prefix="p2"
    )

    rollup = build_rollup(
        conn,
        scope="workflow",
        key="implementation-delivery",
        since=SINCE,
        project_id="p1",
    )

    assert rollup.sample_size == 10
    assert rollup.rework_rate_30d == pytest.approx(0.2)


def test_rollup_is_pure_read() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_schema(conn)
    _seed_workflow_window(conn, "implementation-delivery", 10, 2, RECENT)
    before = _snapshot_counts(conn)

    build_rollup(conn, scope="workflow", key="implementation-delivery", since=SINCE)

    assert _snapshot_counts(conn) == before


def test_trend_from_rates_helper_unit() -> None:
    assert (
        _trend_from_rates(
            recent_rate=0.2,
            prior_rate=0.5,
            sample_size=12,
            min_sample_size_for_trend=10,
        )[0]
        == "improving"
    )
    assert (
        _trend_from_rates(
            recent_rate=0.2,
            prior_rate=0.5,
            sample_size=8,
            min_sample_size_for_trend=10,
        )[0]
        == "insufficient_data"
    )
    assert (
        _trend_from_rates(
            recent_rate=0.5,
            prior_rate=0.2,
            sample_size=12,
            min_sample_size_for_trend=10,
        )[0]
        == "regressing"
    )
    assert (
        _trend_from_rates(
            recent_rate=0.3,
            prior_rate=0.3,
            sample_size=12,
            min_sample_size_for_trend=10,
        )[0]
        == "flat"
    )


def _seed_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE orchestration_runs (
          id TEXT PRIMARY KEY,
          project_id TEXT,
          workflow_key TEXT,
          status TEXT NOT NULL DEFAULT 'completed',
          result_summary TEXT,
          route_result_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE workflow_learning_events (
          id TEXT PRIMARY KEY,
          run_id TEXT,
          signal_kind TEXT,
          created_at TEXT NOT NULL
        );
        CREATE TABLE agentize_evaluations (
          id TEXT PRIMARY KEY,
          run_id TEXT,
          selected_skills_json TEXT NOT NULL DEFAULT '[]',
          selected_standards_json TEXT NOT NULL DEFAULT '[]',
          outcome_quality INTEGER,
          tests_passed INTEGER,
          follow_up_required INTEGER NOT NULL DEFAULT 0,
          major_repair_required INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL
        );
        CREATE TABLE improvement_writebacks (
          id TEXT PRIMARY KEY,
          run_id TEXT,
          status TEXT NOT NULL,
          requires_approval INTEGER NOT NULL DEFAULT 0,
          proposed_change_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL
        );
        CREATE TABLE prompts_used (
          id TEXT PRIMARY KEY,
          run_id TEXT,
          template_id TEXT,
          outcome_score REAL,
          created_at TEXT NOT NULL
        );
        CREATE TABLE workflow_execution_reports (
          id TEXT PRIMARY KEY,
          run_id TEXT,
          workflow_key TEXT NOT NULL,
          status TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE TABLE success_criteria_findings (
          id TEXT PRIMARY KEY,
          run_id TEXT,
          criterion_id TEXT NOT NULL,
          workflow_key TEXT,
          level TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE TABLE artifacts (
          id TEXT PRIMARY KEY,
          metadata_json TEXT,
          created_at TEXT NOT NULL
        );
        """
    )


def _insert_run(
    conn: sqlite3.Connection,
    run_id: str,
    *,
    project_id: str = "p1",
    workflow_key: str = "implementation-delivery",
    status: str = "completed",
    result_summary: str = "done",
    created_at: str = RECENT,
) -> None:
    conn.execute(
        """
        INSERT INTO orchestration_runs
          (id, project_id, workflow_key, status, result_summary, route_result_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            project_id,
            workflow_key,
            status,
            result_summary,
            f'{{"workflow_key":"{workflow_key}","project_id":"{project_id}"}}',
            created_at,
            created_at,
        ),
    )


def _insert_learning_event(
    conn: sqlite3.Connection,
    event_id: str,
    run_id: str,
    signal_kind: str | None,
) -> None:
    conn.execute(
        "INSERT INTO workflow_learning_events (id, run_id, signal_kind, created_at) VALUES (?, ?, ?, ?)",
        (event_id, run_id, signal_kind, RECENT),
    )


def _insert_agentize_eval(
    conn: sqlite3.Connection,
    eval_id: str,
    run_id: str,
    *,
    outcome_quality: int = 4,
    tests_passed: int = 1,
    selected_skills_json: str = "[]",
    selected_standards_json: str = "[]",
    created_at: str = RECENT,
) -> None:
    conn.execute(
        """
        INSERT INTO agentize_evaluations
          (id, run_id, selected_skills_json, selected_standards_json, outcome_quality, tests_passed, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            eval_id,
            run_id,
            selected_skills_json,
            selected_standards_json,
            outcome_quality,
            tests_passed,
            created_at,
        ),
    )


def _insert_prompt(
    conn: sqlite3.Connection,
    prompt_id: str,
    run_id: str,
    template_id: str,
    outcome_score: float,
    *,
    created_at: str = RECENT,
) -> None:
    conn.execute(
        """
        INSERT INTO prompts_used (id, run_id, template_id, outcome_score, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (prompt_id, run_id, template_id, outcome_score, created_at),
    )


def _insert_writeback(
    conn: sqlite3.Connection,
    writeback_id: str,
    run_id: str,
    *,
    status: str,
    requires_approval: int,
    signal_kind: str | None = "weak_workflow",
) -> None:
    payload = "{}" if signal_kind is None else f'{{"signal_kind":"{signal_kind}"}}'
    conn.execute(
        """
        INSERT INTO improvement_writebacks
          (id, run_id, status, requires_approval, proposed_change_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (writeback_id, run_id, status, requires_approval, payload, RECENT),
    )


def _seed_workflow_window(
    conn: sqlite3.Connection,
    workflow_key: str,
    sample_size: int,
    failed_count: int,
    created_at: str,
    *,
    project_id: str = "p1",
    prefix: str = "recent",
) -> None:
    for index in range(sample_size):
        run_id = f"{prefix}-run-{index}"
        _insert_run(
            conn, run_id, project_id=project_id, workflow_key=workflow_key, created_at=created_at
        )
        conn.execute(
            """
            INSERT INTO workflow_execution_reports
              (id, run_id, workflow_key, status, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                f"{prefix}-report-{index}",
                run_id,
                workflow_key,
                "failed" if index < failed_count else "completed",
                created_at,
            ),
        )


def _snapshot_counts(conn: sqlite3.Connection) -> dict[str, int]:
    tables = [
        str(row[0])
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    ]
    return {
        table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) for table in tables
    }
