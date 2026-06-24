from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Literal, TypedDict

from services.quality_pipeline import DEFAULT_CONFIG_PATH, PipelineSummary, get_project_quality_pipeline

ReadinessVerdict = Literal["ready", "evidence_required", "blocked", "excluded"]

# Phase 24 explicitly rectifies all linked-repo readiness blockers except deferred/deprecated repos.
DEFAULT_EXCLUDED_PROJECT_IDS = ("agent-router", "video-pipeline")


class Phase24TargetProject(TypedDict):
    project_id: str
    repo_class: str | None


class ExcludedProject(TypedDict):
    project_id: str
    reason: str


class ProjectReadinessVerdict(TypedDict):
    project_id: str
    repo_class: str | None
    verdict: ReadinessVerdict
    missing_gate_keys: list[str]
    latest_evidence_ids: dict[str, str]
    blockers: list[str]
    exclusion_reason: str | None
    strict_readiness_status: str | None


class Phase24ReadinessReport(TypedDict):
    target_count: int
    excluded_count: int
    ready_count: int
    blocked_count: int
    evidence_required_count: int
    excluded_projects: list[ExcludedProject]
    projects: list[ProjectReadinessVerdict]


def _load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object JSON at {path}")
    return payload


def _configured_projects(config_path: Path) -> list[dict[str, Any]]:
    projects = _load_config(config_path).get("projects")
    return [project for project in projects if isinstance(project, dict)] if isinstance(projects, list) else []


def _project_id(project: dict[str, Any]) -> str:
    value = project.get("project_id")
    return str(value).strip() if isinstance(value, str) else ""


def _optional_str(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def phase24_target_projects(
    *,
    config_path: Path = DEFAULT_CONFIG_PATH,
    excluded_project_ids: tuple[str, ...] = DEFAULT_EXCLUDED_PROJECT_IDS,
) -> list[Phase24TargetProject]:
    excluded = {project_id.casefold() for project_id in excluded_project_ids}
    targets: list[Phase24TargetProject] = []
    for project in _configured_projects(config_path):
        project_id = _project_id(project)
        if not project_id or project_id.casefold() in excluded:
            continue
        targets.append(
            {
                "project_id": project_id,
                "repo_class": _optional_str(project.get("repo_class")),
            }
        )
    return targets


def excluded_phase24_projects(
    *,
    config_path: Path = DEFAULT_CONFIG_PATH,
    excluded_project_ids: tuple[str, ...] = DEFAULT_EXCLUDED_PROJECT_IDS,
) -> list[ExcludedProject]:
    excluded = {project_id.casefold() for project_id in excluded_project_ids}
    projects: list[ExcludedProject] = []
    for project in _configured_projects(config_path):
        project_id = _project_id(project)
        if project_id and project_id.casefold() in excluded:
            projects.append({"project_id": project_id, "reason": "excluded_by_phase24_scope"})
    return projects


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ? LIMIT 1",
        (table,),
    ).fetchone()
    return row is not None


def _ensure_project_rows(conn: sqlite3.Connection, project_ids: list[str]) -> None:
    if not _table_exists(conn, "projects"):
        conn.execute(
            """
            CREATE TABLE projects (
              id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              repo_path TEXT NOT NULL,
              obsidian_path TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'active'
            )
            """
        )
    for project_id in project_ids:
        conn.execute(
            """
            INSERT OR IGNORE INTO projects (id, name, repo_path, obsidian_path, status)
            VALUES (?, ?, '', '', 'active')
            """,
            (project_id, project_id),
        )


def _gate_evidence(summary: PipelineSummary) -> dict[str, str]:
    return {
        gate["key"]: gate["latest_run_id"]
        for gate in summary["gates"]
        if gate["latest_run_id"] is not None
    }


def _missing_required_gate_keys(summary: PipelineSummary) -> list[str]:
    return [
        gate["key"]
        for gate in summary["gates"]
        if gate["required"] and gate["status"] != "pass"
    ]


def _ci_default_proof_missing(summary: PipelineSummary) -> bool:
    ci_gate = next((gate for gate in summary["gates"] if gate["key"] == "ci"), None)
    if ci_gate and ci_gate["status"] == "pass":
        return False
    exception = summary["non_remote_ci_exception"]
    if not exception:
        return True
    required = {"owner", "reason", "review_date", "local_proof_command", "replacement_path"}
    return not required.issubset(set(exception))


def _project_verdict(summary: PipelineSummary) -> ProjectReadinessVerdict:
    missing_gate_keys = _missing_required_gate_keys(summary)
    blockers = list(summary["maturation_blockers"])
    if _ci_default_proof_missing(summary) and "ci" in missing_gate_keys:
        blockers.append("ci_default_proof_missing")
    if any(gate["status"] in {"missing", "blocked", "fail"} for gate in summary["gates"] if gate["required"]):
        verdict: ReadinessVerdict = "blocked"
    elif missing_gate_keys:
        verdict = "evidence_required"
    else:
        verdict = "ready"
    return {
        "project_id": summary["project_id"],
        "repo_class": summary["repo_class"],
        "verdict": verdict,
        "missing_gate_keys": missing_gate_keys,
        "latest_evidence_ids": _gate_evidence(summary),
        "blockers": sorted(set(blockers)),
        "exclusion_reason": None,
        "strict_readiness_status": summary["strict_readiness_status"],
    }


def phase24_readiness_report(
    conn: sqlite3.Connection,
    *,
    config_path: Path = DEFAULT_CONFIG_PATH,
    excluded_project_ids: tuple[str, ...] = DEFAULT_EXCLUDED_PROJECT_IDS,
) -> Phase24ReadinessReport:
    targets = phase24_target_projects(
        config_path=config_path,
        excluded_project_ids=excluded_project_ids,
    )
    excluded = excluded_phase24_projects(
        config_path=config_path,
        excluded_project_ids=excluded_project_ids,
    )
    _ensure_project_rows(conn, [target["project_id"] for target in targets])
    projects = [
        _project_verdict(
            get_project_quality_pipeline(
                conn,
                target["project_id"],
                config_path=config_path,
            )
        )
        for target in targets
    ]
    return {
        "target_count": len(projects),
        "excluded_count": len(excluded),
        "ready_count": len([project for project in projects if project["verdict"] == "ready"]),
        "blocked_count": len([project for project in projects if project["verdict"] == "blocked"]),
        "evidence_required_count": len(
            [project for project in projects if project["verdict"] == "evidence_required"]
        ),
        "excluded_projects": excluded,
        "projects": projects,
    }
