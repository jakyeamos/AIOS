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
DEFAULT_REPORT_DIR = ROOT / ".planning" / "quick" / "260623-aios-field-pressure-gate"
EXPECTED_FLOW = [
    "goal",
    "route",
    "packet",
    "run",
    "evaluation",
    "writeback",
    "unresolved_delta",
    "next_action",
]
OPERATOR_FILES = [
    "aios-ui/app/search/page.tsx",
    "aios-ui/app/runs/page.tsx",
    "aios-ui/app/runs/[id]/page.tsx",
    "aios-ui/app/writebacks/page.tsx",
    "aios-ui/app/control/page.tsx",
    "aios-ui/components/daily-flow/DailyFlowTrace.tsx",
    "aios-ui/components/next-action/NextActionPanel.tsx",
    "aios-ui/components/search/SearchResults.tsx",
    "aios-ui/server/routers/operator-search.ts",
    "aios-ui/server/routers/daily-flow.ts",
    "aios-ui/server/routers/next-action.ts",
]


@dataclass(frozen=True)
class GateResult:
    name: str
    status: str
    summary: str
    details: dict[str, Any]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run AIOS field-pressure simulation gates.")
    parser.add_argument("--source-db", default=str(DEFAULT_SOURCE_DB))
    parser.add_argument("--db-copy", default=None)
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--managed-limit", type=int, default=6)
    args = parser.parse_args()

    source_db = Path(args.source_db).expanduser()
    if not source_db.exists():
        print(f"source DB not found: {source_db}", file=sys.stderr)
        return 2

    temp_dir = tempfile.TemporaryDirectory(prefix="aios-field-pressure-")
    temp_path = Path(temp_dir.name)
    db_copy = (
        Path(args.db_copy).expanduser() if args.db_copy else temp_path / "aios-field-pressure.db"
    )
    db_copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_db, db_copy)
    logs_dir = temp_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    report_dir = Path(args.report_dir).expanduser()
    report_dir.mkdir(parents=True, exist_ok=True)

    try:
        results = run_gate(db_copy, logs_dir, managed_limit=max(0, args.managed_limit))
        ok = all(result.status in {"pass", "warning"} for result in results)
        payload = {
            "ok": ok,
            "generated_at": _now(),
            "source_db": str(source_db),
            "db_copy": str(db_copy),
            "logs_dir": str(logs_dir),
            "score": score_results(results),
            "results": [result.__dict__ for result in results],
        }
        (report_dir / "field-pressure-report.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (report_dir / "field-pressure-report.md").write_text(
            render_markdown(payload), encoding="utf-8"
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if ok else 1
    finally:
        if not args.db_copy:
            temp_dir.cleanup()


def run_gate(db_path: Path, logs_dir: Path, *, managed_limit: int) -> list[GateResult]:
    projects = load_projects(db_path)
    required = {"AIOS", "amos-saas"}
    if not required <= set(projects):
        return [
            GateResult(
                name="project-inventory",
                status="fail",
                summary="AIOS and amos-saas must be active projects for this simulation.",
                details={"project_names": sorted(projects)},
            )
        ]

    results: list[GateResult] = []
    route_runs, route_results = run_route_pressure(db_path, logs_dir, projects)
    results.extend(route_results)

    managed_runs = route_runs[:managed_limit]
    for run in managed_runs:
        results.append(run_managed_runtime(db_path, logs_dir, run))

    results.append(inspect_volume_artifacts(db_path, managed_runs))
    results.extend(inspect_operator_ux(db_path, managed_runs))
    results.extend(inspect_learning_simulation(db_path, projects["AIOS"]))
    results.extend(inspect_failure_recovery(db_path, logs_dir, projects["AIOS"]))
    results.append(inspect_artifact_hygiene())
    results.append(inspect_dirty_tree_classification())
    return results


def load_projects(db_path: Path) -> dict[str, str]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT id, name FROM projects WHERE status = 'active'").fetchall()
    finally:
        conn.close()
    return {str(name).strip(): str(project_id) for project_id, name in rows}


def route_cases(projects: dict[str, str]) -> list[dict[str, str]]:
    aios = projects["AIOS"]
    amos = projects["amos-saas"]
    return [
        case(
            "aios-route-bug",
            "Fix the AIOS route selector metadata bug",
            aios,
            "implementation-delivery",
        ),
        case(
            "aios-daily-flow",
            "Debug the AIOS daily-flow replay schema regression",
            aios,
            "failure-recovery",
        ),
        case(
            "aios-next-action",
            "Add tests for next-action blocker ranking",
            aios,
            "implementation-delivery",
        ),
        case(
            "aios-ui-verify",
            "Verify the AIOS operator UI user stories through the real interface",
            aios,
            "implementation-delivery",
        ),
        case(
            "aios-db-migration",
            "Fix the AIOS SQLite migration for workflow reports",
            aios,
            "implementation-delivery",
        ),
        case(
            "aios-cli-quality", "Repair failing AIOS CLI quality checks", aios, "failure-recovery"
        ),
        case(
            "amos-login",
            "Fix the amos-saas login redirect bug and verify the checks",
            amos,
            "implementation-delivery",
        ),
        case(
            "amos-api",
            "Debug the amos-saas billing API validation failure",
            amos,
            "failure-recovery",
        ),
        case(
            "amos-ui",
            "Verify the amos-saas dashboard user stories after the sidebar change",
            amos,
            "implementation-delivery",
        ),
        case(
            "amos-tests",
            "Add regression tests for the amos-saas invite flow",
            amos,
            "failure-recovery",
        ),
        case(
            "academic-paper",
            "Write an academic paper about local-first agent operating systems",
            aios,
            "academic_paper_v1",
        ),
        case(
            "paper-revision",
            "Revise the academic paper literature review and citations",
            aios,
            "academic_paper_v1",
        ),
    ]


def case(name: str, objective: str, project_id: str, expected_workflow: str) -> dict[str, str]:
    return {
        "name": name,
        "objective": objective,
        "project_id": project_id,
        "expected_workflow": expected_workflow,
    }


def run_route_pressure(
    db_path: Path, logs_dir: Path, projects: dict[str, str]
) -> tuple[list[dict[str, Any]], list[GateResult]]:
    created_runs: list[dict[str, Any]] = []
    details: list[dict[str, Any]] = []
    for item in route_cases(projects):
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
                item["objective"],
                "--project",
                item["project_id"],
            ]
        )
        data = completed.get("json", {})
        run = data.get("data", {}).get("run") if isinstance(data.get("data"), dict) else None
        workflow = run.get("workflow_key") if isinstance(run, dict) else None
        passed = completed["returncode"] == 0 and workflow == item["expected_workflow"]
        if isinstance(run, dict) and item["expected_workflow"] in {
            "implementation-delivery",
            "failure-recovery",
        }:
            created_runs.append(run)
        details.append(
            {
                "name": item["name"],
                "expected_workflow": item["expected_workflow"],
                "actual_workflow": workflow,
                "run_id": run.get("id") if isinstance(run, dict) else None,
                "passed": passed,
                "stderr": completed["stderr"],
            }
        )

    passed_count = len([item for item in details if item["passed"]])
    result = GateResult(
        name="daily-usage-pressure:route-volume",
        status="pass" if passed_count == len(details) else "fail",
        summary=f"{passed_count}/{len(details)} simulated daily objectives routed as expected.",
        details={"cases": details},
    )
    return created_runs, [result]


def run_managed_runtime(db_path: Path, logs_dir: Path, run: dict[str, Any]) -> GateResult:
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
            "--logs-dir",
            str(logs_dir),
        ]
    )
    passed = completed["returncode"] == 0
    return GateResult(
        name=f"daily-usage-pressure:managed-run:{run['id']}",
        status="pass" if passed else "fail",
        summary="Managed runtime completed." if passed else "Managed runtime failed.",
        details={"returncode": completed["returncode"], "stderr": completed["stderr"]},
    )


def inspect_volume_artifacts(db_path: Path, runs: list[dict[str, Any]]) -> GateResult:
    if not runs:
        return GateResult(
            name="daily-usage-pressure:artifact-volume",
            status="fail",
            summary="No managed runs were available for artifact-volume inspection.",
            details={},
        )
    conn = sqlite3.connect(db_path)
    try:
        per_run = []
        for run in runs:
            run_id = str(run["id"])
            counts = {
                "workflow_reports": count(conn, "workflow_execution_reports", run_id),
                "criteria_evaluations": count(conn, "success_criteria_evaluations", run_id),
                "writebacks": count(conn, "improvement_writebacks", run_id),
                "tmcp_receipts": count(conn, "tmcp_traversal_receipts", run_id),
            }
            per_run.append(
                {
                    "run_id": run_id,
                    "counts": counts,
                    "passed": all(value >= 1 for value in counts.values()),
                }
            )
    finally:
        conn.close()
    passed_count = len([item for item in per_run if item["passed"]])
    return GateResult(
        name="daily-usage-pressure:artifact-volume",
        status="pass" if passed_count == len(per_run) else "fail",
        summary=f"{passed_count}/{len(per_run)} managed runs produced closeout artifacts.",
        details={"runs": per_run},
    )


def inspect_operator_ux(db_path: Path, runs: list[dict[str, Any]]) -> list[GateResult]:
    results = [inspect_operator_files(), inspect_operator_lint()]
    if not runs:
        results.append(
            GateResult(
                name="operator-ux:surface-probes",
                status="fail",
                summary="No managed runs were available for operator surface probes.",
                details={},
            )
        )
        return results

    run_id = str(runs[0]["id"])
    search = run_command(
        [
            sys.executable,
            str(ROOT / "bin" / "aios.py"),
            "--db",
            str(db_path),
            "operator-search",
            "--query",
            run_id,
            "--kinds",
            "run",
            "--kinds",
            "route_decision",
            "--kinds",
            "writeback",
            "--kinds",
            "finding",
            "--limit",
            "20",
            "--json",
        ]
    )
    search_data = search.get("json", {})
    hits = (
        search_data.get("data", {}).get("hits", [])
        if isinstance(search_data.get("data"), dict)
        else []
    )
    hit_kinds = {hit.get("kind") for hit in hits if isinstance(hit, dict)}
    search_passed = (
        search["returncode"] == 0
        and {"run", "route_decision", "writeback"} <= hit_kinds
        and all(hit.get("drill_down_path") for hit in hits if isinstance(hit, dict))
    )

    daily = run_command(
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
    daily_data = daily.get("json", {})
    trace = (
        daily_data.get("data", {}).get("trace", {})
        if isinstance(daily_data.get("data"), dict)
        else {}
    )
    steps = trace.get("steps", []) if isinstance(trace, dict) else []
    step_kinds = [step.get("kind") for step in steps if isinstance(step, dict)]
    daily_passed = (
        daily["returncode"] == 0
        and step_kinds == EXPECTED_FLOW
        and all(step.get("drill_down_path") for step in steps if isinstance(step, dict))
    )

    next_action = run_command(
        [
            sys.executable,
            str(ROOT / "bin" / "aios.py"),
            "--db",
            str(db_path),
            "next-action",
            "--limit",
            "5",
            "--json",
        ]
    )
    next_data = next_action.get("json", {})
    actions = (
        next_data.get("data", {}).get("actions", [])
        if isinstance(next_data.get("data"), dict)
        else []
    )
    next_passed = next_action["returncode"] == 0 and all(
        action.get("title") and action.get("rationale") and action.get("drill_down_path")
        for action in actions
        if isinstance(action, dict)
    )
    results.append(
        GateResult(
            name="operator-ux:surface-probes",
            status="pass" if search_passed and daily_passed and next_passed else "fail",
            summary="Operator surfaces expose searchable, drill-downable run state."
            if search_passed and daily_passed and next_passed
            else "Operator surface probe failed.",
            details={
                "run_id": run_id,
                "search_hit_kinds": sorted(str(kind) for kind in hit_kinds),
                "daily_flow_steps": step_kinds,
                "next_action_count": len(actions),
                "stderr": {
                    "search": search["stderr"],
                    "daily_flow": daily["stderr"],
                    "next_action": next_action["stderr"],
                },
            },
        )
    )
    return results


def inspect_operator_lint() -> GateResult:
    completed = run_command(["pnpm", "--dir", "aios-ui", "lint"])
    warning_lines = [
        line
        for line in completed["stdout"].splitlines()
        if "warning" in line.lower() and "0 errors" not in line.lower()
    ]
    passed = completed["returncode"] == 0
    return GateResult(
        name="operator-ux:lint-typecheck",
        status="pass" if passed else "fail",
        summary=(
            "Operator UI lint/typecheck exits cleanly."
            if passed
            else "Operator UI lint/typecheck failed."
        ),
        details={
            "returncode": completed["returncode"],
            "warning_line_count": len(warning_lines),
            "warning_sample": warning_lines[:10],
            "stderr": completed["stderr"],
        },
    )


def inspect_operator_files() -> GateResult:
    missing = [path for path in OPERATOR_FILES if not (ROOT / path).exists()]
    return GateResult(
        name="operator-ux:file-coverage",
        status="pass" if not missing else "fail",
        summary="Operator route/component/server surfaces exist."
        if not missing
        else "Operator UI surface files are missing.",
        details={"missing": missing, "checked": OPERATOR_FILES},
    )


def inspect_learning_simulation(db_path: Path, project_id: str) -> list[GateResult]:
    sys.path.insert(0, str(ROOT))
    from services.context_loops import (
        create_inner_loop_run,
        propose_learning_candidates,
        record_review_event,
    )
    from services.session_summarizer import SessionSummary
    from services.session_writeback import emit_writeback_candidates

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        loop = create_inner_loop_run(
            conn,
            workflow="aios_field_pressure",
            task_type="session_replay",
            task_input="Use prior session saves to identify repeated AIOS routing friction.",
            triggering_event="field_pressure_gate",
            prompt_version="field-pressure-v1",
            guidance_version="field-pressure-v1",
            retrieved_context=[
                {
                    "kind": "session_save",
                    "id": "synthetic-session-1",
                    "summary": "Repeated route selector ambiguity.",
                }
            ],
            context_sources=[{"kind": "session_imports", "id": "synthetic-session-1"}],
            assumptions=["Synthetic replay stands in for repeated daily session pressure."],
            draft_generator=lambda context: (
                "Repeated session saves show routing friction. "
                f"Approved lessons loaded: {len(context.approved_lessons)}."
            ),
            handoff_notes="Synthetic second-brain replay for AIOS field-pressure gate.",
        )
        review = record_review_event(
            conn,
            run_id=str(loop["run_id"]),
            outcome="edited_and_sent",
            final_output="Repeated session saves show routing friction and suggest a route selector checklist.",
            reviewer_notes="Edits added the reusable route selector checklist target.",
        )
        proposal = propose_learning_candidates(conn, min_reviews=1)
        summary = SessionSummary(
            what_i_was_trying_to_do="Use AIOS managed runs and session saves to validate daily usefulness.",
            project_repo_involved="AIOS",
            important_context_used=[
                "session_imports",
                "context_loop_runs",
                "improvement_writebacks",
            ],
            decisions_made=[
                "Keep AIOS routing through implementation-delivery for code-like work."
            ],
            files_modules_touched=["services/workflow_orchestration.py", "services/daily_flow.py"],
            commands_tools_used=["python3 scripts/aios-adoption-gate.py"],
            bugs_failures_encountered=["Daily-flow canonical finding lookup was missing."],
            successful_fixes=["Canonical evaluation lookup now replays through daily-flow."],
            unresolved_follow_ups=[],
            reusable_patterns=["managed-runtime adoption gate"],
            candidate_skills_to_extract=["field-pressure-gate"],
            should_update_truth_file=True,
            should_create_obsidian_note=True,
            confidence=0.9,
            source_provenance={"project_id": project_id, "source": "field_pressure_gate"},
            writeback_proposal_status="pending",
        )
        summary_dir = Path(tempfile.mkdtemp(prefix="aios-field-pressure-summaries-"))
        first = emit_writeback_candidates(
            "synthetic-session-1", summary, conn=conn, summary_dir=summary_dir
        )
        second = emit_writeback_candidates(
            "synthetic-session-2", summary, conn=conn, summary_dir=summary_dir
        )
        third = emit_writeback_candidates(
            "synthetic-session-3", summary, conn=conn, summary_dir=summary_dir
        )
        conn.commit()
        candidate_count = conn.execute(
            "SELECT COUNT(*) FROM context_loop_learning_candidates WHERE review_event_id = ?",
            (review["review_event_id"],),
        ).fetchone()[0]
        memory_count = conn.execute(
            "SELECT COUNT(*) FROM memory_writeback_proposals WHERE source_run_id LIKE 'synthetic-session-%'",
        ).fetchone()[0]
    finally:
        conn.close()

    learning_passed = candidate_count >= 1
    writeback_passed = memory_count >= 4 and any(
        item.candidate_type == "skillification_candidate" for item in third
    )
    return [
        GateResult(
            name="learning-value:context-loop-replay",
            status="pass" if learning_passed else "fail",
            summary="Second-brain/context-loop replay produced a learning candidate."
            if learning_passed
            else "Context-loop replay did not produce a learning candidate.",
            details={
                "loop_run_id": loop["run_id"],
                "review_event_id": review["review_event_id"],
                "candidate_count": candidate_count,
                "proposal": proposal,
            },
        ),
        GateResult(
            name="learning-value:session-save-writebacks",
            status="pass" if writeback_passed else "fail",
            summary="Repeated synthetic session saves produced governed memory and skillification proposals."
            if writeback_passed
            else "Session-save simulation did not produce expected writeback proposals.",
            details={
                "memory_writeback_count": memory_count,
                "first_candidate_types": [item.candidate_type for item in first],
                "second_candidate_types": [item.candidate_type for item in second],
                "third_candidate_types": [item.candidate_type for item in third],
            },
        ),
    ]


def inspect_failure_recovery(db_path: Path, logs_dir: Path, project_id: str) -> list[GateResult]:
    ambiguous = run_command(
        [
            sys.executable,
            str(ROOT / "bin" / "aios.py"),
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "start-work",
            "make it better",
            "--project",
            project_id,
        ]
    )
    ambiguous_data = ambiguous.get("json", {})
    ambiguous_passed = (
        ambiguous["returncode"] != 0 and "route" in json.dumps(ambiguous_data).lower()
    )

    invalid_project = run_command(
        [
            sys.executable,
            str(ROOT / "bin" / "aios.py"),
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "start-work",
            "Fix the AIOS route selector",
            "--project",
            "project-does-not-exist",
        ]
    )
    invalid_project_data = invalid_project.get("json", {})
    invalid_project_passed = (
        invalid_project["returncode"] != 0
        and "not found" in json.dumps(invalid_project_data).lower()
    )

    missing_run = run_command(
        [
            sys.executable,
            str(ROOT / "bin" / "aios.py"),
            "--db",
            str(db_path),
            "daily-flow",
            "--run-id",
            "run-does-not-exist",
            "--json",
        ]
    )
    missing_data = missing_run.get("json", {})
    trace = (
        missing_data.get("data", {}).get("trace", {})
        if isinstance(missing_data.get("data"), dict)
        else {}
    )
    steps = trace.get("steps", []) if isinstance(trace, dict) else []
    missing_passed = (
        missing_run["returncode"] == 0
        and [step.get("provenance") for step in steps if isinstance(step, dict)].count("missing")
        >= 4
    )

    broken_db = Path(tempfile.mkdtemp(prefix="aios-field-pressure-broken-db-")) / "broken.db"
    shutil.copy2(db_path, broken_db)
    conn = sqlite3.connect(broken_db)
    try:
        conn.execute("DROP TABLE IF EXISTS success_criteria_findings")
        conn.commit()
    finally:
        conn.close()
    degraded = run_command(
        [
            sys.executable,
            str(ROOT / "bin" / "aios.py"),
            "--db",
            str(broken_db),
            "daily-flow",
            "--run-id",
            latest_run_id(db_path),
            "--json",
        ]
    )
    degraded_data = degraded.get("json", {})
    degraded_trace = (
        degraded_data.get("data", {}).get("trace", {})
        if isinstance(degraded_data.get("data"), dict)
        else {}
    )
    degraded_steps = degraded_trace.get("steps", []) if isinstance(degraded_trace, dict) else []
    degraded_eval = next(
        (
            step
            for step in degraded_steps
            if isinstance(step, dict) and step.get("kind") == "evaluation"
        ),
        {},
    )
    degraded_passed = degraded["returncode"] == 0 and degraded_eval.get("provenance") == "missing"

    missing_managed = run_command(
        [
            sys.executable,
            str(ROOT / "bin" / "aios-managed-run.py"),
            "--db",
            str(db_path),
            "--run-id",
            "run-does-not-exist",
            "--invocation-id",
            "invoke-does-not-exist",
            "--backend-key",
            "codex-managed-runtime",
            "--logs-dir",
            str(logs_dir),
        ]
    )
    missing_managed_error = parse_json(missing_managed["stderr"])
    missing_managed_passed = (
        missing_managed["returncode"] != 0
        and isinstance(missing_managed_error, dict)
        and missing_managed_error.get("error", {}).get("code") == "managed-run-preflight-failed"
        and "traceback" not in missing_managed["stderr"].lower()
    )

    return [
        GateResult(
            name="failure-recovery:ambiguous-objective",
            status="pass" if ambiguous_passed else "fail",
            summary="Ambiguous objective blocks instead of guessing."
            if ambiguous_passed
            else "Ambiguous objective was not blocked cleanly.",
            details={
                "returncode": ambiguous["returncode"],
                "stderr": ambiguous["stderr"],
                "json": ambiguous_data,
            },
        ),
        GateResult(
            name="failure-recovery:invalid-project",
            status="pass" if invalid_project_passed else "fail",
            summary=(
                "Unknown explicit project fails cleanly."
                if invalid_project_passed
                else "Unknown explicit project did not fail cleanly."
            ),
            details={
                "returncode": invalid_project["returncode"],
                "stderr": invalid_project["stderr"],
                "json": invalid_project_data,
            },
        ),
        GateResult(
            name="failure-recovery:missing-run-replay",
            status="pass" if missing_passed else "fail",
            summary="Daily-flow missing-run replay degrades to explicit missing provenance."
            if missing_passed
            else "Missing-run replay did not degrade cleanly.",
            details={
                "returncode": missing_run["returncode"],
                "step_count": len(steps),
                "stderr": missing_run["stderr"],
            },
        ),
        GateResult(
            name="failure-recovery:stale-schema-replay",
            status="pass" if degraded_passed else "fail",
            summary="Daily-flow stale-schema replay reports missing evaluation evidence without crashing."
            if degraded_passed
            else "Stale-schema replay did not degrade cleanly.",
            details={
                "returncode": degraded["returncode"],
                "evaluation_step": degraded_eval,
                "stderr": degraded["stderr"],
            },
        ),
        GateResult(
            name="failure-recovery:missing-managed-run",
            status="pass" if missing_managed_passed else "fail",
            summary=(
                "Managed runtime missing-run preflight fails cleanly without traceback."
                if missing_managed_passed
                else "Managed runtime missing-run preflight did not fail cleanly."
            ),
            details={
                "returncode": missing_managed["returncode"],
                "stderr_json": missing_managed_error,
                "stderr": missing_managed["stderr"],
            },
        ),
    ]


def inspect_artifact_hygiene() -> GateResult:
    status = run_command(
        [
            "git",
            "status",
            "--short",
            "--ignored",
            "logs/control-plane",
            "logs/session-effectiveness",
        ]
    )
    lines = [line for line in status["stdout"].splitlines() if line.strip()]
    unignored = [line for line in lines if not line.startswith("!! ")]
    ignored = [line for line in lines if line.startswith("!! ")]
    passed = status["returncode"] == 0 and not unignored
    return GateResult(
        name="artifact-hygiene:runtime-logs",
        status="pass" if passed else "fail",
        summary="Managed runtime log directories are ignored by git."
        if passed
        else "Managed runtime logs still appear as source changes.",
        details={
            "ignored_entries": ignored[:20],
            "unignored_entries": unignored[:20],
            "returncode": status["returncode"],
        },
    )


def classify_dirty_tree() -> dict[str, Any]:
    status = run_command(["git", "status", "--short", "--ignored"])
    source_changes: list[str] = []
    ignored_runtime: list[str] = []
    ignored_other: list[str] = []
    for line in status["stdout"].splitlines():
        if not line.strip():
            continue
        path = line[3:] if len(line) > 3 else ""
        if line.startswith("!! "):
            if path.startswith(("logs/", "data/", "staging/", ".pytest_cache/", ".ruff_cache/")):
                ignored_runtime.append(line)
            else:
                ignored_other.append(line)
        else:
            source_changes.append(line)
    return {
        "returncode": status["returncode"],
        "source_change_count": len(source_changes),
        "ignored_runtime_count": len(ignored_runtime),
        "ignored_other_count": len(ignored_other),
        "source_change_sample": source_changes[:30],
        "ignored_runtime_sample": ignored_runtime[:20],
    }


def inspect_dirty_tree_classification() -> GateResult:
    classification = classify_dirty_tree()
    passed = classification["returncode"] == 0
    return GateResult(
        name="artifact-hygiene:dirty-tree-classification",
        status="pass" if passed else "fail",
        summary=(
            "Dirty tree is classified into source changes and ignored runtime artifacts."
            if passed
            else "Dirty-tree classification failed."
        ),
        details=classification,
    )


def latest_run_id(db_path: Path) -> str:
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT id FROM orchestration_runs ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()
    return str(row[0]) if row else "run-does-not-exist"


def count(conn: sqlite3.Connection, table: str, run_id: str) -> int:
    return int(
        conn.execute(f"SELECT COUNT(*) FROM {table} WHERE run_id = ?", (run_id,)).fetchone()[0]
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


def parse_json(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def score_results(results: list[GateResult]) -> int:
    if not results:
        return 0
    points = 0.0
    for result in results:
        if result.status == "pass":
            points += 1.0
        elif result.status == "warning":
            points += 0.5
    return round((points / len(results)) * 100)


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# AIOS Field Pressure Gate",
        "",
        f"Generated: {payload['generated_at']}",
        f"Source DB: `{payload['source_db']}`",
        f"DB copy: `{payload['db_copy']}`",
        f"Overall: {'PASS' if payload['ok'] else 'FAIL'}",
        f"Score: {payload['score']}/100",
        "",
        "| Concern | Status | Summary |",
        "| --- | --- | --- |",
    ]
    for result in payload["results"]:
        concern = result["name"].split(":", 1)[0]
        lines.append(f"| {concern} / {result['name']} | {result['status']} | {result['summary']} |")
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "- Daily usage pressure is simulated through route volume plus managed-runtime subset execution."
    )
    lines.append(
        "- Operator UX is tested through route/component presence, UI lint/typecheck, and executable drill-downable JSON surfaces."
    )
    lines.append(
        "- Artifact hygiene is tested by requiring managed-runtime log directories to be git-ignored and classifying dirty-tree state into source changes versus ignored runtime artifacts."
    )
    lines.append(
        "- Learning value is simulated with context-loop replay and repeated session-save writeback proposals."
    )
    lines.append(
        "- Failure recovery is tested with ambiguous objectives, invalid projects, missing run replay, stale schema replay, and missing managed-run preflight."
    )
    lines.append("")
    return "\n".join(lines)


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
