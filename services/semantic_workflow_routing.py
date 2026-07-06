from __future__ import annotations

import json
import os
import shlex
import subprocess
from collections.abc import Callable, Mapping
from typing import Any

SEMANTIC_ROUTE_CONFIDENCE_THRESHOLD = 0.75
SEMANTIC_ROUTE_COMMAND_ENV = "AIOS_WORKFLOW_SEMANTIC_ROUTER_CMD"
SEMANTIC_ROUTE_COMMAND_TIMEOUT_SECONDS = 20

SemanticWorkflowReasoner = Callable[[dict[str, Any]], dict[str, Any] | None]


def semantic_reasoner_request(
    *,
    objective: str,
    workflows: Mapping[str, Any],
    candidates: list[Any],
) -> dict[str, Any]:
    return {
        "objective": objective,
        "available_workflows": [
            _workflow_route_payload(workflow)
            for workflow in sorted(workflows.values(), key=lambda item: item.key)
            if workflow.lifecycle_state in {"active", "candidate"}
        ],
        "deterministic_candidates": [
            {
                "workflow_key": candidate.workflow_key,
                "workflow_family": candidate.workflow_family,
                "score": candidate.score,
                "matched_terms": list(candidate.matched_terms),
                "rationale": candidate.rationale,
            }
            for candidate in candidates
        ],
        "output_schema": {
            "selected_workflow": "string workflow_key or null",
            "confidence": "number from 0.0 to 1.0",
            "rationale": "short reason grounded in objective and available workflow metadata",
            "alternatives": "optional list of {workflow_key, confidence, rationale}",
        },
    }


def semantic_recommendation(
    *,
    objective: str,
    workflows: Mapping[str, Any],
    candidates: list[Any],
    semantic_reasoner: SemanticWorkflowReasoner | None,
) -> dict[str, Any] | None:
    if semantic_reasoner is None:
        return None
    raw = semantic_reasoner(
        semantic_reasoner_request(
            objective=objective,
            workflows=workflows,
            candidates=candidates,
        )
    )
    if not isinstance(raw, dict):
        return None
    selected_workflow = str(raw.get("selected_workflow") or "").strip()
    confidence = _bounded_float(raw.get("confidence"))
    rationale = str(raw.get("rationale") or "").strip()
    alternatives = raw.get("alternatives")
    if selected_workflow not in workflows:
        return {
            "selected_workflow": selected_workflow or None,
            "confidence": confidence,
            "rationale": rationale,
            "alternatives": alternatives if isinstance(alternatives, list) else [],
            "status": "invalid_workflow",
        }
    return {
        "selected_workflow": selected_workflow,
        "workflow_family": workflows[selected_workflow].workflow_family,
        "confidence": confidence,
        "rationale": rationale,
        "alternatives": alternatives if isinstance(alternatives, list) else [],
        "status": "usable"
        if confidence >= SEMANTIC_ROUTE_CONFIDENCE_THRESHOLD
        else "low_confidence",
    }


def configured_semantic_reasoner() -> SemanticWorkflowReasoner | None:
    command = os.environ.get(SEMANTIC_ROUTE_COMMAND_ENV, "").strip()
    if not command:
        return None
    argv = shlex.split(command)
    if not argv:
        return None

    def reasoner(request: dict[str, Any]) -> dict[str, Any] | None:
        try:
            completed = subprocess.run(
                argv,
                input=json.dumps(request, sort_keys=True),
                text=True,
                capture_output=True,
                check=False,
                timeout=SEMANTIC_ROUTE_COMMAND_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            return {
                "selected_workflow": None,
                "confidence": 0.0,
                "rationale": "Semantic router command timed out.",
            }
        except OSError as exc:
            return {
                "selected_workflow": None,
                "confidence": 0.0,
                "rationale": f"Semantic router command could not run: {exc}",
            }
        if completed.returncode != 0:
            return {
                "selected_workflow": None,
                "confidence": 0.0,
                "rationale": completed.stderr.strip() or "Semantic router command failed.",
            }
        try:
            parsed = json.loads(completed.stdout.strip())
        except json.JSONDecodeError:
            return {
                "selected_workflow": None,
                "confidence": 0.0,
                "rationale": "Semantic router command returned non-JSON output.",
            }
        return parsed if isinstance(parsed, dict) else None

    return reasoner


def _workflow_route_payload(workflow: Any) -> dict[str, Any]:
    return {
        "workflow_key": workflow.key,
        "workflow_family": workflow.workflow_family,
        "name": workflow.name,
        "purpose": workflow.purpose,
        "trigger_hints": list(workflow.trigger_hints),
        "applicability": list(workflow.applicability),
        "lifecycle_state": workflow.lifecycle_state,
    }


def _bounded_float(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, parsed))
