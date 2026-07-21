from __future__ import annotations

import json
import sqlite3
import uuid
from collections.abc import Mapping
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

PAIR_CONTAMINATION_STATUSES = frozenset({"not_checked", "passed", "failed"})
PAIR_REVIEW_STATUSES = frozenset({"pending", "passed", "failed", "not_run"})
PAIR_DECISIONS = frozenset({"promote", "revise", "defer"})
PAIR_REQUIRED_PARITY_FIELDS = frozenset({"model", "effort", "tools", "budget"})
PAIR_HASH_LENGTH = 64


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


def _validate_pair_status(label: str, value: str, allowed: frozenset[str]) -> None:
    if value not in allowed:
        raise ValueError(_allowed_message(label, allowed))


def _validate_sha256(label: str, value: str) -> None:
    if len(value) != PAIR_HASH_LENGTH or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 hex digest.")


def _json_object(value: Mapping[str, object] | None, *, label: str) -> str:
    if value is None:
        return "{}"
    try:
        return json.dumps(dict(value), sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be JSON-serializable.") from exc


def _validate_pair_metadata(parity_metadata: Mapping[str, object]) -> None:
    missing = sorted(PAIR_REQUIRED_PARITY_FIELDS - set(parity_metadata))
    if missing:
        raise ValueError(f"parity_metadata is missing required fields: {', '.join(missing)}")
    if any(parity_metadata[field] is None for field in PAIR_REQUIRED_PARITY_FIELDS):
        raise ValueError("parity_metadata required fields cannot be null.")


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
        CREATE TABLE IF NOT EXISTS eval_pairs (
          id TEXT PRIMARY KEY,
          task_id TEXT NOT NULL REFERENCES eval_tasks(id),
          control_run_id TEXT NOT NULL REFERENCES eval_runs(id),
          treatment_run_id TEXT NOT NULL REFERENCES eval_runs(id),
          protected_start_sha TEXT NOT NULL,
          task_hash TEXT NOT NULL,
          prompt_hash TEXT NOT NULL,
          context_hash TEXT NOT NULL,
          parity_metadata_json TEXT NOT NULL,
          contamination_status TEXT NOT NULL DEFAULT 'not_checked',
          contamination_evidence_json TEXT NOT NULL DEFAULT '{}',
          control_score REAL,
          treatment_score REAL,
          delta REAL,
          independent_review_status TEXT NOT NULL DEFAULT 'pending',
          independent_review_ref TEXT,
          report_path TEXT,
          decision TEXT,
          limitations_json TEXT NOT NULL DEFAULT '[]',
          status TEXT NOT NULL DEFAULT 'open',
          created_at TEXT NOT NULL,
          finalized_at TEXT,
          superseded_at TEXT,
          superseded_reason TEXT
        );
        CREATE TABLE IF NOT EXISTS eval_pair_events (
          id TEXT PRIMARY KEY,
          pair_id TEXT NOT NULL REFERENCES eval_pairs(id),
          event_type TEXT NOT NULL,
          payload_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_eval_pairs_task_created
          ON eval_pairs(task_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_eval_pair_events_pair_created
          ON eval_pair_events(pair_id, created_at ASC);
        """
    )
    pair_columns = {
        str(row["name"])
        for row in conn.execute("PRAGMA table_info(eval_pairs)").fetchall()
    }
    if "report_path" not in pair_columns:
        conn.execute("ALTER TABLE eval_pairs ADD COLUMN report_path TEXT")
    if "superseded_at" not in pair_columns:
        conn.execute("ALTER TABLE eval_pairs ADD COLUMN superseded_at TEXT")
    if "superseded_reason" not in pair_columns:
        conn.execute("ALTER TABLE eval_pairs ADD COLUMN superseded_reason TEXT")
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_eval_pairs_promotion_ready
        ON eval_pairs(status, decision, superseded_at, created_at DESC)
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


def _eval_pair_run_context(
    conn: sqlite3.Connection,
    *,
    task_id: str,
    control_run_id: str,
    treatment_run_id: str,
    protected_start_sha: str,
) -> None:
    rows = conn.execute(
        """
        SELECT r.id, r.task_id, r.condition, t.start_sha
        FROM eval_runs r
        JOIN eval_tasks t ON t.id = r.task_id
        WHERE r.id IN (?, ?)
        """,
        (control_run_id, treatment_run_id),
    ).fetchall()
    by_id = {str(row["id"]): row for row in rows}
    if len(by_id) != 2:
        raise ValueError("Both control_run_id and treatment_run_id must reference eval runs.")
    control = by_id[control_run_id]
    treatment = by_id[treatment_run_id]
    if control_run_id == treatment_run_id:
        raise ValueError("control_run_id and treatment_run_id must be distinct.")
    if str(control["task_id"]) != task_id or str(treatment["task_id"]) != task_id:
        raise ValueError("Both eval runs must belong to task_id.")
    if str(control["condition"]) == str(treatment["condition"]):
        raise ValueError("Control and treatment runs must use distinct conditions.")
    if (
        str(control["start_sha"]) != protected_start_sha
        or str(treatment["start_sha"]) != protected_start_sha
    ):
        raise ValueError("Both eval runs must use protected_start_sha.")


def create_eval_pair(
    conn: sqlite3.Connection,
    *,
    task_id: str,
    control_run_id: str,
    treatment_run_id: str,
    protected_start_sha: str,
    task_hash: str,
    prompt_hash: str,
    context_hash: str,
    parity_metadata: Mapping[str, object],
    contamination_status: str = "not_checked",
    contamination_evidence: Mapping[str, object] | None = None,
    independent_review_status: str = "pending",
    independent_review_ref: str | None = None,
    report_path: str | None = None,
    limitations: list[str] | None = None,
) -> str:
    ensure_eval_schema(conn)
    _validate_sha256("task_hash", task_hash)
    _validate_sha256("prompt_hash", prompt_hash)
    _validate_sha256("context_hash", context_hash)
    _validate_pair_status(
        "contamination_status", contamination_status, PAIR_CONTAMINATION_STATUSES
    )
    _validate_pair_status(
        "independent_review_status", independent_review_status, PAIR_REVIEW_STATUSES
    )
    _validate_pair_metadata(parity_metadata)
    _eval_pair_run_context(
        conn,
        task_id=task_id,
        control_run_id=control_run_id,
        treatment_run_id=treatment_run_id,
        protected_start_sha=protected_start_sha,
    )
    existing = conn.execute(
        """
        SELECT id FROM eval_pairs
        WHERE control_run_id = ? AND treatment_run_id = ?
        LIMIT 1
        """,
        (control_run_id, treatment_run_id),
    ).fetchone()
    if existing is not None:
        raise ValueError(f"Eval run pair already exists: {existing['id']}")
    pair_id = _new_id("eval-pair")
    conn.execute(
        """
        INSERT INTO eval_pairs (
          id, task_id, control_run_id, treatment_run_id, protected_start_sha,
          task_hash, prompt_hash, context_hash, parity_metadata_json,
          contamination_status,
          contamination_evidence_json, independent_review_status,
          independent_review_ref, report_path, limitations_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            pair_id,
            task_id,
            control_run_id,
            treatment_run_id,
            protected_start_sha,
            task_hash,
            prompt_hash,
            context_hash,
            _json_object(parity_metadata, label="parity_metadata"),
            contamination_status,
            _json_object(contamination_evidence, label="contamination_evidence"),
            independent_review_status,
            independent_review_ref,
            report_path,
            json.dumps(list(limitations or []), sort_keys=True),
            _now_iso(),
        ),
    )
    _record_eval_pair_event(
        conn,
        pair_id=pair_id,
        event_type="created",
        payload={
            "control_run_id": control_run_id,
            "treatment_run_id": treatment_run_id,
            "protected_start_sha": protected_start_sha,
        },
    )
    return pair_id


def _record_eval_pair_event(
    conn: sqlite3.Connection,
    *,
    pair_id: str,
    event_type: str,
    payload: Mapping[str, object],
) -> None:
    conn.execute(
        """
        INSERT INTO eval_pair_events (id, pair_id, event_type, payload_json, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            _new_id("eval-pair-event"),
            pair_id,
            event_type,
            _json_object(payload, label="event payload"),
            _now_iso(),
        ),
    )


def _latest_eval_score(conn: sqlite3.Connection, run_id: str) -> float | None:
    row = conn.execute(
        "SELECT overall_score FROM eval_scores WHERE run_id = ? ORDER BY created_at DESC LIMIT 1",
        (run_id,),
    ).fetchone()
    return float(row["overall_score"]) if row is not None else None


def finalize_eval_pair(
    conn: sqlite3.Connection,
    *,
    pair_id: str,
    decision: str,
    contamination_status: str,
    contamination_evidence: Mapping[str, object] | None = None,
    independent_review_status: str,
    independent_review_ref: str | None = None,
    report_path: str | None = None,
    limitations: list[str] | None = None,
) -> dict[str, Any]:
    ensure_eval_schema(conn)
    _validate_pair_status("decision", decision, PAIR_DECISIONS)
    _validate_pair_status(
        "contamination_status", contamination_status, PAIR_CONTAMINATION_STATUSES
    )
    _validate_pair_status(
        "independent_review_status", independent_review_status, PAIR_REVIEW_STATUSES
    )
    row = conn.execute("SELECT * FROM eval_pairs WHERE id = ? LIMIT 1", (pair_id,)).fetchone()
    if row is None:
        raise ValueError(f"Eval pair not found: {pair_id}")
    if str(row["status"]) != "open":
        raise ValueError(f"Eval pair is already finalized: {pair_id}")
    control_score = _latest_eval_score(conn, str(row["control_run_id"]))
    treatment_score = _latest_eval_score(conn, str(row["treatment_run_id"]))
    if decision == "promote":
        if control_score is None or treatment_score is None:
            raise ValueError("Promotion requires scores for both control and treatment runs.")
        if contamination_status != "passed":
            raise ValueError("Promotion requires contamination_status=passed.")
        if independent_review_status != "passed":
            raise ValueError("Promotion requires independent_review_status=passed.")
    delta = (
        round(treatment_score - control_score, 4)
        if control_score is not None and treatment_score is not None
        else None
    )
    pair_status = "finalized" if decision == "promote" else "insufficient_evidence"
    finalized_at = _now_iso()
    conn.execute(
        """
        UPDATE eval_pairs
        SET contamination_status = ?, contamination_evidence_json = ?,
            control_score = ?, treatment_score = ?, delta = ?,
            independent_review_status = ?, independent_review_ref = ?,
            report_path = COALESCE(?, report_path),
            decision = ?, limitations_json = ?, status = ?, finalized_at = ?
        WHERE id = ?
        """,
        (
            contamination_status,
            _json_object(contamination_evidence, label="contamination_evidence"),
            control_score,
            treatment_score,
            delta,
            independent_review_status,
            independent_review_ref,
            report_path,
            decision,
            json.dumps(list(limitations or []), sort_keys=True),
            pair_status,
            finalized_at,
            pair_id,
        ),
    )
    _record_eval_pair_event(
        conn,
        pair_id=pair_id,
        event_type="finalized",
        payload={
            "decision": decision,
            "contamination_status": contamination_status,
            "independent_review_status": independent_review_status,
            "control_score": control_score,
            "treatment_score": treatment_score,
            "delta": delta,
        },
    )
    return get_eval_pair(conn, pair_id)


def _eval_pair_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["parity_metadata"] = json.loads(item.pop("parity_metadata_json") or "{}")
    item["contamination_evidence"] = json.loads(
        item.pop("contamination_evidence_json") or "{}"
    )
    item["limitations"] = _loads_list(item.pop("limitations_json", None))
    return item


def get_eval_pair(conn: sqlite3.Connection, pair_id: str) -> dict[str, Any]:
    ensure_eval_schema(conn)
    row = conn.execute("SELECT * FROM eval_pairs WHERE id = ? LIMIT 1", (pair_id,)).fetchone()
    if row is None:
        raise ValueError(f"Eval pair not found: {pair_id}")
    pair = _eval_pair_row_to_dict(row)
    pair["events"] = []
    for event in conn.execute(
        "SELECT * FROM eval_pair_events WHERE pair_id = ? ORDER BY created_at ASC",
        (pair_id,),
    ).fetchall():
        item = dict(event)
        item["payload"] = json.loads(item.pop("payload_json") or "{}")
        pair["events"].append(item)
    return pair


def list_eval_pairs(
    conn: sqlite3.Connection,
    *,
    task_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    ensure_eval_schema(conn)
    clauses: list[str] = []
    params: list[object] = []
    if task_id:
        clauses.append("task_id = ?")
        params.append(task_id)
    if status:
        clauses.append("status = ?")
        params.append(status)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = conn.execute(
        f"SELECT * FROM eval_pairs {where} ORDER BY created_at DESC LIMIT ?",
        (*params, max(1, int(limit))),
    ).fetchall()
    return [_eval_pair_row_to_dict(row) for row in rows]


def list_promotion_ready_eval_pairs(
    conn: sqlite3.Connection,
    *,
    task_id: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Return only durable, unsuperseded pairs that satisfy promotion gates."""

    ensure_eval_schema(conn)
    clauses = [
        "status = 'finalized'",
        "decision = 'promote'",
        "superseded_at IS NULL",
        "control_score IS NOT NULL",
        "treatment_score IS NOT NULL",
        "delta IS NOT NULL",
        "contamination_status = 'passed'",
        "independent_review_status = 'passed'",
        "independent_review_ref IS NOT NULL",
        "independent_review_ref <> ''",
        "report_path IS NOT NULL",
        "report_path <> ''",
    ]
    params: list[object] = []
    if task_id:
        clauses.append("task_id = ?")
        params.append(task_id)
    rows = conn.execute(
        f"""
        SELECT * FROM eval_pairs
        WHERE {' AND '.join(clauses)}
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (*params, max(1, int(limit))),
    ).fetchall()
    return [_eval_pair_row_to_dict(row) for row in rows]


def supersede_eval_pair(
    conn: sqlite3.Connection,
    *,
    pair_id: str,
    reason: str,
) -> dict[str, Any]:
    """Mark a pair ineligible for promotion without rewriting its audit history."""

    ensure_eval_schema(conn)
    normalized_reason = reason.strip()
    if not normalized_reason:
        raise ValueError("Supersession reason must not be empty.")
    row = conn.execute(
        "SELECT superseded_at FROM eval_pairs WHERE id = ? LIMIT 1", (pair_id,)
    ).fetchone()
    if row is None:
        raise ValueError(f"Eval pair not found: {pair_id}")
    if row["superseded_at"] is not None:
        raise ValueError(f"Eval pair is already superseded: {pair_id}")
    superseded_at = _now_iso()
    conn.execute(
        """
        UPDATE eval_pairs
        SET superseded_at = ?, superseded_reason = ?
        WHERE id = ? AND superseded_at IS NULL
        """,
        (superseded_at, normalized_reason, pair_id),
    )
    _record_eval_pair_event(
        conn,
        pair_id=pair_id,
        event_type="superseded",
        payload={"reason": normalized_reason, "superseded_at": superseded_at},
    )
    return get_eval_pair(conn, pair_id)


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
