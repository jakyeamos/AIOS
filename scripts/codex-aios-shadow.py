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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create an AIOS shadow lane for a Codex task."
    )
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
        print_json({"ok": False, "error": {"code": "project-resolution-failed", "message": str(exc)}})
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
        "inspect": {
            "operator_search": f"python3 {ROOT / 'bin' / 'aios.py'} --json operator-search --query {run['id']} --kinds run --kinds route_decision --kinds writeback",
            "daily_flow": f"python3 {ROOT / 'bin' / 'aios.py'} --json daily-flow --run-id {run['id']}",
            "shadow_parity": f"python3 {ROOT / 'bin' / 'aios.py'} --json shadow parity --task-id {shadow.get('task_id') if isinstance(shadow, dict) else make_task_id(args.objective)}",
        },
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
    }


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
            "shadow_rule": "no shadow worktree was created because AIOS routing failed",
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
