from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, cast

from services.aios_cli import _no_learning_reason
from services.learning_taxonomy import LEARNING_SIGNAL_KINDS, ConservatismPolicy, LearningSignalKind

AssetKind = Literal["prompt", "skill", "workflow", "standard", "route"]
RollupScope = Literal["workflow", "prompt", "skill"]
Trend = Literal["improving", "flat", "regressing", "insufficient_data"]

_DEFAULT_POLICY = ConservatismPolicy(
    min_sample_size=5,
    min_recurrence_count=3,
    min_confidence=0.6,
    cooling_period_days=14,
    min_sample_size_for_trend=10,
)
_TREND_EPSILON = 0.05


@dataclass(frozen=True)
class AssetEvidenceDelta:
    asset_kind: AssetKind
    asset_key: str
    delta_sample_size: int
    delta_success_count: int
    delta_blocker_count: int


@dataclass(frozen=True)
class ProposalCreated:
    writeback_id: str
    signal_kind: LearningSignalKind | None
    requires_approval: bool
    status: str


@dataclass(frozen=True)
class LearningImpactPerRun:
    run_id: str
    workflow_key: str | None
    signals_emitted: tuple[LearningSignalKind, ...]
    assets_evidenced: tuple[AssetEvidenceDelta, ...]
    proposals_created: tuple[ProposalCreated, ...]
    learning_events_persisted: int
    no_learning_reason: str | None


@dataclass(frozen=True)
class LearningImpactRollup:
    scope: RollupScope
    key: str
    since: str
    sample_size: int
    rework_rate_30d: float | None
    rework_rate_90d: float | None
    success_rate_30d: float | None
    blocker_rate_30d: float | None
    trend: Trend
    rationale: str
    project_id: str | None


def build_per_run_impact(
    conn: sqlite3.Connection,
    *,
    run_id: str,
) -> LearningImpactPerRun | None:
    run = _load_run(conn, run_id)
    if run is None:
        return None
    signals = _load_signals_for_run(conn, run_id)
    learning_events_count = _count_learning_events(conn, run_id)
    assets = _load_assets_evidenced_for_run(conn, run)
    proposals = _load_proposals_for_run(conn, run_id)
    reason = None
    if not signals and not proposals:
        reason = _no_learning_reason(conn, run)
    return LearningImpactPerRun(
        run_id=run_id,
        workflow_key=_optional_str(run.get("workflow_key")),
        signals_emitted=signals,
        assets_evidenced=assets,
        proposals_created=proposals,
        learning_events_persisted=learning_events_count,
        no_learning_reason=reason,
    )


def build_rollup(
    conn: sqlite3.Connection,
    *,
    scope: RollupScope,
    key: str,
    since: str,
    project_id: str | None = None,
    min_sample_size_for_trend: int = _DEFAULT_POLICY.min_sample_size_for_trend,
) -> LearningImpactRollup:
    """Build an asset trend rollup.

    Prompt and skill rollups use outcome quality as a rework proxy because those assets do not
    persist explicit rework events yet.
    """
    since_ts = _resolve_since(since)
    recent_cutoff = _format_ts(_parse_ts(since_ts) - timedelta(days=30))
    prior_cutoff = _format_ts(_parse_ts(since_ts) - timedelta(days=90))
    if scope == "workflow":
        recent = _workflow_window(conn, key, since_ts, recent_cutoff, project_id)
        prior = _workflow_window(conn, key, recent_cutoff, prior_cutoff, project_id)
        blocker_rate = _workflow_blocker_rate(conn, key, since_ts, recent_cutoff, project_id)
        success_rate = _success_rate(recent.success_count, recent.sample_size)
    elif scope == "prompt":
        recent = _prompt_window(conn, key, since_ts, recent_cutoff, project_id)
        prior = _prompt_window(conn, key, recent_cutoff, prior_cutoff, project_id)
        blocker_rate = None
        success_rate = _success_rate(recent.success_count, recent.sample_size)
    else:
        recent = _skill_window(conn, key, since_ts, recent_cutoff, project_id)
        prior = _skill_window(conn, key, recent_cutoff, prior_cutoff, project_id)
        blocker_rate = None
        success_rate = _success_rate(recent.success_count, recent.sample_size)
    recent_rate = _rate(recent.rework_count, recent.sample_size)
    prior_rate = _rate(prior.rework_count, prior.sample_size)
    trend, rationale = _trend_from_rates(
        recent_rate=recent_rate or 0.0,
        prior_rate=prior_rate or 0.0,
        sample_size=recent.sample_size,
        min_sample_size_for_trend=min_sample_size_for_trend,
    )
    return LearningImpactRollup(
        scope=scope,
        key=key,
        since=since_ts,
        sample_size=recent.sample_size,
        rework_rate_30d=recent_rate,
        rework_rate_90d=prior_rate,
        success_rate_30d=success_rate,
        blocker_rate_30d=blocker_rate,
        trend=trend,
        rationale=rationale,
        project_id=project_id,
    )


def _trend_from_rates(
    *,
    recent_rate: float,
    prior_rate: float,
    sample_size: int,
    min_sample_size_for_trend: int = _DEFAULT_POLICY.min_sample_size_for_trend,
) -> tuple[Trend, str]:
    if sample_size < min_sample_size_for_trend:
        return (
            "insufficient_data",
            (
                f"sample_size={sample_size} below trend threshold "
                f"{min_sample_size_for_trend}; rate {recent_rate:.2f} not reliable."
            ),
        )
    if recent_rate < prior_rate - _TREND_EPSILON:
        return (
            "improving",
            f"rework_rate dropped {prior_rate:.2f} -> {recent_rate:.2f} over sample_size={sample_size}",
        )
    if recent_rate > prior_rate + _TREND_EPSILON:
        return (
            "regressing",
            f"rework_rate rose {prior_rate:.2f} -> {recent_rate:.2f} over sample_size={sample_size}",
        )
    return (
        "flat",
        f"rework_rate stable at {recent_rate:.2f} over sample_size={sample_size}",
    )


@dataclass(frozen=True)
class _WindowStats:
    sample_size: int
    success_count: int
    rework_count: int


def _load_run(conn: sqlite3.Connection, run_id: str) -> dict[str, Any] | None:
    if not _table_exists(conn, "orchestration_runs"):
        return None
    row = _fetch_one(
        conn,
        "SELECT * FROM orchestration_runs WHERE id = ?",
        (run_id,),
    )
    return row


def _load_signals_for_run(
    conn: sqlite3.Connection,
    run_id: str,
) -> tuple[LearningSignalKind, ...]:
    if not _table_exists(conn, "workflow_learning_events"):
        return ()
    columns = _table_columns(conn, "workflow_learning_events")
    if "signal_kind" not in columns:
        return ()
    rows = _fetch_all(
        conn,
        """
        SELECT signal_kind
        FROM workflow_learning_events
        WHERE run_id = ? AND signal_kind IS NOT NULL
        ORDER BY created_at, id
        """,
        (run_id,),
    )
    signals: list[LearningSignalKind] = []
    for row in rows:
        signal = row.get("signal_kind")
        if signal in LEARNING_SIGNAL_KINDS and signal not in signals:
            signals.append(cast(LearningSignalKind, signal))
    return tuple(signals)


def _count_learning_events(conn: sqlite3.Connection, run_id: str) -> int:
    if not _table_exists(conn, "workflow_learning_events"):
        return 0
    return _int(
        _fetch_scalar(
            conn,
            "SELECT COUNT(*) FROM workflow_learning_events WHERE run_id = ?",
            (run_id,),
        )
    )


def _load_assets_evidenced_for_run(
    conn: sqlite3.Connection,
    run: dict[str, Any],
) -> tuple[AssetEvidenceDelta, ...]:
    run_id = _str(run["id"])
    workflow_key = _optional_str(run.get("workflow_key"))
    blocker_count = _blocker_count_for_run(conn, run_id)
    evaluation = _latest_agentize_evaluation(conn, run_id)
    success = _run_success_count(evaluation)
    assets: list[AssetEvidenceDelta] = []
    if workflow_key:
        assets.append(
            AssetEvidenceDelta(
                asset_kind="workflow",
                asset_key=workflow_key,
                delta_sample_size=1,
                delta_success_count=success,
                delta_blocker_count=blocker_count,
            )
        )
    assets.extend(_prompt_assets(conn, run_id))
    if evaluation:
        for skill_key in _json_keys(
            evaluation.get("selected_skills_json"), key_names=("key", "id", "name")
        ):
            assets.append(_asset("skill", skill_key, success, blocker_count))
        for standard_key in _json_keys(
            evaluation.get("selected_standards_json"), key_names=("standard_id", "id", "key")
        ):
            assets.append(_asset("standard", standard_key, success, blocker_count))
    route_key = _route_key(run.get("route_result_json"))
    if route_key:
        assets.append(_asset("route", route_key, success, blocker_count))
    return tuple(assets)


def _load_proposals_for_run(
    conn: sqlite3.Connection,
    run_id: str,
) -> tuple[ProposalCreated, ...]:
    if not _table_exists(conn, "improvement_writebacks"):
        return ()
    columns = _table_columns(conn, "improvement_writebacks")
    json_column = "metadata_json" if "metadata_json" in columns else "proposed_change_json"
    rows = _fetch_all(
        conn,
        f"""
        SELECT id, status, requires_approval, {json_column} AS payload_json
        FROM improvement_writebacks
        WHERE run_id = ?
        ORDER BY created_at, id
        """,
        (run_id,),
    )
    proposals: list[ProposalCreated] = []
    for row in rows:
        proposals.append(
            ProposalCreated(
                writeback_id=_str(row["id"]),
                signal_kind=_signal_from_json(row.get("payload_json")),
                requires_approval=bool(_int(row.get("requires_approval"))),
                status=_str(row["status"]),
            )
        )
    return tuple(proposals)


def _workflow_window(
    conn: sqlite3.Connection,
    key: str,
    upper: str,
    lower: str,
    project_id: str | None,
) -> _WindowStats:
    if not _table_exists(conn, "workflow_execution_reports"):
        return _WindowStats(0, 0, 0)
    join = ""
    project_clause = ""
    if project_id is not None:
        if not _table_exists(conn, "orchestration_runs"):
            return _WindowStats(0, 0, 0)
        join = " INNER JOIN orchestration_runs r ON r.id = w.run_id"
        project_clause = "AND r.project_id = ?"
    rows = _fetch_all(
        conn,
        f"""
        SELECT w.status AS status
        FROM workflow_execution_reports w
        {join}
        WHERE w.workflow_key = ?
          AND w.created_at >= ?
          AND w.created_at < ?
          {project_clause}
        """,
        (key, lower, upper) if project_id is None else (key, lower, upper, project_id),
    )
    sample_size = len(rows)
    rework_count = sum(1 for row in rows if row.get("status") == "failed")
    success_count = sum(1 for row in rows if row.get("status") in {"completed", "succeeded"})
    return _WindowStats(sample_size, success_count, rework_count)


def _prompt_window(
    conn: sqlite3.Connection,
    key: str,
    upper: str,
    lower: str,
    project_id: str | None,
) -> _WindowStats:
    if not _table_exists(conn, "prompts_used"):
        return _WindowStats(0, 0, 0)
    columns = _table_columns(conn, "prompts_used")
    prompt_column = _first_existing(
        columns, ("template_id", "prompt_id", "classification", "prompt_hash")
    )
    if prompt_column is None or "outcome_score" not in columns or "created_at" not in columns:
        return _WindowStats(0, 0, 0)
    join = ""
    project_clause = ""
    params: tuple[Any, ...]
    if project_id is not None:
        if "run_id" not in columns or not _table_exists(conn, "orchestration_runs"):
            return _WindowStats(0, 0, 0)
        join = " INNER JOIN orchestration_runs r ON r.id = p.run_id"
        project_clause = "AND r.project_id = ?"
        params = (key, lower, upper, project_id)
    else:
        params = (key, lower, upper)
    rows = _fetch_all(
        conn,
        f"""
        SELECT p.outcome_score AS outcome_score
        FROM prompts_used p
        {join}
        WHERE p.{prompt_column} = ?
          AND p.created_at >= ?
          AND p.created_at < ?
          {project_clause}
        """,
        params,
    )
    scores = [
        _float(row.get("outcome_score")) for row in rows if row.get("outcome_score") is not None
    ]
    sample_size = len(scores)
    success_count = sum(1 for score in scores if score >= 0.5)
    rework_count = sample_size - success_count
    return _WindowStats(sample_size, success_count, rework_count)


def _skill_window(
    conn: sqlite3.Connection,
    key: str,
    upper: str,
    lower: str,
    project_id: str | None,
) -> _WindowStats:
    if not _table_exists(conn, "agentize_evaluations"):
        return _WindowStats(0, 0, 0)
    columns = _table_columns(conn, "agentize_evaluations")
    if "selected_skills_json" not in columns or "created_at" not in columns:
        return _WindowStats(0, 0, 0)
    join = ""
    project_clause = ""
    params: tuple[Any, ...]
    if project_id is not None:
        if "run_id" not in columns or not _table_exists(conn, "orchestration_runs"):
            return _WindowStats(0, 0, 0)
        join = " INNER JOIN orchestration_runs r ON r.id = a.run_id"
        project_clause = "AND r.project_id = ?"
        params = (lower, upper, project_id)
    else:
        params = (lower, upper)
    rows = _fetch_all(
        conn,
        f"""
        SELECT a.outcome_quality AS outcome_quality, a.selected_skills_json AS selected_skills_json
        FROM agentize_evaluations a
        {join}
        WHERE a.created_at >= ?
          AND a.created_at < ?
          {project_clause}
        """,
        params,
    )
    matched = [
        row
        for row in rows
        if key in _json_keys(row.get("selected_skills_json"), key_names=("key", "id", "name"))
    ]
    sample_size = len(matched)
    success_count = sum(1 for row in matched if _float(row.get("outcome_quality")) >= 3.0)
    rework_count = sample_size - success_count
    return _WindowStats(sample_size, success_count, rework_count)


def _workflow_blocker_rate(
    conn: sqlite3.Connection,
    workflow_key: str,
    upper: str,
    lower: str,
    project_id: str | None,
) -> float | None:
    if not _table_exists(conn, "success_criteria_findings"):
        return None
    source = _success_finding_source(conn)
    if source is None:
        return None
    source_sql, run_expr, workflow_expr = source
    rows = _fetch_all(
        conn,
        f"""
        SELECT DISTINCT {run_expr} AS run_id
        {source_sql}
        WHERE f.level = 'blocker'
          AND COALESCE({workflow_expr}, '') = ?
          AND f.created_at >= ?
          AND f.created_at < ?
          {_project_clause("r", project_id)}
        """,
        (workflow_key, lower, upper)
        if project_id is None
        else (workflow_key, lower, upper, project_id),
    )
    sample = _workflow_window(conn, workflow_key, upper, lower, project_id).sample_size
    return _rate(len(rows), sample)


def _latest_agentize_evaluation(conn: sqlite3.Connection, run_id: str) -> dict[str, Any] | None:
    if not _table_exists(conn, "agentize_evaluations"):
        return None
    columns = _table_columns(conn, "agentize_evaluations")
    if "run_id" not in columns:
        return None
    return _fetch_one(
        conn,
        """
        SELECT *
        FROM agentize_evaluations
        WHERE run_id = ?
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (run_id,),
    )


def _prompt_assets(conn: sqlite3.Connection, run_id: str) -> tuple[AssetEvidenceDelta, ...]:
    if not _table_exists(conn, "prompts_used"):
        return ()
    columns = _table_columns(conn, "prompts_used")
    if "run_id" not in columns:
        return ()
    key_column = _first_existing(
        columns, ("template_id", "prompt_id", "classification", "prompt_hash")
    )
    if key_column is None:
        return ()
    score_column = "outcome_score" if "outcome_score" in columns else None
    score_expr = f", {score_column} AS outcome_score" if score_column else ", NULL AS outcome_score"
    rows = _fetch_all(
        conn,
        f"""
        SELECT {key_column} AS asset_key{score_expr}
        FROM prompts_used
        WHERE run_id = ?
        ORDER BY id
        """,
        (run_id,),
    )
    return tuple(
        AssetEvidenceDelta(
            asset_kind="prompt",
            asset_key=_str(row["asset_key"]),
            delta_sample_size=1,
            delta_success_count=1 if _float(row.get("outcome_score")) >= 0.5 else 0,
            delta_blocker_count=0,
        )
        for row in rows
        if _str(row["asset_key"])
    )


def _blocker_count_for_run(conn: sqlite3.Connection, run_id: str) -> int:
    source = _success_finding_source(conn)
    if source is None:
        return 0
    source_sql, run_expr, _workflow_expr = source
    return _int(
        _fetch_scalar(
            conn,
            f"""
            SELECT COUNT(*)
            {source_sql}
            WHERE {run_expr} = ? AND f.level = 'blocker'
            """,
            (run_id,),
        )
    )


def _success_finding_source(conn: sqlite3.Connection) -> tuple[str, str, str] | None:
    if not _table_exists(conn, "success_criteria_findings"):
        return None
    columns = _table_columns(conn, "success_criteria_findings")
    if "run_id" in columns and _table_exists(conn, "orchestration_runs"):
        workflow_expr = "f.workflow_key" if "workflow_key" in columns else "r.workflow_key"
        return (
            "FROM success_criteria_findings f INNER JOIN orchestration_runs r ON r.id = f.run_id ",
            "f.run_id",
            workflow_expr,
        )
    if "evaluation_id" in columns and _table_exists(conn, "success_criteria_evaluations"):
        return (
            "FROM success_criteria_findings f "
            "INNER JOIN success_criteria_evaluations e ON e.id = f.evaluation_id "
            "LEFT JOIN orchestration_runs r ON r.id = e.run_id ",
            "e.run_id",
            "r.workflow_key",
        )
    return None


def _run_success_count(evaluation: dict[str, Any] | None) -> int:
    if evaluation is None:
        return 0
    if _int(evaluation.get("tests_passed")) > 0:
        return 1
    return 1 if _float(evaluation.get("outcome_quality")) >= 3.0 else 0


def _asset(
    asset_kind: AssetKind,
    asset_key: str,
    success_count: int,
    blocker_count: int,
) -> AssetEvidenceDelta:
    return AssetEvidenceDelta(
        asset_kind=asset_kind,
        asset_key=asset_key,
        delta_sample_size=1,
        delta_success_count=success_count,
        delta_blocker_count=blocker_count,
    )


def _json_keys(value: object, *, key_names: tuple[str, ...]) -> tuple[str, ...]:
    parsed = _json_loads(value)
    if not isinstance(parsed, list):
        return ()
    keys: list[str] = []
    for item in parsed:
        if isinstance(item, str):
            keys.append(item)
            continue
        if not isinstance(item, dict):
            continue
        for key_name in key_names:
            item_value = item.get(key_name)
            if isinstance(item_value, str) and item_value:
                keys.append(item_value)
                break
    return tuple(keys)


def _route_key(value: object) -> str | None:
    parsed = _json_loads(value)
    if not isinstance(parsed, dict):
        return None
    workflow_key = parsed.get("workflow_key")
    if isinstance(workflow_key, str) and workflow_key:
        return workflow_key
    return None


def _signal_from_json(value: object) -> LearningSignalKind | None:
    parsed = _json_loads(value)
    if not isinstance(parsed, dict):
        return None
    for key in ("signal_kind", "learning_signal_kind"):
        signal = parsed.get(key)
        if signal in LEARNING_SIGNAL_KINDS:
            return cast(LearningSignalKind, signal)
    source = parsed.get("source")
    if source == "learning_analysis":
        return "compounding_gain"
    return None


def _json_loads(value: object) -> object:
    if value is None:
        return None
    try:
        return json.loads(str(value))
    except json.JSONDecodeError:
        return None


def _resolve_since(since: str) -> str:
    stripped = since.strip()
    if stripped.endswith("d") and stripped[:-1].isdigit():
        return _format_ts(datetime.now(UTC) - timedelta(days=int(stripped[:-1])))
    return stripped


def _parse_ts(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _format_ts(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rate(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return max(0.0, min(1.0, numerator / denominator))


def _success_rate(success_count: int, sample_size: int) -> float | None:
    return _rate(success_count, sample_size)


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    if not _table_exists(conn, table_name):
        return set()
    return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}


def _first_existing(columns: set[str], candidates: tuple[str, ...]) -> str | None:
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None


def _project_clause(alias: str, project_id: str | None) -> str:
    if project_id is None:
        return ""
    return f"AND {alias}.project_id = ?"


def _fetch_one(
    conn: sqlite3.Connection,
    sql: str,
    params: tuple[Any, ...],
) -> dict[str, Any] | None:
    rows = _fetch_all(conn, sql, params)
    return rows[0] if rows else None


def _fetch_all(
    conn: sqlite3.Connection,
    sql: str,
    params: tuple[Any, ...],
) -> list[dict[str, Any]]:
    cursor = conn.execute(sql, params)
    names = [column[0] for column in cursor.description or ()]
    return [dict(zip(names, row, strict=False)) for row in cursor.fetchall()]


def _fetch_scalar(
    conn: sqlite3.Connection,
    sql: str,
    params: tuple[Any, ...],
) -> object:
    row = conn.execute(sql, params).fetchone()
    if row is None:
        return None
    return row[0]


def _snapshot_counts(conn: sqlite3.Connection) -> dict[str, int]:
    tables = [
        str(row[0])
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    ]
    return {
        table: _int(_fetch_scalar(conn, f"SELECT COUNT(*) FROM {table}", ())) for table in tables
    }


def _int(value: object) -> int:
    if value is None:
        return 0
    return int(str(value))


def _float(value: object) -> float:
    if value is None:
        return 0.0
    return float(str(value))


def _str(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _optional_str(value: object) -> str | None:
    text = _str(value)
    return text or None


__all__ = [
    "AssetEvidenceDelta",
    "LearningImpactPerRun",
    "LearningImpactRollup",
    "ProposalCreated",
    "build_per_run_impact",
    "build_rollup",
]
