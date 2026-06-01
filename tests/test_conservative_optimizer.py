from __future__ import annotations

import json
import sqlite3
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.conservative_optimizer import (  # noqa: E402
    _writeback_within_cooling_period,
    load_conservatism_policy,
    propose_from_all_patterns,
    propose_from_pattern,
)
from services.learning_analysis import RecurringPattern  # noqa: E402
from services.learning_taxonomy import ConservatismPolicy  # noqa: E402

POLICY_PATH = ROOT / "config" / "learning" / "conservatism-policy.json"


def test_conservatism_policy_json_is_well_formed() -> None:
    payload = json.loads(POLICY_PATH.read_text())

    assert {
        "version",
        "min_sample_size",
        "min_recurrence_count",
        "min_confidence",
        "cooling_period_days",
        "min_sample_size_for_trend",
        "per_signal_overrides",
    } <= set(payload)


def test_load_conservatism_policy_returns_dataclass() -> None:
    payload = json.loads(POLICY_PATH.read_text())

    policy = load_conservatism_policy()

    assert isinstance(policy, ConservatismPolicy)
    assert policy.min_sample_size == payload["min_sample_size"]
    assert isinstance(policy.per_signal_overrides, dict)


def test_load_conservatism_policy_accepts_path_override(tmp_path: Path) -> None:
    custom = tmp_path / "policy.json"
    custom.write_text(
        json.dumps(
            {
                "version": "test",
                "min_sample_size": 9,
                "min_recurrence_count": 4,
                "min_confidence": 0.7,
                "cooling_period_days": 21,
                "min_sample_size_for_trend": 12,
                "per_signal_overrides": {},
            }
        )
    )

    policy = load_conservatism_policy(path=custom)

    assert policy.min_sample_size == 9
    assert policy.cooling_period_days == 21


def test_load_conservatism_policy_rejects_unknown_keys(tmp_path: Path) -> None:
    custom = tmp_path / "policy.json"
    custom.write_text(
        json.dumps(
            {
                "version": "test",
                "min_sample_size": 5,
                "min_recurrence_count": 3,
                "min_confidance": 0.6,
                "cooling_period_days": 14,
                "min_sample_size_for_trend": 10,
                "per_signal_overrides": {},
            }
        )
    )

    with pytest.raises(ValueError, match="min_confidance"):
        load_conservatism_policy(path=custom)


def test_load_conservatism_policy_defaults_when_per_signal_overrides_absent(
    tmp_path: Path,
) -> None:
    custom = tmp_path / "policy.json"
    custom.write_text(
        json.dumps(
            {
                "version": "test",
                "min_sample_size": 5,
                "min_recurrence_count": 3,
                "min_confidence": 0.6,
                "cooling_period_days": 14,
                "min_sample_size_for_trend": 10,
            }
        )
    )

    policy = load_conservatism_policy(path=custom)

    assert policy.per_signal_overrides == {}


def test_conservatism_policy_thresholds_are_conservative() -> None:
    policy = load_conservatism_policy()

    assert policy.min_sample_size >= 5
    assert policy.min_recurrence_count >= 3
    assert policy.min_confidence >= 0.6
    assert policy.cooling_period_days >= 7


def test_propose_from_pattern_rejects_low_sample_size() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_writeback_schema(conn)

    assert propose_from_pattern(conn, _pattern(sample_size=2), _policy()) is None
    assert _count(conn, "improvement_writebacks") == 0


def test_propose_from_pattern_rejects_low_recurrence() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_writeback_schema(conn)

    assert propose_from_pattern(conn, _pattern(recurrence_count=1), _policy()) is None
    assert _count(conn, "improvement_writebacks") == 0


def test_propose_from_pattern_rejects_low_confidence() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_writeback_schema(conn)

    assert propose_from_pattern(conn, _pattern(confidence=0.3), _policy()) is None
    assert _count(conn, "improvement_writebacks") == 0


def test_propose_from_pattern_emits_writeback_when_all_thresholds_met() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_writeback_schema(conn)

    result = propose_from_pattern(conn, _pattern(), _policy())
    row = _writeback_row(conn)

    assert result is not None
    assert result["requires_approval"] is True
    assert _count(conn, "improvement_writebacks") == 1
    assert row["layer_type"] == "workflow"
    assert row["impact_scope"] == "workflow-default"
    assert row["status"] == "pending_approval"
    assert row["requires_approval"] == 1


def test_propose_from_pattern_always_requires_approval() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_writeback_schema(conn)

    propose_from_pattern(conn, _pattern(signal_kind="weak_prompt", scope_kind="prompt"), _policy())
    row = _writeback_row(conn)

    assert row["requires_approval"] == 1
    assert row["status"] == "pending_approval"


def test_propose_from_pattern_skips_informational_signal() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_writeback_schema(conn)

    assert propose_from_pattern(conn, _pattern(signal_kind="writeback_adopted"), _policy()) is None
    assert _count(conn, "improvement_writebacks") == 0


def test_propose_from_pattern_metadata_includes_source_and_pattern_id() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_writeback_schema(conn)
    pattern = _pattern()

    propose_from_pattern(conn, pattern, _policy())
    payload = json.loads(_writeback_row(conn)["proposed_change_json"])

    assert payload["metadata"]["source"] == "learning_analysis"
    assert payload["metadata"]["pattern_id"] == pattern.pattern_id
    assert payload["metadata"]["evidence_run_ids"] == list(pattern.evidence_run_ids)
    assert payload["metadata"]["sample_size"] == pattern.sample_size
    assert payload["metadata"]["recurrence_count"] == pattern.recurrence_count
    assert payload["metadata"]["confidence"] == pattern.confidence


def test_propose_from_pattern_emits_writeback_event() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_writeback_schema(conn)

    result = propose_from_pattern(conn, _pattern(), _policy(), actor="agent")
    event = conn.execute("SELECT * FROM improvement_writeback_events").fetchone()

    assert result is not None
    assert event["writeback_id"] == result["writeback_id"]
    assert event["event_type"] == "proposed"
    assert event["actor"] == "agent"


def test_propose_from_pattern_per_signal_override() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_writeback_schema(conn)
    policy = _policy(per_signal_overrides={"weak_prompt": {"min_sample_size": 20}})

    assert (
        propose_from_pattern(
            conn, _pattern(signal_kind="weak_prompt", scope_kind="prompt", sample_size=10), policy
        )
        is None
    )
    assert (
        propose_from_pattern(
            conn, _pattern(signal_kind="weak_prompt", scope_kind="prompt", sample_size=25), policy
        )
        is not None
    )


def test_propose_from_pattern_only_writes_to_improvement_writebacks_tables() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_writeback_schema(conn)
    conn.execute("CREATE TABLE promotion_lifecycle_items (id TEXT PRIMARY KEY)")
    conn.execute("CREATE TABLE prompts_registry (id TEXT PRIMARY KEY)")
    before = _snapshot_counts(conn)

    propose_from_pattern(conn, _pattern(), _policy())
    after = _snapshot_counts(conn)

    assert after["improvement_writebacks"] == before["improvement_writebacks"] + 1
    assert after["improvement_writeback_events"] == before["improvement_writeback_events"] + 1
    assert after["promotion_lifecycle_items"] == before["promotion_lifecycle_items"]
    assert after["prompts_registry"] == before["prompts_registry"]


def test_writeback_within_cooling_period_finds_recent_proposed() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_writeback_schema(conn)
    _seed_existing_writeback(conn, "pattern-abc", days_ago=3, status="proposed")

    assert _writeback_within_cooling_period(conn, "pattern-abc", 14)


def test_writeback_within_cooling_period_ignores_old() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_writeback_schema(conn)
    _seed_existing_writeback(conn, "pattern-abc", days_ago=30, status="proposed")

    assert not _writeback_within_cooling_period(conn, "pattern-abc", 14)


def test_writeback_within_cooling_period_finds_approved_and_rejected_decisions() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_writeback_schema(conn)
    _seed_existing_writeback(conn, "pattern-abc", days_ago=3, status="approved")
    _seed_existing_writeback(conn, "pattern-def", days_ago=3, status="rejected")

    assert _writeback_within_cooling_period(conn, "pattern-abc", 14)
    assert _writeback_within_cooling_period(conn, "pattern-def", 14)


def test_propose_from_pattern_honors_cooling_period() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_writeback_schema(conn)
    pattern = _pattern()

    assert propose_from_pattern(conn, pattern, _policy()) is not None
    assert propose_from_pattern(conn, pattern, _policy()) is None
    assert _count(conn, "improvement_writebacks") == 1


def test_propose_from_pattern_re_proposes_after_cooling_period() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_writeback_schema(conn)
    pattern = _pattern()

    propose_from_pattern(conn, pattern, _policy())
    old = (datetime.now(UTC) - timedelta(days=30)).replace(microsecond=0).isoformat()
    conn.execute("UPDATE improvement_writebacks SET created_at = ?", (old,))

    assert propose_from_pattern(conn, pattern, _policy()) is not None
    assert _count(conn, "improvement_writebacks") == 2


def test_propose_from_all_patterns_batch() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_writeback_schema(conn)

    result = propose_from_all_patterns(
        conn,
        [
            _pattern(pattern_id="pattern-1"),
            _pattern(pattern_id="pattern-2"),
            _pattern(sample_size=1),
        ],
        _policy(),
    )

    assert result["proposed_count"] == 2
    assert result["skipped_count"] == 1
    assert _count(conn, "improvement_writebacks") == 2


def test_propose_from_all_patterns_dedupes_across_batch() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_writeback_schema(conn)
    pattern = _pattern()

    result = propose_from_all_patterns(conn, [pattern, pattern, pattern], _policy())

    assert result["proposed_count"] == 1
    assert result["skipped_count"] == 2
    assert _count(conn, "improvement_writebacks") == 1


def test_dispatcher_skip_reasons_are_returned() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_writeback_schema(conn)
    cooling = _pattern(pattern_id="pattern-cooling")
    propose_from_pattern(conn, cooling, _policy())

    result = propose_from_all_patterns(
        conn,
        [
            _pattern(pattern_id="pattern-sample", sample_size=1),
            _pattern(pattern_id="pattern-recurrence", recurrence_count=1),
            _pattern(pattern_id="pattern-confidence", confidence=0.1),
            _pattern(pattern_id="pattern-info", signal_kind="compounding_gain"),
            cooling,
        ],
        _policy(),
    )

    assert {entry["reason"] for entry in result["skipped"]} == {
        "below_sample",
        "below_recurrence",
        "below_confidence",
        "informational",
        "within_cooling_period",
    }


def _policy(
    *,
    per_signal_overrides: dict[str, dict[str, int | float]] | None = None,
) -> ConservatismPolicy:
    return ConservatismPolicy(
        min_sample_size=5,
        min_recurrence_count=3,
        min_confidence=0.6,
        cooling_period_days=14,
        min_sample_size_for_trend=10,
        per_signal_overrides=per_signal_overrides or {},
    )


def _pattern(
    *,
    pattern_id: str = "pattern-abc",
    signal_kind: str = "weak_workflow",
    scope_kind: str = "workflow",
    sample_size: int = 10,
    recurrence_count: int = 5,
    confidence: float = 0.8,
) -> RecurringPattern:
    return RecurringPattern(
        pattern_id=pattern_id,
        signal_kind=signal_kind,  # type: ignore[arg-type]
        scope_kind=scope_kind,
        scope_key="implementation-delivery",
        project_id="p1",
        sample_size=sample_size,
        recurrence_count=recurrence_count,
        confidence=confidence,
        since="2026-06-01T00:00:00Z",
        summary="Workflow repeatedly failed.",
        evidence_run_ids=("run-1", "run-2"),
        suggested_remediation_class="tighten_validations_or_deprecate",
    )


def _seed_writeback_schema(conn: sqlite3.Connection) -> None:
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE improvement_writebacks (
          id TEXT PRIMARY KEY,
          run_id TEXT,
          project_id TEXT,
          layer_type TEXT NOT NULL,
          layer_key TEXT NOT NULL,
          title TEXT NOT NULL,
          summary TEXT NOT NULL,
          evidence_json TEXT NOT NULL DEFAULT '[]',
          proposed_change_json TEXT NOT NULL DEFAULT '{}',
          impact_scope TEXT NOT NULL DEFAULT 'scoped',
          status TEXT NOT NULL DEFAULT 'proposed',
          requires_approval INTEGER NOT NULL DEFAULT 0,
          approval_reason TEXT,
          token_regressive INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE improvement_writeback_events (
          id TEXT PRIMARY KEY,
          writeback_id TEXT NOT NULL,
          run_id TEXT,
          event_type TEXT NOT NULL,
          from_status TEXT,
          to_status TEXT,
          actor TEXT NOT NULL DEFAULT 'system',
          note TEXT,
          metadata_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL
        );
        """
    )


def _seed_existing_writeback(
    conn: sqlite3.Connection,
    pattern_id: str,
    *,
    days_ago: int,
    status: str,
) -> None:
    created_at = (datetime.now(UTC) - timedelta(days=days_ago)).replace(microsecond=0)
    conn.execute(
        """
        INSERT INTO improvement_writebacks (
          id, run_id, project_id, layer_type, layer_key, title, summary, evidence_json,
          proposed_change_json, impact_scope, status, requires_approval, approval_reason,
          token_regressive, created_at, updated_at
        )
        VALUES (?, NULL, NULL, 'workflow', 'implementation-delivery', 'title', 'summary', '[]',
          ?, 'workflow-default', ?, 1, NULL, 0, ?, ?)
        """,
        (
            f"writeback-{pattern_id}",
            json.dumps({"metadata": {"pattern_id": pattern_id}}),
            status,
            created_at.isoformat().replace("+00:00", "Z"),
            created_at.isoformat().replace("+00:00", "Z"),
        ),
    )


def _writeback_row(conn: sqlite3.Connection) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM improvement_writebacks LIMIT 1").fetchone()
    assert row is not None
    return row


def _count(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _snapshot_counts(conn: sqlite3.Connection) -> dict[str, int]:
    tables = [
        str(row[0])
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    ]
    return {table: _count(conn, table) for table in tables}
