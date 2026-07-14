from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import TypedDict

AIOS_PROJECT_COMPONENT_KEYS = {
    "taski_summary",
    "knowledge_dossier",
    "standards_health",
    "quality_pipeline",
    "learning_writebacks",
    "active_runs",
}
MUTABLE_FIELDS = {"projectId", "componentKey", "enabled"}


class ProjectComponentSetting(TypedDict):
    project_id: str
    component_key: str
    enabled: bool
    updated_at: str


def _required_string(payload: Mapping[str, object], key: str, *, max_length: int) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} is required")
    if len(value) > max_length:
        raise ValueError(f"{key} exceeds the {max_length}-character limit")
    return value


def _validate_payload(payload: Mapping[str, object]) -> tuple[str, str, bool]:
    unknown = set(payload) - MUTABLE_FIELDS
    if unknown:
        names = ", ".join(sorted(str(name) for name in unknown))
        raise ValueError(f"Unsupported project component fields: {names}")

    project_id = _required_string(payload, "projectId", max_length=200)
    component_key = _required_string(payload, "componentKey", max_length=80)
    if component_key not in AIOS_PROJECT_COMPONENT_KEYS:
        raise ValueError(f"Unknown AIOS project component key: {component_key}")
    enabled = payload.get("enabled")
    if not isinstance(enabled, bool):
        raise ValueError("enabled must be a boolean")
    return project_id, component_key, enabled


def set_project_component_enabled(
    conn: sqlite3.Connection,
    payload: Mapping[str, object],
) -> ProjectComponentSetting:
    """Apply one project component toggle as the Python owner."""

    project_id, component_key, enabled = _validate_payload(payload)
    project = conn.execute(
        "SELECT 1 FROM projects WHERE id = ? LIMIT 1",
        (project_id,),
    ).fetchone()
    if project is None:
        raise LookupError("Project not found")

    updated_at = datetime.now(UTC).isoformat()
    with conn:
        conn.execute(
            """
            INSERT INTO project_aios_component_settings (
              project_id, component_key, enabled, updated_at
            ) VALUES (?, ?, ?, ?)
            ON CONFLICT(project_id, component_key)
            DO UPDATE SET enabled = excluded.enabled, updated_at = excluded.updated_at
            """,
            (project_id, component_key, int(enabled), updated_at),
        )
        row = conn.execute(
            """
            SELECT project_id, component_key, enabled, updated_at
            FROM project_aios_component_settings
            WHERE project_id = ? AND component_key = ?
            LIMIT 1
            """,
            (project_id, component_key),
        ).fetchone()
    if row is None:
        raise RuntimeError("Project component setting was updated but could not be reloaded")
    return {
        "project_id": str(row["project_id"]),
        "component_key": str(row["component_key"]),
        "enabled": bool(row["enabled"]),
        "updated_at": str(row["updated_at"]),
    }
