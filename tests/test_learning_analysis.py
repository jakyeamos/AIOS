from __future__ import annotations

import dataclasses
import sqlite3
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.learning_analysis import (  # noqa: E402
    DETECTORS,
    RecurringPattern,
    _bucket_window,
    _detect_bloated_packets,
    _detect_ignored_rules,
    _detect_repeated_failures,
    _detect_route_misroutes,
    _detect_standards_regression,
    _detect_weak_prompts,
    _detect_weak_workflows,
    _stable_pattern_id,
    detect_recurring_patterns,
)

NOW = datetime(2026, 5, 21, tzinfo=UTC)
RECENT = "2026-05-21T00:00:00Z"
OLD = "2026-01-01T00:00:00Z"


def test_recurring_pattern_is_frozen_dataclass() -> None:
    pattern = RecurringPattern(
        pattern_id="pattern-1",
        signal_kind="weak_workflow",
        scope_kind="workflow",
        scope_key="implementation-delivery",
        project_id=None,
        sample_size=5,
        recurrence_count=3,
        confidence=0.6,
        since=RECENT,
        summary="summary",
        evidence_run_ids=("run-1",),
        suggested_remediation_class="tighten_validations_or_deprecate",
    )

    assert dataclasses.is_dataclass(pattern)
    with pytest.raises(dataclasses.FrozenInstanceError):
        pattern.sample_size = 6  # type: ignore[misc]


def test_detect_recurring_patterns_with_empty_db_returns_empty_list() -> None:
    conn = sqlite3.connect(":memory:")

    assert detect_recurring_patterns(conn, since=RECENT, project_id=None) == []


def test_detect_recurring_patterns_skips_informational_signals() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_minimal_schema(conn)

    assert (
        detect_recurring_patterns(
            conn,
            since=RECENT,
            project_id=None,
            signal_kinds=("writeback_adopted", "compounding_gain"),
        )
        == []
    )


def test_detect_recurring_patterns_runs_all_actionable_when_signal_kinds_omitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = sqlite3.connect(":memory:")
    calls: list[str] = []

    def detector(
        _conn: sqlite3.Connection,
        *,
        since: str,
        project_id: str | None,
    ) -> list[RecurringPattern]:
        assert since == RECENT
        assert project_id is None
        calls.append("called")
        return []

    monkeypatch.setattr(
        "services.learning_analysis.DETECTORS",
        {signal: detector for signal in DETECTORS},
    )

    assert detect_recurring_patterns(conn, since=RECENT, project_id=None) == []
    assert len(calls) == 7


def test_stable_pattern_id_is_deterministic() -> None:
    first = _stable_pattern_id(
        signal_kind="weak_workflow",
        scope_kind="workflow",
        scope_key="implementation-delivery",
        since_window_bucket="2026-W18",
    )
    second = _stable_pattern_id(
        signal_kind="weak_workflow",
        scope_kind="workflow",
        scope_key="implementation-delivery",
        since_window_bucket="2026-W18",
    )
    different = _stable_pattern_id(
        signal_kind="weak_workflow",
        scope_kind="workflow",
        scope_key="implementation-delivery",
        since_window_bucket="2026-W19",
    )

    assert first == second
    assert first != different


def test_bucket_window_handles_iso_and_day_offset_format() -> None:
    assert _bucket_window("2026-05-21T00:00:00Z") == "2026-W21"
    assert isinstance(_bucket_window("30d"), str)


def test_detect_recurring_patterns_honors_since_bound() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_minimal_schema(conn)
    _seed_runs(conn, ["old-run", "new-run", "new-run-2", "new-run-3"], project_id="p1")
    _insert_finding(conn, "old-finding", "old-run", "C-bound", created_at=OLD)
    for index in range(1, 4):
        _insert_finding(
            conn, f"new-finding-{index}", f"new-run{'' if index == 1 else f'-{index}'}", "C-bound"
        )

    patterns = _detect_repeated_failures(conn, since=RECENT, project_id="p1")

    assert len(patterns) == 1
    assert "old-run" not in patterns[0].evidence_run_ids


def test_detect_repeated_failures_groups_by_criterion_and_workflow() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_minimal_schema(conn)
    _seed_runs(conn, ["run-1", "run-2", "run-3"], project_id="p1")
    for index in range(1, 4):
        _insert_finding(conn, f"finding-{index}", f"run-{index}", "C-arch-cohesion")

    patterns = _detect_repeated_failures(conn, since=RECENT, project_id="p1")

    assert len(patterns) == 1
    assert patterns[0].signal_kind == "repeated_failure"
    assert patterns[0].scope_kind == "criterion"
    assert patterns[0].scope_key == "C-arch-cohesion"
    assert patterns[0].recurrence_count == 3
    assert patterns[0].sample_size == 3
    assert set(patterns[0].evidence_run_ids) == {"run-1", "run-2", "run-3"}


def test_detect_repeated_failures_below_threshold_returns_empty() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_minimal_schema(conn)
    _seed_runs(conn, ["run-1"], project_id="p1")
    _insert_finding(conn, "finding-1", "run-1", "C-arch-cohesion")

    assert _detect_repeated_failures(conn, since=RECENT, project_id="p1") == []


def test_detect_repeated_failures_per_project_default() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_minimal_schema(conn)
    _seed_runs(conn, [f"p1-run-{index}" for index in range(4)], project_id="p1")
    _seed_runs(conn, [f"p2-run-{index}" for index in range(4)], project_id="p2")
    for index in range(4):
        _insert_finding(conn, f"p1-finding-{index}", f"p1-run-{index}", "C-p1")
        _insert_finding(conn, f"p2-finding-{index}", f"p2-run-{index}", "C-p2")

    scoped = _detect_repeated_failures(conn, since=RECENT, project_id="p1")
    cross_project = _detect_repeated_failures(conn, since=RECENT, project_id=None)

    assert [pattern.scope_key for pattern in scoped] == ["C-p1"]
    assert {pattern.scope_key for pattern in cross_project} == {"C-p1", "C-p2"}


def test_detect_ignored_rules_requires_multi_run_recurrence() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_minimal_schema(conn)
    _seed_runs(conn, ["run-1", "run-2"], project_id="p1")
    for index in range(1, 3):
        _insert_finding(conn, f"finding-{index}", f"run-{index}", "C-rule")

    patterns = _detect_ignored_rules(conn, since=RECENT, project_id="p1")

    assert len(patterns) == 1
    assert patterns[0].signal_kind == "ignored_rule"
    assert patterns[0].sample_size == 2
    assert patterns[0].suggested_remediation_class == "raise_blocker_priority"


def test_detect_ignored_rules_resolved_findings_excluded() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_minimal_schema(conn)
    _seed_runs(conn, ["run-1", "run-2"], project_id="p1")
    for index in range(1, 3):
        _insert_finding(
            conn,
            f"finding-{index}",
            f"run-{index}",
            "C-rule",
            resolution_status="resolved",
        )

    assert _detect_ignored_rules(conn, since=RECENT, project_id="p1") == []


def test_detect_weak_prompts_mean_below_threshold() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_minimal_schema(conn)
    _seed_runs(conn, [f"run-{index}" for index in range(5)], project_id="p1")
    for index, score in enumerate([0.2, 0.3, 0.25, 0.2, 0.3]):
        _insert_prompt(conn, f"prompt-{index}", f"run-{index}", "research", score)

    patterns = _detect_weak_prompts(conn, since=RECENT, project_id="p1")

    assert len(patterns) == 1
    assert patterns[0].signal_kind == "weak_prompt"
    assert patterns[0].scope_kind == "prompt"
    assert patterns[0].scope_key == "research"
    assert patterns[0].sample_size == 5
    assert patterns[0].confidence == pytest.approx(0.75)


def test_detect_weak_prompts_requires_sample_floor() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_minimal_schema(conn)
    _seed_runs(conn, ["run-1", "run-2"], project_id="p1")
    _insert_prompt(conn, "prompt-1", "run-1", "research", 0.2)
    _insert_prompt(conn, "prompt-2", "run-2", "research", 0.2)

    assert _detect_weak_prompts(conn, since=RECENT, project_id="p1") == []


def test_detect_weak_workflows_high_failure_rate() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_minimal_schema(conn)
    run_ids = [f"run-{index}" for index in range(10)]
    _seed_runs(conn, run_ids, project_id="p1")
    for index, run_id in enumerate(run_ids):
        _insert_workflow_report(
            conn,
            f"report-{index}",
            run_id,
            "implementation-delivery",
            "failed" if index < 6 else "completed",
        )

    patterns = _detect_weak_workflows(conn, since=RECENT, project_id="p1")

    assert len(patterns) == 1
    assert patterns[0].signal_kind == "weak_workflow"
    assert patterns[0].scope_key == "implementation-delivery"
    assert patterns[0].recurrence_count == 6
    assert patterns[0].sample_size == 10


def test_detect_weak_workflows_below_sample_floor_returns_empty() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_minimal_schema(conn)
    _seed_runs(conn, ["run-1", "run-2"], project_id="p1")
    _insert_workflow_report(conn, "report-1", "run-1", "implementation-delivery", "failed")
    _insert_workflow_report(conn, "report-2", "run-2", "implementation-delivery", "failed")

    assert _detect_weak_workflows(conn, since=RECENT, project_id="p1") == []


def test_all_four_detectors_emit_stable_pattern_id() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_four_core_detectors(conn)

    detectors = (
        _detect_repeated_failures,
        _detect_ignored_rules,
        _detect_weak_prompts,
        _detect_weak_workflows,
    )

    for detector in detectors:
        first = detector(conn, since=RECENT, project_id="p1")
        second = detector(conn, since=RECENT, project_id="p1")
        assert first
        assert [pattern.pattern_id for pattern in first] == [
            pattern.pattern_id for pattern in second
        ]


def test_detect_bloated_packets_uses_per_workflow_median() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_minimal_schema(conn)
    counts = [10, 12, 11, 9, 50, 11, 10]
    run_ids = [f"run-{index}" for index in range(len(counts))]
    _seed_runs(conn, run_ids, project_id="p1")
    for index, count in enumerate(counts):
        _insert_packet(conn, f"packet-{index}", f"run-{index}", count)

    patterns = _detect_bloated_packets(conn, since=RECENT, project_id="p1")

    assert len(patterns) == 1
    assert patterns[0].signal_kind == "bloated_packet"
    assert patterns[0].scope_kind == "packet"
    assert patterns[0].scope_key == "run-4"
    assert "Median packet" in patterns[0].summary
    assert "50 sections" in patterns[0].summary


def test_detect_bloated_packets_summary_excludes_raw_content() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_minimal_schema(conn)
    counts = [10, 12, 11, 9, 50, 11, 10]
    run_ids = [f"run-{index}" for index in range(len(counts))]
    _seed_runs(conn, run_ids, project_id="p1")
    for index, count in enumerate(counts):
        _insert_packet(conn, f"packet-{index}", f"run-{index}", count)

    summary = _detect_bloated_packets(conn, since=RECENT, project_id="p1")[0].summary

    assert "raw selection trace" not in summary
    assert "median" in summary.lower()
    assert "sections" in summary


def test_detect_route_misroutes_uses_route_result_json() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_minimal_schema(conn)
    run_ids = [f"run-{index}" for index in range(4)]
    _seed_runs(conn, run_ids, project_id="p1", route_workflow_key="audit-only")
    for index, run_id in enumerate(run_ids):
        _insert_finding(conn, f"finding-{index}", run_id, "C-route")

    patterns = _detect_route_misroutes(conn, since=RECENT, project_id="p1")

    assert len(patterns) == 1
    assert patterns[0].signal_kind == "route_misroute"
    assert patterns[0].scope_kind == "route"
    assert patterns[0].scope_key == "audit-only"
    assert set(patterns[0].evidence_run_ids) == set(run_ids)


def test_detect_route_misroutes_clean_runs_excluded() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_minimal_schema(conn)
    _seed_runs(
        conn,
        [f"run-{index}" for index in range(4)],
        project_id="p1",
        route_workflow_key="implementation-delivery",
    )

    assert _detect_route_misroutes(conn, since=RECENT, project_id="p1") == []


def test_detect_route_misroutes_evidence_run_ids_cite_actual_runs() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_minimal_schema(conn)
    run_ids = [f"run-{index}" for index in range(4)]
    _seed_runs(conn, run_ids, project_id="p1", route_workflow_key="audit-only")
    for index, run_id in enumerate(run_ids):
        _insert_finding(conn, f"finding-{index}", run_id, "C-route")

    pattern = _detect_route_misroutes(conn, since=RECENT, project_id="p1")[0]

    assert pattern.evidence_run_ids == tuple(run_ids)


def test_detect_standards_regression_reads_priority_bucket() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_minimal_schema(conn)
    _seed_standards_regressions(conn, snapshot_count=3)

    patterns = _detect_standards_regression(conn, since=RECENT, project_id="p1")

    assert len(patterns) == 1
    assert patterns[0].signal_kind == "standards_regression"
    assert patterns[0].scope_kind == "standard"
    assert patterns[0].scope_key == "STND-coverage"
    assert patterns[0].sample_size == 3
    assert patterns[0].recurrence_count == 3


def test_detect_standards_regression_single_instance_excluded() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_minimal_schema(conn)
    _seed_standards_regressions(conn, snapshot_count=1)

    assert _detect_standards_regression(conn, since=RECENT, project_id="p1") == []


def test_dispatcher_since_bound_applies_to_all_detectors() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_all_seven(conn, include_old=True, created_at=_recent_window_timestamp())

    patterns = detect_recurring_patterns(conn, since="30d", project_id=None)
    cutoff = datetime.now(UTC) - timedelta(days=30)

    assert patterns
    for pattern in patterns:
        for run_id in pattern.evidence_run_ids:
            created_at = _run_created_at(conn, run_id)
            assert created_at >= cutoff


def test_dispatcher_returns_patterns_from_all_seven_kinds_when_seeded() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_all_seven(conn)

    patterns = detect_recurring_patterns(conn, since=RECENT, project_id=None)

    assert {pattern.signal_kind for pattern in patterns} == {
        "repeated_failure",
        "ignored_rule",
        "bloated_packet",
        "weak_prompt",
        "weak_workflow",
        "route_misroute",
        "standards_regression",
    }


def _seed_minimal_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE orchestration_runs (
          id TEXT PRIMARY KEY,
          project_id TEXT,
          workflow_key TEXT NOT NULL,
          route_result_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL
        );
        CREATE TABLE success_criteria_findings (
          id TEXT PRIMARY KEY,
          run_id TEXT NOT NULL,
          criterion_id TEXT NOT NULL,
          workflow_key TEXT NOT NULL,
          level TEXT NOT NULL,
          resolution_status TEXT NOT NULL DEFAULT 'open',
          created_at TEXT NOT NULL
        );
        CREATE TABLE prompts_used (
          id TEXT PRIMARY KEY,
          run_id TEXT NOT NULL,
          template_id TEXT NOT NULL,
          classification TEXT,
          outcome_score REAL,
          created_at TEXT NOT NULL
        );
        CREATE TABLE workflow_execution_reports (
          id TEXT PRIMARY KEY,
          run_id TEXT NOT NULL,
          workflow_key TEXT NOT NULL,
          status TEXT NOT NULL,
          report_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL
        );
        CREATE TABLE briefing_packets (
          id TEXT PRIMARY KEY,
          run_id TEXT NOT NULL,
          workflow_key TEXT NOT NULL,
          selected_context_packets_json TEXT NOT NULL DEFAULT '[]',
          selection_trace_json TEXT NOT NULL DEFAULT '[]',
          created_at TEXT NOT NULL
        );
        CREATE TABLE standards_health_snapshots (
          id TEXT PRIMARY KEY,
          project_id TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE TABLE standards_delta_items (
          id TEXT PRIMARY KEY,
          snapshot_id TEXT NOT NULL,
          project_id TEXT NOT NULL,
          standard_id TEXT NOT NULL,
          priority_bucket TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        """
    )


def _seed_runs(
    conn: sqlite3.Connection,
    run_ids: list[str],
    *,
    project_id: str,
    workflow_key: str = "implementation-delivery",
    route_workflow_key: str | None = None,
    created_at: str | None = None,
) -> None:
    route_key = route_workflow_key or workflow_key
    for run_id in run_ids:
        conn.execute(
            """
            INSERT INTO orchestration_runs
              (id, project_id, workflow_key, route_result_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                run_id,
                project_id,
                workflow_key,
                f'{{"workflow_key":"{route_key}","project_id":"{project_id}"}}',
                created_at or RECENT,
            ),
        )


def _insert_finding(
    conn: sqlite3.Connection,
    finding_id: str,
    run_id: str,
    criterion_id: str,
    *,
    workflow_key: str = "implementation-delivery",
    level: str = "blocker",
    resolution_status: str = "open",
    created_at: str = RECENT,
) -> None:
    conn.execute(
        """
        INSERT INTO success_criteria_findings
          (id, run_id, criterion_id, workflow_key, level, resolution_status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (finding_id, run_id, criterion_id, workflow_key, level, resolution_status, created_at),
    )


def _insert_prompt(
    conn: sqlite3.Connection,
    prompt_id: str,
    run_id: str,
    template_id: str,
    score: float,
    *,
    created_at: str = RECENT,
) -> None:
    conn.execute(
        """
        INSERT INTO prompts_used (id, run_id, template_id, outcome_score, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (prompt_id, run_id, template_id, score, created_at),
    )


def _insert_workflow_report(
    conn: sqlite3.Connection,
    report_id: str,
    run_id: str,
    workflow_key: str,
    status: str,
    *,
    created_at: str = RECENT,
) -> None:
    conn.execute(
        """
        INSERT INTO workflow_execution_reports
          (id, run_id, workflow_key, status, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (report_id, run_id, workflow_key, status, created_at),
    )


def _insert_packet(
    conn: sqlite3.Connection,
    packet_id: str,
    run_id: str,
    section_count: int,
    *,
    workflow_key: str = "implementation-delivery",
    created_at: str = RECENT,
) -> None:
    sections = ",".join('"section"' for _ in range(section_count))
    conn.execute(
        """
        INSERT INTO briefing_packets
          (id, run_id, workflow_key, selected_context_packets_json, selection_trace_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            packet_id,
            run_id,
            workflow_key,
            f"[{sections}]",
            '["raw selection trace sentinel"]',
            created_at,
        ),
    )


def _recent_window_timestamp() -> str:
    return (
        (datetime.now(UTC) - timedelta(days=1))
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _seed_standards_regressions(
    conn: sqlite3.Connection, *, snapshot_count: int, created_at: str = RECENT
) -> None:
    for index in range(snapshot_count):
        snapshot_id = f"snapshot-{index}"
        conn.execute(
            "INSERT INTO standards_health_snapshots (id, project_id, created_at) VALUES (?, ?, ?)",
            (snapshot_id, "p1", created_at),
        )
        conn.execute(
            """
            INSERT INTO standards_delta_items
              (id, snapshot_id, project_id, standard_id, priority_bucket, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (f"delta-{index}", snapshot_id, "p1", "STND-coverage", "regressed", created_at),
        )


def _seed_four_core_detectors(conn: sqlite3.Connection) -> None:
    _seed_minimal_schema(conn)
    _seed_runs(conn, [f"rf-run-{index}" for index in range(3)], project_id="p1")
    for index in range(3):
        _insert_finding(conn, f"rf-finding-{index}", f"rf-run-{index}", "C-repeat")
    _seed_runs(conn, [f"prompt-run-{index}" for index in range(5)], project_id="p1")
    for index in range(5):
        _insert_prompt(conn, f"prompt-{index}", f"prompt-run-{index}", "research", 0.2)
    _seed_runs(conn, [f"workflow-run-{index}" for index in range(5)], project_id="p1")
    for index in range(5):
        _insert_workflow_report(
            conn,
            f"workflow-report-{index}",
            f"workflow-run-{index}",
            "implementation-delivery",
            "failed",
        )


def _seed_all_seven(
    conn: sqlite3.Connection, *, include_old: bool = False, created_at: str = RECENT
) -> None:
    _seed_minimal_schema(conn)
    _seed_runs(
        conn, [f"rf-run-{index}" for index in range(3)], project_id="p1", created_at=created_at
    )
    for index in range(3):
        _insert_finding(
            conn, f"rf-finding-{index}", f"rf-run-{index}", "C-repeat", created_at=created_at
        )
    _seed_runs(
        conn,
        [f"prompt-run-{index}" for index in range(5)],
        project_id="p1",
        created_at=created_at,
    )
    for index in range(5):
        _insert_prompt(
            conn, f"prompt-{index}", f"prompt-run-{index}", "research", 0.2, created_at=created_at
        )
    _seed_runs(
        conn,
        [f"workflow-run-{index}" for index in range(5)],
        project_id="p1",
        created_at=created_at,
    )
    for index in range(5):
        _insert_workflow_report(
            conn,
            f"workflow-report-{index}",
            f"workflow-run-{index}",
            "implementation-delivery",
            "failed",
            created_at=created_at,
        )
    packet_counts = [10, 12, 11, 9, 50, 11, 10]
    _seed_runs(
        conn,
        [f"packet-run-{index}" for index in range(7)],
        project_id="p1",
        created_at=created_at,
    )
    for index, count in enumerate(packet_counts):
        _insert_packet(conn, f"packet-{index}", f"packet-run-{index}", count, created_at=created_at)
    _seed_runs(
        conn,
        [f"route-run-{index}" for index in range(4)],
        project_id="p1",
        route_workflow_key="audit-only",
        created_at=created_at,
    )
    for index in range(4):
        _insert_finding(
            conn, f"route-finding-{index}", f"route-run-{index}", "C-route", created_at=created_at
        )
    _seed_standards_regressions(conn, snapshot_count=3, created_at=created_at)
    if include_old:
        _seed_runs(conn, ["old-run-1", "old-run-2", "old-run-3"], project_id="p1", created_at=OLD)
        for index in range(1, 4):
            _insert_finding(
                conn, f"old-finding-{index}", f"old-run-{index}", "C-old", created_at=OLD
            )


def _run_created_at(conn: sqlite3.Connection, run_id: str) -> datetime:
    row = conn.execute(
        "SELECT created_at FROM orchestration_runs WHERE id = ?", (run_id,)
    ).fetchone()
    assert row is not None
    value = str(row[0]).replace("Z", "+00:00")
    return datetime.fromisoformat(value).astimezone(UTC)
