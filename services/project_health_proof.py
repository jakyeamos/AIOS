from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from services.standards_health import ensure_standards_health_schema, evaluate_and_record

DEFAULT_PROVING_PROJECTS = ("AIOS", "soundscape-app", "Terrace", "portfolio", "GitNexus", "amos-saas")


def _load_configured_projects(config_root: Path) -> dict[str, dict[str, Any]]:
    projects_path = config_root / "architecture-enforcement" / "projects.json"
    if not projects_path.exists():
        return {}

    loaded = json.loads(projects_path.read_text(encoding="utf-8"))
    projects = loaded.get("projects", [])
    if not isinstance(projects, list):
        return {}

    configured: dict[str, dict[str, Any]] = {}
    for item in projects:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("id") or "")
        if not name:
            continue
        raw_path = str(item.get("path") or "")
        resolved_path = str(Path(raw_path).expanduser()) if raw_path else None
        configured[name.casefold()] = {
            "name": name,
            "path": resolved_path,
            "profile_ids": [
                str(binding.get("profile_id"))
                for binding in item.get("profile_bindings", [])
                if isinstance(binding, dict) and binding.get("profile_id")
            ],
        }
    return configured


def _project_candidates(conn: sqlite3.Connection, name: str) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT id, name, repo_path, status
        FROM projects
        WHERE lower(name) = lower(?)
        ORDER BY
          CASE WHEN repo_path IS NOT NULL AND repo_path != '' THEN 0 ELSE 1 END,
          id ASC
        """,
        (name,),
    ).fetchall()


def _best_candidate(candidates: list[sqlite3.Row]) -> sqlite3.Row | None:
    if not candidates:
        return None
    existing = [
        row
        for row in candidates
        if row["repo_path"] and Path(str(row["repo_path"])).expanduser().exists()
    ]
    return existing[0] if existing else candidates[0]


def _missing_project_result(name: str, configured: dict[str, Any] | None) -> dict[str, Any]:
    configured_path = configured.get("path") if configured else None
    path_exists = bool(configured_path and Path(str(configured_path)).expanduser().exists())
    status = "missing_inventory" if path_exists else "missing_source"
    return {
        "name": name,
        "project_id": None,
        "repo_path": configured_path,
        "configured_profile_ids": configured.get("profile_ids", []) if configured else [],
        "status": status,
        "snapshot_id": None,
        "health_score": None,
        "critical_delta_count": None,
        "unknown_count": None,
        "missing_reason": (
            "Project is absent from inventory."
            if path_exists
            else "Project is absent from inventory and its configured repository path is not available on disk."
        ),
    }


def prove_project_health(
    conn: sqlite3.Connection,
    *,
    config_root: Path,
    project_names: list[str] | None = None,
) -> dict[str, Any]:
    ensure_standards_health_schema(conn)
    configured_projects = _load_configured_projects(config_root)
    registry_path = config_root / "standards" / "registry.json"
    target_names = project_names or list(DEFAULT_PROVING_PROJECTS)

    results: list[dict[str, Any]] = []
    for name in target_names:
        configured = configured_projects.get(name.casefold())
        candidates = _project_candidates(conn, name)
        candidate = _best_candidate(candidates)
        if candidate is None:
            results.append(_missing_project_result(name, configured))
            continue

        repo_path = str(candidate["repo_path"]) if candidate["repo_path"] else None
        if not repo_path or not Path(repo_path).expanduser().exists():
            results.append(
                {
                    "name": str(candidate["name"]),
                    "project_id": str(candidate["id"]),
                    "repo_path": repo_path,
                    "configured_profile_ids": configured.get("profile_ids", []) if configured else [],
                    "status": "missing_source",
                    "snapshot_id": None,
                    "health_score": None,
                    "critical_delta_count": None,
                    "unknown_count": None,
                    "candidate_count": len(candidates),
                    "missing_reason": f"Project repo_path is not available on disk: {repo_path}",
                }
            )
            continue

        snapshot = evaluate_and_record(
            conn,
            project_id=str(candidate["id"]),
            project_name=str(candidate["name"]),
            registry_path=registry_path,
            trigger_kind="tier_one_project_health_proof",
        )
        results.append(
            {
                "name": str(candidate["name"]),
                "project_id": str(candidate["id"]),
                "repo_path": repo_path,
                "configured_profile_ids": configured.get("profile_ids", []) if configured else [],
                "status": "snapshot_recorded",
                "snapshot_id": snapshot["snapshot_id"],
                "health_score": snapshot["health_score"],
                "critical_delta_count": snapshot["critical_delta_count"],
                "unknown_count": snapshot["unknown_count"],
                "candidate_count": len(candidates),
                "missing_reason": None,
            }
        )

    conn.commit()
    status_counts: dict[str, int] = {}
    for result in results:
        status = str(result["status"])
        status_counts[status] = status_counts.get(status, 0) + 1

    return {
        "summary": {
            "target_count": len(target_names),
            "snapshot_recorded_count": status_counts.get("snapshot_recorded", 0),
            "missing_source_count": status_counts.get("missing_source", 0),
            "missing_inventory_count": status_counts.get("missing_inventory", 0),
            "status_counts": status_counts,
        },
        "projects": results,
    }
