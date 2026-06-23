from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.retrospective_artifacts import (  # noqa: E402
    list_retrospective_artifacts,
    record_retrospective_artifact,
)


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


def test_retrospective_artifact_defaults_to_reviewable_no_auto_apply() -> None:
    conn = _connect()

    artifact_id = record_retrospective_artifact(
        conn,
        task_id="task-1",
        outcome="failure",
        failed_phase="validate",
        root_cause_category="weak_verification",
        evidence_refs=[{"type": "verifier", "id": "verifier-1"}],
        harness_gap="Verifier was not required before closeout.",
        proposed_change="Require verifier artifacts for implementation workflows.",
        target_file_or_component="config/workflows/registry.json",
        risk="medium",
        should_become="check",
    )

    artifacts = list_retrospective_artifacts(conn, task_id="task-1")

    assert artifacts[0]["id"] == artifact_id
    assert artifacts[0]["auto_apply"] is False
    assert artifacts[0]["learning_proposal"]["event_source"] == "retrospective_artifact"
    assert artifacts[0]["learning_proposal"]["approval_state"] == "pending_review"
    assert artifacts[0]["evidence_refs"] == [{"type": "verifier", "id": "verifier-1"}]
