from __future__ import annotations

import json
import sqlite3
import subprocess
import uuid
from pathlib import Path
from typing import Any

from services.success_criteria import evaluate_and_record, preview_applicable_criteria

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTEXT_ROOT = REPO_ROOT / "aios" / "context"
DEFAULT_HARNESS_WORKFLOW_KEY = "implementation-delivery"
DEFAULT_HARNESS_AGENT_KEY = "implementation-lead"

EVENT_STATUS: dict[str, str] = {
    "task_created": "planned",
    "briefing_packet_generated": "ready",
    "agent_started": "in_progress",
    "tests_failed": "failed_validation",
    "agent_requested_approval": "waiting_for_user",
    "operator_rejected": "blocked",
    "run_closed_failed": "failed",
}


def _now_sql() -> str:
    return "strftime('%Y-%m-%dT%H:%M:%SZ', 'now')"


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _project_name(conn: sqlite3.Connection, project_id: str | None) -> str | None:
    if not project_id:
        return None
    row = conn.execute("SELECT name FROM projects WHERE id = ? LIMIT 1", (project_id,)).fetchone()
    if row is None:
        return project_id
    return str(row["name"] if isinstance(row, sqlite3.Row) else row[0])


def _run_context_compiler(task: str, context_root: Path) -> dict[str, Any]:
    result = subprocess.run(
        [
            "node",
            str(REPO_ROOT / "tools" / "context-compile.mjs"),
            "--task",
            task,
            "--context-root",
            str(context_root),
            "--no-write",
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    loaded = json.loads(result.stdout)
    if not isinstance(loaded, dict):
        raise ValueError("Context compiler returned non-object JSON")
    return loaded


def _approval_requirements(task: str, selected_ids: set[str]) -> list[str]:
    lowered = task.lower()
    requirements: list[str] = []
    if "global" in lowered and ("standard" in lowered or "rule" in lowered):
        requirements.append("global_standards_change")
    if "secret" in lowered or "oidc" in lowered or "security" in lowered:
        requirements.append("security_policy_review")
    if "packets.workflow.approval-gates" in selected_ids:
        requirements.append("writeback_approval_gate")
    return sorted(set(requirements))


def brief_task(
    conn: sqlite3.Connection,
    *,
    task: str,
    project_id: str | None = None,
    context_root: Path = CONTEXT_ROOT,
) -> dict[str, Any]:
    project_name = _project_name(conn, project_id)
    context_payload = _run_context_compiler(task, context_root)
    criteria = preview_applicable_criteria(
        project_id=project_id,
        project_name=project_name,
        objective=task,
        prompt_classifications=["implement"],
    )
    selected_packets = [
        {
            "id": str(item.get("id")),
            "path": str(item.get("path")),
            "tier": str(item.get("tier")),
            "reason": str(item.get("reason")),
        }
        for item in context_payload.get("selected_context_files", [])
        if isinstance(item, dict)
    ]
    selected_ids = {item["id"] for item in selected_packets}
    task_classification = context_payload.get("task_classification", {})
    criteria_rows = criteria.get("criteria", [])
    gates = [
        "success_criteria",
        "test_evidence",
        "truth_file_update",
        "approval_review",
        "writeback_proposal_review",
    ]
    return {
        "task": task,
        "project_id": project_id,
        "task_type": task_classification,
        "selected_context_packets": selected_packets,
        "standards": [
            item for item in selected_packets if item["id"].startswith("global.")
        ],
        "success_criteria": criteria_rows,
        "risks": context_payload.get("known_risks", []),
        "expected_artifacts": ["orchestration_run", "briefing_packet", "harness_evaluation"],
        "gates": gates,
        "approval_requirements": _approval_requirements(task, selected_ids),
    }


def _insert_run(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    project_id: str | None,
    task: str,
) -> None:
    conn.execute(
        f"""
        INSERT INTO orchestration_runs (
            id, project_id, objective, workflow_key, agent_key, status, rationale,
            assumptions_json, context_trace_json, status_reason_json, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, 'planned', ?, '[]', '[]', '{{}}', {_now_sql()}, {_now_sql()})
        """,
        (
            run_id,
            project_id,
            task,
            DEFAULT_HARNESS_WORKFLOW_KEY,
            DEFAULT_HARNESS_AGENT_KEY,
            "Created by backend-neutral AIOS harness simulation.",
        ),
    )


def _record_event(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    project_id: str | None,
    event: dict[str, Any],
    from_status: str | None,
    to_status: str | None,
) -> None:
    event_type = str(event.get("type", "unknown"))
    conn.execute(
        f"""
        INSERT INTO orchestration_run_events (
            id, run_id, project_id, event_type, from_status, to_status, summary,
            reason_json, metadata_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, {_now_sql()})
        """,
        (
            f"run-event-{uuid.uuid4()}",
            run_id,
            project_id,
            event_type,
            from_status,
            to_status,
            str(event.get("summary") or event_type),
            _json({"source": "harness"}),
            _json(event),
        ),
    )


def _set_run_status(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    status: str,
    reason: dict[str, Any] | None = None,
) -> None:
    timestamp_column = {
        "completed": "completed_at",
        "failed": "failed_at",
        "canceled": "canceled_at",
    }.get(status)
    assignments = ["status = ?", "status_reason_json = ?", f"updated_at = {_now_sql()}"]
    values: list[Any] = [status, _json(reason or {})]
    if status == "in_progress":
        assignments.append(f"started_at = COALESCE(started_at, {_now_sql()})")
    if timestamp_column:
        assignments.append(f"{timestamp_column} = {_now_sql()}")
    conn.execute(
        f"UPDATE orchestration_runs SET {', '.join(assignments)} WHERE id = ?",
        (*values, run_id),
    )


def _insert_packet(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    project_id: str | None,
    task: str,
    briefing: dict[str, Any],
) -> str:
    packet_id = f"packet-{uuid.uuid4()}"
    conn.execute(
        f"""
        INSERT INTO briefing_packets (
            id, run_id, project_id, objective, workflow_key, agent_key, packet_markdown,
            sections_json, policy_mode, token_budget, selection_trace_json, omitted_context_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'compact-ranked', 900, ?, '[]', {_now_sql()})
        """,
        (
            packet_id,
            run_id,
            project_id,
            task,
            DEFAULT_HARNESS_WORKFLOW_KEY,
            DEFAULT_HARNESS_AGENT_KEY,
            "# AIOS Harness Briefing\n",
            _json(briefing),
            _json({"source": "harness-brief"}),
        ),
    )
    conn.execute("UPDATE orchestration_runs SET packet_id = ? WHERE id = ?", (packet_id, run_id))
    return packet_id


def _is_code_file(path: str) -> bool:
    return Path(path).suffix.lower() in {".py", ".ts", ".tsx", ".js", ".jsx", ".sql"}


def _is_test_file(path: str) -> bool:
    lowered = path.lower()
    return "test" in lowered or "spec" in lowered


def _evaluate_harness(
    *,
    task: str,
    changed_files: list[str],
    event_types: list[str],
    criteria_result: dict[str, Any] | None,
    project_name: str | None,
) -> dict[str, Any]:
    tests_failed = "tests_failed" in event_types
    tests_passed = "tests_passed" in event_types
    claimed_complete = "run_closed_completed" in event_types
    code_changed = any(_is_code_file(path) and not _is_test_file(path) for path in changed_files)
    truth_changed = any(Path(path).name == "PROJECT.md" for path in changed_files)
    counts = (criteria_result or {}).get("counts", {})
    blocker_count = int(counts.get("blocker", 0) or 0)
    warning_count = int(counts.get("warning", 0) or 0)

    violations: list[str] = []
    if tests_failed:
        violations.append("tests_failed")
    if code_changed and project_name == "AIOS" and not truth_changed:
        violations.append("missing_truth_file_update")
    if claimed_complete and tests_failed:
        violations.append("claimed_complete_after_failed_gate")
    if blocker_count > 0:
        violations.append("success_criteria_blockers")

    complete = claimed_complete and tests_passed and not violations
    if blocker_count > 0 or tests_failed:
        direction = "negative"
        value = -1
    elif warning_count > 0:
        direction = "slight_negative"
        value = -0.25
    elif complete:
        direction = "positive"
        value = 1
    else:
        direction = "neutral_unknown"
        value = 0

    return {
        "completion_status": "complete" if complete else "not_complete",
        "violations": violations,
        "test_evidence": {
            "passed": tests_passed,
            "failed": tests_failed,
            "commands": [],
        },
        "success_criteria": criteria_result,
        "health_delta": {
            "direction": direction,
            "value": value,
            "reason": "Deterministic harness v1 gate evaluation.",
        },
        "approval_eligible": complete,
        "writeback_proposal_eligible": complete,
    }


def _evaluate_from_events(
    conn: sqlite3.Connection | None,
    *,
    task: str,
    project_id: str | None,
    run_id: str | None,
    packet_id: str | None,
    session_id: str | None,
    events: list[dict[str, Any]],
    record: bool,
) -> dict[str, Any]:
    changed_files = [
        str(event["path"])
        for event in events
        if event.get("type") == "file_changed" and event.get("path")
    ]
    event_types = [str(event.get("type")) for event in events]
    project_name = _project_name(conn, project_id) if conn is not None else None
    execution_evidence = [
        str(event.get("command"))
        for event in events
        if event.get("type") in {"tests_passed", "tests_failed"} and event.get("command")
    ]
    criteria_result = None
    if conn is not None and record:
        criteria_result = evaluate_and_record(
            conn,
            project_id=project_id,
            project_name=project_name,
            run_id=run_id,
            session_id=session_id,
            packet_id=packet_id,
            objective=task,
            task_id=None,
            trigger_kind="harness_simulation",
            cwd=str(REPO_ROOT),
            prompt_classifications=["implement"],
            changed_files=changed_files,
            execution_evidence=execution_evidence,
        )
    return _evaluate_harness(
        task=task,
        changed_files=changed_files,
        event_types=event_types,
        criteria_result=criteria_result,
        project_name=project_name,
    )


def simulate_fixture(
    conn: sqlite3.Connection,
    *,
    fixture_path: Path,
    context_root: Path = CONTEXT_ROOT,
) -> dict[str, Any]:
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    if not isinstance(fixture, dict):
        raise ValueError("Harness fixture must be a JSON object")
    task = str(fixture.get("task") or "")
    if not task:
        raise ValueError("Harness fixture task is required")
    project_id = str(fixture.get("project_id") or "") or None
    events = [event for event in fixture.get("events", []) if isinstance(event, dict)]
    run_id = f"run-harness-{uuid.uuid4()}"
    _insert_run(conn, run_id=run_id, project_id=project_id, task=task)

    current_status: str | None = None
    packet_id: str | None = None
    briefing: dict[str, Any] | None = None
    for event in events:
        event_type = str(event.get("type"))
        if event_type == "briefing_packet_generated":
            briefing = brief_task(conn, task=task, project_id=project_id, context_root=context_root)
            packet_id = _insert_packet(
                conn,
                run_id=run_id,
                project_id=project_id,
                task=task,
                briefing=briefing,
            )
        if event_type == "run_closed_completed":
            evaluation = _evaluate_from_events(
                conn,
                task=task,
                project_id=project_id,
                run_id=run_id,
                packet_id=packet_id,
                session_id=None,
                events=events,
                record=True,
            )
            target_status = "completed" if evaluation["completion_status"] == "complete" else "failed_validation"
        else:
            target_status = EVENT_STATUS.get(event_type)
        _record_event(
            conn,
            run_id=run_id,
            project_id=project_id,
            event=event,
            from_status=current_status,
            to_status=target_status,
        )
        if target_status:
            _set_run_status(
                conn,
                run_id=run_id,
                status=target_status,
                reason={"event_type": event_type, "source": "harness"},
            )
            current_status = target_status

    if "run_closed_completed" not in [str(event.get("type")) for event in events]:
        evaluation = _evaluate_from_events(
            conn,
            task=task,
            project_id=project_id,
            run_id=run_id,
            packet_id=packet_id,
            session_id=None,
            events=events,
            record=True,
        )
    conn.commit()
    return {
        "mode": "simulate",
        "run_id": run_id,
        "packet_id": packet_id,
        "briefing": briefing,
        "events": events,
        "evaluation": evaluation,
    }


def replay_session(conn: sqlite3.Connection, *, session_id: str) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT id, project_id, objective, status, ended_at
        FROM sessions
        WHERE id = ?
        LIMIT 1
        """,
        (session_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Session not found: {session_id}")
    objective = str(row["objective"] if isinstance(row, sqlite3.Row) else row[2] or "Replay session")
    project_id = str(row["project_id"] if isinstance(row, sqlite3.Row) else row[1])
    status = str(row["status"] if isinstance(row, sqlite3.Row) else row[3])
    events: list[dict[str, Any]] = [
        {"type": "task_created", "summary": objective},
        {"type": "agent_started", "summary": "Replayed session started."},
    ]
    tool_rows = conn.execute(
        """
        SELECT event_type, payload_json
        FROM tool_events
        WHERE session_id = ?
        ORDER BY event_time, id
        """,
        (session_id,),
    ).fetchall()
    for tool_row in tool_rows:
        payload = json.loads(str(tool_row["payload_json"] if isinstance(tool_row, sqlite3.Row) else tool_row[1]) or "{}")
        command = str(payload.get("command") or "")
        exit_code = payload.get("exit_code")
        if "pytest" in command and exit_code not in (0, "0", None):
            events.append({"type": "tests_failed", "command": command, "summary": "Replayed tests failed."})
        elif "pytest" in command and exit_code in (0, "0"):
            events.append({"type": "tests_passed", "command": command, "summary": "Replayed tests passed."})
    artifact_rows = conn.execute(
        """
        SELECT artifact_type, path
        FROM artifacts
        WHERE session_id = ?
        ORDER BY created_at, id
        """,
        (session_id,),
    ).fetchall()
    for artifact_row in artifact_rows:
        artifact_type = str(artifact_row["artifact_type"] if isinstance(artifact_row, sqlite3.Row) else artifact_row[0])
        artifact_path = str(artifact_row["path"] if isinstance(artifact_row, sqlite3.Row) else artifact_row[1])
        if artifact_type in {"patch", "file", "changed-file"} and artifact_path:
            events.append({"type": "file_changed", "path": artifact_path, "summary": "Replayed file change."})
    has_failed_tests = any(event["type"] == "tests_failed" for event in events)
    if status == "closed" and has_failed_tests:
        events.append({"type": "run_closed_failed", "summary": "Replayed session closed with failed tests."})
    elif status == "closed":
        events.append({"type": "run_closed_completed", "summary": "Replayed session closed."})
    evaluation = _evaluate_from_events(
        None,
        task=objective,
        project_id=project_id,
        run_id=None,
        packet_id=None,
        session_id=session_id,
        events=events,
        record=False,
    )
    return {
        "mode": "replay",
        "session_id": session_id,
        "task": objective,
        "events": events,
        "evaluation": evaluation,
        "recovery_recommendation": "Inspect failed gates before active harness enforcement."
        if evaluation["completion_status"] != "complete"
        else "Replay gates passed.",
    }


def _latest_session_id(conn: sqlite3.Connection) -> str | None:
    row = conn.execute(
        "SELECT id FROM sessions ORDER BY started_at DESC LIMIT 1",
    ).fetchone()
    if row is None:
        return None
    return str(row["id"] if isinstance(row, sqlite3.Row) else row[0])


def shadow_evaluate_session(conn: sqlite3.Connection, *, session_id: str) -> dict[str, Any]:
    resolved_session_id = _latest_session_id(conn) if session_id == "latest" else session_id
    if not resolved_session_id:
        raise ValueError("No session available for shadow evaluation")
    replay = replay_session(conn, session_id=resolved_session_id)
    return {
        **replay,
        "mode": "shadow",
        "session_id": resolved_session_id,
        "shadow_policy": "read_only_no_blocking_no_writebacks",
    }


def active_readiness() -> dict[str, Any]:
    checks = [
        "context_precision_recall_fixtures",
        "fake_lifecycle_tests",
        "deterministic_replay_reports",
        "shadow_mode_reviewed_output",
        "inspectable_approval_writeback_actions",
    ]
    return {
        "active_harness_ready": False,
        "backend_policy": "backend_neutral_invocation_contract",
        "required_checks": checks,
        "reason": "Active launch remains disabled until fake, replay, and shadow gates have reviewed evidence.",
    }
