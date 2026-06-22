from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any

from services.eval_run_service import ensure_eval_schema, get_eval_run_detail


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"


def ensure_second_brain_eval_schema(conn: sqlite3.Connection) -> None:
    ensure_eval_schema(conn)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
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


def record_retrieval(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    source_type: str,
    source_id: str,
    source_path: str | None,
    was_needed: bool,
    was_stale: bool = False,
    stale_reason: str | None = None,
    relevance_score: float | None = None,
) -> str:
    ensure_second_brain_eval_schema(conn)
    retrieval_id = _new_id("eval-retrieval")
    conn.execute(
        """
        INSERT INTO eval_second_brain_retrievals (
          id, run_id, source_type, source_id, source_path, was_needed, was_stale,
          stale_reason, relevance_score, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            retrieval_id,
            run_id,
            source_type,
            source_id,
            source_path,
            int(was_needed),
            int(was_stale),
            stale_reason,
            relevance_score,
            _now_iso(),
        ),
    )
    return retrieval_id


def compute_retrieval_metrics(conn: sqlite3.Connection, run_id: str) -> dict[str, Any]:
    ensure_second_brain_eval_schema(conn)
    rows = conn.execute(
        """
        SELECT source_id, source_type, was_needed, was_stale
        FROM eval_second_brain_retrievals
        WHERE run_id = ?
        """,
        (run_id,),
    ).fetchall()
    count_total = len(rows)
    count_needed = sum(1 for row in rows if int(row["was_needed"] or 0) == 1)
    count_stale = sum(1 for row in rows if int(row["was_stale"] or 0) == 1)
    precision = count_needed / count_total if count_total else 0.0
    required_rows = conn.execute(
        """
        SELECT gc.required_source_id, gc.required_source_type
        FROM eval_runs r
        JOIN eval_gold_set_tasks gt ON gt.task_id = r.task_id
        JOIN eval_gold_set_context gc ON gc.gold_task_id = gt.id
        WHERE r.id = ?
        """,
        (run_id,),
    ).fetchall()
    required = {
        (str(row["required_source_id"]), str(row["required_source_type"]))
        for row in required_rows
    }
    retrieved = {
        (str(row["source_id"]), str(row["source_type"]))
        for row in rows
    }
    recall = len(required & retrieved) / len(required) if required else precision
    return {
        "precision": precision,
        "recall": recall,
        "staleness_rate": count_stale / count_total if count_total else 0.0,
        "count_total": count_total,
        "count_needed": count_needed,
        "count_stale": count_stale,
    }


def register_gold_set_task(
    conn: sqlite3.Connection,
    *,
    task_id: str,
    required_sources: list[dict[str, str]],
    known_correct_outcome: str,
) -> str:
    ensure_second_brain_eval_schema(conn)
    gold_task_id = _new_id("eval-gold")
    conn.execute(
        """
        INSERT INTO eval_gold_set_tasks (
          id, task_id, required_context_sources_json, expected_retrieval_ids_json,
          known_correct_outcome, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            gold_task_id,
            task_id,
            json.dumps(required_sources, sort_keys=True),
            "[]",
            known_correct_outcome,
            _now_iso(),
        ),
    )
    conn.executemany(
        """
        INSERT INTO eval_gold_set_context (
          gold_task_id, required_source_id, required_source_type
        )
        VALUES (?, ?, ?)
        """,
        [
            (
                gold_task_id,
                source["source_id"],
                source.get("source_type", "unknown"),
            )
            for source in required_sources
        ],
    )
    return gold_task_id


def evaluate_gold_set_run(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    gold_task_id: str,
) -> dict[str, Any]:
    ensure_second_brain_eval_schema(conn)
    required_rows = conn.execute(
        """
        SELECT required_source_id, required_source_type
        FROM eval_gold_set_context
        WHERE gold_task_id = ?
        """,
        (gold_task_id,),
    ).fetchall()
    retrieved_rows = conn.execute(
        """
        SELECT source_id, source_type, was_needed, was_stale
        FROM eval_second_brain_retrievals
        WHERE run_id = ?
        """,
        (run_id,),
    ).fetchall()
    required = {
        (str(row["required_source_id"]), str(row["required_source_type"]))
        for row in required_rows
    }
    retrieved = {
        (str(row["source_id"]), str(row["source_type"]))
        for row in retrieved_rows
    }
    matched = required & retrieved
    metrics = compute_retrieval_metrics(conn, run_id)
    missed_sources = [
        {"source_id": source_id, "source_type": source_type}
        for source_id, source_type in sorted(required - retrieved)
    ]
    return {
        "recall": len(matched) / len(required) if required else 0.0,
        "precision": metrics["precision"],
        "staleness_rate": metrics["staleness_rate"],
        "missed_sources": missed_sources,
    }


def compute_second_brain_lift(
    conn: sqlite3.Connection,
    *,
    full_run_id: str,
    repo_only_run_id: str,
) -> dict[str, Any]:
    try:
        full_run = get_eval_run_detail(conn, full_run_id)
        repo_only_run = get_eval_run_detail(conn, repo_only_run_id)
    except ValueError as exc:
        missing = repo_only_run_id if repo_only_run_id in str(exc) else full_run_id
        return {"available": False, "missing_condition": missing}
    if full_run.get("task_id") != repo_only_run.get("task_id"):
        return {"available": False, "missing_condition": "task_mismatch"}
    if not full_run["scores"]:
        return {"available": False, "missing_condition": full_run_id}
    if not repo_only_run["scores"]:
        return {"available": False, "missing_condition": repo_only_run_id}
    full_score = full_run["scores"][0]
    repo_score = repo_only_run["scores"][0]
    dimensions: dict[str, float] = {}
    for key, full_value in full_score.items():
        if key in {"id", "run_id", "reviewer_notes", "created_at"}:
            continue
        repo_value = repo_score.get(key)
        if isinstance(full_value, int | float) and isinstance(repo_value, int | float):
            dimensions[key] = float(full_value) - float(repo_value)
    return {
        "available": True,
        "task_id": full_run.get("task_id"),
        "full_run_id": full_run_id,
        "repo_only_run_id": repo_only_run_id,
        "dimensions": dimensions,
        "overall_lift": dimensions.get("overall_score", 0.0),
    }
