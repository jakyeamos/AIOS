from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import pytest

import services.aios_cli as aios_cli
from services.automation_trigger import (
    automation_trigger_objective,
    validate_automation_trigger_payload,
)


def test_validate_automation_trigger_payload_preserves_prefixed_objective() -> None:
    payload = validate_automation_trigger_payload(
        {
            "automationId": "automation-1",
            "workflowKey": "implementation-delivery",
            "objective": "Review the current release state",
            "projectId": None,
        }
    )

    assert payload["project_id"] is None
    assert automation_trigger_objective(payload) == (
        "[automation:automation-1] [workflow:implementation-delivery] Review the current release state"
    )


@pytest.mark.parametrize(
    "payload, message",
    [
        ({"automationId": "a", "workflowKey": "w", "objective": "short"}, "at least 8"),
        (
            {
                "automationId": "a",
                "workflowKey": "w",
                "objective": "valid objective",
                "unexpected": True,
            },
            "Unsupported automation trigger fields",
        ),
    ],
)
def test_validate_automation_trigger_payload_rejects_invalid_input(
    payload: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        validate_automation_trigger_payload(payload)


def test_automation_trigger_cli_payload_launches_python_owned_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE orchestration_runs (
          id TEXT PRIMARY KEY,
          project_id TEXT,
          session_id TEXT,
          objective TEXT,
          workflow_key TEXT,
          agent_key TEXT,
          status TEXT,
          rationale TEXT,
          assumptions_json TEXT,
          context_trace_json TEXT,
          created_at TEXT,
          updated_at TEXT,
          completed_at TEXT,
          started_at TEXT,
          failed_at TEXT,
          canceled_at TEXT,
          backend_key TEXT,
          active_invocation_id TEXT,
          superseded_by_run_id TEXT,
          status_reason_json TEXT,
          result_summary TEXT,
          memory_update_id TEXT,
          packet_id TEXT,
          route_id TEXT,
          route_status TEXT,
          route_result_json TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE briefing_packets (
          id TEXT PRIMARY KEY,
          run_id TEXT,
          project_id TEXT,
          objective TEXT,
          workflow_key TEXT,
          agent_key TEXT,
          packet_markdown TEXT,
          sections_json TEXT,
          policy_mode TEXT,
          token_budget INTEGER,
          route_id TEXT,
          route_result_json TEXT,
          selection_trace_json TEXT,
          omitted_context_json TEXT,
          created_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE orchestration_invocations (
          id TEXT PRIMARY KEY,
          run_id TEXT,
          backend_key TEXT,
          backend_label TEXT,
          status TEXT NOT NULL,
          handshake_token TEXT,
          session_id TEXT,
          pid INTEGER,
          command_json TEXT NOT NULL,
          metadata_json TEXT NOT NULL,
          created_at TEXT,
          started_at TEXT,
          ended_at TEXT,
          updated_at TEXT NOT NULL,
          reserved TEXT
        )
        """
    )

    start = {
        "run": {
            "id": "run-1",
            "project_id": None,
            "session_id": None,
            "objective": "[automation:a] [workflow:w] valid objective",
            "workflow_key": "w",
            "agent_key": "agent",
            "backend_key": "codex-managed-runtime",
            "route_id": "route-1",
            "route_status": "ready",
            "status": "ready",
            "packet_id": "packet-1",
            "active_invocation_id": "invoke-manual-1",
        },
        "packet": {
            "id": "packet-1",
            "policy_mode": "compact-ranked",
            "markdown": "packet",
            "sections": [],
            "contract_version": "governed-handoff-v1",
        },
        "invocation": {
            "id": "invoke-manual-1",
            "status": "prepared",
            "backend_key": "codex-managed-runtime",
            "backend_label": "Codex managed runtime",
            "session_id": None,
        },
    }
    conn.execute(
        "INSERT INTO orchestration_invocations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "invoke-manual-1",
            "run-1",
            "codex-managed-runtime",
            "Codex managed runtime",
            "prepared",
            "run-1",
            None,
            None,
            "[]",
            "{}",
            "created",
            None,
            None,
            "before",
            None,
        ),
    )
    conn.execute(
        "INSERT INTO orchestration_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "run-1",
            None,
            None,
            start["run"]["objective"],
            "w",
            "agent",
            "ready",
            "rationale",
            "[]",
            "[]",
            "created",
            "updated",
            None,
            None,
            None,
            None,
            "codex-managed-runtime",
            "invoke-manual-1",
            None,
            "{}",
            None,
            None,
            "packet-1",
            "route-1",
            "ready",
            "{}",
        ),
    )
    conn.execute(
        "INSERT INTO briefing_packets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "packet-1",
            "run-1",
            None,
            start["run"]["objective"],
            "w",
            "agent",
            "packet",
            "[]",
            "compact-ranked",
            900,
            "route-1",
            "{}",
            "[]",
            "[]",
            "created",
        ),
    )
    conn.commit()
    monkeypatch.setattr(aios_cli, "_start_work_payload", lambda *args, **kwargs: start)

    class Child:
        pid = 4242

    monkeypatch.setattr(aios_cli.subprocess, "Popen", lambda *args, **kwargs: Child())

    result = aios_cli._automation_trigger_payload(
        conn,
        argparse.Namespace(
            payload_json=json.dumps(
                {
                    "automationId": "automation-1",
                    "workflowKey": "implementation-delivery",
                    "objective": "valid objective",
                }
            )
        ),
        db_path=tmp_path / "aios.db",
        logs_dir=tmp_path / "logs",
    )

    assert result["schema"] == "automation-trigger-result-v1"
    assert result["automation_id"] == "automation-1"
    assert result["plan"]["run"]["id"] == "run-1"
    assert result["invocation"]["run_detail"]["invocations"][0]["pid"] == 4242
    row = conn.execute(
        "SELECT status, pid, command_json FROM orchestration_invocations WHERE id = ?",
        ("invoke-manual-1",),
    ).fetchone()
    assert row["status"] == "launching"
    assert row["pid"] == 4242
    assert "aios-managed-run.py" in row["command_json"]
    conn.close()
