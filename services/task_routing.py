from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal, cast

from services.asset_recommendation import (
    AssetRecommendation,
    build_asset_usage_evidence,
    recommend_assets_for_packet,
)
from services.invocation_backends import Surface, get_backend_for_surface
from services.project_inventory import ProjectCandidate, rank_project_candidates
from services.workflow_orchestration import recommend_route_primitives

ProjectOutcome = Literal["exact", "likely", "ambiguous", "unsupported"]
RouteStatus = Literal["ready", "blocked"]


@dataclass(frozen=True)
class ProjectResolution:
    outcome: ProjectOutcome
    selected_project_id: str | None
    rationale: str
    candidates: tuple[ProjectCandidate, ...]

    def to_json(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome,
            "selected_project_id": self.selected_project_id,
            "rationale": self.rationale,
            "candidates": [candidate.to_json() for candidate in self.candidates],
        }


@dataclass(frozen=True)
class RouteResult:
    status: RouteStatus
    objective: str
    surface: str
    project: ProjectResolution
    selected_workflow: dict[str, Any] | None
    workflow_candidates: list[dict[str, Any]]
    prompt_recommendation: dict[str, Any] | None
    backend_recommendation: dict[str, Any] | None
    agent_recommendation: dict[str, Any] | None
    task_family: str | None
    blocked_reason: str | None
    rationale: str
    skill_recommendations: tuple[AssetRecommendation, ...] = ()
    workflow_alternatives: tuple[AssetRecommendation, ...] = ()

    def to_json(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["project"] = self.project.to_json()
        return payload


def _resolve_project(
    conn: sqlite3.Connection,
    *,
    objective: str,
    cwd: str | None,
    explicit_project_id: str | None,
) -> ProjectResolution:
    candidates = tuple(
        rank_project_candidates(
            conn,
            objective=objective,
            cwd=cwd,
            explicit_project_id=explicit_project_id,
        )
    )
    if explicit_project_id and not candidates:
        return ProjectResolution(
            outcome="unsupported",
            selected_project_id=None,
            rationale=f"Explicit project {explicit_project_id} was not found in the registered project inventory.",
            candidates=(),
        )
    if not candidates:
        return ProjectResolution(
            outcome="unsupported",
            selected_project_id=None,
            rationale="No registered project matched the objective or current working directory strongly enough.",
            candidates=(),
        )

    top = candidates[0]
    runner_up = candidates[1] if len(candidates) > 1 else None
    lead = top.score - runner_up.score if runner_up else top.score

    if explicit_project_id or top.match_kind in {
        "explicit_project_id",
        "cwd_match",
        "project_name_exact",
    }:
        if runner_up and runner_up.score >= top.score - 8:
            return ProjectResolution(
                outcome="ambiguous",
                selected_project_id=None,
                rationale=(
                    f"Top project candidates {top.name} and {runner_up.name} are too close to choose safely."
                ),
                candidates=candidates,
            )
        return ProjectResolution(
            outcome="exact",
            selected_project_id=top.id,
            rationale=top.rationale,
            candidates=candidates,
        )

    if runner_up and runner_up.score >= top.score - 8:
        return ProjectResolution(
            outcome="ambiguous",
            selected_project_id=None,
            rationale=f"Top project candidates {top.name} and {runner_up.name} have near-equal scores.",
            candidates=candidates,
        )

    if top.score >= 35 and lead >= 10:
        return ProjectResolution(
            outcome="likely",
            selected_project_id=top.id,
            rationale=top.rationale,
            candidates=candidates,
        )

    return ProjectResolution(
        outcome="unsupported",
        selected_project_id=None,
        rationale=f"Project evidence for {top.name} was too weak to route safely.",
        candidates=candidates,
    )


def route_objective(
    conn: sqlite3.Connection,
    *,
    objective: str,
    surface: str = "codex",
    cwd: str | None = None,
    explicit_project_id: str | None = None,
    workflow_registry_path: Path | None = None,
    prompt_registry_path: Path | None = None,
) -> RouteResult:
    project = _resolve_project(
        conn,
        objective=objective,
        cwd=cwd,
        explicit_project_id=explicit_project_id,
    )
    if project.outcome in {"ambiguous", "unsupported"}:
        return RouteResult(
            status="blocked",
            objective=objective,
            surface=surface,
            project=project,
            selected_workflow=None,
            workflow_candidates=[],
            prompt_recommendation=None,
            backend_recommendation=None,
            agent_recommendation=None,
            skill_recommendations=(),
            workflow_alternatives=(),
            task_family=None,
            blocked_reason=project.rationale,
            rationale=f"Routing blocked until project resolution is safe: {project.rationale}",
        )

    route_primitives = recommend_route_primitives(
        objective,
        surface=surface,
        workflow_registry_path=workflow_registry_path,
        prompt_registry_path=prompt_registry_path,
    )
    selected_workflow = route_primitives.get("selected_workflow")
    workflow_candidates = route_primitives.get("workflow_candidates") or []
    prompt_recommendation = route_primitives.get("prompt_recommendation")
    backend_recommendation = route_primitives.get("backend_recommendation")
    if selected_workflow is None:
        return RouteResult(
            status="blocked",
            objective=objective,
            surface=surface,
            project=project,
            selected_workflow=None,
            workflow_candidates=workflow_candidates,
            prompt_recommendation=prompt_recommendation,
            backend_recommendation=backend_recommendation,
            agent_recommendation=None,
            skill_recommendations=(),
            workflow_alternatives=(),
            task_family=None,
            blocked_reason="No governed workflow matched the objective strongly enough.",
            rationale="Routing blocked because workflow selection returned no viable governed route.",
        )

    workflow_family = str(selected_workflow.get("workflow_family", ""))
    enriched_backend = backend_recommendation
    if backend_recommendation and backend_recommendation.get("selected_surface"):
        backend = get_backend_for_surface(cast(Surface, backend_recommendation["selected_surface"]))
        enriched_backend = {
            **backend_recommendation,
            "selected_backend_key": backend.key,
            "selected_backend_label": backend.label,
        }
    agent_recommendation = {
        "agent_key": "implementation-lead",
        "rationale": (
            f"Defaulted to implementation-lead because {workflow_family or 'the selected workflow'} "
            "still executes through the implementation-oriented harness path."
        ),
    }
    task_classifications = (workflow_family,) if workflow_family else ()
    skill_recommendations = tuple(
        recommend_assets_for_packet(
            conn,
            task_classifications=task_classifications,
            workflow_family=workflow_family,
            project_id=project.selected_project_id,
            asset_kind="skill",
            limit=5,
        )
    )
    workflow_alternatives = tuple(
        recommend_assets_for_packet(
            conn,
            task_classifications=task_classifications,
            workflow_family=workflow_family,
            project_id=project.selected_project_id,
            asset_kind="workflow",
            limit=3,
        )
    )
    if prompt_recommendation and prompt_recommendation.get("template_id"):
        evidence = build_asset_usage_evidence(
            conn,
            asset_kind="prompt",
            asset_key=str(prompt_recommendation["template_id"]),
        )
        prompt_recommendation = {
            **prompt_recommendation,
            "rationale": (
                f"{prompt_recommendation.get('rationale', '')} "
                f"Usefulness evidence: success_rate={evidence.success_rate:.2f}, sample_size={evidence.sample_size}."
            ).strip(),
        }
    return RouteResult(
        status="ready",
        objective=objective,
        surface=surface,
        project=project,
        selected_workflow=selected_workflow,
        workflow_candidates=workflow_candidates,
        prompt_recommendation=prompt_recommendation,
        backend_recommendation=enriched_backend,
        agent_recommendation=agent_recommendation,
        skill_recommendations=skill_recommendations,
        workflow_alternatives=workflow_alternatives,
        task_family=workflow_family,
        blocked_reason=None,
        rationale=(
            f"Resolved project outcome={project.outcome}; selected workflow "
            f"{selected_workflow.get('workflow_key')} with prompt family "
            f"{prompt_recommendation.get('prompt_family') if prompt_recommendation else None}."
        ),
    )
