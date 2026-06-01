from __future__ import annotations

import hashlib
import json
import sqlite3
import statistics
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol, cast

from services.learning_taxonomy import (
    IS_ACTIONABLE_SIGNAL,
    LEARNING_SIGNAL_KINDS,
    LearningSignalKind,
)

ScopeKind = str

_REPEATED_FAILURE_RECURRENCE_THRESHOLD = 3
_IGNORED_RULE_RECURRENCE_THRESHOLD = 2
_WEAK_PROMPT_SAMPLE_FLOOR = 5
_WEAK_PROMPT_MEAN_THRESHOLD = 0.5
_WEAK_WORKFLOW_SAMPLE_FLOOR = 5
_WEAK_WORKFLOW_FAILURE_RATE_THRESHOLD = 0.4
_BLOATED_PACKET_SAMPLE_FLOOR = 5
_BLOATED_PACKET_STDEV_MULTIPLIER = 2.0
_ROUTE_MISROUTE_RECURRENCE_FLOOR = 3
_ROUTE_MISROUTE_RATE_THRESHOLD = 0.4
_STANDARDS_REGRESSION_RECURRENCE_FLOOR = 2


@dataclass(frozen=True)
class RecurringPattern:
    pattern_id: str
    signal_kind: LearningSignalKind
    scope_kind: ScopeKind
    scope_key: str
    project_id: str | None
    sample_size: int
    recurrence_count: int
    confidence: float
    since: str
    summary: str
    evidence_run_ids: tuple[str, ...]
    suggested_remediation_class: str
    metadata: dict[str, Any] = field(default_factory=dict)


_DetectorFn = Callable[[sqlite3.Connection, str, str | None], list[RecurringPattern]]


class _Detector(Protocol):
    def __call__(
        self,
        conn: sqlite3.Connection,
        *,
        since: str,
        project_id: str | None,
    ) -> list[RecurringPattern]: ...


def _stable_pattern_id(
    *,
    signal_kind: str,
    scope_kind: str,
    scope_key: str,
    since_window_bucket: str,
) -> str:
    raw = "|".join((signal_kind, scope_kind, scope_key, since_window_bucket))
    return f"pattern-{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _bucket_window(since: str) -> str:
    """Return an ISO year-week bucket for an ISO timestamp or relative day offset."""
    return _parse_since(since).strftime("%G-W%V")


def _resolve_since(since: str | None) -> str:
    if since is None:
        return _format_ts(datetime.now(UTC) - timedelta(days=30))
    stripped = since.strip()
    if stripped.endswith("d") and stripped[:-1].isdigit():
        return _format_ts(datetime.now(UTC) - timedelta(days=int(stripped[:-1])))
    return stripped


def detect_recurring_patterns(
    conn: sqlite3.Connection,
    *,
    since: str | None,
    project_id: str | None,
    signal_kinds: Iterable[LearningSignalKind] | None = None,
) -> list[RecurringPattern]:
    patterns, _partial = detect_recurring_patterns_partial(
        conn,
        since=since,
        project_id=project_id,
        signal_kinds=signal_kinds,
    )
    return patterns


def detect_recurring_patterns_partial(
    conn: sqlite3.Connection,
    *,
    since: str | None,
    project_id: str | None,
    signal_kinds: Iterable[LearningSignalKind] | None = None,
) -> tuple[list[RecurringPattern], bool]:
    """Return patterns plus a partial flag when a detector hits a missing schema surface."""
    resolved_since = _resolve_since(since)
    requested = tuple(signal_kinds) if signal_kinds is not None else LEARNING_SIGNAL_KINDS
    patterns: list[RecurringPattern] = []
    partial = False
    for signal_kind in requested:
        if signal_kind not in IS_ACTIONABLE_SIGNAL:
            continue
        detector = DETECTORS.get(signal_kind)
        if detector is None:
            continue
        try:
            patterns.extend(detector(conn, since=resolved_since, project_id=project_id))
        except sqlite3.OperationalError:
            partial = True
    return patterns, partial


def _detect_repeated_failures(
    conn: sqlite3.Connection,
    *,
    since: str,
    project_id: str | None,
) -> list[RecurringPattern]:
    return _with_project_fallback(conn, _detect_repeated_failures_scoped, since, project_id)


def _detect_ignored_rules(
    conn: sqlite3.Connection,
    *,
    since: str,
    project_id: str | None,
) -> list[RecurringPattern]:
    return _with_project_fallback(conn, _detect_ignored_rules_scoped, since, project_id)


def _detect_bloated_packets(
    conn: sqlite3.Connection,
    *,
    since: str,
    project_id: str | None,
) -> list[RecurringPattern]:
    return _with_project_fallback(conn, _detect_bloated_packets_scoped, since, project_id)


def _detect_weak_prompts(
    conn: sqlite3.Connection,
    *,
    since: str,
    project_id: str | None,
) -> list[RecurringPattern]:
    return _with_project_fallback(conn, _detect_weak_prompts_scoped, since, project_id)


def _detect_weak_workflows(
    conn: sqlite3.Connection,
    *,
    since: str,
    project_id: str | None,
) -> list[RecurringPattern]:
    return _with_project_fallback(conn, _detect_weak_workflows_scoped, since, project_id)


def _detect_route_misroutes(
    conn: sqlite3.Connection,
    *,
    since: str,
    project_id: str | None,
) -> list[RecurringPattern]:
    return _with_project_fallback(conn, _detect_route_misroutes_scoped, since, project_id)


def _detect_standards_regression(
    conn: sqlite3.Connection,
    *,
    since: str,
    project_id: str | None,
) -> list[RecurringPattern]:
    return _with_project_fallback(conn, _detect_standards_regression_scoped, since, project_id)


DETECTORS: dict[LearningSignalKind, _Detector] = {
    "repeated_failure": _detect_repeated_failures,
    "ignored_rule": _detect_ignored_rules,
    "bloated_packet": _detect_bloated_packets,
    "weak_prompt": _detect_weak_prompts,
    "weak_workflow": _detect_weak_workflows,
    "route_misroute": _detect_route_misroutes,
    "standards_regression": _detect_standards_regression,
}


def _detect_repeated_failures_scoped(
    conn: sqlite3.Connection,
    since: str,
    project_id: str | None,
) -> list[RecurringPattern]:
    source = _success_finding_source(conn)
    if source is None:
        return []
    source_sql, run_expr, workflow_expr = source
    rows = _fetch_dicts(
        conn,
        f"""
        SELECT f.criterion_id AS criterion_id,
               COALESCE({workflow_expr}, '') AS workflow_key,
               COUNT(*) AS recurrence,
               COUNT(DISTINCT {run_expr}) AS sample_size,
               GROUP_CONCAT(DISTINCT {run_expr}) AS run_ids
        {source_sql}
        WHERE f.level = 'blocker'
          AND f.created_at >= ?
          {_project_clause("r", project_id)}
        GROUP BY f.criterion_id, COALESCE({workflow_expr}, '')
        HAVING COUNT(*) >= ?
        """,
        _params(since, project_id, _REPEATED_FAILURE_RECURRENCE_THRESHOLD),
    )
    return [
        _pattern(
            signal_kind="repeated_failure",
            scope_kind="criterion",
            scope_key=_str(row["criterion_id"]),
            project_id=project_id,
            sample_size=_int(row["sample_size"]),
            recurrence_count=_int(row["recurrence"]),
            confidence=_ratio(_int(row["recurrence"]), _int(row["sample_size"])),
            since=since,
            summary=(
                f"Criterion {_str(row['criterion_id'])!r} blocked {_int(row['recurrence'])} "
                f"runs of workflow {_str(row['workflow_key'])!r} in the scoped window."
            ),
            evidence_run_ids=_split_ids(row["run_ids"]),
            suggested_remediation_class="raise_blocker_priority",
            metadata={
                "workflow_key": _str(row["workflow_key"]),
                "scope_used": _scope_text(project_id),
            },
        )
        for row in rows
    ]


def _detect_ignored_rules_scoped(
    conn: sqlite3.Connection,
    since: str,
    project_id: str | None,
) -> list[RecurringPattern]:
    source = _success_finding_source(conn)
    if source is None:
        return []
    source_sql, run_expr, _workflow_expr = source
    rows = _fetch_dicts(
        conn,
        f"""
        SELECT f.criterion_id AS criterion_id,
               COUNT(DISTINCT {run_expr}) AS sample_size,
               COUNT(*) AS recurrence,
               GROUP_CONCAT(DISTINCT {run_expr}) AS run_ids
        {source_sql}
        WHERE f.level = 'blocker'
          AND COALESCE(f.resolution_status, 'open') = 'open'
          AND f.created_at >= ?
          {_project_clause("r", project_id)}
        GROUP BY f.criterion_id
        HAVING COUNT(DISTINCT {run_expr}) >= ?
        """,
        _params(since, project_id, _IGNORED_RULE_RECURRENCE_THRESHOLD),
    )
    return [
        _pattern(
            signal_kind="ignored_rule",
            scope_kind="criterion",
            scope_key=_str(row["criterion_id"]),
            project_id=project_id,
            sample_size=_int(row["sample_size"]),
            recurrence_count=_int(row["recurrence"]),
            confidence=_ratio(_int(row["recurrence"]), _int(row["sample_size"])),
            since=since,
            summary=(
                f"Criterion {_str(row['criterion_id'])!r} remained open across "
                f"{_int(row['sample_size'])} runs in the scoped window."
            ),
            evidence_run_ids=_split_ids(row["run_ids"]),
            suggested_remediation_class="raise_blocker_priority",
            metadata={"scope_used": _scope_text(project_id)},
        )
        for row in rows
    ]


def _detect_weak_prompts_scoped(
    conn: sqlite3.Connection,
    since: str,
    project_id: str | None,
) -> list[RecurringPattern]:
    if not _table_exists(conn, "prompts_used"):
        return []
    columns = _table_columns(conn, "prompts_used")
    prompt_key = _first_existing(
        columns, ("template_id", "prompt_id", "classification", "prompt_hash")
    )
    if prompt_key is None or "outcome_score" not in columns:
        return []
    run_col = "run_id" if "run_id" in columns else None
    join = ""
    where_project = ""
    if run_col and _table_exists(conn, "orchestration_runs"):
        join = f" LEFT JOIN orchestration_runs r ON r.id = p.{run_col}"
        where_project = _project_clause("r", project_id)
    elif project_id is not None:
        return []
    created_col = "created_at" if "created_at" in columns else None
    if created_col is None:
        return []
    run_expr = f"GROUP_CONCAT(DISTINCT p.{run_col})" if run_col else "''"
    rows = _fetch_dicts(
        conn,
        f"""
        SELECT p.{prompt_key} AS prompt_key,
               AVG(CAST(p.outcome_score AS REAL)) AS mean_score,
               COUNT(*) AS sample_size,
               {run_expr} AS run_ids
        FROM prompts_used p
        {join}
        WHERE p.outcome_score IS NOT NULL
          AND p.{created_col} >= ?
          {where_project}
        GROUP BY p.{prompt_key}
        HAVING COUNT(*) >= ? AND AVG(CAST(p.outcome_score AS REAL)) < ?
        """,
        _params(since, project_id if where_project else None, _WEAK_PROMPT_SAMPLE_FLOOR)
        + (_WEAK_PROMPT_MEAN_THRESHOLD,),
    )
    return [
        _pattern(
            signal_kind="weak_prompt",
            scope_kind="prompt",
            scope_key=_str(row["prompt_key"]),
            project_id=project_id,
            sample_size=_int(row["sample_size"]),
            recurrence_count=_int(row["sample_size"]),
            confidence=_clamp(1.0 - _float(row["mean_score"])),
            since=since,
            summary=(
                f"Prompt {_str(row['prompt_key'])!r} averaged "
                f"{_float(row['mean_score']):.2f} outcome score across "
                f"{_int(row['sample_size'])} samples in the scoped window."
            ),
            evidence_run_ids=_split_ids(row["run_ids"]),
            suggested_remediation_class="deprecate_prompt_or_revise",
            metadata={
                "mean_score": _float(row["mean_score"]),
                "scope_used": _scope_text(project_id),
            },
        )
        for row in rows
    ]


def _detect_weak_workflows_scoped(
    conn: sqlite3.Connection,
    since: str,
    project_id: str | None,
) -> list[RecurringPattern]:
    if not _table_exists(conn, "workflow_execution_reports"):
        return []
    join = ""
    where_project = ""
    if _table_exists(conn, "orchestration_runs"):
        join = " LEFT JOIN orchestration_runs r ON r.id = w.run_id"
        where_project = _project_clause("r", project_id)
    elif project_id is not None:
        return []
    rows = _fetch_dicts(
        conn,
        f"""
        SELECT w.workflow_key AS workflow_key,
               SUM(CASE WHEN w.status = 'failed' THEN 1 ELSE 0 END) AS failed,
               COUNT(*) AS sample_size,
               GROUP_CONCAT(DISTINCT w.run_id) AS run_ids
        FROM workflow_execution_reports w
        {join}
        WHERE w.created_at >= ?
          {where_project}
        GROUP BY w.workflow_key
        HAVING COUNT(*) >= ?
           AND CAST(SUM(CASE WHEN w.status = 'failed' THEN 1 ELSE 0 END) AS REAL) / COUNT(*) > ?
        """,
        _params(since, project_id if where_project else None, _WEAK_WORKFLOW_SAMPLE_FLOOR)
        + (_WEAK_WORKFLOW_FAILURE_RATE_THRESHOLD,),
    )
    return [
        _pattern(
            signal_kind="weak_workflow",
            scope_kind="workflow",
            scope_key=_str(row["workflow_key"]),
            project_id=project_id,
            sample_size=_int(row["sample_size"]),
            recurrence_count=_int(row["failed"]),
            confidence=_ratio(_int(row["failed"]), _int(row["sample_size"])),
            since=since,
            summary=(
                f"Workflow {_str(row['workflow_key'])!r} failed {_int(row['failed'])} of "
                f"{_int(row['sample_size'])} runs in the scoped window."
            ),
            evidence_run_ids=_split_ids(row["run_ids"]),
            suggested_remediation_class="tighten_validations_or_deprecate",
            metadata={"scope_used": _scope_text(project_id)},
        )
        for row in rows
    ]


def _detect_bloated_packets_scoped(
    conn: sqlite3.Connection,
    since: str,
    project_id: str | None,
) -> list[RecurringPattern]:
    if not _table_exists(conn, "briefing_packets") or not _table_exists(conn, "orchestration_runs"):
        return []
    packet_cols = _table_columns(conn, "briefing_packets")
    count_source = _first_existing(packet_cols, ("selected_context_packets_json", "sections_json"))
    if count_source is None:
        return []
    rows = _fetch_dicts(
        conn,
        f"""
        SELECT b.run_id AS run_id,
               COALESCE(b.workflow_key, r.workflow_key, '') AS workflow_key,
               b.{count_source} AS selected_context_packets_json
        FROM briefing_packets b
        INNER JOIN orchestration_runs r ON r.id = b.run_id
        WHERE b.created_at >= ?
          {_project_clause("r", project_id)}
          AND b.{count_source} IS NOT NULL
        """,
        _params(since, project_id),
    )
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        count = _json_array_length(row["selected_context_packets_json"])
        if count is None:
            continue
        item = {
            "run_id": _str(row["run_id"]),
            "workflow_key": _str(row["workflow_key"]),
            "count": count,
        }
        grouped.setdefault(item["workflow_key"], []).append(item)

    patterns: list[RecurringPattern] = []
    for workflow_key, items in grouped.items():
        if len(items) < _BLOATED_PACKET_SAMPLE_FLOOR:
            continue
        counts = [cast(int, item["count"]) for item in items]
        median = statistics.median(counts)
        stdev = statistics.pstdev(counts)
        threshold = median + (_BLOATED_PACKET_STDEV_MULTIPLIER * stdev)
        for item in items:
            count = cast(int, item["count"])
            if count <= threshold:
                continue
            run_id = _str(item["run_id"])
            patterns.append(
                _pattern(
                    signal_kind="bloated_packet",
                    scope_kind="packet",
                    scope_key=run_id,
                    project_id=project_id,
                    sample_size=len(items),
                    recurrence_count=1,
                    confidence=_clamp((count - median) / count),
                    since=since,
                    summary=(
                        f"Median packet for workflow {workflow_key!r} has {median:.0f} sections; "
                        f"this packet has {count} sections (> median + 2 stdev)."
                    ),
                    evidence_run_ids=(run_id,),
                    suggested_remediation_class="trim_packet_section",
                    metadata={
                        "workflow_key": workflow_key,
                        "median_sections": median,
                        "section_count": count,
                        "scope_used": _scope_text(project_id),
                    },
                )
            )
    return patterns


def _detect_route_misroutes_scoped(
    conn: sqlite3.Connection,
    since: str,
    project_id: str | None,
) -> list[RecurringPattern]:
    if not _table_exists(conn, "orchestration_runs"):
        return []
    source = _success_finding_source(conn)
    if source is None:
        return []
    source_sql, run_expr, _workflow_expr = source
    run_rows = _fetch_dicts(
        conn,
        f"""
        SELECT r.id AS run_id, r.workflow_key AS workflow_key, r.route_result_json AS route_result_json
        FROM orchestration_runs r
        WHERE r.created_at >= ?
          {_project_clause("r", project_id)}
          AND r.route_result_json IS NOT NULL
        """,
        _params(since, project_id),
    )
    blocker_rows = _fetch_dicts(
        conn,
        f"""
        SELECT DISTINCT {run_expr} AS run_id
        {source_sql}
        WHERE f.level = 'blocker'
          AND f.created_at >= ?
          {_project_clause("r", project_id)}
        """,
        _params(since, project_id),
    )
    blocker_run_ids = {_str(row["run_id"]) for row in blocker_rows}
    grouped: dict[str, dict[str, list[str]]] = {}
    for row in run_rows:
        workflow_key = _route_workflow_key(row["route_result_json"]) or _str(row["workflow_key"])
        if not workflow_key:
            continue
        group = grouped.setdefault(workflow_key, {"all": [], "blocked": []})
        run_id = _str(row["run_id"])
        group["all"].append(run_id)
        if run_id in blocker_run_ids:
            group["blocked"].append(run_id)

    patterns: list[RecurringPattern] = []
    for workflow_key, group in grouped.items():
        sample_size = len(group["all"])
        recurrence = len(group["blocked"])
        rate = _ratio(recurrence, sample_size)
        if recurrence < _ROUTE_MISROUTE_RECURRENCE_FLOOR or rate <= _ROUTE_MISROUTE_RATE_THRESHOLD:
            continue
        patterns.append(
            _pattern(
                signal_kind="route_misroute",
                scope_kind="route",
                scope_key=workflow_key,
                project_id=project_id,
                sample_size=sample_size,
                recurrence_count=recurrence,
                confidence=rate,
                since=since,
                summary=(
                    f"Route {workflow_key!r} led to blocker findings in {recurrence} of "
                    f"{sample_size} scoped runs."
                ),
                evidence_run_ids=tuple(sorted(group["blocked"])),
                suggested_remediation_class="tighten_route_hint_or_lower_priority",
                metadata={"scope_used": _scope_text(project_id)},
            )
        )
    return patterns


def _detect_standards_regression_scoped(
    conn: sqlite3.Connection,
    since: str,
    project_id: str | None,
) -> list[RecurringPattern]:
    if not _table_exists(conn, "standards_delta_items"):
        return []
    join = ""
    where_project = ""
    if _table_exists(conn, "standards_health_snapshots"):
        join = " LEFT JOIN standards_health_snapshots s ON s.id = d.snapshot_id"
        where_project = _project_clause("s", project_id)
    elif project_id is not None:
        return []
    rows = _fetch_dicts(
        conn,
        f"""
        SELECT d.standard_id AS standard_id,
               COUNT(DISTINCT d.snapshot_id) AS recurrence,
               GROUP_CONCAT(DISTINCT d.snapshot_id) AS snapshot_ids
        FROM standards_delta_items d
        {join}
        WHERE d.priority_bucket = 'regressed'
          AND d.created_at >= ?
          {where_project}
        GROUP BY d.standard_id
        HAVING COUNT(DISTINCT d.snapshot_id) >= ?
        """,
        _params(
            since, project_id if where_project else None, _STANDARDS_REGRESSION_RECURRENCE_FLOOR
        ),
    )
    return [
        _pattern(
            signal_kind="standards_regression",
            scope_kind="standard",
            scope_key=_str(row["standard_id"]),
            project_id=project_id,
            sample_size=_int(row["recurrence"]),
            recurrence_count=_int(row["recurrence"]),
            confidence=1.0,
            since=since,
            summary=(
                f"Standard {_str(row['standard_id'])!r} regressed in "
                f"{_int(row['recurrence'])} snapshots in the scoped window."
            ),
            evidence_run_ids=(),
            suggested_remediation_class="prioritize_backfill",
            metadata={
                "snapshot_ids": _split_ids(row["snapshot_ids"]),
                "scope_used": _scope_text(project_id),
            },
        )
        for row in rows
    ]


def _success_finding_source(conn: sqlite3.Connection) -> tuple[str, str, str] | None:
    if not _table_exists(conn, "success_criteria_findings"):
        return None
    finding_columns = _table_columns(conn, "success_criteria_findings")
    if "run_id" in finding_columns:
        workflow_expr = "f.workflow_key" if "workflow_key" in finding_columns else "r.workflow_key"
        return (
            "FROM success_criteria_findings f INNER JOIN orchestration_runs r ON r.id = f.run_id ",
            "f.run_id",
            workflow_expr,
        )
    if "evaluation_id" in finding_columns and _table_exists(conn, "success_criteria_evaluations"):
        return (
            "FROM success_criteria_findings f "
            "INNER JOIN success_criteria_evaluations e ON e.id = f.evaluation_id "
            "LEFT JOIN orchestration_runs r ON r.id = e.run_id ",
            "e.run_id",
            "r.workflow_key",
        )
    return None


def _with_project_fallback(
    conn: sqlite3.Connection,
    detector: _DetectorFn,
    since: str,
    project_id: str | None,
) -> list[RecurringPattern]:
    scoped = detector(conn, since, project_id)
    if project_id is None or scoped:
        return scoped
    fallback = detector(conn, since, None)
    return [
        replace(
            pattern,
            metadata={
                **pattern.metadata,
                "requested_project_id": project_id,
                "scope_fallback": "cross-project",
                "scope_used": "cross-project",
            },
        )
        for pattern in fallback
    ]


def _pattern(
    *,
    signal_kind: LearningSignalKind,
    scope_kind: ScopeKind,
    scope_key: str,
    project_id: str | None,
    sample_size: int,
    recurrence_count: int,
    confidence: float,
    since: str,
    summary: str,
    evidence_run_ids: tuple[str, ...],
    suggested_remediation_class: str,
    metadata: dict[str, Any],
) -> RecurringPattern:
    return RecurringPattern(
        pattern_id=_stable_pattern_id(
            signal_kind=signal_kind,
            scope_kind=scope_kind,
            scope_key=scope_key,
            since_window_bucket=_bucket_window(since),
        ),
        signal_kind=signal_kind,
        scope_kind=scope_kind,
        scope_key=scope_key,
        project_id=project_id,
        sample_size=sample_size,
        recurrence_count=recurrence_count,
        confidence=_clamp(confidence),
        since=since,
        summary=summary,
        evidence_run_ids=evidence_run_ids,
        suggested_remediation_class=suggested_remediation_class,
        metadata=metadata,
    )


def _fetch_dicts(
    conn: sqlite3.Connection,
    sql: str,
    params: tuple[Any, ...],
) -> list[dict[str, Any]]:
    cursor = conn.execute(sql, params)
    names = [column[0] for column in cursor.description or ()]
    return [dict(zip(names, row, strict=False)) for row in cursor.fetchall()]


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


def _params(since: str, project_id: str | None, *extra: Any) -> tuple[Any, ...]:
    values: tuple[Any, ...] = (since,)
    if project_id is not None:
        values += (project_id,)
    return values + extra


def _parse_since(since: str) -> datetime:
    resolved = _resolve_since(since)
    normalized = resolved.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _format_ts(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _split_ids(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    return tuple(item for item in str(value).split(",") if item)


def _json_array_length(value: object) -> int | None:
    if value is None:
        return None
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, list):
        return len(parsed)
    return None


def _route_workflow_key(value: object) -> str | None:
    if value is None:
        return None
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    workflow_key = parsed.get("workflow_key")
    if isinstance(workflow_key, str) and workflow_key:
        return workflow_key
    return None


def _scope_text(project_id: str | None) -> str:
    if project_id is None:
        return "cross-project"
    return f"project:{project_id}"


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return _clamp(numerator / denominator)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


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
