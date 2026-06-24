#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DB = ROOT / "data" / "aios.db"
DEFAULT_REPORT_DIR = ROOT / ".planning" / "quick" / "260623-aios-adoption-gate"
EXPECTED_FLOW = ["goal", "route", "packet", "run", "evaluation", "writeback", "unresolved_delta", "next_action"]


@dataclass(frozen=True)
class GateResult:
    name: str
    status: str
    summary: str
    details: dict[str, Any]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the AIOS managed-run adoption gate.")
    parser.add_argument("--source-db", default=str(DEFAULT_SOURCE_DB))
    parser.add_argument("--db-copy", default=None)
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    args = parser.parse_args()

    source_db = Path(args.source_db).expanduser()
    if not source_db.exists():
        print(f"source DB not found: {source_db}", file=sys.stderr)
        return 2

    temp_dir = tempfile.TemporaryDirectory(prefix="aios-adoption-gate-")
    temp_path = Path(temp_dir.name)
    db_copy = Path(args.db_copy).expanduser() if args.db_copy else temp_path / "aios-adoption.db"
    db_copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_db, db_copy)
    logs_dir = temp_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    report_dir = Path(args.report_dir).expanduser()
    report_dir.mkdir(parents=True, exist_ok=True)

    try:
        results = run_gate(db_copy, logs_dir)
        ok = all(result.status == "pass" for result in results)
        payload = {
            "ok": ok,
            "generated_at": _now(),
            "source_db": str(source_db),
            "db_copy": str(db_copy),
            "logs_dir": str(logs_dir),
            "results": [result.__dict__ for result in results],
        }
        (report_dir / "adoption-gate-report.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (report_dir / "adoption-gate-report.md").write_text(render_markdown(payload), encoding="utf-8")
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if ok else 1
    finally:
        if not args.db_copy:
            temp_dir.cleanup()


def run_gate(db_path: Path, logs_dir: Path) -> list[GateResult]:
    projects = load_projects(db_path)
    required = {"AIOS", "amos-saas"}
    if not required <= set(projects):
        return [
            GateResult(
                name="project-inventory",
                status="fail",
                summary="AIOS and amos-saas must be registered for the adoption gate.",
                details={"project_names": sorted(projects)},
            )
        ]

    cases = [
        {
            "name": "aios-internal-bugfix",
            "objective": "Fix the AIOS start-work route metadata bug",
            "project_id": projects["AIOS"],
            "expected_workflow": "implementation-delivery",
        },
        {
            "name": "non-aios-bugfix",
            "objective": "Fix the amos-saas login redirect bug and verify the quality checks",
            "project_id": projects["amos-saas"],
            "expected_workflow": "implementation-delivery",
        },
        {
            "name": "aios-ui-verification",
            "objective": "Verify the AIOS operator UI user stories through the real interface",
            "project_id": projects["AIOS"],
            "expected_workflow": "implementation-delivery",
        },
    ]

    results: list[GateResult] = []
    for case in cases:
        start_result, run = start_work(db_path, logs_dir, case)
        results.append(start_result)
        if not run:
            continue
        results.append(run_managed_runtime(db_path, run))
        results.extend(inspect_run(db_path, run))
    return results


def load_projects(db_path: Path) -> dict[str, str]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT id, name FROM projects WHERE status = 'active'").fetchall()
    finally:
        conn.close()
    return {str(name).strip(): str(project_id) for project_id, name in rows}


def start_work(db_path: Path, logs_dir: Path, case: dict[str, str]) -> tuple[GateResult, dict[str, Any] | None]:
    completed = run_command(
        [
            sys.executable,
            str(ROOT / "bin" / "aios.py"),
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "start-work",
            case["objective"],
            "--project",
            case["project_id"],
        ]
    )
    data = completed.get("json", {})
    run = data.get("data", {}).get("run") if isinstance(data.get("data"), dict) else None
    workflow = run.get("workflow_key") if isinstance(run, dict) else None
    passed = completed["returncode"] == 0 and workflow == case["expected_workflow"]
    return (
        GateResult(
            name=f"start-work:{case['name']}",
            status="pass" if passed else "fail",
            summary=(
                f"Created ready run with {workflow}."
                if passed
                else f"Expected {case['expected_workflow']} but got {workflow}."
            ),
            details={
                "objective": case["objective"],
                "project_id": case["project_id"],
                "run_id": run.get("id") if isinstance(run, dict) else None,
                "invocation_id": run.get("active_invocation_id") if isinstance(run, dict) else None,
                "returncode": completed["returncode"],
                "stderr": completed["stderr"],
            },
        ),
        run if isinstance(run, dict) else None,
    )


def run_managed_runtime(db_path: Path, run: dict[str, Any]) -> GateResult:
    completed = run_command(
        [
            sys.executable,
            str(ROOT / "bin" / "aios-managed-run.py"),
            "--db",
            str(db_path),
            "--run-id",
            str(run["id"]),
            "--invocation-id",
            str(run["active_invocation_id"]),
            "--backend-key",
            str(run["backend_key"]),
        ]
    )
    passed = completed["returncode"] == 0
    return GateResult(
        name=f"managed-runtime:{run['id']}",
        status="pass" if passed else "fail",
        summary="Managed runtime completed." if passed else "Managed runtime failed.",
        details={"returncode": completed["returncode"], "stderr": completed["stderr"]},
    )


def inspect_run(db_path: Path, run: dict[str, Any]) -> list[GateResult]:
    run_id = str(run["id"])
    invocation_id = str(run["active_invocation_id"])
    return [
        inspect_lifecycle(db_path, run_id, invocation_id),
        inspect_artifacts(db_path, run_id),
        inspect_operator_search(db_path, run_id),
        inspect_daily_flow(db_path, run_id),
    ]


def inspect_lifecycle(db_path: Path, run_id: str, invocation_id: str) -> GateResult:
    conn = sqlite3.connect(db_path)
    try:
        run_row = conn.execute(
            "SELECT status, session_id, active_invocation_id FROM orchestration_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
        invocation_row = conn.execute(
            "SELECT status, session_id, ended_at FROM orchestration_invocations WHERE id = ?",
            (invocation_id,),
        ).fetchone()
        session_row = conn.execute(
            "SELECT id, status, run_id, invocation_id FROM sessions WHERE run_id = ?",
            (run_id,),
        ).fetchone()
    finally:
        conn.close()
    passed = (
        run_row is not None
        and invocation_row is not None
        and session_row is not None
        and run_row[0] == "completed"
        and invocation_row[0] == "completed"
        and session_row[1] == "closed"
        and run_row[1] == session_row[0]
        and run_row[2] == invocation_id
    )
    return GateResult(
        name=f"lifecycle:{run_id}",
        status="pass" if passed else "fail",
        summary="Run, invocation, and session closed with explicit linkage." if passed else "Lifecycle linkage incomplete.",
        details={
            "run": list(run_row) if run_row else None,
            "invocation": list(invocation_row) if invocation_row else None,
            "session": list(session_row) if session_row else None,
        },
    )


def inspect_artifacts(db_path: Path, run_id: str) -> GateResult:
    conn = sqlite3.connect(db_path)
    try:
        counts = {
            "workflow_reports": _count(conn, "workflow_execution_reports", run_id),
            "criteria_evaluations": _count(conn, "success_criteria_evaluations", run_id),
            "writebacks": _count(conn, "improvement_writebacks", run_id),
            "tmcp_receipts": _count(conn, "tmcp_traversal_receipts", run_id),
        }
    finally:
        conn.close()
    passed = all(value >= 1 for value in counts.values())
    return GateResult(
        name=f"artifacts:{run_id}",
        status="pass" if passed else "fail",
        summary="Workflow, evaluation, writeback, and TMCP artifacts exist." if passed else "Missing managed-run artifacts.",
        details=counts,
    )


def _count(conn: sqlite3.Connection, table: str, run_id: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table} WHERE run_id = ?", (run_id,)).fetchone()[0])


def inspect_operator_search(db_path: Path, run_id: str) -> GateResult:
    completed = run_command(
        [
            sys.executable,
            str(ROOT / "bin" / "aios.py"),
            "--db",
            str(db_path),
            "operator-search",
            "--query",
            run_id,
            "--kinds",
            "route_decision",
            "--limit",
            "10",
            "--json",
        ]
    )
    data = completed.get("json", {})
    hits = data.get("data", {}).get("hits", []) if isinstance(data.get("data"), dict) else []
    passed = completed["returncode"] == 0 and any(hit.get("drill_down_path") for hit in hits)
    return GateResult(
        name=f"operator-search:{run_id}",
        status="pass" if passed else "fail",
        summary="Route decision is searchable." if passed else "Route decision search failed.",
        details={"hits": hits, "stderr": completed["stderr"]},
    )


def inspect_daily_flow(db_path: Path, run_id: str) -> GateResult:
    completed = run_command(
        [
            sys.executable,
            str(ROOT / "bin" / "aios.py"),
            "--db",
            str(db_path),
            "daily-flow",
            "--run-id",
            run_id,
            "--json",
        ]
    )
    data = completed.get("json", {})
    trace = data.get("data", {}).get("trace", {}) if isinstance(data.get("data"), dict) else {}
    steps = trace.get("steps", []) if isinstance(trace, dict) else []
    kinds = [step.get("kind") for step in steps if isinstance(step, dict)]
    provenance = {
        step.get("kind"): step.get("provenance") for step in steps if isinstance(step, dict)
    }
    passed = (
        completed["returncode"] == 0
        and kinds == EXPECTED_FLOW
        and provenance.get("route") == "confirmed"
        and provenance.get("packet") == "confirmed"
        and provenance.get("run") == "confirmed"
        and provenance.get("evaluation") in {"confirmed", "contradictory"}
        and provenance.get("writeback") == "confirmed"
    )
    return GateResult(
        name=f"daily-flow:{run_id}",
        status="pass" if passed else "fail",
        summary="Daily-flow replay exposes route, packet, run, evaluation, and writeback." if passed else "Daily-flow replay incomplete.",
        details={"step_kinds": kinds, "provenance": provenance, "stderr": completed["stderr"]},
    )


def run_command(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    parsed: Any = {}
    if completed.stdout.strip():
        try:
            parsed = json.loads(completed.stdout)
        except json.JSONDecodeError:
            parsed = {"raw_stdout": completed.stdout}
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "json": parsed,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# AIOS Adoption Gate",
        "",
        f"Generated: {payload['generated_at']}",
        f"Source DB: `{payload['source_db']}`",
        f"DB copy: `{payload['db_copy']}`",
        f"Overall: {'PASS' if payload['ok'] else 'FAIL'}",
        "",
        "| Check | Status | Summary |",
        "| --- | --- | --- |",
    ]
    for result in payload["results"]:
        lines.append(f"| {result['name']} | {result['status']} | {result['summary']} |")
    lines.append("")
    return "\n".join(lines)


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
