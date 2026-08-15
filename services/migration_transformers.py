from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from services.storage import ensure_migration_schema, quarantine_row

SESSION_REFERENCE_TABLES = (
    "orchestration_runs",
    "orchestration_invocations",
    "orchestration_run_events",
)


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ? LIMIT 1",
            (table_name,),
        ).fetchone()
        is not None
    )


def _row_payload(row: sqlite3.Row) -> dict[str, object]:
    keys = tuple(row.keys())
    return {key: row[key] for key in keys}


def _normalized_path(value: str) -> str:
    return os.path.normcase(os.path.normpath(str(Path(value).expanduser())))


def _project_ids_by_repo_path(conn: sqlite3.Connection) -> dict[str, tuple[str, ...]]:
    if not _table_exists(conn, "projects"):
        return {}
    paths: dict[str, list[str]] = {}
    for row in conn.execute("SELECT id, repo_path FROM projects WHERE repo_path IS NOT NULL"):
        repo_path = str(row["repo_path"]).strip()
        if repo_path:
            paths.setdefault(_normalized_path(repo_path), []).append(str(row["id"]))
    return {path: tuple(ids) for path, ids in paths.items()}


def _quarantine_missing_sessions(conn: sqlite3.Connection, migration_id: str) -> list[int]:
    quarantined: list[int] = []
    for table in SESSION_REFERENCE_TABLES:
        if not _table_exists(conn, table) or not _table_exists(conn, "sessions"):
            continue
        quoted_table = _quote_identifier(table)
        rows = conn.execute(
            f"""
            SELECT *
            FROM {quoted_table} AS source
            WHERE source.session_id IS NOT NULL
              AND (
                TRIM(source.session_id) = ''
                OR NOT EXISTS (
                 SELECT 1 FROM sessions WHERE sessions.id = source.session_id
                )
              )
            ORDER BY source.id
            """
        ).fetchall()
        for row in rows:
            row_id = str(row["id"])
            quarantined.append(
                quarantine_row(
                    conn,
                    migration_id=migration_id,
                    source_table=table,
                    source_primary_key=row_id,
                    original_payload=_row_payload(row),
                    reason="session reference is blank or has no trusted parent",
                    proposed_disposition="retain-with-null-session-or-review",
                )
            )
            conn.execute(
                f"UPDATE {quoted_table} SET session_id = NULL WHERE id = ?",
                (row["id"],),
            )
    return quarantined


def _quarantine_shadow_tasks(conn: sqlite3.Connection, migration_id: str) -> list[int]:
    if not _table_exists(conn, "shadow_branch_runs") or not _table_exists(conn, "eval_tasks"):
        return []
    rows = conn.execute(
        """
        SELECT *
        FROM shadow_branch_runs AS source
        WHERE source.task_id IS NOT NULL
          AND NOT EXISTS (
            SELECT 1 FROM eval_tasks WHERE eval_tasks.id = source.task_id
          )
        ORDER BY source.id
        """
    ).fetchall()
    quarantined: list[int] = []
    for row in rows:
        quarantined.append(
            quarantine_row(
                conn,
                migration_id=migration_id,
                source_table="shadow_branch_runs",
                source_primary_key=str(row["id"]),
                original_payload=_row_payload(row),
                reason="shadow task reference has no source eval_tasks row",
                proposed_disposition="retain-with-null-task-or-archive",
            )
        )
        conn.execute(
            "UPDATE shadow_branch_runs SET task_id = NULL WHERE id = ?",
            (row["id"],),
        )
    return quarantined


def _metadata_working_directory(raw: object) -> str | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    working_directory = parsed.get("working_directory")
    return (
        working_directory
        if isinstance(working_directory, str) and working_directory.strip()
        else None
    )


def _quarantine_quality_projects(conn: sqlite3.Connection, migration_id: str) -> list[int]:
    if not _table_exists(conn, "quality_pipeline_runs") or not _table_exists(conn, "projects"):
        return []
    project_paths = _project_ids_by_repo_path(conn)
    rows = conn.execute(
        """
        SELECT *
        FROM quality_pipeline_runs
        WHERE project_id IS NULL
           OR project_id NOT IN (SELECT id FROM projects)
        ORDER BY id
        """
    ).fetchall()
    quarantined: list[int] = []
    for row in rows:
        working_directory = _metadata_working_directory(row["metadata_json"])
        candidates = (
            project_paths.get(_normalized_path(working_directory), ()) if working_directory else ()
        )
        row_id = str(row["id"])
        if len(candidates) == 1:
            disposition = "mapped-by-unique-working-directory"
            conn.execute(
                "UPDATE quality_pipeline_runs SET project_id = ? WHERE id = ?",
                (candidates[0], row["id"]),
            )
        else:
            disposition = "archive-unresolved-project"
            conn.execute("DELETE FROM quality_pipeline_runs WHERE id = ?", (row["id"],))
        quarantined.append(
            quarantine_row(
                conn,
                migration_id=migration_id,
                source_table="quality_pipeline_runs",
                source_primary_key=row_id,
                original_payload=_row_payload(row),
                reason=(
                    "project id was not registered and a unique working-directory mapping was found"
                    if len(candidates) == 1
                    else "project id was not registered and no unique working-directory mapping was found"
                ),
                proposed_disposition=disposition,
            )
        )
    return quarantined


def quarantine_known_fk_violations(
    conn: sqlite3.Connection,
    *,
    migration_id: str,
) -> tuple[int, ...]:
    ensure_migration_schema(conn)
    quarantined = []
    quarantined.extend(_quarantine_quality_projects(conn, migration_id))
    quarantined.extend(_quarantine_missing_sessions(conn, migration_id))
    quarantined.extend(_quarantine_shadow_tasks(conn, migration_id))
    return tuple(quarantined)
