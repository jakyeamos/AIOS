#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "aios.db"
DEFAULT_ROUTE_FAILURES = ROOT / "data" / "aios-route-failures.jsonl"
GATE_ADOPTION_WORKFLOW_KEY = "repo_gate_adoption_v1"
GATE_ADOPTION_ARTIFACTS = {
    "repo_scan_json": "repo-scan.json",
    "gate_matrix_json": "gate-matrix.json",
    "gate_matrix_markdown": "gate-matrix.md",
    "tmcp_expert_enrichment_json": "tmcp-expert-enrichment.json",
    "rubric_pack_json": "rubric-pack.json",
    "rubric_detail_manifest_json": "rubric-detail-manifest.json",
    "rollout_plan_json": "rollout-plan.json",
    "rollout_plan_markdown": "rollout-plan.md",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an AIOS shadow lane for a Codex task.")
    parser.add_argument("objective", help="Task objective to shadow")
    parser.add_argument("--project", default=None, help="Project id, name, or repo path")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="AIOS SQLite database")
    parser.add_argument("--cwd", default=str(Path.cwd()), help="Workspace path used for inference")
    parser.add_argument(
        "--no-worktree",
        action="store_true",
        help="Only create the AIOS route/evidence record; do not create a git worktree",
    )
    parser.add_argument(
        "--governed-route",
        action="store_true",
        help="Mark the AIOS route as governing the baseline task. Use for explicit /aios prompts.",
    )
    args = parser.parse_args()

    route_helper = load_route_helper()
    db_path = Path(args.db).expanduser()
    cwd = Path(args.cwd).expanduser()
    try:
        project = route_helper.resolve_project(db_path, explicit=args.project, cwd=cwd)
    except ValueError as exc:
        print_json(
            {"ok": False, "error": {"code": "project-resolution-failed", "message": str(exc)}}
        )
        return 2

    route_result = route_helper.start_work(
        db_path=db_path,
        objective=args.objective,
        project_id=project["id"],
    )
    if route_result["returncode"] != 0:
        if not args.governed_route:
            diagnostics_path = DEFAULT_ROUTE_FAILURES
            record_route_failure(
                diagnostics_path,
                objective=args.objective,
                project=project,
                route_result=route_result,
                governed_route=args.governed_route,
            )
            print_json(
                route_failure_payload(
                    objective=args.objective,
                    project=project,
                    route_result=route_result,
                    governed_route=args.governed_route,
                    diagnostics_path=diagnostics_path,
                )
            )
            return 0
        print_json(route_result["json"] or route_result)
        return int(route_result["returncode"])

    repo_path = Path(project["repo_path"]).expanduser()
    git_state = git_snapshot(repo_path)
    shadow: dict[str, Any] | None = None
    if not args.no_worktree:
        task_id = make_task_id(args.objective)
        try:
            shadow = create_shadow_lane(
                db_path=db_path,
                repo_path=repo_path,
                task_id=task_id,
                start_sha=str(git_state["head"]),
                condition="full-aios",
            )
        except subprocess.CalledProcessError as exc:
            print_json(
                {
                    "ok": False,
                    "error": {
                        "code": "shadow-worktree-create-failed",
                        "message": exc.stderr.strip() or exc.stdout.strip() or str(exc),
                        "command": exc.cmd,
                    },
                }
            )
            return int(exc.returncode or 1)

    run = route_result["json"]["data"]["run"]
    task_id_for_inspection = (
        str(shadow.get("task_id")) if isinstance(shadow, dict) else make_task_id(args.objective)
    )
    inspect_commands = {
        "operator_search": f"python3 {ROOT / 'bin' / 'aios.py'} --json operator-search --query {run['id']} --kinds run --kinds route_decision --kinds writeback",
        "daily_flow": f"python3 {ROOT / 'bin' / 'aios.py'} --json daily-flow --run-id {run['id']}",
        "shadow_parity": f"python3 {ROOT / 'bin' / 'aios.py'} --json shadow parity --task-id {task_id_for_inspection}",
    }
    evidence_report = build_shadow_evidence_report(
        repo_path=repo_path,
        run_id=str(run["id"]),
        workflow_key=str(run["workflow_key"]),
        baseline_dirty=bool(git_state["dirty"]),
        shadow=shadow,
        inspect_commands=inspect_commands,
    )
    payload = {
        "ok": True,
        "mode": "shadow",
        "governed_route": args.governed_route,
        "objective": args.objective,
        "project": project,
        "baseline": {
            "repo_path": str(repo_path),
            "branch": git_state["branch"],
            "head": git_state["head"],
            "dirty": git_state["dirty"],
            "instruction": baseline_instruction(args.governed_route),
        },
        "aios_route": {
            "run_id": run["id"],
            "workflow_key": run["workflow_key"],
            "packet_id": run["packet_id"],
            "route_id": run["route_id"],
            "status": run["status"],
        },
        "shadow": shadow,
        "shadow_prompt": shadow_prompt(args.objective, shadow),
        "evidence_report": evidence_report,
        "compare_policy": {
            "source_of_truth": "baseline current workspace unless you explicitly promote shadow output",
            "shadow_rule": "do not merge or copy shadow changes back without review",
            "route_rule": route_rule(args.governed_route),
            "useful_evidence": [
                "route differences",
                "context/packet usefulness",
                "test outcomes",
                "diff size",
                "failure modes",
                "operator-search and daily-flow evidence",
            ],
        },
        "inspect": inspect_commands,
    }
    print_json(payload)
    return 0


def load_route_helper() -> Any:
    module_path = ROOT / "scripts" / "codex-aios-route.py"
    spec = importlib.util.spec_from_file_location("codex_aios_route_helper", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load route helper: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git_snapshot(repo_path: Path) -> dict[str, Any]:
    head = run_git(repo_path, "rev-parse", "HEAD")
    branch = run_git(repo_path, "branch", "--show-current") or "detached"
    dirty = bool(run_git(repo_path, "status", "--short"))
    return {"head": head, "branch": branch, "dirty": dirty}


def create_shadow_lane(
    *,
    db_path: Path,
    repo_path: Path,
    task_id: str,
    start_sha: str,
    condition: str,
) -> dict[str, Any]:
    sys.path.insert(0, str(ROOT))
    from services.shadow_branch_runner import (
        create_shadow_worktree,
        record_shadow_branch_run,
    )

    branch_name = make_branch_name(task_id)
    worktree_path = create_shadow_worktree(
        repo_path=repo_path,
        start_sha=start_sha,
        branch_name=branch_name,
    )
    conn = sqlite3.connect(db_path)
    try:
        shadow_run_id = record_shadow_branch_run(
            conn,
            task_id=task_id,
            condition=condition,
            start_sha=start_sha,
            aios_branch=branch_name,
            worktree_path=worktree_path,
            no_evidence_reason=(
                "shadow lane created by codex-aios-shadow; run the generated shadow prompt "
                "before treating this row as implementation evidence"
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return {
        "shadow_run_id": shadow_run_id,
        "task_id": task_id,
        "branch_name": branch_name,
        "worktree_path": worktree_path,
        "contamination_check_passed": False,
        "parity_checklist_status": "no_evidence",
    }


def build_shadow_evidence_report(
    *,
    repo_path: Path,
    run_id: str,
    workflow_key: str,
    baseline_dirty: bool,
    shadow: dict[str, Any] | None,
    inspect_commands: dict[str, str],
) -> dict[str, Any]:
    baseline_dir = repo_path / "AIOS-backfill" / "gate-adoption" / run_id
    shadow_dir = None
    if isinstance(shadow, dict) and shadow.get("worktree_path"):
        shadow_dir = Path(str(shadow["worktree_path"])) / "AIOS-backfill" / "gate-adoption" / run_id

    baseline_inventory = gate_adoption_artifact_inventory(baseline_dir)
    shadow_inventory = gate_adoption_artifact_inventory(shadow_dir)
    comparison = compare_gate_adoption_artifacts(
        baseline_dir=baseline_dir,
        shadow_dir=shadow_dir,
    )
    findings = shadow_evidence_findings(
        workflow_key=workflow_key,
        baseline_dirty=baseline_dirty,
        shadow=shadow,
        baseline_inventory=baseline_inventory,
        shadow_inventory=shadow_inventory,
        comparison=comparison,
    )
    quality_signal = shadow_evidence_quality_signal(
        workflow_key=workflow_key,
        baseline_inventory=baseline_inventory,
        shadow_inventory=shadow_inventory,
        comparison=comparison,
    )
    return {
        "schema": "aios-shadow-evidence-report-v0.1",
        "quality_signal": quality_signal,
        "headline": shadow_evidence_headline(quality_signal, findings),
        "run_id": run_id,
        "workflow_key": workflow_key,
        "artifact_dirs": {
            "baseline": str(baseline_dir),
            "shadow": str(shadow_dir) if shadow_dir else None,
        },
        "artifact_inventory": {
            "baseline": baseline_inventory,
            "shadow": shadow_inventory,
        },
        "comparison": comparison,
        "findings": findings,
        "next_inspections": shadow_next_inspections(
            workflow_key=workflow_key,
            quality_signal=quality_signal,
            inspect_commands=inspect_commands,
            baseline_dir=baseline_dir,
            shadow_dir=shadow_dir,
        ),
    }


def gate_adoption_artifact_inventory(output_dir: Path | None) -> dict[str, Any]:
    paths = {
        name: str(output_dir / filename) if output_dir else None
        for name, filename in GATE_ADOPTION_ARTIFACTS.items()
    }
    present = {
        name: bool(output_dir and (output_dir / filename).exists())
        for name, filename in GATE_ADOPTION_ARTIFACTS.items()
    }
    rubric_dir = output_dir / "rubrics" if output_dir else None
    rubric_docs = sorted(rubric_dir.glob("*")) if rubric_dir and rubric_dir.exists() else []
    return {
        "output_dir": str(output_dir) if output_dir else None,
        "exists": bool(output_dir and output_dir.exists()),
        "artifact_paths": paths,
        "present": present,
        "present_count": sum(1 for value in present.values() if value),
        "missing": [name for name, exists in present.items() if not exists],
        "rubric_doc_count": len([path for path in rubric_docs if path.is_file()]),
    }


def compare_gate_adoption_artifacts(
    *,
    baseline_dir: Path,
    shadow_dir: Path | None,
) -> dict[str, Any]:
    baseline_gate_matrix = _read_json_object(baseline_dir / "gate-matrix.json")
    shadow_gate_matrix = _read_json_object(shadow_dir / "gate-matrix.json") if shadow_dir else {}
    baseline_rollout = _read_json_object(baseline_dir / "rollout-plan.json")
    shadow_rollout = _read_json_object(shadow_dir / "rollout-plan.json") if shadow_dir else {}
    baseline_rubric_pack = _read_json_object(baseline_dir / "rubric-pack.json")
    shadow_rubric_pack = _read_json_object(shadow_dir / "rubric-pack.json") if shadow_dir else {}
    return {
        "gate_matrix": compare_gate_matrices(baseline_gate_matrix, shadow_gate_matrix),
        "rollout_plan": compare_rollout_plans(baseline_rollout, shadow_rollout),
        "rubric_pack": compare_rubric_packs(baseline_rubric_pack, shadow_rubric_pack),
    }


def compare_gate_matrices(baseline: dict[str, Any], shadow: dict[str, Any]) -> dict[str, Any]:
    baseline_gates = _gates_by_id(baseline)
    shadow_gates = _gates_by_id(shadow)
    shared_gate_ids = sorted(set(baseline_gates) & set(shadow_gates))
    status_changes = []
    enforcement_changes = []
    maturity_changes = []
    for gate_id in shared_gate_ids:
        baseline_gate = baseline_gates[gate_id]
        shadow_gate = shadow_gates[gate_id]
        for field, bucket in (
            ("status", status_changes),
            ("enforcement", enforcement_changes),
            ("maturity", maturity_changes),
        ):
            before = baseline_gate.get(field)
            after = shadow_gate.get(field)
            if before != after:
                bucket.append({"gate_id": gate_id, "baseline": before, "shadow": after})
    return {
        "available": bool(baseline_gates or shadow_gates),
        "baseline_summary": baseline.get("summary", {}) if isinstance(baseline, dict) else {},
        "shadow_summary": shadow.get("summary", {}) if isinstance(shadow, dict) else {},
        "baseline_gate_count": len(baseline_gates),
        "shadow_gate_count": len(shadow_gates),
        "added_gate_ids": sorted(set(shadow_gates) - set(baseline_gates)),
        "removed_gate_ids": sorted(set(baseline_gates) - set(shadow_gates)),
        "status_changes": status_changes,
        "enforcement_changes": enforcement_changes,
        "maturity_changes": maturity_changes,
        "top_shadow_absent_gates": _gate_ids_with_status(shadow_gates, "absent")[:8],
        "top_shadow_partial_gates": _gate_ids_with_status(shadow_gates, "partial")[:8],
    }


def compare_rollout_plans(baseline: dict[str, Any], shadow: dict[str, Any]) -> dict[str, Any]:
    baseline_phases = _phases_by_id(baseline)
    shadow_phases = _phases_by_id(shadow)
    return {
        "available": bool(baseline_phases or shadow_phases),
        "baseline_phase_count": len(baseline_phases),
        "shadow_phase_count": len(shadow_phases),
        "added_phase_ids": sorted(set(shadow_phases) - set(baseline_phases)),
        "removed_phase_ids": sorted(set(baseline_phases) - set(shadow_phases)),
        "shadow_phase_titles": [
            {"id": phase_id, "title": str(phase.get("title", ""))}
            for phase_id, phase in sorted(shadow_phases.items())[:8]
        ],
    }


def compare_rubric_packs(baseline: dict[str, Any], shadow: dict[str, Any]) -> dict[str, Any]:
    baseline_broad = _rubric_ids(baseline, "broad_rubrics")
    shadow_broad = _rubric_ids(shadow, "broad_rubrics")
    baseline_gate = _rubric_ids(baseline, "gate_specific_rubrics")
    shadow_gate = _rubric_ids(shadow, "gate_specific_rubrics")
    return {
        "available": bool(baseline_broad or shadow_broad or baseline_gate or shadow_gate),
        "baseline_broad_rubric_count": len(baseline_broad),
        "shadow_broad_rubric_count": len(shadow_broad),
        "baseline_gate_rubric_count": len(baseline_gate),
        "shadow_gate_rubric_count": len(shadow_gate),
        "added_broad_rubrics": sorted(set(shadow_broad) - set(baseline_broad)),
        "removed_broad_rubrics": sorted(set(baseline_broad) - set(shadow_broad)),
        "added_gate_rubrics": sorted(set(shadow_gate) - set(baseline_gate))[:12],
        "removed_gate_rubrics": sorted(set(baseline_gate) - set(shadow_gate))[:12],
        "baseline_tmcp_expert_status": _tmcp_expert_status(baseline),
        "shadow_tmcp_expert_status": _tmcp_expert_status(shadow),
    }


def shadow_evidence_findings(
    *,
    workflow_key: str,
    baseline_dirty: bool,
    shadow: dict[str, Any] | None,
    baseline_inventory: dict[str, Any],
    shadow_inventory: dict[str, Any],
    comparison: dict[str, Any],
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    if baseline_dirty:
        findings.append(
            {
                "severity": "warning",
                "title": "Baseline workspace was dirty",
                "why_it_matters": "Shadow output can still be useful, but it is not a clean baseline comparison.",
                "next_step": "Use shadow artifacts as leads; do not treat diff/parity as proof until a clean baseline run exists.",
            }
        )
    if isinstance(shadow, dict) and shadow.get("contamination_check_passed") is False:
        findings.append(
            {
                "severity": "warning",
                "title": "Contamination check did not pass",
                "why_it_matters": "The shadow lane may be trace evidence rather than reliable parity evidence.",
                "next_step": "Run the shadow parity command and inspect baseline cleanliness before comparing changes.",
            }
        )
    if workflow_key != GATE_ADOPTION_WORKFLOW_KEY:
        findings.append(
            {
                "severity": "info",
                "title": "Route is not repo gate adoption",
                "why_it_matters": "No repo-adoption artifact comparison is expected for this workflow.",
                "next_step": "Inspect operator-search and daily-flow for route quality and follow-up work.",
            }
        )
        return findings

    if shadow_inventory["present_count"] == 0:
        findings.append(
            {
                "severity": "warning",
                "title": "No shadow gate-adoption artifacts found yet",
                "why_it_matters": "The run currently proves routing and worktree creation, not implementation-quality evidence.",
                "next_step": "Run the shadow prompt in the worktree, then compare AIOS-backfill/gate-adoption artifacts.",
            }
        )
    else:
        findings.append(
            {
                "severity": "info",
                "title": "Shadow gate-adoption artifacts are inspectable",
                "why_it_matters": "The shadow run produced concrete repo-scan, gate-matrix, rubric, or rollout evidence.",
                "next_step": "Inspect shadow gate-matrix and rollout-plan before deciding whether any insight should influence baseline work.",
            }
        )
    if baseline_inventory["present_count"] and shadow_inventory["present_count"]:
        gate_matrix = comparison["gate_matrix"]
        changed_count = (
            len(gate_matrix["status_changes"])
            + len(gate_matrix["enforcement_changes"])
            + len(gate_matrix["maturity_changes"])
        )
        findings.append(
            {
                "severity": "info",
                "title": f"Gate matrix comparison found {changed_count} field changes",
                "why_it_matters": "Changed gate status, enforcement, or maturity is the highest-signal adoption feedback.",
                "next_step": "Review comparison.gate_matrix before reading full documents.",
            }
        )
    return findings


def shadow_evidence_quality_signal(
    *,
    workflow_key: str,
    baseline_inventory: dict[str, Any],
    shadow_inventory: dict[str, Any],
    comparison: dict[str, Any],
) -> str:
    if workflow_key != GATE_ADOPTION_WORKFLOW_KEY:
        return "trace_only"
    if baseline_inventory["present_count"] and shadow_inventory["present_count"]:
        gate_matrix = comparison["gate_matrix"]
        rollout = comparison["rollout_plan"]
        if (
            gate_matrix["status_changes"]
            or gate_matrix["enforcement_changes"]
            or gate_matrix["maturity_changes"]
            or rollout["added_phase_ids"]
            or rollout["removed_phase_ids"]
        ):
            return "actionable_comparison"
        return "comparable_no_delta"
    if shadow_inventory["present_count"]:
        return "actionable_shadow_artifacts"
    return "trace_only_needs_shadow_execution"


def shadow_evidence_headline(quality_signal: str, findings: list[dict[str, str]]) -> str:
    warning_count = len([finding for finding in findings if finding["severity"] == "warning"])
    if quality_signal == "actionable_comparison":
        return f"Shadow produced comparable artifact deltas; inspect them before implementation decisions ({warning_count} warning(s))."
    if quality_signal == "actionable_shadow_artifacts":
        return f"Shadow produced gate-adoption artifacts, but no baseline artifact set was found for direct comparison ({warning_count} warning(s))."
    if quality_signal == "comparable_no_delta":
        return f"Baseline and shadow artifacts are comparable and show no high-level gate or rollout delta ({warning_count} warning(s))."
    if quality_signal == "trace_only_needs_shadow_execution":
        return f"Shadow route exists, but no gate-adoption artifacts were found yet ({warning_count} warning(s))."
    return f"Shadow evidence is route trace only for this workflow ({warning_count} warning(s))."


def shadow_next_inspections(
    *,
    workflow_key: str,
    quality_signal: str,
    inspect_commands: dict[str, str],
    baseline_dir: Path,
    shadow_dir: Path | None,
) -> list[dict[str, str]]:
    inspections = [
        {
            "name": "shadow parity",
            "priority": "p0",
            "why": "Confirms contamination and comparison metadata before trusting shadow output.",
            "command": inspect_commands["shadow_parity"],
        },
        {
            "name": "operator-search",
            "priority": "p1",
            "why": "Shows route, packet, and writeback evidence connected to this run.",
            "command": inspect_commands["operator_search"],
        },
        {
            "name": "daily-flow",
            "priority": "p1",
            "why": "Shows whether the run created operator-visible follow-up work.",
            "command": inspect_commands["daily_flow"],
        },
    ]
    if workflow_key == GATE_ADOPTION_WORKFLOW_KEY:
        inspections.insert(
            1,
            {
                "name": "gate-adoption artifacts",
                "priority": "p0" if quality_signal.startswith("actionable") else "p1",
                "why": "Repo adoption quality lives in repo-scan, gate-matrix, rubric-pack, and rollout-plan outputs.",
                "command": f"Compare {baseline_dir} with {shadow_dir}"
                if shadow_dir
                else f"Inspect {baseline_dir}",
            },
        )
    return inspections


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _gates_by_id(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    gates = payload.get("gates") if isinstance(payload, dict) else None
    if not isinstance(gates, list):
        return {}
    return {
        str(gate["id"]): gate
        for gate in gates
        if isinstance(gate, dict) and isinstance(gate.get("id"), str)
    }


def _phases_by_id(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    phases = payload.get("phases") if isinstance(payload, dict) else None
    if not isinstance(phases, list):
        return {}
    return {
        str(phase["id"]): phase
        for phase in phases
        if isinstance(phase, dict) and isinstance(phase.get("id"), str)
    }


def _rubric_ids(payload: dict[str, Any], field: str) -> list[str]:
    rubrics = payload.get(field) if isinstance(payload, dict) else None
    if not isinstance(rubrics, list):
        return []
    return [
        str(rubric["id"]) for rubric in rubrics if isinstance(rubric, dict) and rubric.get("id")
    ]


def _gate_ids_with_status(gates: dict[str, dict[str, Any]], status: str) -> list[str]:
    return sorted(gate_id for gate_id, gate in gates.items() if gate.get("status") == status)


def _tmcp_expert_status(payload: dict[str, Any]) -> str:
    enrichment = payload.get("tmcp_expert_enrichment") if isinstance(payload, dict) else None
    return str(enrichment.get("status", "missing")) if isinstance(enrichment, dict) else "missing"


def run_git(repo_path: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_path,
        text=True,
        capture_output=True,
        check=True,
    )
    return completed.stdout.strip()


def make_task_id(objective: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", objective.lower()).strip("-")[:42] or "codex-task"
    digest = hashlib.sha256(objective.encode("utf-8")).hexdigest()[:8]
    stamp = datetime.now(UTC).strftime("%y%m%d%H%M%S")
    return f"codex-shadow-{stamp}-{slug}-{digest}"


def make_branch_name(task_id: str) -> str:
    safe = re.sub(r"[^a-z0-9-]+", "-", task_id.lower()).strip("-")[:80]
    return f"codex/aios-shadow-{safe}"


def shadow_prompt(objective: str, shadow: dict[str, Any] | None) -> str | None:
    if not shadow:
        return None
    worktree_path = shadow.get("worktree_path")
    if not worktree_path:
        return None
    return (
        f"Open {worktree_path} in a separate Codex thread and run: "
        f"/aios-shadow-implementation {objective}"
    )


def baseline_instruction(governed_route: bool) -> str:
    if governed_route:
        return "Continue the baseline task in the current workspace using the AIOS route and packet as governing context."
    return "Continue the baseline task normally in the current workspace; the AIOS route and packet are shadow evidence only."


def route_rule(governed_route: bool) -> str:
    if governed_route:
        return "explicit /aios command: AIOS route and packet govern the baseline task"
    return "automatic shadow: AIOS route and packet are evidence only and do not govern the baseline task"


def route_failure_payload(
    *,
    objective: str,
    project: dict[str, str],
    route_result: dict[str, Any],
    governed_route: bool,
    diagnostics_path: Path,
) -> dict[str, Any]:
    error = route_error(route_result)
    return {
        "ok": True,
        "mode": "shadow",
        "governed_route": governed_route,
        "objective": objective,
        "project": project,
        "baseline": {
            "repo_path": project.get("repo_path"),
            "instruction": baseline_instruction(governed_route),
            "approval_required": governed_route,
            "can_continue_without_shadow": not governed_route,
        },
        "aios_route": {
            "status": "route_failed",
            "blocking": governed_route,
            "error": error,
        },
        "shadow": None,
        "shadow_prompt": None,
        "diagnostics": {
            "path": str(diagnostics_path),
            "document": str(ROOT / "docs" / "diagnostics" / "route-blocked-failures.md"),
        },
        "compare_policy": {
            "source_of_truth": "baseline current workspace",
            "shadow_rule": shadow_route_failure_rule(governed_route),
            "route_rule": route_rule(governed_route),
            "useful_evidence": [
                "objective text",
                "error code and message",
                "project inference result",
                "route selector candidates",
                "workflow registry coverage gaps",
            ],
        },
    }


def shadow_route_failure_rule(governed_route: bool) -> str:
    if governed_route:
        return "no shadow worktree was created because governed AIOS routing failed"
    return (
        "no shadow worktree was created because automatic AIOS routing failed; "
        "this is diagnostic evidence only and does not require user approval to continue"
    )


def record_route_failure(
    path: Path,
    *,
    objective: str,
    project: dict[str, str],
    route_result: dict[str, Any],
    governed_route: bool,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "recorded_at": datetime.now(UTC).isoformat(),
        "mode": "governed-route" if governed_route else "automatic-shadow",
        "blocking": governed_route,
        "objective": objective,
        "project": project,
        "returncode": route_result.get("returncode"),
        **route_error(route_result),
    }
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(event, sort_keys=True) + "\n")


def route_error(route_result: dict[str, Any]) -> dict[str, Any]:
    payload = route_result.get("json")
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            return {
                "code": str(error.get("code") or "unknown"),
                "message": str(error.get("message") or ""),
                "payload": payload,
            }
    raw = route_result.get("stdout") or route_result.get("stderr") or ""
    return {"code": "route-failed", "message": str(raw), "payload": payload}


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
