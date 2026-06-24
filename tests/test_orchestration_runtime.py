"""
Regression tests for the orchestration runtime/control-plane handshake.

Run from the repository root:
    python3 -m pytest tests/test_orchestration_runtime.py -v
"""

import importlib.util
import io
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin"))


def _load_module(module_name: str, relative_path: str):
    module_path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _apply_base_schema(conn: sqlite3.Connection) -> None:
    schema = (ROOT / "schema.sql").read_text()
    conn.executescript(schema)


def _insert_project(conn: sqlite3.Connection, repo_path: Path) -> str:
    project_id = "project-aios"
    conn.execute(
        """
        INSERT INTO projects (id, name, repo_path, obsidian_path, status)
        VALUES (?, 'AIOS', ?, ?, 'active')
        """,
        (project_id, str(repo_path), str(repo_path)),
    )
    return project_id


def _legacy_workflow_learning_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE workflow_learning_events (
            id TEXT PRIMARY KEY,
            run_id TEXT,
            evidence_type TEXT NOT NULL,
            proposal_target TEXT,
            confidence REAL NOT NULL DEFAULT 0.5,
            approval_state TEXT NOT NULL DEFAULT 'not_required',
            rationale TEXT NOT NULL,
            source_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """
    )


def test_signal_kind_column_added_idempotently() -> None:
    from aios_orchestration_runtime import _ensure_workflow_learning_signal_kind_column

    conn = sqlite3.connect(":memory:")
    _legacy_workflow_learning_table(conn)

    _ensure_workflow_learning_signal_kind_column(conn)
    _ensure_workflow_learning_signal_kind_column(conn)

    columns = [
        row[1] for row in conn.execute("PRAGMA table_info(workflow_learning_events)").fetchall()
    ]
    assert columns.count("signal_kind") == 1
    index = conn.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type = 'index' AND name = 'idx_workflow_learning_events_signal'
        """
    ).fetchone()
    assert index is not None


def test_signal_kind_column_left_alone_when_present() -> None:
    from aios_orchestration_runtime import _ensure_workflow_learning_signal_kind_column

    conn = sqlite3.connect(":memory:")
    _legacy_workflow_learning_table(conn)
    conn.execute("ALTER TABLE workflow_learning_events ADD COLUMN signal_kind TEXT")

    _ensure_workflow_learning_signal_kind_column(conn)

    columns = [
        row[1] for row in conn.execute("PRAGMA table_info(workflow_learning_events)").fetchall()
    ]
    assert columns.count("signal_kind") == 1


def test_ensure_runtime_schema_invokes_signal_kind_helper() -> None:
    from aios_orchestration_runtime import ensure_runtime_schema

    conn = sqlite3.connect(":memory:")
    _apply_base_schema(conn)
    ensure_runtime_schema(conn)

    columns = [
        row[1] for row in conn.execute("PRAGMA table_info(workflow_learning_events)").fetchall()
    ]
    assert "signal_kind" in columns


def test_writeback_policy_route_default_requires_approval() -> None:
    from aios_orchestration_runtime import writeback_approval_policy

    policy = writeback_approval_policy(
        layer_type="route",
        impact_scope="route-default",
        proposed_change=None,
    )

    assert policy == {
        "policy_class": "route-default_change",
        "requires_approval": True,
        "reason": "route-default changes require approval before promotion.",
    }


def test_writeback_policy_packet_default_requires_approval() -> None:
    from aios_orchestration_runtime import writeback_approval_policy

    policy = writeback_approval_policy(
        layer_type="packet",
        impact_scope="packet-default",
        proposed_change=None,
    )

    assert policy == {
        "policy_class": "packet-default_change",
        "requires_approval": True,
        "reason": "packet-default changes require approval before promotion.",
    }


def test_writeback_policy_existing_scopes_unchanged() -> None:
    from aios_orchestration_runtime import writeback_approval_policy

    for scope in (
        "global",
        "project-truth",
        "workflow-default",
        "prompt-default",
        "skill-default",
        "standards-default",
    ):
        policy = writeback_approval_policy(
            layer_type="workflow",
            impact_scope=scope,
            proposed_change=None,
        )
        assert policy["requires_approval"] is True
        assert policy["policy_class"] == f"{scope}_change"

    scoped = writeback_approval_policy(
        layer_type="memory",
        impact_scope="scoped",
        proposed_change=None,
    )
    assert scoped["requires_approval"] is False


def test_pre_migration_rows_remain_visible_in_select() -> None:
    from aios_orchestration_runtime import _ensure_workflow_learning_signal_kind_column

    conn = sqlite3.connect(":memory:")
    _legacy_workflow_learning_table(conn)
    conn.execute(
        """
        INSERT INTO workflow_learning_events (
            id, run_id, evidence_type, proposal_target, confidence,
            approval_state, rationale, source_json
        )
        VALUES ('event-1', 'run-1', 'workflow_evidence', 'workflow', 0.7,
                'not_required', 'legacy', '{}')
        """
    )

    _ensure_workflow_learning_signal_kind_column(conn)

    row = conn.execute(
        "SELECT id, signal_kind FROM workflow_learning_events WHERE id = 'event-1'"
    ).fetchone()
    assert row == ("event-1", None)


@pytest.fixture
def runtime_db(tmp_path: Path) -> Path:
    from aios_orchestration_runtime import ensure_runtime_schema

    db_path = tmp_path / "aios.db"
    conn = sqlite3.connect(db_path)
    _apply_base_schema(conn)
    ensure_runtime_schema(conn)
    conn.commit()
    conn.close()
    return db_path


def test_hook_stop_uses_explicit_run_handshake(
    runtime_db: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hook_stop = _load_module("hook_stop", "bin/hook-stop.py")

    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    (repo_path / "PROJECT.md").write_text("# AIOS\n\n## Still Missing\n- Old gap\n")

    conn = sqlite3.connect(runtime_db)
    project_id = _insert_project(conn, repo_path)
    session_id = "session-explicit"
    run_id = "run-explicit"
    invocation_id = "invoke-explicit"

    conn.execute(
        """
        INSERT INTO sessions (id, project_id, tool, started_at, objective, status, cwd)
        VALUES (?, ?, 'claude-code', '2026-04-19T00:00:00Z', 'Close the run explicitly', 'open', ?)
        """,
        (session_id, project_id, str(repo_path)),
    )
    conn.execute(
        """
        INSERT INTO orchestration_runs (
            id, project_id, objective, workflow_key, agent_key, status, rationale,
            assumptions_json, context_trace_json, created_at, updated_at
        )
        VALUES (?, ?, 'Close the run explicitly', 'implementation-delivery', 'implementation-lead',
                'ready', 'Test rationale', '[]', '[]', '2026-04-19T00:00:00Z', '2026-04-19T00:00:00Z')
        """,
        (run_id, project_id),
    )
    conn.execute(
        """
        INSERT INTO orchestration_invocations (
            id, run_id, backend_key, backend_label, status, handshake_token,
            command_json, metadata_json, created_at, updated_at
        )
        VALUES (?, ?, 'aios-managed-runtime', 'AIOS Managed Runtime', 'launching', ?, '[]', '{}',
                '2026-04-19T00:00:00Z', '2026-04-19T00:00:00Z')
        """,
        (invocation_id, run_id, run_id),
    )
    conn.execute(
        """
        UPDATE sessions
        SET run_id = ?, invocation_id = ?, runtime_metadata_json = ?
        WHERE id = ?
        """,
        (run_id, invocation_id, json.dumps({"backend_key": "aios-managed-runtime"}), session_id),
    )
    conn.execute(
        """
        INSERT INTO artifacts (id, session_id, artifact_type, path, metadata_json, created_at)
        VALUES ('artifact-patch', ?, 'patch', ?, '{}', '2026-04-19T00:00:00Z')
        """,
        (session_id, str(repo_path / "services" / "orchestration.py")),
    )
    conn.execute(
        """
        INSERT INTO artifacts (id, session_id, artifact_type, path, metadata_json, created_at)
        VALUES ('artifact-report', ?, 'control-plane-report', ?, '{}', '2026-04-19T00:01:00Z')
        """,
        (session_id, str(tmp_path / "reports" / "invocation.json")),
    )
    conn.commit()
    conn.close()

    captured_criteria_args: dict[str, object] = {}

    def _fake_evaluate_and_record(_conn: sqlite3.Connection, **kwargs: object) -> dict[str, object]:
        captured_criteria_args.update(kwargs)
        return {
            "evaluation_id": "criteria-eval-test",
            "summary": "ok",
            "counts": {"pass": 1, "warning": 0, "blocker": 0},
            "criteria_ids": ["code-simplicity"],
        }

    monkeypatch.setattr(hook_stop, "DB", str(runtime_db))
    monkeypatch.setattr(hook_stop, "LOG", str(tmp_path / "hooks.log"))
    monkeypatch.setattr(hook_stop, "SUMMARIES_DIR", str(tmp_path / "summaries"))
    monkeypatch.setattr(hook_stop, "evaluate_and_record", _fake_evaluate_and_record)
    monkeypatch.setattr(hook_stop.subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        hook_stop,
        "find_matching_orchestration_run",
        lambda *_args, **_kwargs: pytest.fail(
            "legacy matcher should not run for explicit handshake"
        ),
    )
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            json.dumps(
                {
                    "session_id": session_id,
                    "run_id": run_id,
                    "invocation_id": invocation_id,
                    "run_outcome": "completed",
                    "result_summary": "Managed runtime completed successfully.",
                    "reason_json": {"kind": "normal_exit"},
                }
            )
        ),
    )

    hook_stop.main()

    conn = sqlite3.connect(runtime_db)
    run = conn.execute(
        """
        SELECT status, session_id, result_summary, completed_at, active_invocation_id
        FROM orchestration_runs
        WHERE id = ?
        """,
        (run_id,),
    ).fetchone()
    assert run is not None
    assert run[0] == "completed"
    assert run[1] == session_id
    assert run[2] == "Managed runtime completed successfully."
    assert run[3] is not None
    assert run[4] == invocation_id

    invocation = conn.execute(
        "SELECT status, session_id, ended_at FROM orchestration_invocations WHERE id = ?",
        (invocation_id,),
    ).fetchone()
    assert invocation == ("completed", session_id, invocation[2])

    event_rows = conn.execute(
        """
        SELECT event_type, to_status, summary
        FROM orchestration_run_events
        WHERE run_id = ?
        ORDER BY created_at
        """,
        (run_id,),
    ).fetchall()
    assert ("completed", "completed", "Managed runtime completed successfully.") in event_rows
    closeout_report = conn.execute(
        """
        SELECT status, report_json, artifact_path
        FROM workflow_execution_reports
        WHERE run_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (run_id,),
    ).fetchone()
    assert closeout_report is not None
    report_payload = json.loads(closeout_report[1])
    assert closeout_report[0] == "completed"
    assert report_payload["report_type"] == "governed_closeout"
    assert report_payload["checks_run"]["success_criteria_evaluation_id"] == "criteria-eval-test"
    assert report_payload["governance"]["approval_required_count"] >= 1
    assert "workflow-default_change" in report_payload["governance"]["approval_policy_classes"]
    assert report_payload["governance"]["requires_review"] is True
    assert isinstance(report_payload["changed_artifacts"], list)
    assert closeout_report[2] is not None
    assert captured_criteria_args["changed_files"] == [
        str(repo_path / "services" / "orchestration.py")
    ]
    conn.close()


def test_base_schema_exposes_route_metadata_columns(runtime_db: Path) -> None:
    conn = sqlite3.connect(runtime_db)
    run_columns = {
        row[1] for row in conn.execute("PRAGMA table_info(orchestration_runs)").fetchall()
    }
    packet_columns = {
        row[1] for row in conn.execute("PRAGMA table_info(briefing_packets)").fetchall()
    }

    assert {"route_id", "route_status", "route_result_json"} <= run_columns
    assert {"route_id", "route_result_json"} <= packet_columns
    conn.close()


def test_closeout_governance_includes_stage_evaluations(runtime_db: Path) -> None:
    hook_stop = _load_module("hook_stop", "bin/hook-stop.py")
    conn = sqlite3.connect(runtime_db)
    conn.execute(
        """
        INSERT INTO orchestration_runs (
            id, objective, workflow_key, agent_key, status, rationale,
            assumptions_json, context_trace_json
        )
        VALUES ('run-stage', 'Test stage findings', 'agentize', 'agentize', 'completed',
                'test', '[]', '[]')
        """
    )
    conn.execute(
        """
        INSERT INTO success_criteria_stage_findings (
            id, run_id, stage_key, stage_kind, criterion_id, criterion_title,
            criterion_scope, level, summary
        )
        VALUES
            ('criteria-stage-finding-1', 'run-stage', 'validate', 'validate',
             'testing-trust', 'Testing Trust', 'global', 'blocker', 'Missing test evidence.'),
            ('criteria-stage-finding-2', 'run-stage', 'validate', 'validate',
             'truth-file-consistency', 'Truth File', 'global', 'pass', 'Truth update present.')
        """
    )

    stage_evaluations = hook_stop._stage_evaluations_for_run(conn, "run-stage")

    assert stage_evaluations == [
        {
            "stage_key": "validate",
            "stage_kind": "validate",
            "blocker_count": 1,
            "warning_count": 0,
            "pass_count": 1,
            "finding_ids": ["criteria-stage-finding-1", "criteria-stage-finding-2"],
        }
    ]
    conn.close()


def test_execution_first_accepts_tool_event_evidence(runtime_db: Path) -> None:
    hook_stop = _load_module("hook_stop", "bin/hook-stop.py")
    conn = sqlite3.connect(runtime_db)
    conn.execute(
        """
        INSERT INTO sessions (id, project_id, tool, started_at, status, cwd)
        VALUES ('session-evidence', 'p1', 'claude-code', '2026-04-23T00:00:00Z', 'open', '/tmp')
        """
    )
    conn.execute(
        """
        INSERT INTO tool_events (id, session_id, source_tool, event_type, event_time, payload_json)
        VALUES ('tool-1', 'session-evidence', 'claude-code', 'Bash',
                '2026-04-23T00:01:00Z', ?)
        """,
        (json.dumps({"command": "uv run pytest tests/test_success_criteria.py"}),),
    )

    evidence = hook_stop.execution_evidence_for_session(conn, "session-evidence")

    assert "tool-event: uv run pytest tests/test_success_criteria.py" in evidence
    conn.close()


def test_execution_first_accepts_workflow_report_stage_evidence(runtime_db: Path) -> None:
    hook_stop = _load_module("hook_stop", "bin/hook-stop.py")
    conn = sqlite3.connect(runtime_db)
    conn.execute(
        """
        INSERT INTO sessions (id, project_id, tool, started_at, status, cwd, run_id)
        VALUES ('session-evidence', 'p1', 'claude-code', '2026-04-23T00:00:00Z',
                'open', '/tmp', 'run-evidence')
        """
    )
    conn.execute(
        """
        INSERT INTO orchestration_runs (
            id, objective, workflow_key, agent_key, status, rationale,
            assumptions_json, context_trace_json
        )
        VALUES ('run-evidence', 'Test workflow evidence', 'agentize', 'agentize',
                'completed', 'test', '[]', '[]')
        """
    )
    conn.execute(
        """
        INSERT INTO workflow_execution_reports (
            id, run_id, workflow_key, status, report_json
        )
        VALUES ('report-evidence', 'run-evidence', 'agentize', 'completed', ?)
        """,
        (
            json.dumps(
                {
                    "stages": [
                        {
                            "stage_key": "validate",
                            "kind": "validate",
                            "test_command": "uv run pytest tests/test_agentize.py",
                        }
                    ]
                }
            ),
        ),
    )

    evidence = hook_stop.execution_evidence_for_session(conn, "session-evidence")

    assert "workflow-stage: validate: uv run pytest tests/test_agentize.py" in evidence
    conn.close()


def test_insert_writeback_derives_approval_policy_for_high_impact_changes(
    runtime_db: Path, tmp_path: Path
) -> None:
    from aios_orchestration_runtime import ensure_runtime_schema, insert_writeback

    conn = sqlite3.connect(runtime_db)
    project_id = _insert_project(conn, tmp_path)
    ensure_runtime_schema(conn)
    conn.execute(
        """
        INSERT INTO orchestration_runs (
            id, project_id, objective, workflow_key, agent_key, status, rationale,
            assumptions_json, context_trace_json, created_at, updated_at
        )
        VALUES (
            'run-policy', ?, 'Change workflow defaults', 'implementation-delivery',
            'implementation-lead', 'completed', 'Policy test', '[]', '[]',
            '2026-05-19T00:00:00Z', '2026-05-19T00:00:00Z'
        )
        """,
        (project_id,),
    )

    writeback_id = insert_writeback(
        conn,
        run_id="run-policy",
        project_id=project_id,
        layer_type="workflow",
        layer_key="implementation-delivery",
        title="Workflow default proposal",
        summary="Change the default workflow behavior.",
        evidence=["workflow result"],
        proposed_change={"default_packet_policy": "explore"},
        impact_scope="workflow-default",
    )
    row = conn.execute(
        """
        SELECT status, requires_approval, approval_reason, proposed_change_json
        FROM improvement_writebacks
        WHERE id = ?
        """,
        (writeback_id,),
    ).fetchone()
    event = conn.execute(
        """
        SELECT metadata_json
        FROM improvement_writeback_events
        WHERE writeback_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (writeback_id,),
    ).fetchone()
    conn.close()

    proposed_change = json.loads(row[3])
    event_metadata = json.loads(event[0])
    assert row[0] == "pending_approval"
    assert row[1] == 1
    assert "workflow-default changes require approval" in row[2]
    assert proposed_change["approval_policy"]["policy_class"] == "workflow-default_change"
    assert event_metadata["approval_policy"]["requires_approval"] is True


def test_runtime_transition_records_failed_reason_metadata(
    runtime_db: Path, tmp_path: Path
) -> None:
    from aios_orchestration_runtime import ensure_runtime_schema, transition_run

    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    (repo_path / "PROJECT.md").write_text("# AIOS\n")

    conn = sqlite3.connect(runtime_db)
    project_id = _insert_project(conn, repo_path)
    ensure_runtime_schema(conn)
    run_id = "run-failed"

    conn.execute(
        """
        INSERT INTO orchestration_runs (
            id, project_id, objective, workflow_key, agent_key, status, rationale,
            assumptions_json, context_trace_json, created_at, updated_at
        )
        VALUES (?, ?, 'Managed runtime fails', 'implementation-delivery', 'debug-surgeon',
                'in_progress', 'Failure path', '[]', '[]', '2026-04-19T00:00:00Z', '2026-04-19T00:00:00Z')
        """,
        (run_id, project_id),
    )

    transition_run(
        conn,
        run_id=run_id,
        to_status="failed",
        event_type="failed",
        summary="Backend command crashed.",
        reason={"kind": "exception", "error": "RuntimeError", "message": "boom"},
    )
    conn.commit()

    run = conn.execute(
        "SELECT status, status_reason_json, failed_at FROM orchestration_runs WHERE id = ?",
        (run_id,),
    ).fetchone()
    assert run is not None
    assert run[0] == "failed"
    assert json.loads(run[1]) == {"kind": "exception", "error": "RuntimeError", "message": "boom"}
    assert run[2] is not None

    event = conn.execute(
        """
        SELECT event_type, to_status, reason_json
        FROM orchestration_run_events
        WHERE run_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (run_id,),
    ).fetchone()
    assert event is not None
    assert event[0] == "failed"
    assert event[1] == "failed"
    assert json.loads(event[2]) == {"kind": "exception", "error": "RuntimeError", "message": "boom"}
    conn.close()


def test_runtime_transition_records_partial_closeout_metadata(
    runtime_db: Path, tmp_path: Path
) -> None:
    from aios_orchestration_runtime import ensure_runtime_schema, transition_run

    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    (repo_path / "PROJECT.md").write_text("# AIOS\n")

    conn = sqlite3.connect(runtime_db)
    project_id = _insert_project(conn, repo_path)
    ensure_runtime_schema(conn)
    run_id = "run-partial"

    conn.execute(
        """
        INSERT INTO orchestration_runs (
            id, project_id, objective, workflow_key, agent_key, status, rationale,
            assumptions_json, context_trace_json, created_at, updated_at
        )
        VALUES (?, ?, 'Ship partial workflow progress', 'implementation-delivery', 'implementation-lead',
                'in_progress', 'Partial path', '[]', '[]', '2026-04-19T00:00:00Z', '2026-04-19T00:00:00Z')
        """,
        (run_id, project_id),
    )

    transition_run(
        conn,
        run_id=run_id,
        to_status="partial",
        event_type="partial",
        summary="Scoped implementation shipped; follow-up verification remains.",
        reason={"kind": "partial_closeout", "remaining": ["broader regression pass"]},
    )
    conn.commit()

    run = conn.execute(
        "SELECT status, status_reason_json, completed_at FROM orchestration_runs WHERE id = ?",
        (run_id,),
    ).fetchone()
    assert run is not None
    assert run[0] == "partial"
    assert json.loads(run[1]) == {
        "kind": "partial_closeout",
        "remaining": ["broader regression pass"],
    }
    assert run[2] is not None

    event = conn.execute(
        """
        SELECT event_type, to_status, reason_json
        FROM orchestration_run_events
        WHERE run_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (run_id,),
    ).fetchone()
    assert event is not None
    assert event[0] == "partial"
    assert event[1] == "partial"
    assert json.loads(event[2]) == {
        "kind": "partial_closeout",
        "remaining": ["broader regression pass"],
    }
    conn.close()


def test_runtime_persists_resume_snapshot(runtime_db: Path, tmp_path: Path) -> None:
    from aios_orchestration_runtime import (
        ensure_runtime_schema,
        load_resume_snapshot,
        store_resume_snapshot,
    )

    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    (repo_path / "PROJECT.md").write_text("# AIOS\n")

    conn = sqlite3.connect(runtime_db)
    project_id = _insert_project(conn, repo_path)
    ensure_runtime_schema(conn)
    run_id = "run-resume"

    conn.execute(
        """
        INSERT INTO orchestration_runs (
            id, project_id, objective, workflow_key, agent_key, status, rationale,
            assumptions_json, context_trace_json, created_at, updated_at
        )
        VALUES (?, ?, 'Resume workflow execution', 'implementation-delivery', 'implementation-lead',
                'waiting_for_user', 'Resume path', '[]', '[]', '2026-04-19T00:00:00Z', '2026-04-19T00:00:00Z')
        """,
        (run_id, project_id),
    )

    store_resume_snapshot(
        conn,
        run_id,
        {
            "packet_id": "packet-resume",
            "current_stage": "awaiting_approval",
            "next_recommended_action": "Review the pending writeback and resume the run.",
            "pending_approval_count": 1,
            "approval_targets": ["workflow-default"],
        },
    )
    conn.commit()

    snapshot = load_resume_snapshot(conn, run_id)
    assert snapshot["packet_id"] == "packet-resume"
    assert snapshot["current_stage"] == "awaiting_approval"
    assert snapshot["pending_approval_count"] == 1
    assert snapshot["approval_targets"] == ["workflow-default"]
    conn.close()


def test_legacy_linkage_requires_explicit_emergency_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    hook_stop = _load_module("hook_stop_fallback", "bin/hook-stop.py")

    monkeypatch.delenv("AIOS_ALLOW_LEGACY_RUN_LINK", raising=False)
    assert hook_stop.legacy_run_link_fallback_enabled() is False

    monkeypatch.setenv("AIOS_ALLOW_LEGACY_RUN_LINK", "1")
    assert hook_stop.legacy_run_link_fallback_enabled() is True


def test_structured_evaluator_emits_stale_and_contradiction_findings(
    runtime_db: Path, tmp_path: Path
) -> None:
    from aios_orchestration_runtime import ensure_runtime_schema, evaluate_run_consistency

    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    (repo_path / "PROJECT.md").write_text(
        "\n".join(
            [
                "# AIOS",
                "",
                "Last updated: 2026-04-18",
                "",
                "## Still Missing",
                "- explicit run/session handshake",
                "- approval UI for global changes",
                "",
                "## Guardrails",
                "- compact ranked output reaches the agent by default",
            ]
        )
    )

    conn = sqlite3.connect(runtime_db)
    project_id = _insert_project(conn, repo_path)
    ensure_runtime_schema(conn)

    run_id = "run-eval"
    packet_id = "packet-eval"
    conn.execute(
        """
        INSERT INTO orchestration_runs (
            id, project_id, objective, workflow_key, agent_key, status, rationale,
            assumptions_json, context_trace_json, packet_id, result_summary,
            completed_at, created_at, updated_at
        )
        VALUES (
            ?, ?, 'Implement explicit run handshake and approval UI',
            'knowledge-os-evolution', 'implementation-lead', 'completed',
            'Evaluator test', '[]', '[]', ?, 'Explicit handshake shipped with approval controls.',
            '2026-04-19T12:00:00Z', '2026-04-19T12:00:00Z', '2026-04-19T12:00:00Z'
        )
        """,
        (run_id, project_id, packet_id),
    )
    conn.execute(
        """
        INSERT INTO briefing_packets (
            id, run_id, project_id, objective, workflow_key, agent_key, packet_markdown,
            sections_json, policy_mode, token_budget, selection_trace_json, omitted_context_json, created_at
        )
        VALUES (
            ?, ?, ?, 'Implement explicit run handshake and approval UI',
            'knowledge-os-evolution', 'implementation-lead', 'packet',
            ?, 'explore', 1500, '[]', '[]', '2026-04-19T11:55:00Z'
        )
        """,
        (
            packet_id,
            run_id,
            project_id,
            json.dumps(
                [
                    {
                        "title": "Objective",
                        "items": ["explicit run/session handshake", "approval UI"],
                    },
                    {"title": "Policy", "items": ["Use compact ranked output by default."]},
                ]
            ),
        ),
    )
    conn.execute(
        """
        INSERT INTO memory_updates (
            id, project_id, run_id, packet_id, source, summary,
            changes_json, risks_json, open_questions_json, created_at
        )
        VALUES (
            'memory-eval', ?, ?, ?, 'hook-stop',
            'Shipped the explicit run handshake and approval UI.',
            ?, ?, ?, '2026-04-19T12:01:00Z'
        )
        """,
        (
            project_id,
            run_id,
            packet_id,
            json.dumps(["Added explicit run/session handshake", "Added approval UI"]),
            json.dumps(["Run objective still conflicts with a recent canceled attempt"]),
            json.dumps(["Should compact-ranked remain the only default?"]),
        ),
    )
    conn.execute(
        """
        INSERT INTO artifacts (id, session_id, artifact_type, path, metadata_json, created_at)
        VALUES (
            'artifact-unpredicted', 'session-eval', 'patch', ?, ?,
            '2026-04-19T12:02:00Z'
        )
        """,
        (
            str(repo_path / "services" / "new_runtime.py"),
            json.dumps({"run_id": run_id}),
        ),
    )
    conn.execute(
        """
        INSERT INTO standards_health_snapshots (
            id, project_id, profile_id, attached_version, latest_version, standards_version,
            overall_score, weighted_delta, max_penalty, unmet_standards_count, critical_delta_count,
            regression_count, unknown_count, unknown_coverage, evaluation_confidence,
            domain_scores_json, score_explain_json, migration_json, created_at
        )
        VALUES (
            'health-eval', ?, 'aios-core', '2026.04.0', '2026.05.0', '2026.05.0',
            72.0, 12.0, 40.0, 3, 1, 0, 2, 0.25, 0.7,
            '{}', '{}', '{}', '2026-04-19T12:03:00Z'
        )
        """,
        (project_id,),
    )
    conn.execute(
        """
        INSERT INTO orchestration_runs (
            id, project_id, objective, workflow_key, agent_key, status, rationale,
            assumptions_json, context_trace_json, created_at, updated_at
        )
        VALUES (
            'run-canceled', ?, 'Implement explicit run handshake',
            'implementation-delivery', 'debug-surgeon', 'canceled',
            'Canceled attempt', '[]', '[]', '2026-04-19T10:00:00Z', '2026-04-19T10:00:00Z'
        )
        """,
        (project_id,),
    )
    conn.commit()

    evaluation_id = evaluate_run_consistency(conn, run_id)
    findings = conn.execute(
        """
        SELECT finding_kind, rule_key, summary
        FROM consistency_findings
        WHERE evaluation_id = ?
        ORDER BY finding_kind, rule_key
        """,
        (evaluation_id,),
    ).fetchall()
    conn.close()

    kinds = {row[0] for row in findings}
    assert "likely_stale" in kinds
    assert "direct_contradiction" in kinds
    assert "soft_tension" in kinds
    assert "file_topic_delta" in kinds
    assert "standards_evidence_gap" in kinds


def test_managed_runtime_completes_via_explicit_handshake(runtime_db: Path, tmp_path: Path) -> None:
    from aios_orchestration_runtime import ensure_runtime_schema

    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    (repo_path / "PROJECT.md").write_text(
        "\n".join(
            [
                "# AIOS",
                "",
                "Last updated: 2026-04-19",
                "",
                "## Guardrails",
                "- compact ranked output reaches the agent by default",
            ]
        )
    )

    home = tmp_path / "home"
    (home / "AIOS" / "logs").mkdir(parents=True)

    conn = sqlite3.connect(runtime_db)
    project_id = _insert_project(conn, repo_path)
    ensure_runtime_schema(conn)
    run_id = "run-managed"
    invocation_id = "invoke-managed"
    packet_id = "packet-managed"

    conn.execute(
        """
        INSERT INTO orchestration_runs (
            id, project_id, objective, workflow_key, agent_key, status, rationale,
            assumptions_json, context_trace_json, backend_key, packet_id, created_at, updated_at
        )
        VALUES (
            ?, ?, 'Managed runtime handshake integration',
            'implementation-delivery', 'implementation-lead', 'ready',
            'Managed runtime test', '[]', '[]', 'aios-managed-runtime', ?, '2026-04-19T00:00:00Z', '2026-04-19T00:00:00Z'
        )
        """,
        (run_id, project_id, packet_id),
    )
    conn.execute(
        """
        INSERT INTO briefing_packets (
            id, run_id, project_id, objective, workflow_key, agent_key,
            packet_markdown, sections_json, policy_mode, token_budget,
            selection_trace_json, omitted_context_json, created_at
        )
        VALUES (
            ?, ?, ?, 'Managed runtime handshake integration',
            'implementation-delivery', 'implementation-lead',
            'packet', '[]', 'compact-ranked', 900, '[]', '[]', '2026-04-19T00:00:00Z'
        )
        """,
        (packet_id, run_id, project_id),
    )
    conn.execute(
        """
        INSERT INTO orchestration_invocations (
            id, run_id, backend_key, backend_label, status, handshake_token,
            command_json, metadata_json, created_at, updated_at
        )
        VALUES (
            ?, ?, 'aios-managed-runtime', 'AIOS Managed Runtime', 'launching', ?,
            '[]', '{}', '2026-04-19T00:00:00Z', '2026-04-19T00:00:00Z'
        )
        """,
        (invocation_id, run_id, run_id),
    )
    conn.commit()
    conn.close()

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "bin" / "aios-managed-run.py"),
            "--run-id",
            run_id,
            "--invocation-id",
            invocation_id,
            "--db",
            str(runtime_db),
        ],
        cwd=str(ROOT),
        env={
            **os.environ,
            "HOME": str(home),
            "AIOS_DB": str(runtime_db),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout

    conn = sqlite3.connect(runtime_db)
    run = conn.execute(
        """
        SELECT status, session_id, active_invocation_id, completed_at
        FROM orchestration_runs
        WHERE id = ?
        """,
        (run_id,),
    ).fetchone()
    assert run is not None
    assert run[0] == "completed"
    assert run[1] is not None
    assert run[2] == invocation_id
    assert run[3] is not None

    invocation = conn.execute(
        """
        SELECT status, session_id, started_at, ended_at
        FROM orchestration_invocations
        WHERE id = ?
        """,
        (invocation_id,),
    ).fetchone()
    assert invocation is not None
    assert invocation[0] == "completed"
    assert invocation[1] == run[1]
    assert invocation[2] is not None
    assert invocation[3] is not None

    workflow_report = conn.execute(
        """
        SELECT workflow_key, status, artifact_path, report_json
        FROM workflow_execution_reports
        WHERE run_id = ?
        LIMIT 1
        """,
        (run_id,),
    ).fetchone()
    assert workflow_report is not None
    assert workflow_report[0] == "implementation-delivery"
    assert workflow_report[1] == "completed"
    assert workflow_report[2] is not None
    workflow_payload = json.loads(workflow_report[3])
    assert workflow_payload["stage_evaluations"][2]["stage_finding_ids"]
    assert workflow_payload["artifacts"]["tmcp_packet"]["task_id"] == "agent_workflow"
    assert workflow_payload["artifacts"]["tmcp_packet"]["receipt_id"]
    assert workflow_payload["artifacts"]["tmcp_packet_path"]
    assert (
        conn.execute(
            "SELECT COUNT(*) FROM success_criteria_stage_findings WHERE run_id = ?",
            (run_id,),
        ).fetchone()[0]
        > 0
    )

    workflow_artifact = conn.execute(
        """
        SELECT artifact_type, path
        FROM artifacts
        WHERE session_id = ? AND artifact_type = 'workflow-execution-report'
        LIMIT 1
        """,
        (run[1],),
    ).fetchone()
    assert workflow_artifact is not None
    assert workflow_artifact[1] == workflow_report[2]

    tmcp_receipt = conn.execute(
        """
        SELECT task_id, traversal_fingerprint, packet_json
        FROM tmcp_traversal_receipts
        WHERE run_id = ? AND invocation_id = ?
        LIMIT 1
        """,
        (run_id, invocation_id),
    ).fetchone()
    assert tmcp_receipt is not None
    assert tmcp_receipt[0] == "agent_workflow"
    assert tmcp_receipt[1]
    assert json.loads(tmcp_receipt[2])["entry_node"] == "@task:agent_workflow"

    tmcp_artifact = conn.execute(
        """
        SELECT artifact_type, path, metadata_json
        FROM artifacts
        WHERE session_id = ? AND artifact_type = 'tmcp-packet'
        LIMIT 1
        """,
        (run[1],),
    ).fetchone()
    assert tmcp_artifact is not None
    assert Path(tmcp_artifact[1]).exists()
    assert json.loads(tmcp_artifact[2])["tmcp_receipt_id"] == workflow_payload["artifacts"][
        "tmcp_packet"
    ]["receipt_id"]

    prompt = conn.execute(
        """
        SELECT prompt_text, classification
        FROM prompts_used
        WHERE session_id = ?
        """,
        (run[1],),
    ).fetchone()
    assert prompt == ("Managed runtime handshake integration", "other")

    event_types = {
        row[0]
        for row in conn.execute(
            "SELECT event_type FROM orchestration_run_events WHERE run_id = ?",
            (run_id,),
        ).fetchall()
    }
    conn.close()

    assert "in_progress" in event_types
    assert "completed" in event_types


def test_managed_runtime_missing_run_fails_without_traceback(tmp_path: Path) -> None:
    runtime_db = tmp_path / "runtime.db"
    conn = sqlite3.connect(runtime_db)
    _apply_base_schema(conn)
    conn.close()

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "bin" / "aios-managed-run.py"),
            "--run-id",
            "run-missing",
            "--invocation-id",
            "invoke-missing",
            "--db",
            str(runtime_db),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "Traceback" not in result.stderr
    payload = json.loads(result.stderr)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "managed-run-preflight-failed"
    assert payload["run_id"] == "run-missing"


def test_managed_runtime_uses_promoted_tmcp_shortcut(runtime_db: Path, tmp_path: Path) -> None:
    from aios_orchestration_runtime import ensure_runtime_schema

    from services.tmcp_runtime import (
        compile_tmcp_packet,
        ensure_tmcp_schema,
        persist_tmcp_traversal_receipt,
    )

    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    (repo_path / "PROJECT.md").write_text("# AIOS\n", encoding="utf-8")
    home = tmp_path / "home"
    (home / "AIOS" / "logs").mkdir(parents=True)

    conn = sqlite3.connect(runtime_db)
    project_id = _insert_project(conn, repo_path)
    ensure_runtime_schema(conn)
    ensure_tmcp_schema(conn)
    run_id = "run-managed-shortcut"
    invocation_id = "invoke-managed-shortcut"
    packet_id = "packet-managed-shortcut"
    objective = "Managed runtime handshake integration"

    conn.execute(
        """
        INSERT INTO orchestration_runs (
            id, project_id, objective, workflow_key, agent_key, status, rationale,
            assumptions_json, context_trace_json, backend_key, packet_id, created_at, updated_at
        )
        VALUES (?, ?, ?, 'implementation-delivery', 'implementation-lead', 'ready',
            'Managed runtime shortcut test', '[]', '[]', 'aios-managed-runtime', ?,
            '2026-04-19T00:00:00Z', '2026-04-19T00:00:00Z')
        """,
        (run_id, project_id, objective, packet_id),
    )
    conn.execute(
        """
        INSERT INTO briefing_packets (
            id, run_id, project_id, objective, workflow_key, agent_key,
            packet_markdown, sections_json, policy_mode, token_budget,
            selection_trace_json, omitted_context_json, created_at
        )
        VALUES (?, ?, ?, ?, 'implementation-delivery', 'implementation-lead',
            'packet', '[]', 'compact-ranked', 900, '[]', '[]', '2026-04-19T00:00:00Z')
        """,
        (packet_id, run_id, project_id, objective),
    )
    conn.execute(
        """
        INSERT INTO orchestration_invocations (
            id, run_id, backend_key, backend_label, status, handshake_token,
            command_json, metadata_json, created_at, updated_at
        )
        VALUES (?, ?, 'aios-managed-runtime', 'AIOS Managed Runtime', 'launching', ?,
            '[]', '{}', '2026-04-19T00:00:00Z', '2026-04-19T00:00:00Z')
        """,
        (invocation_id, run_id, run_id),
    )
    seed_packet = compile_tmcp_packet(
        objective=objective,
        project_path=str(repo_path),
        context_receipt_id=packet_id,
    )
    seed_packet["token_estimates"] = {
        **seed_packet["token_estimates"],
        "estimated_token_delta": 250,
    }
    for index in range(3):
        persist_tmcp_traversal_receipt(
            conn,
            packet=seed_packet,
            run_id=f"prior-run-{index}",
            invocation_id=f"prior-invoke-{index}",
            session_id=f"prior-session-{index}",
            execution_outcome="completed",
            validation_evidence=["scope_check passed"],
        )
    conn.commit()
    conn.close()

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "bin" / "aios-managed-run.py"),
            "--run-id",
            run_id,
            "--invocation-id",
            invocation_id,
            "--db",
            str(runtime_db),
        ],
        cwd=str(ROOT),
        env={
            **os.environ,
            "HOME": str(home),
            "AIOS_DB": str(runtime_db),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout

    conn = sqlite3.connect(runtime_db)
    workflow_payload = json.loads(
        conn.execute(
            """
            SELECT report_json
            FROM workflow_execution_reports
            WHERE run_id = ?
            LIMIT 1
            """,
            (run_id,),
        ).fetchone()[0]
    )
    tmcp_packet = workflow_payload["artifacts"]["tmcp_packet"]
    assert tmcp_packet["phase"] == "closeout"
    assert workflow_payload["artifacts"]["tmcp_packet_expansions"]

    initial_shortcut_receipt = conn.execute(
        """
        SELECT packet_json, execution_outcome
        FROM tmcp_traversal_receipts
        WHERE run_id = ? AND invocation_id = ?
          AND execution_outcome = 'superseded_by_runtime_expansion'
        ORDER BY created_at ASC
        LIMIT 1
        """,
        (run_id, invocation_id),
    ).fetchone()
    assert initial_shortcut_receipt is not None
    initial_shortcut_packet = json.loads(initial_shortcut_receipt[0])
    assert initial_shortcut_packet["shortcut_candidate"]["matched"] is True
    assert initial_shortcut_packet["shortcut_candidate"]["status"] == "active"
    assert initial_shortcut_packet["entry_node"].startswith("@shortcut:agent_workflow:")

    receipt = conn.execute(
        """
        SELECT execution_outcome, validation_evidence_json
        FROM tmcp_traversal_receipts
        WHERE id = ?
        LIMIT 1
        """,
        (tmcp_packet["receipt_id"],),
    ).fetchone()
    conn.close()
    assert receipt[0] == "completed"
    assert "scope_check passed" in json.loads(receipt[1])


def test_managed_runtime_routes_workflow_strategy_comparison_to_planning(
    runtime_db: Path,
    tmp_path: Path,
) -> None:
    from aios_orchestration_runtime import ensure_runtime_schema

    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    home = tmp_path / "home"
    (home / "AIOS" / "logs").mkdir(parents=True)

    conn = sqlite3.connect(runtime_db)
    project_id = _insert_project(conn, repo_path)
    ensure_runtime_schema(conn)
    run_id = "run-managed-failed-workflow"
    invocation_id = "invoke-managed-failed-workflow"
    packet_id = "packet-managed-failed-workflow"

    conn.execute(
        """
        INSERT INTO orchestration_runs (
            id, project_id, objective, workflow_key, agent_key, status, rationale,
            assumptions_json, context_trace_json, backend_key, packet_id, created_at, updated_at
        )
        VALUES (
            ?, ?, 'Compare workflow promotion strategies',
            'divergent-strategy', 'implementation-lead', 'ready',
            'Managed runtime failed workflow evidence test', '[]', '[]',
            'aios-managed-runtime', ?, '2026-04-19T00:00:00Z', '2026-04-19T00:00:00Z'
        )
        """,
        (run_id, project_id, packet_id),
    )
    conn.execute(
        """
        INSERT INTO orchestration_invocations (
            id, run_id, backend_key, backend_label, status, handshake_token,
            command_json, metadata_json, created_at, updated_at
        )
        VALUES (
            ?, ?, 'aios-managed-runtime', 'AIOS Managed Runtime', 'launching', ?,
            '[]', '{}', '2026-04-19T00:00:00Z', '2026-04-19T00:00:00Z'
        )
        """,
        (invocation_id, run_id, run_id),
    )
    conn.commit()
    conn.close()

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "bin" / "aios-managed-run.py"),
            "--run-id",
            run_id,
            "--invocation-id",
            invocation_id,
            "--db",
            str(runtime_db),
        ],
        cwd=str(ROOT),
        env={**os.environ, "HOME": str(home), "AIOS_DB": str(runtime_db)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout

    conn = sqlite3.connect(runtime_db)
    run = conn.execute("SELECT status FROM orchestration_runs WHERE id = ?", (run_id,)).fetchone()
    workflow_report = conn.execute(
        """
        SELECT workflow_key, status, report_json, artifact_path
        FROM workflow_execution_reports
        WHERE run_id = ?
        LIMIT 1
        """,
        (run_id,),
    ).fetchone()
    tmcp_receipt = conn.execute(
        """
        SELECT task_id, packet_json
        FROM tmcp_traversal_receipts
        WHERE run_id = ? AND invocation_id = ?
        LIMIT 1
        """,
        (run_id, invocation_id),
    ).fetchone()
    conn.close()

    assert run[0] == "completed"
    assert workflow_report is not None
    assert workflow_report[0] == "divergent-strategy"
    assert workflow_report[1] == "completed"
    assert workflow_report[3] is not None
    workflow_payload = json.loads(workflow_report[2])
    assert workflow_payload["unresolved_issues"] == []
    tmcp_packet = workflow_payload["artifacts"]["tmcp_packet"]
    assert tmcp_packet["task_id"] == "planning"
    assert tmcp_packet["entry_node"] == "@task:planning"
    assert tmcp_packet["selected_branches"][0]["branch"] == "@branch:approval_before_edit"
    assert "@namespace:portable_dev_process/@task:planning_review" in tmcp_packet["selected_nodes"]
    assert "@namespace:portable_dev_process/@module:test_authoring" in tmcp_packet["selected_nodes"]
    assert tmcp_receipt is not None
    assert tmcp_receipt[0] == "planning"
    assert json.loads(tmcp_receipt[1])["entry_node"] == "@task:planning"


def test_managed_closeout_repairs_authoritative_run_state(runtime_db: Path, tmp_path: Path) -> None:
    from aios_orchestration_runtime import ensure_runtime_schema

    managed_runtime = _load_module("managed_runtime_closeout", "bin/aios-managed-run.py")

    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    home = tmp_path / "home"
    (home / "AIOS" / "logs").mkdir(parents=True)

    conn = sqlite3.connect(runtime_db)
    project_id = _insert_project(conn, repo_path)
    ensure_runtime_schema(conn)
    run_id = "run-closeout-repair"
    invocation_id = "invoke-closeout-repair"
    session_id = "session-closeout-repair"

    conn.execute(
        """
        INSERT INTO sessions (id, project_id, tool, started_at, objective, status, cwd, run_id, invocation_id)
        VALUES (?, ?, 'codex', '2026-04-29T00:00:00Z', 'Repair closeout state', 'open', ?, ?, ?)
        """,
        (session_id, project_id, str(repo_path), run_id, invocation_id),
    )
    conn.execute(
        """
        INSERT INTO orchestration_runs (
            id, project_id, session_id, objective, workflow_key, agent_key, status, rationale,
            assumptions_json, context_trace_json, backend_key, active_invocation_id, created_at, updated_at
        )
        VALUES (
            ?, ?, NULL, 'Repair closeout state',
            'implementation-delivery', 'implementation-lead', 'ready',
            'Closeout repair test', '[]', '[]', 'aios-managed-runtime', NULL,
            '2026-04-29T00:00:00Z', '2026-04-29T00:00:00Z'
        )
        """,
        (run_id, project_id),
    )
    conn.execute(
        """
        INSERT INTO orchestration_invocations (
            id, run_id, backend_key, backend_label, status, handshake_token,
            command_json, metadata_json, created_at, updated_at
        )
        VALUES (
            ?, ?, 'aios-managed-runtime', 'AIOS Managed Runtime', 'running', ?,
            '[]', '{}', '2026-04-29T00:00:00Z', '2026-04-29T00:00:00Z'
        )
        """,
        (invocation_id, run_id, run_id),
    )
    conn.commit()
    conn.close()

    managed_runtime.ensure_managed_closeout(
        str(runtime_db),
        run_id=run_id,
        invocation_id=invocation_id,
        session_id=session_id,
        outcome="completed",
        result_summary="Managed runtime closeout repair completed.",
        reason_json={"kind": "normal_exit"},
    )

    conn = sqlite3.connect(runtime_db)
    run = conn.execute(
        """
        SELECT status, session_id, active_invocation_id, result_summary, completed_at
        FROM orchestration_runs
        WHERE id = ?
        """,
        (run_id,),
    ).fetchone()
    assert run is not None
    assert run[0] == "completed"
    assert run[1] == session_id
    assert run[2] == invocation_id
    assert run[3] == "Managed runtime closeout repair completed."
    assert run[4] is not None

    invocation = conn.execute(
        "SELECT status, session_id, ended_at FROM orchestration_invocations WHERE id = ?",
        (invocation_id,),
    ).fetchone()
    assert invocation is not None
    assert invocation[0] == "completed"
    assert invocation[1] == session_id
    assert invocation[2] is not None

    session = conn.execute(
        "SELECT status, ended_at FROM sessions WHERE id = ?", (session_id,)
    ).fetchone()
    assert session is not None
    assert session[0] == "closed"
    assert session[1] is not None

    reason = conn.execute(
        """
        SELECT reason_json
        FROM orchestration_run_events
        WHERE run_id = ? AND to_status = 'completed'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (run_id,),
    ).fetchone()
    conn.close()
    assert reason is not None
    assert json.loads(reason[0])["linkage"] == "managed-runtime-closeout"
