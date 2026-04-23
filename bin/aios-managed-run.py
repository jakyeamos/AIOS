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

from aios_orchestration_runtime import (
    default_db_path,
    ensure_runtime_schema,
    insert_workflow_execution_report,
    update_invocation,
)

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.workflow_orchestration import (  # noqa: E402
    WorkflowExecutionContext,
    execute_workflow,
    summarize_execution_report,
)

HOOK_SESSION_START = ROOT / "bin" / "hook-session-start.py"
HOOK_STOP = ROOT / "bin" / "hook-stop.py"
REPORT_DIR = ROOT / "logs" / "control-plane" / "invocations"
WORKFLOW_REPORT_DIR = ROOT / "logs" / "control-plane" / "workflow-reports"


class RunCanceled(Exception):
    pass


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def load_run_context(db_path: str, run_id: str) -> dict[str, str | None]:
    conn = sqlite3.connect(db_path)
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

    conn = sqlite3.connect(db_path)
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
            json.dumps({"report_path": str(report_path), "run_id": run_id}),
        ),
    )
    conn.commit()
    conn.close()
    return str(report_path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--invocation-id", required=True)
    parser.add_argument("--backend-key", default=os.environ.get("AIOS_BACKEND_KEY", "aios-managed-runtime"))
    parser.add_argument("--db", default=os.environ.get("AIOS_DB", default_db_path()))
    args = parser.parse_args()

    run_id = args.run_id
    invocation_id = args.invocation_id
    backend_key = args.backend_key
    db_path = args.db
    session_id = f"managed-{invocation_id}"
    canceled = {"flag": False}

    def handle_cancel(_signum: int, _frame: object) -> None:
        canceled["flag"] = True
        raise RunCanceled("Managed invocation canceled by operator signal.")

    signal.signal(signal.SIGTERM, handle_cancel)
    signal.signal(signal.SIGINT, handle_cancel)

    context = load_run_context(db_path, run_id)
    env = {
        **os.environ,
        "AIOS_RUN_ID": run_id,
        "AIOS_INVOCATION_ID": invocation_id,
        "AIOS_BACKEND_KEY": backend_key,
        "AIOS_DB": db_path,
    }

    conn = sqlite3.connect(db_path)
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

    outcome = "completed"
    result_summary = "Managed runtime captured invocation metadata and completed normally."
    reason_json: dict[str, object] = {"kind": "normal_exit", "backend_key": backend_key}
    workflow_report_id: str | None = None
    workflow_report_path: str | None = None
    workflow_summary: str | None = None

    try:
        surface = "claude_code" if "claude" in backend_key else "codex"
        workflow_context = WorkflowExecutionContext(
            objective=context["objective"] or "",
            workflow_key=context["workflow_key"] or "implementation-delivery",
            surface=surface,
            repo_path=context["repo_path"],
            vault_root=context["obsidian_path"],
            run_id=run_id,
            invocation_id=invocation_id,
        )
        workflow_report = execute_workflow(workflow_context)
        workflow_summary = summarize_execution_report(workflow_report)
        if workflow_report.get("status") != "completed":
            raise RuntimeError(
                f"Workflow execution failed for {workflow_context.workflow_key}: "
                + "; ".join(workflow_report.get("unresolved_issues", []))
            )

        WORKFLOW_REPORT_DIR.mkdir(parents=True, exist_ok=True)
        workflow_path = WORKFLOW_REPORT_DIR / f"{invocation_id}.json"
        workflow_path.write_text(json.dumps(workflow_report, indent=2), encoding="utf-8")
        workflow_report_path = str(workflow_path)

        conn = sqlite3.connect(db_path)
        ensure_runtime_schema(conn)
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
                    }
                ),
                now_iso(),
            ),
        )
        conn.commit()
        conn.close()

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

    return 0 if outcome == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
