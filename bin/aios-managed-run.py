#!/usr/bin/env python3
"""
Managed AIOS backend runtime.

Starts a hook-linked managed session for an orchestration run, writes a durable
invocation artifact, and closes through the explicit run/session handshake.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import sqlite3
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aios_orchestration_runtime import (  # noqa: E402
    default_db_path,
    ensure_runtime_schema,
    insert_workflow_execution_report,
    transition_run,
    update_invocation,
)

from services.storage import connect as connect_storage  # noqa: E402
from services.tmcp_runtime import (  # noqa: E402
    compile_tmcp_packet,
    ensure_tmcp_schema,
    persist_tmcp_traversal_receipt,
    update_tmcp_traversal_receipt_outcome,
)
from services.workflow_orchestration import (  # noqa: E402
    WorkflowExecutionContext,
    execute_workflow,
    summarize_execution_report,
)

HOOK_SESSION_START = ROOT / "bin" / "hook-session-start.py"
HOOK_PROMPT_SUBMIT = ROOT / "bin" / "hook-prompt-submit.py"
HOOK_STOP = ROOT / "bin" / "hook-stop.py"
DEFAULT_LOGS_DIR = ROOT / "logs"
REPORT_DIR = DEFAULT_LOGS_DIR / "control-plane" / "invocations"
WORKFLOW_REPORT_DIR = DEFAULT_LOGS_DIR / "control-plane" / "workflow-reports"
TMCP_PACKET_DIR = DEFAULT_LOGS_DIR / "control-plane" / "tmcp-packets"
BACKEND_SURFACES = {
    "codex-managed-runtime": "codex",
    "claude-managed-runtime": "claude_code",
    "aios-managed-runtime": "codex",
}


class RunCanceled(Exception):
    pass


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def load_run_context(db_path: str, run_id: str) -> dict[str, str | None]:
    conn = connect_storage(db_path)
    ensure_runtime_schema(conn)
    row = conn.execute(
        """
        SELECT
            r.objective,
            r.workflow_key,
            r.agent_key,
            COALESCE(p.repo_path, ?) AS repo_path,
            p.obsidian_path,
            r.packet_id
        FROM orchestration_runs r
        LEFT JOIN projects p ON p.id = r.project_id
        WHERE r.id = ?
        LIMIT 1
        """,
        (str(ROOT), run_id),
    ).fetchone()
    conn.close()
    if row is None:
        raise RuntimeError(f"Run not found: {run_id}")
    return {
        "objective": row[0],
        "workflow_key": row[1],
        "agent_key": row[2],
        "repo_path": row[3],
        "obsidian_path": row[4],
        "packet_id": row[5],
    }


def emit_hook(script: Path, payload: dict[str, object], env: dict[str, str]) -> None:
    subprocess.run(
        ["python3", str(script)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
        env=env,
        cwd=str(ROOT),
    )


def write_invocation_report(
    db_path: str,
    *,
    run_id: str,
    invocation_id: str,
    session_id: str,
    backend_key: str,
    context: dict[str, str | None],
    workflow_report_path: str | None = None,
    workflow_report_id: str | None = None,
    workflow_summary: str | None = None,
) -> str:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"{invocation_id}.json"
    report = {
        "run_id": run_id,
        "invocation_id": invocation_id,
        "session_id": session_id,
        "backend_key": backend_key,
        "objective": context["objective"],
        "workflow_key": context["workflow_key"],
        "agent_key": context["agent_key"],
        "packet_id": context["packet_id"],
        "workflow_report_id": workflow_report_id,
        "workflow_report_path": workflow_report_path,
        "workflow_summary": workflow_summary,
        "recorded_at": now_iso(),
    }
    report_path.write_text(json.dumps(report, indent=2))

    conn = connect_storage(db_path)
    conn.execute(
        """
        INSERT INTO artifacts (id, session_id, artifact_type, path, metadata_json, created_at)
        VALUES (?, ?, 'control-plane-report', ?, ?, ?)
        """,
        (
            f"artifact-{uuid.uuid4()}",
            session_id,
            str(report_path),
            json.dumps({"run_id": run_id, "invocation_id": invocation_id}),
            now_iso(),
        ),
    )
    conn.execute(
        """
        INSERT INTO tool_events (id, session_id, source_tool, event_type, event_time, payload_json)
        VALUES (?, ?, 'aios-managed-runtime', 'ManagedInvocationReport', ?, ?)
        """,
        (
            f"tool-event-{uuid.uuid4()}",
            session_id,
            now_iso(),
            json.dumps(
                {"report_path": str(report_path), "run_id": run_id, "backend_key": backend_key}
            ),
        ),
    )
    conn.commit()
    conn.close()
    return str(report_path)


def write_tmcp_packet_artifact(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    run_id: str,
    invocation_id: str,
    packet: dict[str, object],
    receipt_id: str,
) -> str:
    TMCP_PACKET_DIR.mkdir(parents=True, exist_ok=True)
    packet_path = TMCP_PACKET_DIR / f"{invocation_id}.json"
    packet_path.write_text(json.dumps(packet, indent=2, sort_keys=True), encoding="utf-8")
    metadata_json = json.dumps(
        {
            "run_id": run_id,
            "invocation_id": invocation_id,
            "tmcp_receipt_id": receipt_id,
            "task_id": packet.get("task_id"),
            "traversal_fingerprint": packet.get("traversal_fingerprint"),
        },
        sort_keys=True,
    )
    updated = conn.execute(
        """
        UPDATE artifacts
        SET metadata_json = ?, created_at = ?
        WHERE session_id = ?
          AND artifact_type = 'tmcp-packet'
          AND path = ?
        """,
        (
            metadata_json,
            now_iso(),
            session_id,
            str(packet_path),
        ),
    )
    if updated.rowcount:
        return str(packet_path)
    conn.execute(
        """
        INSERT INTO artifacts (id, session_id, artifact_type, path, metadata_json, created_at)
        VALUES (?, ?, 'tmcp-packet', ?, ?, ?)
        """,
        (
            f"artifact-{uuid.uuid4()}",
            session_id,
            str(packet_path),
            metadata_json,
            now_iso(),
        ),
    )
    return str(packet_path)


def _tmcp_validation_evidence(workflow_report: dict[str, object]) -> list[str]:
    evidence: list[str] = []
    validations = workflow_report.get("validations", [])
    if not isinstance(validations, list):
        validations = []
    for validation in validations:
        if not isinstance(validation, dict):
            continue
        validation_key = str(validation.get("validation_key", "validation"))
        passed = "passed" if validation.get("passed") else "failed"
        evidence.append(f"{validation_key} {passed}")
    stage_evaluations = workflow_report.get("stage_evaluations", [])
    if not isinstance(stage_evaluations, list):
        stage_evaluations = []
    for stage in stage_evaluations:
        if not isinstance(stage, dict):
            continue
        stage_key = str(stage.get("stage_key", "stage"))
        outcome = str(stage.get("outcome", "unknown"))
        blockers = int(stage.get("blocker_count", 0) or 0)
        warnings = int(stage.get("warning_count", 0) or 0)
        evidence.append(f"{stage_key} {outcome} blockers={blockers} warnings={warnings}")
    return evidence


def ensure_managed_start(
    db_path: str,
    *,
    run_id: str,
    invocation_id: str,
    session_id: str,
    backend_key: str,
) -> None:
    conn = connect_storage(db_path)
    ensure_runtime_schema(conn)
    now = now_iso()
    row = conn.execute(
        """
        SELECT status, session_id, active_invocation_id
        FROM orchestration_runs
        WHERE id = ?
        LIMIT 1
        """,
        (run_id,),
    ).fetchone()
    if row is None:
        conn.close()
        raise RuntimeError(f"Run not found during start: {run_id}")

    has_event = conn.execute(
        """
        SELECT 1
        FROM orchestration_run_events
        WHERE run_id = ? AND to_status = 'in_progress'
        LIMIT 1
        """,
        (run_id,),
    ).fetchone()
    if (
        has_event is None
        or row[0] in {"planned", "ready"}
        or row[1] != session_id
        or row[2] != invocation_id
    ):
        transition_run(
            conn,
            run_id=run_id,
            to_status="in_progress",
            event_type="in_progress",
            summary="Managed runtime session started.",
            reason={"kind": "managed_runtime_start", "backend_key": backend_key},
            session_id=session_id,
            invocation_id=invocation_id,
            created_at=now,
        )

    conn.execute(
        """
        UPDATE sessions
        SET run_id = COALESCE(run_id, ?),
            invocation_id = COALESCE(invocation_id, ?),
            objective = objective,
            runtime_metadata_json = ?
        WHERE id = ?
        """,
        (
            run_id,
            invocation_id,
            json.dumps({"backend_key": backend_key, "linked_via": "managed-runtime-start"}),
            session_id,
        ),
    )
    conn.commit()
    conn.close()


def emit_managed_prompt_capture(
    *,
    session_id: str,
    run_id: str,
    invocation_id: str,
    backend_key: str,
    context: dict[str, str | None],
    env: dict[str, str],
) -> None:
    objective = (context["objective"] or "").strip()
    if not objective:
        return
    emit_hook(
        HOOK_PROMPT_SUBMIT,
        {
            "session_id": session_id,
            "cwd": context["repo_path"] or str(ROOT),
            "prompt": objective,
            "run_id": run_id,
            "invocation_id": invocation_id,
            "backend_key": backend_key,
            "source": "aios-managed-runtime",
        },
        env,
    )


def ensure_managed_closeout(
    db_path: str,
    *,
    run_id: str,
    invocation_id: str,
    session_id: str,
    outcome: str,
    result_summary: str,
    reason_json: dict[str, object],
) -> None:
    conn = connect_storage(db_path)
    ensure_runtime_schema(conn)
    now = now_iso()
    row = conn.execute(
        """
        SELECT status, session_id, active_invocation_id
        FROM orchestration_runs
        WHERE id = ?
        LIMIT 1
        """,
        (run_id,),
    ).fetchone()
    if row is None:
        conn.close()
        raise RuntimeError(f"Run not found during closeout: {run_id}")

    if row[0] != outcome or row[1] != session_id or row[2] != invocation_id:
        transition_run(
            conn,
            run_id=run_id,
            to_status=outcome,
            event_type=outcome,
            summary=result_summary,
            reason={**reason_json, "linkage": "managed-runtime-closeout"},
            session_id=session_id,
            invocation_id=invocation_id,
            result_summary=result_summary,
            created_at=now,
        )

    update_invocation(
        conn,
        invocation_id=invocation_id,
        status=outcome,
        session_id=session_id,
        metadata={
            "result_summary": result_summary,
            "reason": reason_json,
            "linked_via": "managed-runtime-closeout",
        },
        ended_at=now,
    )
    conn.execute(
        """
        UPDATE sessions
        SET status = 'closed',
            ended_at = COALESCE(ended_at, ?),
            run_id = COALESCE(run_id, ?),
            invocation_id = COALESCE(invocation_id, ?)
        WHERE id = ?
        """,
        (now, run_id, invocation_id, session_id),
    )
    conn.commit()
    conn.close()


def main() -> int:
    global REPORT_DIR, TMCP_PACKET_DIR, WORKFLOW_REPORT_DIR

    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--invocation-id", required=True)
    parser.add_argument(
        "--backend-key", default=os.environ.get("AIOS_BACKEND_KEY", "codex-managed-runtime")
    )
    parser.add_argument("--db", default=os.environ.get("AIOS_DB", default_db_path()))
    parser.add_argument(
        "--logs-dir", default=os.environ.get("AIOS_LOGS_DIR", str(DEFAULT_LOGS_DIR))
    )
    args = parser.parse_args()

    run_id = args.run_id
    invocation_id = args.invocation_id
    backend_key = args.backend_key
    db_path = args.db
    logs_dir = Path(args.logs_dir).expanduser().resolve()
    REPORT_DIR = logs_dir / "control-plane" / "invocations"
    WORKFLOW_REPORT_DIR = logs_dir / "control-plane" / "workflow-reports"
    TMCP_PACKET_DIR = logs_dir / "control-plane" / "tmcp-packets"
    session_id = f"managed-{invocation_id}"
    canceled = {"flag": False}

    def handle_cancel(_signum: int, _frame: object) -> None:
        canceled["flag"] = True
        raise RunCanceled("Managed invocation canceled by operator signal.")

    signal.signal(signal.SIGTERM, handle_cancel)
    signal.signal(signal.SIGINT, handle_cancel)

    try:
        context = load_run_context(db_path, run_id)
    except RuntimeError as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": {
                        "code": "managed-run-preflight-failed",
                        "message": str(exc),
                    },
                    "run_id": run_id,
                    "invocation_id": invocation_id,
                    "backend_key": backend_key,
                    "generated_at": now_iso(),
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    env = {
        **os.environ,
        "AIOS_RUN_ID": run_id,
        "AIOS_INVOCATION_ID": invocation_id,
        "AIOS_BACKEND_KEY": backend_key,
        "AIOS_DB": db_path,
        "AIOS_LOGS_DIR": str(logs_dir),
    }

    conn = connect_storage(db_path)
    ensure_runtime_schema(conn)
    update_invocation(
        conn,
        invocation_id=invocation_id,
        status="running",
        pid=os.getpid(),
        metadata={"session_id": session_id, "backend_key": backend_key},
        started_at=now_iso(),
    )
    conn.commit()
    conn.close()

    emit_hook(
        HOOK_SESSION_START,
        {
            "session_id": session_id,
            "cwd": context["repo_path"] or str(ROOT),
            "objective": context["objective"] or "",
            "run_id": run_id,
            "invocation_id": invocation_id,
            "backend_key": backend_key,
        },
        env,
    )
    ensure_managed_start(
        db_path,
        run_id=run_id,
        invocation_id=invocation_id,
        session_id=session_id,
        backend_key=backend_key,
    )
    emit_managed_prompt_capture(
        session_id=session_id,
        run_id=run_id,
        invocation_id=invocation_id,
        backend_key=backend_key,
        context=context,
        env=env,
    )

    outcome = "completed"
    result_summary = "Managed runtime captured invocation metadata and completed normally."
    reason_json: dict[str, object] = {"kind": "normal_exit", "backend_key": backend_key}
    workflow_report_id: str | None = None
    workflow_report_path: str | None = None
    workflow_summary: str | None = None
    tmcp_packet: dict[str, object] | None = None
    tmcp_receipt_id: str | None = None
    tmcp_packet_path: str | None = None

    try:
        surface = BACKEND_SURFACES.get(backend_key)
        if surface is None:
            raise RuntimeError(f"Unsupported managed backend key: {backend_key}")
        conn = connect_storage(db_path)
        try:
            ensure_runtime_schema(conn)
            ensure_tmcp_schema(conn)
            tmcp_packet = compile_tmcp_packet(
                objective=context["objective"] or "",
                project_path=context["repo_path"],
                context_receipt_id=context["packet_id"],
                receipt_conn=conn,
            )
            workflow_context = WorkflowExecutionContext(
                objective=context["objective"] or "",
                workflow_key=context["workflow_key"] or "implementation-delivery",
                surface=surface,
                repo_path=context["repo_path"],
                vault_root=context["obsidian_path"],
                run_id=run_id,
                invocation_id=invocation_id,
                session_id=session_id,
                tmcp_packet=tmcp_packet,
            )
            tmcp_receipt_id = persist_tmcp_traversal_receipt(
                conn,
                packet=tmcp_packet,
                run_id=run_id,
                invocation_id=invocation_id,
                session_id=session_id,
            )
            tmcp_packet["receipt_id"] = tmcp_receipt_id
            tmcp_packet_path = write_tmcp_packet_artifact(
                conn,
                session_id=session_id,
                run_id=run_id,
                invocation_id=invocation_id,
                packet=tmcp_packet,
                receipt_id=tmcp_receipt_id,
            )
            workflow_report = execute_workflow(workflow_context, conn=conn)
            active_tmcp_packet = workflow_report.get("artifacts", {}).get("tmcp_packet")
            active_tmcp_receipt_id = tmcp_receipt_id
            if isinstance(active_tmcp_packet, dict):
                tmcp_packet = active_tmcp_packet
                active_tmcp_receipt_id = str(
                    active_tmcp_packet.get("receipt_id") or tmcp_receipt_id
                )
                tmcp_packet_path = write_tmcp_packet_artifact(
                    conn,
                    session_id=session_id,
                    run_id=run_id,
                    invocation_id=invocation_id,
                    packet=tmcp_packet,
                    receipt_id=active_tmcp_receipt_id,
                )
            workflow_report.setdefault("artifacts", {})["tmcp_packet_path"] = tmcp_packet_path
            if active_tmcp_receipt_id != tmcp_receipt_id:
                update_tmcp_traversal_receipt_outcome(
                    conn,
                    receipt_id=tmcp_receipt_id,
                    execution_outcome="superseded_by_runtime_expansion",
                    validation_evidence=[
                        f"active_receipt_id={active_tmcp_receipt_id}",
                    ],
                )
            update_tmcp_traversal_receipt_outcome(
                conn,
                receipt_id=active_tmcp_receipt_id,
                execution_outcome=str(workflow_report.get("status", "completed")),
                validation_evidence=_tmcp_validation_evidence(workflow_report),
            )
            tmcp_receipt_id = active_tmcp_receipt_id
            workflow_summary = summarize_execution_report(workflow_report)
            WORKFLOW_REPORT_DIR.mkdir(parents=True, exist_ok=True)
            workflow_path = WORKFLOW_REPORT_DIR / f"{invocation_id}.json"
            workflow_path.write_text(json.dumps(workflow_report, indent=2), encoding="utf-8")
            workflow_report_path = str(workflow_path)

            workflow_report_id = insert_workflow_execution_report(
                conn,
                run_id=run_id,
                invocation_id=invocation_id,
                workflow_key=workflow_context.workflow_key,
                status=str(workflow_report.get("status", "completed")),
                report=workflow_report,
                artifact_path=workflow_report_path,
            )
            conn.execute(
                """
                INSERT INTO artifacts (id, session_id, artifact_type, path, metadata_json, created_at)
                VALUES (?, ?, 'workflow-execution-report', ?, ?, ?)
                """,
                (
                    f"artifact-{uuid.uuid4()}",
                    session_id,
                    workflow_report_path,
                    json.dumps(
                        {
                            "run_id": run_id,
                            "invocation_id": invocation_id,
                            "workflow_key": workflow_context.workflow_key,
                            "workflow_report_id": workflow_report_id,
                            "tmcp_receipt_id": tmcp_receipt_id,
                            "tmcp_packet_path": tmcp_packet_path,
                        }
                    ),
                    now_iso(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

        if workflow_report.get("status") != "completed":
            raise RuntimeError(
                f"Workflow execution failed for {workflow_context.workflow_key}: "
                + "; ".join(workflow_report.get("unresolved_issues", []))
            )

        report_path = write_invocation_report(
            db_path,
            run_id=run_id,
            invocation_id=invocation_id,
            session_id=session_id,
            backend_key=backend_key,
            context=context,
            workflow_report_path=workflow_report_path,
            workflow_report_id=workflow_report_id,
            workflow_summary=workflow_summary,
        )
        result_summary = (
            f"Managed runtime completed and wrote invocation report {report_path}. "
            f"{workflow_summary}"
        )
    except RunCanceled as exc:
        outcome = "canceled"
        result_summary = "Managed runtime canceled before completion."
        reason_json = {"kind": "signal_cancel", "message": str(exc), "backend_key": backend_key}
    except Exception as exc:
        outcome = "failed"
        result_summary = f"Managed runtime failed: {exc}"
        reason_json = {
            "kind": "exception",
            "error": exc.__class__.__name__,
            "message": str(exc),
            "backend_key": backend_key,
            "workflow_report_id": workflow_report_id,
            "workflow_report_path": workflow_report_path,
            "tmcp_receipt_id": tmcp_receipt_id,
            "tmcp_packet_path": tmcp_packet_path,
        }

    if canceled["flag"] and outcome == "completed":
        outcome = "canceled"
        result_summary = "Managed runtime canceled before completion."
        reason_json = {"kind": "signal_cancel", "message": "SIGTERM", "backend_key": backend_key}

    emit_hook(
        HOOK_STOP,
        {
            "session_id": session_id,
            "run_id": run_id,
            "invocation_id": invocation_id,
            "backend_key": backend_key,
            "run_outcome": outcome,
            "result_summary": result_summary,
            "reason_json": reason_json,
        },
        env,
    )
    ensure_managed_closeout(
        db_path,
        run_id=run_id,
        invocation_id=invocation_id,
        session_id=session_id,
        outcome=outcome,
        result_summary=result_summary,
        reason_json=reason_json,
    )

    return 0 if outcome == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
