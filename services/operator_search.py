from __future__ import annotations

import logging
import math
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Final, Literal, get_args

logger = logging.getLogger(__name__)

EntityKind = Literal[
    "run",
    "packet",
    "writeback",
    "finding",
    "prompt_template",
    "prompt_use",
    "skill",
    "workflow",
    "knowledge_object",
    "route_decision",
    "delta_item",
    "backfill_task",
    "automation",
    "experiment",
    "divergent_run",
    "learning_pattern",
    "promotion_lifecycle_item",
]

ENTITY_KINDS: tuple[EntityKind, ...] = get_args(EntityKind)
MAX_QUERY_LENGTH: Final[int] = 200
DEFAULT_LIMIT: Final[int] = 50
MAX_LIMIT: Final[int] = 200
PER_KIND_CAP: Final[int] = 20
RECENCY_BOOST_HALF_LIFE_DAYS: Final[float] = 14.0
EXACT_KEY_BOOST: Final[float] = 0.3


@dataclass(frozen=True)
class OperatorSearchHit:
    kind: EntityKind
    id: str
    title: str
    summary: str
    project_id: str | None
    score: float
    source_table: str
    last_updated_at: str
    drill_down_path: str
    metadata: dict[str, Any] = field(default_factory=dict)


def _safe_table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table_name,),
    ).fetchone()
    return row is not None


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    if not _safe_table_exists(conn, table_name):
        return set()
    return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}


def _drill_down_for(
    kind: EntityKind,
    *,
    id_: str,
    project_id: str | None = None,
    run_id: str | None = None,
) -> str:
    if kind == "run":
        return f"/runs/{id_}"
    if kind == "packet":
        return f"/control?packet={id_}"
    if kind == "writeback":
        return f"/writebacks#{id_}"
    if kind == "finding":
        return f"/runs/{run_id or id_}?finding={id_}"
    if kind == "prompt_template":
        return f"/prompts#{id_}"
    if kind == "prompt_use":
        return f"/prompts#use-{id_}"
    if kind == "skill":
        return f"/workflows?skill={id_}"
    if kind == "workflow":
        return f"/workflows#{id_}"
    if kind == "knowledge_object":
        return f"/knowledge#{id_}"
    if kind == "route_decision":
        return f"/runs/{run_id or id_}?route={id_}"
    if kind == "delta_item":
        return f"/projects/{project_id}?delta={id_}" if project_id else f"/projects?delta={id_}"
    if kind == "backfill_task":
        return (
            f"/projects/{project_id}?backfill={id_}" if project_id else f"/projects?backfill={id_}"
        )
    if kind == "automation":
        return f"/automations#{id_}"
    if kind == "experiment":
        return f"/experiments#{id_}"
    if kind == "divergent_run":
        return f"/divergent#{id_}"
    if kind == "learning_pattern":
        return f"/control?pattern={id_}"
    if kind == "promotion_lifecycle_item":
        return f"/workflows?promotion={id_}"
    raise ValueError(f"Unsupported entity kind: {kind}")


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _score_hit(
    *,
    query: str,
    title: str,
    summary: str,
    key: str,
    last_updated_at: str,
    now: datetime,
) -> float:
    normalized = query.strip().lower()
    base = 0.0
    if normalized:
        if normalized in title.lower():
            base += 0.5
        if normalized in summary.lower():
            base += 0.3
        if normalized == key.lower():
            base += EXACT_KEY_BOOST
    parsed = _parse_time(last_updated_at)
    recency = 0.0
    if parsed is not None:
        age_seconds = max(0.0, (now - parsed).total_seconds())
        age_days = age_seconds / 86400
        recency = 0.2 * math.pow(0.5, age_days / RECENCY_BOOST_HALF_LIFE_DAYS)
    return round(min(base + recency, 1.0), 6)


def _text_or_empty(value: Any) -> str:
    return "" if value is None else str(value)


def _last_updated_expr(columns: set[str]) -> str:
    if "updated_at" in columns and "created_at" in columns:
        return "COALESCE(updated_at, created_at)"
    if "updated_at" in columns:
        return "updated_at"
    if "created_at" in columns:
        return "created_at"
    return "''"


def _selectable(columns: set[str], column: str, fallback: str = "''") -> str:
    return column if column in columns else f"{fallback} AS {column}"


def _matches_query(query: str, *values: str) -> bool:
    if not query:
        return True
    normalized = query.lower()
    return any(normalized in value.lower() for value in values)


def _project_allowed(project_id: str | None, row_project_id: str | None) -> bool:
    return project_id is None or row_project_id is None or row_project_id == project_id


def _make_hit(
    *,
    kind: EntityKind,
    id_: str,
    title: str,
    summary: str,
    project_id: str | None,
    source_table: str,
    last_updated_at: str,
    query: str,
    key: str,
    now: datetime,
    metadata: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> OperatorSearchHit:
    return OperatorSearchHit(
        kind=kind,
        id=id_,
        title=title or id_,
        summary=summary,
        project_id=project_id,
        score=_score_hit(
            query=query,
            title=title or id_,
            summary=summary,
            key=key or id_,
            last_updated_at=last_updated_at,
            now=now,
        ),
        source_table=source_table,
        last_updated_at=last_updated_at,
        drill_down_path=_drill_down_for(kind, id_=id_, project_id=project_id, run_id=run_id),
        metadata=metadata or {},
    )


def _fetch_rows(
    conn: sqlite3.Connection,
    *,
    table: str,
    columns: str,
    where: str = "",
    params: tuple[Any, ...] = (),
    order_expr: str,
) -> list[sqlite3.Row]:
    sql = f"SELECT {columns} FROM {table}{where} ORDER BY {order_expr} DESC LIMIT ?"
    return conn.execute(sql, (*params, PER_KIND_CAP)).fetchall()


def _search_runs(
    conn: sqlite3.Connection, *, query: str, project_id: str | None, now: datetime
) -> list[OperatorSearchHit]:
    if not _safe_table_exists(conn, "orchestration_runs"):
        logger.debug("operator_search: orchestration_runs table missing; skipping")
        return []
    columns = _table_columns(conn, "orchestration_runs")
    last_expr = _last_updated_expr(columns)
    where = " WHERE project_id = ?" if project_id and "project_id" in columns else ""
    params: tuple[Any, ...] = (project_id,) if where else ()
    rows = _fetch_rows(
        conn,
        table="orchestration_runs",
        columns=(
            "id, objective, "
            f"{_selectable(columns, 'project_id', 'NULL')}, "
            f"{_selectable(columns, 'status')}, {last_expr} AS last_updated_at"
        ),
        where=where,
        params=params,
        order_expr="last_updated_at",
    )
    hits = []
    for row in rows:
        title = _text_or_empty(row["objective"])
        summary = f"status: {_text_or_empty(row['status'])}"
        if _matches_query(query, title, summary, _text_or_empty(row["id"])):
            hits.append(
                _make_hit(
                    kind="run",
                    id_=_text_or_empty(row["id"]),
                    title=title,
                    summary=summary,
                    project_id=row["project_id"],
                    source_table="orchestration_runs",
                    last_updated_at=_text_or_empty(row["last_updated_at"]),
                    query=query,
                    key=_text_or_empty(row["id"]),
                    now=now,
                    metadata={"status": row["status"]},
                )
            )
    return hits


def _search_packets(
    conn: sqlite3.Connection, *, query: str, project_id: str | None, now: datetime
) -> list[OperatorSearchHit]:
    if not _safe_table_exists(conn, "briefing_packets"):
        logger.debug("operator_search: briefing_packets table missing; skipping")
        return []
    columns = _table_columns(conn, "briefing_packets")
    last_expr = _last_updated_expr(columns)
    where = " WHERE project_id = ?" if project_id and "project_id" in columns else ""
    params: tuple[Any, ...] = (project_id,) if where else ()
    rows = _fetch_rows(
        conn,
        table="briefing_packets",
        columns=(
            "id, "
            f"{_selectable(columns, 'summary')}, "
            f"{_selectable(columns, 'project_id', 'NULL')}, "
            f"{_selectable(columns, 'run_id', 'NULL')}, {last_expr} AS last_updated_at"
        ),
        where=where,
        params=params,
        order_expr="last_updated_at",
    )
    return [
        _make_hit(
            kind="packet",
            id_=_text_or_empty(row["id"]),
            title=f"Packet {_text_or_empty(row['id'])}",
            summary=_text_or_empty(row["summary"]),
            project_id=row["project_id"],
            source_table="briefing_packets",
            last_updated_at=_text_or_empty(row["last_updated_at"]),
            query=query,
            key=_text_or_empty(row["id"]),
            now=now,
            metadata={"run_id": row["run_id"]},
        )
        for row in rows
        if _matches_query(query, _text_or_empty(row["id"]), _text_or_empty(row["summary"]))
    ]


def _search_writebacks(
    conn: sqlite3.Connection, *, query: str, project_id: str | None, now: datetime
) -> list[OperatorSearchHit]:
    if not _safe_table_exists(conn, "improvement_writebacks"):
        logger.debug("operator_search: improvement_writebacks table missing; skipping")
        return []
    columns = _table_columns(conn, "improvement_writebacks")
    last_expr = _last_updated_expr(columns)
    where = " WHERE project_id = ?" if project_id and "project_id" in columns else ""
    params: tuple[Any, ...] = (project_id,) if where else ()
    rows = _fetch_rows(
        conn,
        table="improvement_writebacks",
        columns=(
            "id, title, summary, "
            f"{_selectable(columns, 'project_id', 'NULL')}, "
            f"{_selectable(columns, 'run_id', 'NULL')}, "
            f"{_selectable(columns, 'layer_key')}, "
            f"{_selectable(columns, 'status')}, {last_expr} AS last_updated_at"
        ),
        where=where,
        params=params,
        order_expr="last_updated_at",
    )
    return [
        _make_hit(
            kind="writeback",
            id_=_text_or_empty(row["id"]),
            title=_text_or_empty(row["title"]),
            summary=_text_or_empty(row["summary"]),
            project_id=row["project_id"],
            source_table="improvement_writebacks",
            last_updated_at=_text_or_empty(row["last_updated_at"]),
            query=query,
            key=_text_or_empty(row["layer_key"] or row["id"]),
            now=now,
            metadata={"status": row["status"], "layer_key": row["layer_key"], "run_id": row["run_id"]},
        )
        for row in rows
        if _matches_query(
            query,
            _text_or_empty(row["id"]),
            _text_or_empty(row["run_id"]),
            _text_or_empty(row["title"]),
            _text_or_empty(row["summary"]),
            _text_or_empty(row["layer_key"]),
        )
    ]


def _search_findings(
    conn: sqlite3.Connection, *, query: str, project_id: str | None, now: datetime
) -> list[OperatorSearchHit]:
    if not _safe_table_exists(conn, "success_criteria_findings"):
        logger.debug("operator_search: success_criteria_findings table missing; skipping")
        return []
    columns = _table_columns(conn, "success_criteria_findings")
    has_direct_run = "run_id" in columns
    has_evaluations = _safe_table_exists(conn, "success_criteria_evaluations")
    evaluation_columns = _table_columns(conn, "success_criteria_evaluations")
    message_expr = (
        "f.message" if "message" in columns else "f.summary" if "summary" in columns else "''"
    )
    run_expr = "f.run_id" if has_direct_run else "e.run_id"
    project_expr = (
        "f.project_id"
        if "project_id" in columns
        else "e.project_id"
        if has_evaluations and "project_id" in evaluation_columns
        else "NULL"
    )
    last_expr = (
        "f.updated_at"
        if "updated_at" in columns
        else "f.created_at"
        if "created_at" in columns
        else "''"
    )
    join = (
        " LEFT JOIN success_criteria_evaluations e ON e.id = f.evaluation_id"
        if not has_direct_run and has_evaluations and "evaluation_id" in columns
        else ""
    )
    where = ""
    params: tuple[Any, ...] = ()
    if project_id and project_expr != "NULL":
        where = f" WHERE {project_expr} = ?"
        params = (project_id,)
    criterion_expr = "f.criterion_id" if "criterion_id" in columns else "''"
    level_expr = "f.level" if "level" in columns else "''"
    rows = _fetch_rows(
        conn,
        table=f"success_criteria_findings f{join}",
        columns=(
            "f.id AS id, "
            f"{run_expr} AS run_id, "
            f"{project_expr} AS project_id, "
            f"{criterion_expr} AS criterion_id, "
            f"{level_expr} AS level, "
            f"{message_expr} AS message, "
            f"{last_expr} AS last_updated_at"
        ),
        where=where,
        params=params,
        order_expr="last_updated_at",
    )
    hits = []
    for row in rows:
        title = f"{_text_or_empty(row['level'])} {_text_or_empty(row['criterion_id'])}".strip()
        summary = _text_or_empty(row["message"])
        if _matches_query(query, _text_or_empty(row["id"]), _text_or_empty(row["run_id"]), title, summary):
            hits.append(
                _make_hit(
                    kind="finding",
                    id_=_text_or_empty(row["id"]),
                    title=title or _text_or_empty(row["id"]),
                    summary=summary,
                    project_id=row["project_id"],
                    source_table="success_criteria_findings",
                    last_updated_at=_text_or_empty(row["last_updated_at"]),
                    query=query,
                    key=_text_or_empty(row["criterion_id"] or row["id"]),
                    now=now,
                    metadata={"run_id": row["run_id"], "level": row["level"]},
                    run_id=row["run_id"],
                )
            )
    return hits


def _search_prompt_templates(
    conn: sqlite3.Connection, *, query: str, project_id: str | None, now: datetime
) -> list[OperatorSearchHit]:
    if not _safe_table_exists(conn, "prompts"):
        logger.debug("operator_search: prompts table missing; skipping prompt templates")
        return []
    columns = _table_columns(conn, "prompts")
    last_expr = _last_updated_expr(columns)
    title_expr = "title" if "title" in columns else "id"
    summary_expr = (
        "summary"
        if "summary" in columns
        else "classification"
        if "classification" in columns
        else "''"
    )
    rows = _fetch_rows(
        conn,
        table="prompts",
        columns=f"id, {title_expr} AS title, {summary_expr} AS summary, {last_expr} AS last_updated_at",
        order_expr="last_updated_at",
    )
    return [
        _make_hit(
            kind="prompt_template",
            id_=_text_or_empty(row["id"]),
            title=_text_or_empty(row["title"]),
            summary=_text_or_empty(row["summary"]),
            project_id=None,
            source_table="prompts",
            last_updated_at=_text_or_empty(row["last_updated_at"]),
            query=query,
            key=_text_or_empty(row["id"]),
            now=now,
        )
        for row in rows
        if _matches_query(
            query,
            _text_or_empty(row["id"]),
            _text_or_empty(row["title"]),
            _text_or_empty(row["summary"]),
        )
    ]


def _search_prompt_uses(
    conn: sqlite3.Connection, *, query: str, project_id: str | None, now: datetime
) -> list[OperatorSearchHit]:
    if not _safe_table_exists(conn, "prompts_used"):
        logger.debug("operator_search: prompts_used table missing; skipping")
        return []
    columns = _table_columns(conn, "prompts_used")
    last_expr = _last_updated_expr(columns)
    rows = _fetch_rows(
        conn,
        table="prompts_used",
        columns=(
            f"{_selectable(columns, 'id', 'rowid')}, "
            f"{_selectable(columns, 'template_id')}, "
            f"{_selectable(columns, 'classification')}, "
            f"{_selectable(columns, 'outcome_score', 'NULL')}, {last_expr} AS last_updated_at"
        ),
        order_expr="last_updated_at",
    )
    return [
        _make_hit(
            kind="prompt_use",
            id_=_text_or_empty(row["id"]),
            title=f"Prompt use {_text_or_empty(row['template_id'] or row['classification'])}",
            summary=f"classification: {_text_or_empty(row['classification'])}",
            project_id=None,
            source_table="prompts_used",
            last_updated_at=_text_or_empty(row["last_updated_at"]),
            query=query,
            key=_text_or_empty(row["template_id"] or row["classification"] or row["id"]),
            now=now,
            metadata={"outcome_score": row["outcome_score"]},
        )
        for row in rows
        if _matches_query(
            query,
            _text_or_empty(row["id"]),
            _text_or_empty(row["template_id"]),
            _text_or_empty(row["classification"]),
        )
    ]


def _search_skills(
    conn: sqlite3.Connection, *, query: str, project_id: str | None, now: datetime
) -> list[OperatorSearchHit]:
    if not _safe_table_exists(conn, "workflow_skill_experiments"):
        logger.debug("operator_search: workflow_skill_experiments table missing; skipping skills")
        return []
    columns = _table_columns(conn, "workflow_skill_experiments")
    last_expr = _last_updated_expr(columns)
    rows = _fetch_rows(
        conn,
        table="workflow_skill_experiments",
        columns=f"skill_key AS id, skill_key, workflow_key, {last_expr} AS last_updated_at",
        order_expr="last_updated_at",
    )
    seen: set[str] = set()
    hits = []
    for row in rows:
        skill_key = _text_or_empty(row["skill_key"])
        if skill_key in seen:
            continue
        seen.add(skill_key)
        summary = f"workflow: {_text_or_empty(row['workflow_key'])}"
        if _matches_query(query, skill_key, summary):
            hits.append(
                _make_hit(
                    kind="skill",
                    id_=skill_key,
                    title=skill_key,
                    summary=summary,
                    project_id=None,
                    source_table="workflow_skill_experiments",
                    last_updated_at=_text_or_empty(row["last_updated_at"]),
                    query=query,
                    key=skill_key,
                    now=now,
                    metadata={"workflow_key": row["workflow_key"]},
                )
            )
    return hits


def _search_workflows(
    conn: sqlite3.Connection, *, query: str, project_id: str | None, now: datetime
) -> list[OperatorSearchHit]:
    if not _safe_table_exists(conn, "orchestration_runs"):
        logger.debug("operator_search: orchestration_runs table missing; skipping workflows")
        return []
    columns = _table_columns(conn, "orchestration_runs")
    if "workflow_key" not in columns:
        return []
    last_expr = _last_updated_expr(columns)
    where = " WHERE workflow_key IS NOT NULL"
    params: tuple[Any, ...] = ()
    if project_id and "project_id" in columns:
        where += " AND project_id = ?"
        params = (project_id,)
    sql = (
        "SELECT workflow_key AS id, workflow_key, "
        f"{_selectable(columns, 'project_id', 'NULL')}, MAX({last_expr}) AS last_updated_at "
        f"FROM orchestration_runs{where} GROUP BY workflow_key ORDER BY last_updated_at DESC LIMIT ?"
    )
    rows = conn.execute(sql, (*params, PER_KIND_CAP)).fetchall()
    return [
        _make_hit(
            kind="workflow",
            id_=_text_or_empty(row["id"]),
            title=_text_or_empty(row["workflow_key"]),
            summary="Workflow observed in orchestration runs",
            project_id=row["project_id"],
            source_table="orchestration_runs",
            last_updated_at=_text_or_empty(row["last_updated_at"]),
            query=query,
            key=_text_or_empty(row["workflow_key"]),
            now=now,
        )
        for row in rows
        if _matches_query(query, _text_or_empty(row["workflow_key"]))
    ]


def _search_knowledge_objects(
    conn: sqlite3.Connection, *, query: str, project_id: str | None, now: datetime
) -> list[OperatorSearchHit]:
    if not _safe_table_exists(conn, "knowledge_objects"):
        logger.debug("operator_search: knowledge_objects table missing; skipping")
        return []
    columns = _table_columns(conn, "knowledge_objects")
    last_expr = _last_updated_expr(columns)
    where = " WHERE project_id = ?" if project_id and "project_id" in columns else ""
    params: tuple[Any, ...] = (project_id,) if where else ()
    rows = _fetch_rows(
        conn,
        table="knowledge_objects",
        columns=(
            "id, title, summary, "
            f"{_selectable(columns, 'key')}, {_selectable(columns, 'kind')}, "
            f"{_selectable(columns, 'project_id', 'NULL')}, {last_expr} AS last_updated_at"
        ),
        where=where,
        params=params,
        order_expr="last_updated_at",
    )
    return [
        _make_hit(
            kind="knowledge_object",
            id_=_text_or_empty(row["id"]),
            title=_text_or_empty(row["title"]),
            summary=_text_or_empty(row["summary"]),
            project_id=row["project_id"],
            source_table="knowledge_objects",
            last_updated_at=_text_or_empty(row["last_updated_at"]),
            query=query,
            key=_text_or_empty(row["key"] or row["id"]),
            now=now,
            metadata={"knowledge_kind": row["kind"]},
        )
        for row in rows
        if _matches_query(
            query,
            _text_or_empty(row["id"]),
            _text_or_empty(row["title"]),
            _text_or_empty(row["summary"]),
            _text_or_empty(row["key"]),
        )
    ]


def _search_route_decisions(
    conn: sqlite3.Connection, *, query: str, project_id: str | None, now: datetime
) -> list[OperatorSearchHit]:
    if not _safe_table_exists(conn, "orchestration_runs"):
        logger.debug("operator_search: orchestration_runs table missing; skipping routes")
        return []
    columns = _table_columns(conn, "orchestration_runs")
    if "route_result_json" not in columns:
        return []
    last_expr = _last_updated_expr(columns)
    where = " WHERE route_result_json IS NOT NULL AND route_result_json != ''"
    params: tuple[Any, ...] = ()
    if project_id and "project_id" in columns:
        where += " AND project_id = ?"
        params = (project_id,)
    rows = _fetch_rows(
        conn,
        table="orchestration_runs",
        columns=(
            "id, objective, route_result_json, "
            f"{_selectable(columns, 'project_id', 'NULL')}, {last_expr} AS last_updated_at"
        ),
        where=where,
        params=params,
        order_expr="last_updated_at",
    )
    hits = []
    for row in rows:
        route_id = f"route-{_text_or_empty(row['id'])}"
        summary = "Route decision attached to run"
        searchable = (
            f"{_text_or_empty(row['objective'])} {_text_or_empty(row['route_result_json'])}"
        )
        if _matches_query(query, route_id, searchable):
            hits.append(
                _make_hit(
                    kind="route_decision",
                    id_=route_id,
                    title=f"Route for {_text_or_empty(row['objective'])}",
                    summary=summary,
                    project_id=row["project_id"],
                    source_table="orchestration_runs",
                    last_updated_at=_text_or_empty(row["last_updated_at"]),
                    query=query,
                    key=route_id,
                    now=now,
                    metadata={"run_id": row["id"]},
                    run_id=row["id"],
                )
            )
    return hits


def _search_delta_items(
    conn: sqlite3.Connection, *, query: str, project_id: str | None, now: datetime
) -> list[OperatorSearchHit]:
    return _search_simple_project_table(
        conn,
        kind="delta_item",
        table="standards_delta_items",
        title_column="domain",
        summary_column="summary",
        key_column="id",
        query=query,
        project_id=project_id,
        now=now,
        metadata_columns=("priority_bucket",),
    )


def _search_backfill_tasks(
    conn: sqlite3.Connection, *, query: str, project_id: str | None, now: datetime
) -> list[OperatorSearchHit]:
    return _search_simple_project_table(
        conn,
        kind="backfill_task",
        table="standards_backfill_tasks",
        title_column="summary",
        summary_column="status",
        key_column="id",
        query=query,
        project_id=project_id,
        now=now,
        metadata_columns=("status",),
    )


def _search_automations(
    conn: sqlite3.Connection, *, query: str, project_id: str | None, now: datetime
) -> list[OperatorSearchHit]:
    return _search_simple_project_table(
        conn,
        kind="automation",
        table="automations",
        title_column="key",
        summary_column="summary",
        key_column="key",
        query=query,
        project_id=project_id,
        now=now,
    )


def _search_experiments(
    conn: sqlite3.Connection, *, query: str, project_id: str | None, now: datetime
) -> list[OperatorSearchHit]:
    return _search_simple_project_table(
        conn,
        kind="experiment",
        table="experiments",
        title_column="id",
        summary_column="summary",
        key_column="id",
        query=query,
        project_id=project_id,
        now=now,
    )


def _search_divergent_runs(
    conn: sqlite3.Connection, *, query: str, project_id: str | None, now: datetime
) -> list[OperatorSearchHit]:
    if not _safe_table_exists(conn, "divergent_runs"):
        logger.debug("operator_search: divergent_runs table missing; skipping")
        return []
    columns = _table_columns(conn, "divergent_runs")
    title_column = "objective" if "objective" in columns else "source_task"
    return _search_simple_project_table(
        conn,
        kind="divergent_run",
        table="divergent_runs",
        title_column=title_column,
        summary_column="summary",
        key_column="id",
        query=query,
        project_id=project_id,
        now=now,
    )


def _search_learning_patterns(
    conn: sqlite3.Connection, *, query: str, project_id: str | None, now: datetime
) -> list[OperatorSearchHit]:
    return _search_simple_project_table(
        conn,
        kind="learning_pattern",
        table="workflow_learning_events",
        title_column="signal_kind",
        summary_column="rationale",
        key_column="id",
        query=query,
        project_id=project_id,
        now=now,
        metadata_columns=("run_id",),
    )


def _search_promotion_lifecycle_items(
    conn: sqlite3.Connection, *, query: str, project_id: str | None, now: datetime
) -> list[OperatorSearchHit]:
    if not _safe_table_exists(conn, "promotion_lifecycle_items"):
        logger.debug("operator_search: promotion_lifecycle_items table missing; skipping")
        return []
    columns = _table_columns(conn, "promotion_lifecycle_items")
    last_expr = _last_updated_expr(columns)
    rows = _fetch_rows(
        conn,
        table="promotion_lifecycle_items",
        columns=(
            "id, item_kind, item_key, status, "
            f"{_selectable(columns, 'source_run_id', 'NULL')}, {last_expr} AS last_updated_at"
        ),
        order_expr="last_updated_at",
    )
    return [
        _make_hit(
            kind="promotion_lifecycle_item",
            id_=_text_or_empty(row["id"]),
            title=f"{_text_or_empty(row['item_kind'])}: {_text_or_empty(row['item_key'])}",
            summary=f"status: {_text_or_empty(row['status'])}",
            project_id=None,
            source_table="promotion_lifecycle_items",
            last_updated_at=_text_or_empty(row["last_updated_at"]),
            query=query,
            key=_text_or_empty(row["item_key"] or row["id"]),
            now=now,
            metadata={"source_run_id": row["source_run_id"], "status": row["status"]},
        )
        for row in rows
        if _matches_query(
            query,
            _text_or_empty(row["id"]),
            _text_or_empty(row["item_key"]),
            _text_or_empty(row["status"]),
        )
    ]


def _search_simple_project_table(
    conn: sqlite3.Connection,
    *,
    kind: EntityKind,
    table: str,
    title_column: str,
    summary_column: str,
    key_column: str,
    query: str,
    project_id: str | None,
    now: datetime,
    metadata_columns: tuple[str, ...] = (),
) -> list[OperatorSearchHit]:
    if not _safe_table_exists(conn, table):
        logger.debug("operator_search: %s table missing; skipping", table)
        return []
    columns = _table_columns(conn, table)
    last_expr = _last_updated_expr(columns)
    select_parts = [
        "id",
        f"{_selectable(columns, title_column)}",
        f"{_selectable(columns, summary_column)}",
        f"{_selectable(columns, key_column)}",
        f"{_selectable(columns, 'project_id', 'NULL')}",
        f"{last_expr} AS last_updated_at",
    ]
    for column in metadata_columns:
        select_parts.append(_selectable(columns, column, "NULL"))
    where = " WHERE project_id = ?" if project_id and "project_id" in columns else ""
    params: tuple[Any, ...] = (project_id,) if where else ()
    rows = _fetch_rows(
        conn,
        table=table,
        columns=", ".join(select_parts),
        where=where,
        params=params,
        order_expr="last_updated_at",
    )
    hits = []
    for row in rows:
        row_project_id = row["project_id"]
        if not _project_allowed(project_id, row_project_id):
            continue
        title = _text_or_empty(row[title_column])
        summary = _text_or_empty(row[summary_column])
        key = _text_or_empty(row[key_column] or row["id"])
        if not _matches_query(query, _text_or_empty(row["id"]), title, summary, key):
            continue
        row_keys = set(row.keys())
        metadata = {column: row[column] for column in metadata_columns if column in row_keys}
        hits.append(
            _make_hit(
                kind=kind,
                id_=_text_or_empty(row["id"]),
                title=title,
                summary=summary,
                project_id=row_project_id,
                source_table=table,
                last_updated_at=_text_or_empty(row["last_updated_at"]),
                query=query,
                key=key,
                now=now,
                metadata=metadata,
            )
        )
    return hits


_DISPATCH: dict[EntityKind, Callable[..., list[OperatorSearchHit]]] = {
    "run": _search_runs,
    "packet": _search_packets,
    "writeback": _search_writebacks,
    "finding": _search_findings,
    "prompt_template": _search_prompt_templates,
    "prompt_use": _search_prompt_uses,
    "skill": _search_skills,
    "workflow": _search_workflows,
    "knowledge_object": _search_knowledge_objects,
    "route_decision": _search_route_decisions,
    "delta_item": _search_delta_items,
    "backfill_task": _search_backfill_tasks,
    "automation": _search_automations,
    "experiment": _search_experiments,
    "divergent_run": _search_divergent_runs,
    "learning_pattern": _search_learning_patterns,
    "promotion_lifecycle_item": _search_promotion_lifecycle_items,
}


def search_entities(
    conn: sqlite3.Connection,
    *,
    query: str,
    kinds: tuple[EntityKind, ...] | None = None,
    project_id: str | None = None,
    limit: int = DEFAULT_LIMIT,
) -> list[OperatorSearchHit]:
    if len(query) > MAX_QUERY_LENGTH:
        raise ValueError(
            f"query length {len(query)} exceeds max {MAX_QUERY_LENGTH}; "
            "refine the query or split it into multiple searches"
        )
    if limit < 1 or limit > MAX_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_LIMIT}")
    target_kinds = kinds or ENTITY_KINDS
    unknown = [kind for kind in target_kinds if kind not in _DISPATCH]
    if unknown:
        raise ValueError(f"unknown entity kind(s): {', '.join(unknown)}")
    conn.row_factory = sqlite3.Row
    normalized_query = query.strip()
    now = datetime.now(UTC)
    hits: list[OperatorSearchHit] = []
    for kind in target_kinds:
        hits.extend(
            _DISPATCH[kind](
                conn,
                query=normalized_query,
                project_id=project_id,
                now=now,
            )
        )
    hits.sort(key=lambda hit: hit.score, reverse=True)
    return hits[:limit]


__all__ = [
    "DEFAULT_LIMIT",
    "ENTITY_KINDS",
    "EntityKind",
    "MAX_QUERY_LENGTH",
    "OperatorSearchHit",
    "search_entities",
]
