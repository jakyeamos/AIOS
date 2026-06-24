#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "aios.db"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Route a Codex prompt through AIOS with project inference."
    )
    parser.add_argument("objective", help="Task objective to route through AIOS")
    parser.add_argument("--project", default=None, help="Project id, name, or repo path")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="AIOS SQLite database")
    parser.add_argument("--cwd", default=os.getcwd(), help="Workspace path used for project inference")
    parser.add_argument(
        "--managed",
        action="store_true",
        help="Also execute the returned run through bin/aios-managed-run.py",
    )
    args = parser.parse_args()

    db_path = Path(args.db).expanduser()
    if not db_path.exists():
        print_json_error("db-not-found", f"AIOS DB not found: {db_path}")
        return 2

    try:
        project = resolve_project(db_path, explicit=args.project, cwd=Path(args.cwd).expanduser())
    except ValueError as exc:
        print_json_error("project-resolution-failed", str(exc))
        return 2

    started = start_work(db_path=db_path, objective=args.objective, project_id=project["id"])
    if started["returncode"] != 0:
        print(json.dumps(started["json"] or started, indent=2, sort_keys=True))
        return int(started["returncode"])

    data = started["json"].get("data", {})
    run = data.get("run", {}) if isinstance(data, dict) else {}
    managed_result: dict[str, Any] | None = None
    if args.managed:
        managed_result = run_json_command(
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
        if managed_result["returncode"] != 0:
            print(json.dumps(managed_result["json"] or managed_result, indent=2, sort_keys=True))
            return int(managed_result["returncode"])

    payload = {
        "ok": True,
        "project": project,
        "objective": args.objective,
        "run": run,
        "managed": managed_result is not None,
        "managed_result": managed_result["json"] if managed_result else None,
        "inspect": {
            "operator_search": [
                sys.executable,
                str(ROOT / "bin" / "aios.py"),
                "--json",
                "operator-search",
                "--query",
                str(run["id"]),
                "--kinds",
                "run",
                "--kinds",
                "route_decision",
                "--kinds",
                "writeback",
            ],
            "daily_flow": [
                sys.executable,
                str(ROOT / "bin" / "aios.py"),
                "--json",
                "daily-flow",
                "--run-id",
                str(run["id"]),
            ],
            "next_action": [
                sys.executable,
                str(ROOT / "bin" / "aios.py"),
                "--json",
                "next-action",
                "--limit",
                "5",
            ],
        },
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def resolve_project(db_path: Path, *, explicit: str | None, cwd: Path) -> dict[str, str]:
    projects = load_projects(db_path)
    if explicit:
        normalized = explicit.strip().lower()
        for project in projects:
            if normalized in {
                project["id"].lower(),
                project["name"].lower(),
                str(Path(project["repo_path"]).expanduser()).lower(),
            }:
                return project
        raise ValueError(f"No active AIOS project matched {explicit!r}.")

    cwd_resolved = cwd.resolve()
    candidates = []
    for project in projects:
        repo = Path(project["repo_path"]).expanduser()
        try:
            repo_resolved = repo.resolve()
        except FileNotFoundError:
            continue
        if cwd_resolved == repo_resolved or repo_resolved in cwd_resolved.parents:
            candidates.append((len(repo_resolved.parts), project))
    if candidates:
        return sorted(candidates, key=lambda item: item[0], reverse=True)[0][1]
    raise ValueError(
        f"Could not infer an AIOS project for cwd {cwd}. Pass --project with a project name or id."
    )


def load_projects(db_path: Path) -> list[dict[str, str]]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT id, name, repo_path FROM projects WHERE status = 'active' ORDER BY name"
        ).fetchall()
    finally:
        conn.close()
    return [
        {"id": str(row[0]), "name": str(row[1]).strip(), "repo_path": str(row[2] or "")}
        for row in rows
        if row[2]
    ]


def start_work(*, db_path: Path, objective: str, project_id: str) -> dict[str, Any]:
    result = run_json_command(start_work_command(db_path, objective, project_id))
    if is_implicit_session_not_found(result):
        result = run_json_command(start_work_command(db_path, objective, project_id, detach_session=True))
    return result


def start_work_command(
    db_path: Path, objective: str, project_id: str, detach_session: bool = False
) -> list[str]:
    command = [
        sys.executable,
        str(ROOT / "bin" / "aios.py"),
        "--json",
        "--db",
        str(db_path),
        "start-work",
        objective,
        "--project",
        project_id,
    ]
    if detach_session:
        command.extend(["--session-id", ""])
    return command


def is_implicit_session_not_found(result: dict[str, Any]) -> bool:
    if result.get("returncode") == 0:
        return False
    payload = result.get("json")
    if not isinstance(payload, dict):
        return False
    error = payload.get("error")
    if not isinstance(error, dict):
        return False
    return error.get("code") == "session-not-found"


def run_json_command(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    parsed: Any = {}
    raw = completed.stdout.strip() or completed.stderr.strip()
    if raw:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"raw": raw}
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "json": parsed,
    }


def print_json_error(code: str, message: str) -> None:
    print(json.dumps({"ok": False, "error": {"code": code, "message": message}}, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
