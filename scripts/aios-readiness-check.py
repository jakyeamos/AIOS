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
DEFAULT_REPORT_DIR = ROOT / ".planning" / "quick" / "260623-aios-readiness-check"


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    summary: str
    details: dict[str, Any]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run AIOS default-routing readiness checks.")
    parser.add_argument("--source-db", default=str(DEFAULT_SOURCE_DB))
    parser.add_argument("--db-copy", default=None)
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    args = parser.parse_args()

    source_db = Path(args.source_db).expanduser()
    if not source_db.exists():
        print(f"source DB not found: {source_db}", file=sys.stderr)
        return 2

    report_dir = Path(args.report_dir).expanduser()
    report_dir.mkdir(parents=True, exist_ok=True)
    if args.db_copy:
        db_copy = Path(args.db_copy).expanduser()
        db_copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_db, db_copy)
        temp_dir_obj = None
    else:
        temp_dir_obj = tempfile.TemporaryDirectory(prefix="aios-readiness-")
        db_copy = Path(temp_dir_obj.name) / "aios-readiness.db"
        shutil.copy2(source_db, db_copy)
    logs_dir = db_copy.parent / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    try:
        results = run_checks(db_copy, logs_dir)
        ok = all(result.status == "pass" for result in results)
        payload = {
            "ok": ok,
            "generated_at": _now(),
            "source_db": str(source_db),
            "db_copy": str(db_copy),
            "logs_dir": str(logs_dir),
            "results": [result.__dict__ for result in results],
        }
        (report_dir / "readiness-report.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (report_dir / "readiness-report.md").write_text(
            render_markdown(payload),
            encoding="utf-8",
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if ok else 1
    finally:
        if temp_dir_obj is not None:
            temp_dir_obj.cleanup()


def run_checks(db_path: Path, logs_dir: Path) -> list[CheckResult]:
    projects = load_projects(db_path)
    aios_project = projects.get("AIOS")
    amos_project = projects.get("amos-saas")
    results: list[CheckResult] = []
    if not aios_project or not amos_project:
        return [
            CheckResult(
                name="project-inventory",
                status="fail",
                summary="Required readiness projects AIOS and amos-saas were not both registered.",
                details={"project_names": sorted(projects)},
            )
        ]

    route_cases = [
        {
            "name": "aios-bugfix",
            "objective": "Fix the AIOS start-work route metadata bug",
            "project_id": aios_project,
            "workflow": "implementation-delivery",
        },
        {
            "name": "non-aios-login-bugfix",
            "objective": "Fix the amos-saas login redirect bug and verify the quality checks",
            "project_id": amos_project,
            "workflow": "implementation-delivery",
        },
        {
            "name": "ui-user-story-verification",
            "objective": "Verify the AIOS operator UI user stories through the real interface",
            "project_id": aios_project,
            "workflow": "implementation-delivery",
        },
        {
            "name": "academic-writing-positive-control",
            "objective": "Write an academic paper with citations about AIOS routing",
            "project_id": aios_project,
            "workflow": "academic_paper_v1",
        },
    ]
    created_runs: list[dict[str, Any]] = []
    for case in route_cases:
        result, run = check_start_work_case(db_path, logs_dir, case)
        results.append(result)
        if run:
            created_runs.append(run)

    results.append(check_ambiguous_blocks(db_path, logs_dir))
    if created_runs:
        first_run = created_runs[0]
        results.append(check_operator_search(db_path, first_run))
        results.append(check_daily_flow_replay(db_path, first_run))
    else:
        results.append(
            CheckResult(
                name="operator-search",
                status="fail",
                summary="No created run was available for route-decision search.",
                details={},
            )
        )
        results.append(
            CheckResult(
                name="daily-flow-replay",
                status="fail",
                summary="No created run was available for daily-flow replay.",
                details={},
            )
        )
    results.append(check_daily_flow_preview(db_path, amos_project))
    results.append(check_next_action(db_path, amos_project))
    return results


def load_projects(db_path: Path) -> dict[str, str]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT id, name FROM projects WHERE status = 'active'").fetchall()
    finally:
        conn.close()
    return {str(name).strip(): str(project_id) for project_id, name in rows}


def check_start_work_case(
    db_path: Path, logs_dir: Path, case: dict[str, str]
) -> tuple[CheckResult, dict[str, Any] | None]:
    command = [
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
    completed = run_command(command)
    data = completed.get("json", {})
    run = data.get("data", {}).get("run") if isinstance(data.get("data"), dict) else None
    route = data.get("data", {}).get("route") if isinstance(data.get("data"), dict) else None
    workflow = run.get("workflow_key") if isinstance(run, dict) else None
    route_status = run.get("route_status") if isinstance(run, dict) else None
    passed = (
        completed["returncode"] == 0 and workflow == case["workflow"] and route_status == "ready"
    )
    details = {
        "case": case,
        "returncode": completed["returncode"],
        "workflow": workflow,
        "route_status": route_status,
        "route_rationale": route.get("rationale") if isinstance(route, dict) else None,
        "stderr": completed["stderr"],
    }
    return (
        CheckResult(
            name=f"route-selector:{case['name']}",
            status="pass" if passed else "fail",
            summary=(
                f"Selected {workflow} for {case['name']}."
                if passed
                else f"Expected {case['workflow']} but selected {workflow}."
            ),
            details=details,
        ),
        run if isinstance(run, dict) else None,
    )


def check_ambiguous_blocks(db_path: Path, logs_dir: Path) -> CheckResult:
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
            "Fix the bug",
        ]
    )
    data = completed.get("json", {})
    raw_error = data.get("error") if isinstance(data, dict) else {}
    error = raw_error if isinstance(raw_error, dict) else {}
    passed = completed["returncode"] != 0 and error.get("code") == "route-blocked"
    return CheckResult(
        name="route-selector:ambiguous-block",
        status="pass" if passed else "fail",
        summary="Ambiguous objective blocked before packet creation."
        if passed
        else "Ambiguous objective did not block correctly.",
        details={
            "returncode": completed["returncode"],
            "error": error,
            "stderr": completed["stderr"],
        },
    )


def check_operator_search(db_path: Path, run: dict[str, Any]) -> CheckResult:
    objective = str(run.get("objective", ""))
    query = " ".join(objective.split()[:4]) or str(run.get("id", ""))
    completed = run_command(
        [
            sys.executable,
            str(ROOT / "bin" / "aios.py"),
            "--db",
            str(db_path),
            "operator-search",
            "--query",
            query,
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
    return CheckResult(
        name="operator-inspectability:route-search",
        status="pass" if passed else "fail",
        summary="Route decision is searchable with a drill-down path."
        if passed
        else "Route decision search failed.",
        details={"query": query, "hits": hits, "stderr": completed["stderr"]},
    )


def check_daily_flow_preview(db_path: Path, project_id: str) -> CheckResult:
    completed = run_command(
        [
            sys.executable,
            str(ROOT / "bin" / "aios.py"),
            "--db",
            str(db_path),
            "daily-flow",
            "--objective",
            "Fix the amos-saas login redirect bug and verify the quality checks",
            "--project",
            project_id,
            "--dry-run",
            "--json",
        ]
    )
    return check_daily_flow_output("daily-flow:preview", completed)


def check_daily_flow_replay(db_path: Path, run: dict[str, Any]) -> CheckResult:
    completed = run_command(
        [
            sys.executable,
            str(ROOT / "bin" / "aios.py"),
            "--db",
            str(db_path),
            "daily-flow",
            "--run-id",
            str(run["id"]),
            "--json",
        ]
    )
    return check_daily_flow_output("daily-flow:replay", completed)


def check_daily_flow_output(name: str, completed: dict[str, Any]) -> CheckResult:
    data = completed.get("json", {})
    trace = data.get("data", {}).get("trace", {}) if isinstance(data.get("data"), dict) else {}
    steps = trace.get("steps", []) if isinstance(trace, dict) else []
    kinds = [step.get("kind") for step in steps if isinstance(step, dict)]
    expected = [
        "goal",
        "route",
        "packet",
        "run",
        "evaluation",
        "writeback",
        "unresolved_delta",
        "next_action",
    ]
    passed = completed["returncode"] == 0 and kinds == expected
    return CheckResult(
        name=name,
        status="pass" if passed else "fail",
        summary="Daily-flow returned the canonical 8-step trace."
        if passed
        else "Daily-flow did not return the canonical trace.",
        details={"step_kinds": kinds, "stderr": completed["stderr"]},
    )


def check_next_action(db_path: Path, project_id: str) -> CheckResult:
    completed = run_command(
        [
            sys.executable,
            str(ROOT / "bin" / "aios.py"),
            "--db",
            str(db_path),
            "next-action",
            "--project",
            project_id,
            "--json",
        ]
    )
    data = completed.get("json", {})
    actions = data.get("data", {}).get("actions", []) if isinstance(data.get("data"), dict) else []
    passed = completed["returncode"] == 0 and isinstance(actions, list)
    return CheckResult(
        name="operator-inspectability:next-action",
        status="pass" if passed else "fail",
        summary="Next-action returned a structured action list."
        if passed
        else "Next-action failed.",
        details={"total_actions": len(actions), "stderr": completed["stderr"]},
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
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "json": parsed,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# AIOS Readiness Check",
        "",
        f"Generated: {payload['generated_at']}",
        f"Source DB: `{payload['source_db']}`",
        f"DB copy: `{payload['db_copy']}`",
        f"Logs dir: `{payload['logs_dir']}`",
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
