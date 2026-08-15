from __future__ import annotations

from collections.abc import Mapping
from typing import TypedDict


class AutomationTriggerPayload(TypedDict):
    automation_id: str
    workflow_key: str
    objective: str
    project_id: str | None


MUTABLE_FIELDS = {"automationId", "workflowKey", "objective", "projectId"}


def _required_string(
    payload: Mapping[str, object], key: str, *, minimum: int, maximum: int | None = None
) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or len(value) < minimum:
        raise ValueError(f"{key} must be a string with at least {minimum} characters")
    if maximum is not None and len(value) > maximum:
        raise ValueError(f"{key} exceeds the {maximum}-character limit")
    return value


def validate_automation_trigger_payload(
    payload: Mapping[str, object],
) -> AutomationTriggerPayload:
    """Validate the automation trigger boundary before orchestration writes."""

    unknown = set(payload) - MUTABLE_FIELDS
    if unknown:
        names = ", ".join(sorted(str(name) for name in unknown))
        raise ValueError(f"Unsupported automation trigger fields: {names}")

    project_id = payload.get("projectId")
    if project_id is not None and (not isinstance(project_id, str) or len(project_id) < 1):
        raise ValueError("projectId must be a non-empty string or null")

    return {
        "automation_id": _required_string(payload, "automationId", minimum=1),
        "workflow_key": _required_string(payload, "workflowKey", minimum=1),
        "objective": _required_string(payload, "objective", minimum=8, maximum=500),
        "project_id": project_id,
    }


def automation_trigger_objective(payload: AutomationTriggerPayload) -> str:
    return (
        f"[automation:{payload['automation_id']}] "
        f"[workflow:{payload['workflow_key']}] {payload['objective']}"
    )
