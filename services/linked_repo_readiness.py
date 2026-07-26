from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Literal, TypedDict

from services.quality_pipeline import (
    DEFAULT_CONFIG_PATH,
    PipelineSummary,
    get_project_quality_pipeline,
)

ReadinessVerdict = Literal["ready", "evidence_required", "blocked", "excluded"]
AdoptionCertificationStatus = Literal["adoption_ready", "adopted_but_blocked", "not_adopted"]

# Phase 24 explicitly rectifies all linked-repo readiness blockers except deferred/deprecated repos.
DEFAULT_EXCLUDED_PROJECT_IDS = ("agent-router", "video-pipeline", "manga-sync")


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
    adoption_status: AdoptionCertificationStatus
    missing_gate_keys: list[str]
    latest_evidence_ids: dict[str, str]
    blockers: list[str]
    exclusion_reason: str | None
    strict_readiness_status: str | None
    quality_certification: dict[str, Any]


class Phase24ReadinessReport(TypedDict):
    target_count: int
    excluded_count: int
    ready_count: int
    blocked_count: int
    evidence_required_count: int
    adoption_ready_count: int
    adopted_but_blocked_count: int
    not_adopted_count: int
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
    return (
        [project for project in projects if isinstance(project, dict)]
        if isinstance(projects, list)
        else []
    )


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


def _ensure_projects_table(conn: sqlite3.Connection) -> None:
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


def _gate_evidence(summary: PipelineSummary) -> dict[str, str]:
    return {
        gate["key"]: gate["latest_run_id"]
        for gate in summary["gates"]
        if gate["latest_run_id"] is not None
    }


def _missing_required_gate_keys(summary: PipelineSummary) -> list[str]:
    return [
        gate["key"] for gate in summary["gates"] if gate["required"] and gate["status"] != "pass"
    ]


def _required_gate_keys(summary: PipelineSummary) -> list[str]:
    return [gate["key"] for gate in summary["gates"] if gate["required"]]


def _configured_required_gate_keys(summary: PipelineSummary) -> list[str]:
    return [gate["key"] for gate in summary["gates"] if gate["required"] and gate["configured"]]


def _passing_required_gate_keys(summary: PipelineSummary) -> list[str]:
    return [
        gate["key"] for gate in summary["gates"] if gate["required"] and gate["status"] == "pass"
    ]


def _command_is_placeholder(command: str | None) -> bool:
    if command is None:
        return False
    normalized = " ".join(command.strip().casefold().split())
    if not normalized:
        return False
    if normalized in {
        "true",
        ":",
        "echo ok",
        "echo pass",
        "echo todo",
        "noop",
        "no-op",
        "todo",
        "tbd",
    }:
        return True
    return any(
        marker in normalized
        for marker in (
            "todo:",
            "tbd:",
            "placeholder",
            "replace me",
            "not implemented",
            "coming soon",
        )
    )


def _gate_profile_selected(summary: PipelineSummary, standard: dict[str, Any]) -> bool:
    repo_class = summary["repo_class"]
    classes = standard.get("classes")
    if not repo_class or not isinstance(classes, dict):
        return False
    profile = classes.get(repo_class)
    return isinstance(profile, dict) and bool(profile.get("required_gates"))


def _required_certification_subworkflow(standard: dict[str, Any]) -> str:
    adoption_rule = standard.get("adoption_readiness_rule")
    if isinstance(adoption_rule, dict):
        workflow_key = adoption_rule.get("required_quality_certification_workflow")
        if isinstance(workflow_key, str) and workflow_key.strip():
            return workflow_key.strip()
    return "repo_gate_adoption_v1"


def _ci_default_proof_missing(summary: PipelineSummary) -> bool:
    ci_gate = next((gate for gate in summary["gates"] if gate["key"] == "ci"), None)
    if ci_gate and ci_gate["status"] == "pass":
        return False
    exception = summary["non_remote_ci_exception"]
    if not exception:
        return True
    required = {"owner", "reason", "review_date", "local_proof_command", "replacement_path"}
    return not required.issubset(set(exception))


def _accepted_exceptions(summary: PipelineSummary) -> list[str]:
    exception = summary["non_remote_ci_exception"]
    if not exception:
        return []
    required = {"owner", "reason", "review_date", "local_proof_command", "replacement_path"}
    if required.issubset(set(exception)):
        return ["non_remote_ci_exception"]
    return []


def _quality_certification(
    summary: PipelineSummary,
    *,
    standard: dict[str, Any],
    blockers: list[str],
) -> dict[str, Any]:
    required_subworkflow = _required_certification_subworkflow(standard)
    required_gate_keys = _required_gate_keys(summary)
    configured_gate_keys = _configured_required_gate_keys(summary)
    passing_gate_keys = _passing_required_gate_keys(summary)
    missing_command_gate_keys = [
        gate["key"]
        for gate in summary["gates"]
        if gate["required"] and not str(gate["command"] or "").strip()
    ]
    placeholder_command_gate_keys = [
        gate["key"]
        for gate in summary["gates"]
        if gate["required"] and _command_is_placeholder(gate["command"])
    ]
    non_passing_required = [
        f"{gate['key']}:{gate['status']}"
        for gate in summary["gates"]
        if gate["required"] and gate["status"] != "pass"
    ]
    certification_blockers = list(blockers)
    if not summary["repo_class"]:
        certification_blockers.append("repo_classification_missing")
    if not _gate_profile_selected(summary, standard):
        certification_blockers.append("gate_profile_not_selected")
    certification_blockers.extend(
        f"gate_command_missing:{gate}" for gate in missing_command_gate_keys
    )
    certification_blockers.extend(
        f"gate_command_placeholder:{gate}" for gate in placeholder_command_gate_keys
    )
    certification_blockers.extend(f"gate_not_passing:{gate}" for gate in non_passing_required)
    if "ci" in required_gate_keys and "non_remote_ci_exception" in _accepted_exceptions(summary):
        ci_gate = next((gate for gate in summary["gates"] if gate["key"] == "ci"), None)
        if ci_gate and ci_gate["status"] != "pass":
            certification_blockers.append("ci_local_replacement_proof_missing")
    if "pre_cr" in required_gate_keys and "pre_cr" not in passing_gate_keys:
        certification_blockers.append("pre_cr_not_passing")
    if "anti_slop" in required_gate_keys and "anti_slop" not in passing_gate_keys:
        certification_blockers.append("anti_slop_not_passing")
    if summary["strict_readiness_status"] and summary["strict_readiness_status"] != "ready":
        certification_blockers.append(
            f"strict_readiness_status_not_ready:{summary['strict_readiness_status']}"
        )

    unique_blockers = sorted(set(certification_blockers))
    aios_wired = (
        _gate_profile_selected(summary, standard)
        and set(required_gate_keys) <= set(configured_gate_keys)
        and not missing_command_gate_keys
        and not placeholder_command_gate_keys
    )
    quality_standard_compliant = aios_wired and not unique_blockers
    release_ready = quality_standard_compliant and (
        "ci" not in required_gate_keys or "ci" in passing_gate_keys
    )
    if release_ready:
        adoption_status: AdoptionCertificationStatus = "adoption_ready"
    elif aios_wired:
        adoption_status = "adopted_but_blocked"
    else:
        adoption_status = "not_adopted"

    return {
        "workflow_key": required_subworkflow,
        "required_subworkflow": required_subworkflow,
        "repo_classification": summary["repo_class"],
        "gate_profile_key": summary["repo_class"]
        if _gate_profile_selected(summary, standard)
        else None,
        "stage_statuses": {
            "aios_wired": "pass" if aios_wired else "fail",
            "quality_standard_compliant": "pass" if quality_standard_compliant else "fail",
            "release_ready": "pass" if release_ready else "fail",
        },
        "adoption_status": adoption_status,
        "required_gate_keys": required_gate_keys,
        "configured_gate_keys": configured_gate_keys,
        "passing_gate_keys": passing_gate_keys,
        "missing_gate_keys": _missing_required_gate_keys(summary),
        "missing_command_gate_keys": missing_command_gate_keys,
        "placeholder_command_gate_keys": placeholder_command_gate_keys,
        "accepted_exceptions": _accepted_exceptions(summary),
        "blockers": unique_blockers,
        "evidence": {
            "standard_version": summary["standard_version"],
            "strict_readiness_status": summary["strict_readiness_status"],
            "latest_evidence_ids": _gate_evidence(summary),
        },
    }


def _project_verdict(
    summary: PipelineSummary, *, standard: dict[str, Any]
) -> ProjectReadinessVerdict:
    missing_gate_keys = _missing_required_gate_keys(summary)
    blockers = list(summary["maturation_blockers"])
    if _ci_default_proof_missing(summary) and "ci" in missing_gate_keys:
        blockers.append("ci_default_proof_missing")
    if any(
        gate["status"] in {"missing", "blocked", "fail"}
        for gate in summary["gates"]
        if gate["required"]
    ):
        verdict: ReadinessVerdict = "blocked"
    elif missing_gate_keys:
        verdict = "evidence_required"
    else:
        verdict = "ready"
    quality_certification = _quality_certification(
        summary,
        standard=standard,
        blockers=blockers,
    )
    return {
        "project_id": summary["project_id"],
        "repo_class": summary["repo_class"],
        "verdict": verdict,
        "adoption_status": quality_certification["adoption_status"],
        "missing_gate_keys": missing_gate_keys,
        "latest_evidence_ids": _gate_evidence(summary),
        "blockers": sorted(set(blockers)),
        "exclusion_reason": None,
        "strict_readiness_status": summary["strict_readiness_status"],
        "quality_certification": quality_certification,
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
    _ensure_projects_table(conn)
    config_payload = _load_config(config_path)
    standard = config_payload.get("standard")
    standard_payload = standard if isinstance(standard, dict) else {}
    projects = [
        _project_verdict(
            get_project_quality_pipeline(
                conn,
                target["project_id"],
                config_path=config_path,
            ),
            standard=standard_payload,
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
        "adoption_ready_count": len(
            [project for project in projects if project["adoption_status"] == "adoption_ready"]
        ),
        "adopted_but_blocked_count": len(
            [project for project in projects if project["adoption_status"] == "adopted_but_blocked"]
        ),
        "not_adopted_count": len(
            [project for project in projects if project["adoption_status"] == "not_adopted"]
        ),
        "excluded_projects": excluded,
        "projects": projects,
    }
