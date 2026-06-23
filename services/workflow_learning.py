from __future__ import annotations

from typing import Any


def retrospective_artifact_learning_proposal(artifact: dict[str, Any]) -> dict[str, Any]:
    """Convert a retrospective artifact into a reviewable learning proposal."""
    return {
        "event_source": "retrospective_artifact",
        "task_id": artifact.get("task_id"),
        "proposal_target": artifact.get("target_file_or_component"),
        "should_become": artifact.get("should_become"),
        "proposed_change": artifact.get("proposed_change"),
        "harness_gap": artifact.get("harness_gap"),
        "auto_apply": False,
        "approval_state": "pending_review",
    }
