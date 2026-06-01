from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal, cast

from services.learning_analysis import RecurringPattern
from services.learning_taxonomy import (
    IS_ACTIONABLE_SIGNAL,
    ConservatismPolicy,
    LearningSignalKind,
    impact_scope_for_signal,
)

_DEFAULT_POLICY_PATH = (
    Path(__file__).resolve().parents[1] / "config" / "learning" / "conservatism-policy.json"
)
_POLICY_KEYS = frozenset(
    {
        "version",
        "min_sample_size",
        "min_recurrence_count",
        "min_confidence",
        "cooling_period_days",
        "min_sample_size_for_trend",
        "per_signal_overrides",
    }
)
SkipReason = Literal[
    "below_sample",
    "below_recurrence",
    "below_confidence",
    "informational",
    "within_cooling_period",
]


def load_conservatism_policy(path: Path | str | None = None) -> ConservatismPolicy:
    """Load the operator-tunable policy and reject unknown top-level keys."""
    policy_path = Path(path) if path is not None else _DEFAULT_POLICY_PATH
    with policy_path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("conservatism-policy.json must contain a JSON object")
    unknown = sorted(set(payload) - _POLICY_KEYS)
    if unknown:
        raise ValueError(
            f"Unknown key {unknown[0]!r} in conservatism-policy.json; allowed: {sorted(_POLICY_KEYS)}"
        )
    overrides = payload.get("per_signal_overrides", {})
    if overrides is None:
        overrides = {}
    if not isinstance(overrides, dict):
        raise ValueError("per_signal_overrides must be an object")
    return ConservatismPolicy(
        min_sample_size=int(payload["min_sample_size"]),
        min_recurrence_count=int(payload["min_recurrence_count"]),
        min_confidence=float(payload["min_confidence"]),
        cooling_period_days=int(payload["cooling_period_days"]),
        min_sample_size_for_trend=int(payload["min_sample_size_for_trend"]),
        per_signal_overrides=cast(dict[str, dict[str, float | int]], overrides),
    )


def propose_from_pattern(
    conn: sqlite3.Connection,
    pattern: RecurringPattern,
    policy: ConservatismPolicy,
    *,
    actor: str = "learning_analysis",
) -> dict[str, Any] | None:
    if _classify_skip_reason(conn, pattern, policy) is not None:
        return None
    impact_scope = impact_scope_for_signal(pattern.signal_kind)
    layer_type = _layer_type_for_signal(pattern.signal_kind)
    proposed_change = _proposed_change(pattern)
    writeback_id = _insert_conservative_writeback(
        conn,
        run_id=pattern.evidence_run_ids[0] if pattern.evidence_run_ids else None,
        project_id=pattern.project_id,
        layer_type=layer_type,
        layer_key=pattern.scope_key,
        title=(
            f"Conservative improvement: {pattern.signal_kind} on "
            f"{pattern.scope_kind} {pattern.scope_key}"
        ),
        summary=pattern.summary,
        evidence_run_ids=pattern.evidence_run_ids,
        proposed_change=proposed_change,
        impact_scope=impact_scope,
        actor=actor,
    )
    return {
        "writeback_id": writeback_id,
        "pattern_id": pattern.pattern_id,
        "requires_approval": True,
    }


def propose_from_all_patterns(
    conn: sqlite3.Connection,
    patterns: list[RecurringPattern] | tuple[RecurringPattern, ...],
    policy: ConservatismPolicy,
    *,
    actor: str = "learning_analysis",
) -> dict[str, Any]:
    writebacks: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for pattern in patterns:
        result = propose_from_pattern(conn, pattern, policy, actor=actor)
        if result is not None:
            writebacks.append(result)
            continue
        reason = _classify_skip_reason(conn, pattern, policy)
        skipped.append(
            {
                "pattern_id": pattern.pattern_id,
                "signal_kind": pattern.signal_kind,
                "reason": reason or "within_cooling_period",
            }
        )
    return {
        "proposed_count": len(writebacks),
        "skipped_count": len(skipped),
        "writebacks": writebacks,
        "skipped": skipped,
        "policy_version": None,
    }


def _classify_skip_reason(
    conn: sqlite3.Connection,
    pattern: RecurringPattern,
    policy: ConservatismPolicy,
) -> SkipReason | None:
    if pattern.signal_kind not in IS_ACTIONABLE_SIGNAL:
        return "informational"
    min_sample, min_recurrence, min_confidence = _effective_thresholds(pattern.signal_kind, policy)
    if pattern.sample_size < min_sample:
        return "below_sample"
    if pattern.recurrence_count < min_recurrence:
        return "below_recurrence"
    if pattern.confidence < min_confidence:
        return "below_confidence"
    if _writeback_within_cooling_period(conn, pattern.pattern_id, policy.cooling_period_days):
        return "within_cooling_period"
    return None


def _writeback_within_cooling_period(
    conn: sqlite3.Connection,
    pattern_id: str,
    cooling_period_days: int,
) -> bool:
    if not _table_exists(conn, "improvement_writebacks"):
        return False
    cutoff = _now() - timedelta(days=cooling_period_days)
    row = conn.execute(
        """
        SELECT id
        FROM improvement_writebacks
        WHERE proposed_change_json LIKE ?
          AND created_at >= ?
        LIMIT 1
        """,
        (f'%"pattern_id": "{pattern_id}"%', _iso(cutoff)),
    ).fetchone()
    return row is not None


def _layer_type_for_signal(kind: LearningSignalKind) -> str:
    match kind:
        case "repeated_failure" | "weak_workflow":
            return "workflow"
        case "ignored_rule" | "standards_regression":
            return "standard"
        case "bloated_packet":
            return "packet"
        case "weak_prompt":
            return "prompt"
        case "route_misroute":
            return "route"
        case _:
            raise ValueError(f"Informational signal {kind!r} cannot emit writebacks")


def _insert_conservative_writeback(
    conn: sqlite3.Connection,
    *,
    run_id: str | None,
    project_id: str | None,
    layer_type: str,
    layer_key: str,
    title: str,
    summary: str,
    evidence_run_ids: tuple[str, ...],
    proposed_change: dict[str, Any],
    impact_scope: str,
    actor: str,
) -> str:
    _ensure_writeback_schema(conn)
    writeback_id = f"writeback-{uuid.uuid4()}"
    timestamp = _iso(_now())
    conn.execute(
        """
        INSERT INTO improvement_writebacks (
            id,
            run_id,
            project_id,
            layer_type,
            layer_key,
            title,
            summary,
            evidence_json,
            proposed_change_json,
            impact_scope,
            status,
            requires_approval,
            approval_reason,
            token_regressive,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending_approval', 1, ?, 0, ?, ?)
        """,
        (
            writeback_id,
            run_id,
            project_id,
            layer_type,
            layer_key,
            title,
            summary,
            _json(list(evidence_run_ids)),
            _json(proposed_change),
            impact_scope,
            "Learning-analysis proposals must be reviewed before mutation.",
            timestamp,
            timestamp,
        ),
    )
    conn.execute(
        """
        INSERT INTO improvement_writeback_events (
            id,
            writeback_id,
            run_id,
            event_type,
            from_status,
            to_status,
            actor,
            note,
            metadata_json,
            created_at
        )
        VALUES (?, ?, ?, 'proposed', NULL, 'pending_approval', ?, ?, ?, ?)
        """,
        (
            f"writeback-event-{uuid.uuid4()}",
            writeback_id,
            run_id,
            actor,
            summary,
            _json({"source": "learning_analysis"}),
            timestamp,
        ),
    )
    return writeback_id


def _effective_thresholds(
    signal_kind: LearningSignalKind,
    policy: ConservatismPolicy,
) -> tuple[int, int, float]:
    overrides = policy.per_signal_overrides.get(signal_kind, {})
    return (
        int(overrides.get("min_sample_size", policy.min_sample_size)),
        int(overrides.get("min_recurrence_count", policy.min_recurrence_count)),
        float(overrides.get("min_confidence", policy.min_confidence)),
    )


def _proposed_change(pattern: RecurringPattern) -> dict[str, Any]:
    return {
        "signal_kind": pattern.signal_kind,
        "scope_kind": pattern.scope_kind,
        "scope_key": pattern.scope_key,
        "suggested_remediation_class": pattern.suggested_remediation_class,
        "rationale": pattern.summary,
        "metadata": {
            "source": "learning_analysis",
            "pattern_id": pattern.pattern_id,
            "evidence_run_ids": list(pattern.evidence_run_ids),
            "sample_size": pattern.sample_size,
            "recurrence_count": pattern.recurrence_count,
            "confidence": pattern.confidence,
        },
    }


def _ensure_writeback_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS improvement_writebacks (
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
          updated_at TEXT NOT NULL,
          decision_note TEXT,
          decision_actor TEXT,
          decision_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS improvement_writeback_events (
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
        )
        """
    )


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True)


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
