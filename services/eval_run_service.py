from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any

# agent-eval-contract 0.3.0 dropped the AIOS workflow vocabulary from its
# public surface ("private workflow vocabulary" is explicitly out of scope),
# so the authoritative vocabulary for the local SQLite schema lives here.
CONTEXT_PROFILES = frozenset(
    {
        "jakye_second_brain_full",
        "jakye_second_brain_limited",
        "jakye_repo_only",
        "peer_repo_only",
        "peer_portable_context_packet",
        "external_clean_room",
    }
)
FINAL_STATUSES = frozenset({"success", "partial", "failed", "abandoned"})
FAILURE_PRIORITIES = frozenset({"low", "medium", "high", "critical"})

# Dimension columns of the local eval_scores table. agent-eval-contract 0.3.0
# replaced its flat SCORE_FIELDS constant with a Pydantic metrics map, so the
# authoritative list for the local SQLite schema lives here.
SCORE_FIELDS = (
    "task_success",
    "quality_adherence",
    "workflow_speed",
    "cost_efficiency",
    "context_effectiveness",
    "second_brain_effectiveness",
    "context_portability",
    "autonomy",
    "user_trust",
)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"


def _json_list(values: list[str] | tuple[str, ...] | None) -> str:
    return json.dumps(list(values or []), sort_keys=True)


def _loads_list(raw: str | None) -> list[Any]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _allowed_message(label: str, allowed: frozenset[str]) -> str:
    return f"Invalid {label}. Use one of: {', '.join(sorted(allowed))}."


def _validate_context_profile(context_profile: str) -> None:
    if context_profile not in CONTEXT_PROFILES:
        raise ValueError(_allowed_message("context_profile", CONTEXT_PROFILES))


def _validate_final_status(final_status: str) -> None:
    if final_status not in FINAL_STATUSES:
        raise ValueError(_allowed_message("final_status", FINAL_STATUSES))


def _validate_priority(priority: str) -> None:
    if priority not in FAILURE_PRIORITIES:
        raise ValueError(_allowed_message("priority", FAILURE_PRIORITIES))


def _validate_task_exists(conn: sqlite3.Connection, task_id: str) -> None:
    row = conn.execute("SELECT 1 FROM eval_tasks WHERE id = ? LIMIT 1", (task_id,)).fetchone()
    if row is None:
        raise ValueError(f"Eval task not found: {task_id}")


def ensure_eval_schema(conn: sqlite3.Connection) -> None:
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS eval_tasks (
          id TEXT PRIMARY KEY,
          repo_id TEXT,
          source TEXT,
          start_sha TEXT NOT NULL,
          context_profile TEXT NOT NULL,
          task_type TEXT,
          prompt_summary TEXT,
          acceptance_criteria_json TEXT,
          success_criteria_files_json TEXT,
          created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS eval_runs (
          id TEXT PRIMARY KEY,
          task_id TEXT REFERENCES eval_tasks(id),
          condition TEXT NOT NULL,
          mode TEXT NOT NULL,
          harness TEXT,
          model TEXT,
          context_profile TEXT NOT NULL,
          branch_name TEXT,
          duration_ms INTEGER,
          total_tokens INTEGER,
          estimated_cost_usd REAL,
          tool_calls INTEGER,
          failed_commands INTEGER,
          files_changed INTEGER,
          tests_run_json TEXT,
          final_status TEXT NOT NULL,
          created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS eval_scores (
          id TEXT PRIMARY KEY,
          run_id TEXT REFERENCES eval_runs(id),
          task_success REAL,
          quality_adherence REAL,
          workflow_speed REAL,
          cost_efficiency REAL,
          context_effectiveness REAL,
          second_brain_effectiveness REAL,
          context_portability REAL,
          autonomy REAL,
          user_trust REAL,
          overall_score REAL NOT NULL,
          reviewer_notes TEXT,
          created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS eval_failures (
          id TEXT PRIMARY KEY,
          run_id TEXT REFERENCES eval_runs(id),
          failure_types_json TEXT NOT NULL,
          summary TEXT,
          suspected_cause TEXT,
          affected_components_json TEXT,
          recommended_fixes_json TEXT,
          priority TEXT NOT NULL,
          regression_task_created INTEGER DEFAULT 0,
          backfill_item_created INTEGER DEFAULT 0,
          standards_update_needed INTEGER DEFAULT 0,
          created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS eval_gold_set_tasks (
          id TEXT PRIMARY KEY,
          task_id TEXT REFERENCES eval_tasks(id),
          required_context_sources_json TEXT NOT NULL,
          expected_retrieval_ids_json TEXT,
          known_correct_outcome TEXT,
          created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS eval_second_brain_retrievals (
          id TEXT PRIMARY KEY,
          run_id TEXT REFERENCES eval_runs(id),
          source_type TEXT,
          source_id TEXT,
          source_path TEXT,
          was_needed INTEGER,
          was_stale INTEGER,
          stale_reason TEXT,
          relevance_score REAL,
          created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS eval_gold_set_context (
          gold_task_id TEXT REFERENCES eval_gold_set_tasks(id),
          required_source_id TEXT,
          required_source_type TEXT,
          PRIMARY KEY (gold_task_id, required_source_id)
        );
        """
    )


def create_eval_task(
    conn: sqlite3.Connection,
    *,
    repo_id: str | None,
    source: str | None,
    start_sha: str,
    context_profile: str,
    task_type: str | None,
    prompt_summary: str | None,
    acceptance_criteria: list[str],
    success_criteria_files: list[str],
) -> str:
    ensure_eval_schema(conn)
    _validate_context_profile(context_profile)
    task_id = _new_id("eval-task")
    conn.execute(
        """
        INSERT INTO eval_tasks (
          id, repo_id, source, start_sha, context_profile, task_type, prompt_summary,
          acceptance_criteria_json, success_criteria_files_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            task_id,
            repo_id,
            source,
            start_sha,
            context_profile,
            task_type,
            prompt_summary,
            _json_list(acceptance_criteria),
            _json_list(success_criteria_files),
            _now_iso(),
        ),
    )
    return task_id


def create_eval_run(
    conn: sqlite3.Connection,
    *,
    task_id: str,
    condition: str,
    mode: str,
    harness: str | None,
    model: str | None,
    context_profile: str,
    **kwargs: Any,
) -> str:
    ensure_eval_schema(conn)
    _validate_task_exists(conn, task_id)
    _validate_context_profile(context_profile)
    final_status = str(kwargs.get("final_status", "partial"))
    _validate_final_status(final_status)
    run_id = _new_id("eval-run")
    conn.execute(
        """
        INSERT INTO eval_runs (
          id, task_id, condition, mode, harness, model, context_profile, branch_name,
          duration_ms, total_tokens, estimated_cost_usd, tool_calls, failed_commands,
          files_changed, tests_run_json, final_status, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            task_id,
            condition,
            mode,
            harness,
            model,
            context_profile,
            kwargs.get("branch_name"),
            kwargs.get("duration_ms"),
            kwargs.get("total_tokens"),
            kwargs.get("estimated_cost_usd"),
            kwargs.get("tool_calls", 0),
            kwargs.get("failed_commands", 0),
            kwargs.get("files_changed", 0),
            _json_list(kwargs.get("tests_run")),
            final_status,
            _now_iso(),
        ),
    )
    return run_id


def record_eval_score(conn: sqlite3.Connection, *, run_id: str, **score_fields: Any) -> str:
    ensure_eval_schema(conn)
    values = {field: score_fields.get(field) for field in SCORE_FIELDS}
    numeric_values = [float(value) for value in values.values() if isinstance(value, int | float)]
    raw_overall_score = score_fields.get("overall_score")
    if isinstance(raw_overall_score, int | float):
        overall_score = float(raw_overall_score)
    else:
        overall_score = sum(numeric_values) / len(numeric_values) if numeric_values else 0.0
    score_id = _new_id("eval-score")
    conn.execute(
        """
        INSERT INTO eval_scores (
          id, run_id, task_success, quality_adherence, workflow_speed, cost_efficiency,
          context_effectiveness, second_brain_effectiveness, context_portability, autonomy,
          user_trust, overall_score, reviewer_notes, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            score_id,
            run_id,
            values["task_success"],
            values["quality_adherence"],
            values["workflow_speed"],
            values["cost_efficiency"],
            values["context_effectiveness"],
            values["second_brain_effectiveness"],
            values["context_portability"],
            values["autonomy"],
            values["user_trust"],
            overall_score,
            score_fields.get("reviewer_notes"),
            _now_iso(),
        ),
    )
    return score_id


def record_eval_failure(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    failure_types: list[str],
    summary: str | None,
    suspected_cause: str | None,
    affected_components: list[str],
    recommended_fixes: list[str],
    priority: str,
) -> str:
    ensure_eval_schema(conn)
    _validate_priority(priority)
    failure_id = _new_id("eval-failure")
    conn.execute(
        """
        INSERT INTO eval_failures (
          id, run_id, failure_types_json, summary, suspected_cause,
          affected_components_json, recommended_fixes_json, priority, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            failure_id,
            run_id,
            _json_list(failure_types),
            summary,
            suspected_cause,
            _json_list(affected_components),
            _json_list(recommended_fixes),
            priority,
            _now_iso(),
        ),
    )
    return failure_id


def _run_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    payload = dict(row)
    payload["tests_run"] = _loads_list(payload.pop("tests_run_json", None))
    return payload


def list_eval_runs(
    conn: sqlite3.Connection,
    *,
    task_id: str | None = None,
    condition: str | None = None,
    context_profile: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    ensure_eval_schema(conn)
    filters: list[str] = []
    params: list[Any] = []
    if task_id:
        filters.append("r.task_id = ?")
        params.append(task_id)
    if condition:
        filters.append("r.condition = ?")
        params.append(condition)
    if context_profile:
        _validate_context_profile(context_profile)
        filters.append("r.context_profile = ?")
        params.append(context_profile)
    where_sql = f"WHERE {' AND '.join(filters)}" if filters else ""
    rows = conn.execute(
        f"""
        SELECT r.*, t.repo_id, t.source AS task_source, t.prompt_summary
        FROM eval_runs r
        LEFT JOIN eval_tasks t ON t.id = r.task_id
        {where_sql}
        ORDER BY r.created_at DESC
        LIMIT ?
        """,
        (*params, max(1, int(limit))),
    ).fetchall()
    return [_run_row_to_dict(row) for row in rows]


def get_eval_run_detail(conn: sqlite3.Connection, run_id: str) -> dict[str, Any]:
    ensure_eval_schema(conn)
    row = conn.execute(
        """
        SELECT r.*, t.repo_id, t.source AS task_source, t.start_sha, t.task_type,
               t.prompt_summary, t.acceptance_criteria_json, t.success_criteria_files_json
        FROM eval_runs r
        LEFT JOIN eval_tasks t ON t.id = r.task_id
        WHERE r.id = ?
        LIMIT 1
        """,
        (run_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Eval run not found: {run_id}")
    run = _run_row_to_dict(row)
    run["acceptance_criteria"] = _loads_list(run.pop("acceptance_criteria_json", None))
    run["success_criteria_files"] = _loads_list(run.pop("success_criteria_files_json", None))
    run["scores"] = [
        dict(score)
        for score in conn.execute(
            "SELECT * FROM eval_scores WHERE run_id = ? ORDER BY created_at DESC",
            (run_id,),
        ).fetchall()
    ]
    failures = []
    for failure in conn.execute(
        "SELECT * FROM eval_failures WHERE run_id = ? ORDER BY created_at DESC",
        (run_id,),
    ).fetchall():
        item = dict(failure)
        item["failure_types"] = _loads_list(item.pop("failure_types_json", None))
        item["affected_components"] = _loads_list(item.pop("affected_components_json", None))
        item["recommended_fixes"] = _loads_list(item.pop("recommended_fixes_json", None))
        failures.append(item)
    run["failures"] = failures
    return run


def get_eval_summary(conn: sqlite3.Connection, *, project_id: str | None = None) -> dict[str, Any]:
    ensure_eval_schema(conn)
    filters = ["t.repo_id = ?"] if project_id else []
    params: list[Any] = [project_id] if project_id else []
    where_sql = f"WHERE {' AND '.join(filters)}" if filters else ""
    row = conn.execute(
        f"""
        SELECT COUNT(r.id) AS run_count,
               AVG((
                 SELECT s.overall_score
                 FROM eval_scores s
                 WHERE s.run_id = r.id
                 ORDER BY s.created_at DESC, s.rowid DESC
                 LIMIT 1
               )) AS average_score,
               COUNT(DISTINCT r.task_id) AS task_count
        FROM eval_runs r
        LEFT JOIN eval_tasks t ON t.id = r.task_id
        {where_sql}
        """,
        params,
    ).fetchone()
    by_status = {
        item["final_status"]: item["count"]
        for item in conn.execute(
            f"""
            SELECT r.final_status, COUNT(*) AS count
            FROM eval_runs r
            LEFT JOIN eval_tasks t ON t.id = r.task_id
            {where_sql}
            GROUP BY r.final_status
            """,
            params,
        ).fetchall()
    }
    by_context_profile = {
        item["context_profile"]: item["count"]
        for item in conn.execute(
            f"""
            SELECT r.context_profile, COUNT(*) AS count
            FROM eval_runs r
            LEFT JOIN eval_tasks t ON t.id = r.task_id
            {where_sql}
            GROUP BY r.context_profile
            """,
            params,
        ).fetchall()
    }
    return {
        "project_id": project_id,
        "run_count": int(row["run_count"] or 0),
        "task_count": int(row["task_count"] or 0),
        "average_score": row["average_score"],
        "by_status": by_status,
        "by_context_profile": by_context_profile,
    }
