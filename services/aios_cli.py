from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
from collections import deque
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_ROOT = REPO_ROOT / "config"
DEFAULT_DB_PATH = Path.home() / "AIOS" / "data" / "aios.db"
DEFAULT_LOGS_DIR = Path.home() / "AIOS" / "logs"
LOG_SOURCE_FILES = {
    "hooks": "hooks.log",
    "pipeline": "pipeline.log",
    "maintenance": "maintenance.log",
    "health": "health.log",
    "promote-patterns": "promote-patterns.log",
}

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_NOT_FOUND = 3
EXIT_DEPENDENCY = 4
EXIT_RUNTIME = 5


class CLIError(Exception):
    def __init__(self, code: str, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.exit_code = exit_code


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (name,),
    ).fetchone()
    return row is not None


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _resolve_vault_root(explicit: str | None = None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    env_root = os.environ.get("AIOS_VAULT_ROOT")
    candidates = [
        Path(env_root).expanduser() if env_root else None,
        Path.home() / "projects" / "Vaults" / "Command-Center",
        Path.home() / "Vaults" / "Command-Center",
    ]
    for candidate in candidates:
        if candidate and candidate.is_dir():
            return candidate.resolve()
    return (Path.home() / "projects" / "Vaults" / "Command-Center").resolve()


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, dict):
        raise CLIError("invalid-json", f"Expected object JSON at {path}", EXIT_RUNTIME)
    return loaded


def _connect_db(path: Path) -> sqlite3.Connection:
    if not path.exists():
        raise CLIError("db-not-found", f"SQLite database not found: {path}", EXIT_DEPENDENCY)
    try:
        conn = sqlite3.connect(path)
    except sqlite3.Error as exc:
        raise CLIError("db-connect-failed", str(exc), EXIT_RUNTIME) from exc
    conn.row_factory = sqlite3.Row
    return conn


def _count(conn: sqlite3.Connection, table: str, where: str = "1=1") -> int:
    if not _table_exists(conn, table):
        return 0
    row = conn.execute(f"SELECT COUNT(*) AS count FROM {table} WHERE {where}").fetchone()
    return int(row["count"]) if row else 0


def _tail_lines(path: Path, limit: int) -> list[str]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return list(deque(handle, maxlen=limit))


def _json_envelope(command: str, data: Any) -> dict[str, Any]:
    return {
        "ok": True,
        "command": command,
        "generated_at": _now_iso(),
        "data": data,
    }


def _error_envelope(command: str, err: CLIError) -> dict[str, Any]:
    return {
        "ok": False,
        "command": command,
        "generated_at": _now_iso(),
        "error": {
            "code": err.code,
            "message": err.message,
            "exit_code": err.exit_code,
        },
    }


def _last_session(conn: sqlite3.Connection) -> dict[str, Any] | None:
    if not _table_exists(conn, "sessions"):
        return None
    query = """
        SELECT s.id, s.status, s.started_at, s.ended_at, s.cwd, p.name AS project
        FROM sessions s
        LEFT JOIN projects p ON p.id = s.project_id
        ORDER BY s.started_at DESC
        LIMIT 1
    """
    row = conn.execute(query).fetchone()
    if not row:
        return None
    return dict(row)


def _run_status_counts(conn: sqlite3.Connection) -> dict[str, int]:
    if not _table_exists(conn, "orchestration_runs"):
        return {}
    rows = conn.execute(
        "SELECT status, COUNT(*) AS count FROM orchestration_runs GROUP BY status"
    ).fetchall()
    return {str(row["status"]): int(row["count"]) for row in rows}


def _linked_projects(config_root: Path) -> list[dict[str, Any]]:
    projects_path = config_root / "architecture-enforcement" / "projects.json"
    if not projects_path.exists():
        return []
    loaded = _load_json(projects_path)
    projects = loaded.get("projects", [])
    if not isinstance(projects, list):
        return []

    results: list[dict[str, Any]] = []
    for item in projects:
        if not isinstance(item, dict):
            continue
        raw_path = str(item.get("path", ""))
        resolved = Path(raw_path).expanduser()
        results.append(
            {
                "id": str(item.get("id", "")),
                "name": str(item.get("name", "")),
                "path": str(resolved),
                "path_exists": resolved.exists(),
                "proof_target": bool(item.get("proof_target", False)),
                "profile_ids": [
                    str(binding.get("profile_id", ""))
                    for binding in item.get("profile_bindings", [])
                    if isinstance(binding, dict)
                ],
            }
        )
    return results


def _criteria_catalog_summary(config_root: Path) -> dict[str, Any]:
    registry_path = config_root / "success-criteria" / "registry.json"
    if not registry_path.exists():
        return {"count": 0, "registry_path": str(registry_path), "criteria_ids": []}
    loaded = _load_json(registry_path)
    criteria = loaded.get("criteria", [])
    if not isinstance(criteria, list):
        criteria = []
    criteria_ids = [
        str(item.get("id", ""))
        for item in criteria
        if isinstance(item, dict) and item.get("id")
    ]
    return {
        "count": len(criteria_ids),
        "registry_path": str(registry_path),
        "criteria_ids": criteria_ids,
    }


def _workflow_registry_summary(config_root: Path) -> dict[str, Any]:
    registry_path = config_root / "workflows" / "registry.json"
    if not registry_path.exists():
        return {"count": 0, "registry_path": str(registry_path), "workflow_keys": []}

    loaded = _load_json(registry_path)
    workflows = loaded.get("workflows", [])
    if not isinstance(workflows, list):
        workflows = []
    workflow_keys = [
        str(item.get("key", ""))
        for item in workflows
        if isinstance(item, dict) and item.get("key")
    ]
    return {
        "count": len(workflow_keys),
        "registry_path": str(registry_path),
        "workflow_keys": workflow_keys,
    }


def _execution_strategy_summary(config_root: Path) -> dict[str, Any]:
    registry_path = config_root / "execution-strategies" / "registry.json"
    if not registry_path.exists():
        return {
            "task_family_count": 0,
            "strategy_count": 0,
            "registry_path": str(registry_path),
            "task_families": [],
        }

    loaded = _load_json(registry_path)
    task_families = loaded.get("task_families", [])
    selection = loaded.get("selection", [])
    if not isinstance(task_families, list):
        task_families = []
    if not isinstance(selection, list):
        selection = []
    return {
        "task_family_count": len(task_families),
        "strategy_count": len(selection),
        "registry_path": str(registry_path),
        "task_families": [str(item) for item in task_families],
    }


def _latest_success_criteria_evaluation(conn: sqlite3.Connection) -> dict[str, Any] | None:
    if not _table_exists(conn, "success_criteria_evaluations"):
        return None
    row = conn.execute(
        """
        SELECT id, project_id, run_id, session_id, pass_count, warning_count, blocker_count, summary, created_at
        FROM success_criteria_evaluations
        ORDER BY created_at DESC
        LIMIT 1
        """
    ).fetchone()
    if row is None:
        return None
    return {
        "id": row["id"],
        "project_id": row["project_id"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "pass_count": row["pass_count"],
        "warning_count": row["warning_count"],
        "blocker_count": row["blocker_count"],
        "summary": row["summary"],
        "created_at": row["created_at"],
    }


def _latest_workflow_execution_report(conn: sqlite3.Connection) -> dict[str, Any] | None:
    if not _table_exists(conn, "workflow_execution_reports"):
        return None
    row = conn.execute(
        """
        SELECT id, run_id, invocation_id, workflow_key, status, artifact_path, created_at
        FROM workflow_execution_reports
        ORDER BY created_at DESC
        LIMIT 1
        """
    ).fetchone()
    if row is None:
        return None
    return {
        "id": row["id"],
        "run_id": row["run_id"],
        "invocation_id": row["invocation_id"],
        "workflow_key": row["workflow_key"],
        "status": row["status"],
        "artifact_path": row["artifact_path"],
        "created_at": row["created_at"],
    }


def _extract_hash(content: str) -> str | None:
    for line in content.splitlines():
        if line.startswith("source_hash:"):
            return line.partition(":")[2].strip()
    return None


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _load_instruction_registry(config_root: Path) -> list[dict[str, Any]]:
    registry_path = config_root / "instruction-registry.json"
    if not registry_path.exists():
        return []
    loaded = _load_json(registry_path)
    entries = loaded.get("entries", [])
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict)]


def _instruction_status(
    config_root: Path,
    vault_root: Path,
    project_id: str | None = None,
) -> dict[str, Any]:
    entries = _load_instruction_registry(config_root)
    results: list[dict[str, Any]] = []
    for entry in entries:
        entry_project_id = entry.get("project_id")
        if project_id and entry_project_id not in {project_id, None}:
            continue

        source_path = Path(str(entry.get("source", ""))).expanduser()
        target_path = (vault_root / str(entry.get("target", ""))).resolve()
        source_exists = source_path.exists()
        target_exists = target_path.exists()
        source_hash = _sha256_file(source_path) if source_exists else None
        target_hash = None
        if target_exists:
            target_hash = _extract_hash(target_path.read_text(encoding="utf-8", errors="replace"))

        status = "in_sync"
        if not source_exists:
            status = "missing_source"
        elif not target_exists:
            status = "missing_target"
        elif target_hash != source_hash:
            status = "outdated"

        results.append(
            {
                "id": str(entry.get("id", "")),
                "project_id": entry_project_id,
                "source": str(source_path),
                "target": str(target_path),
                "source_exists": source_exists,
                "target_exists": target_exists,
                "status": status,
            }
        )

    summary = {
        "total": len(results),
        "in_sync": sum(1 for row in results if row["status"] == "in_sync"),
        "outdated": sum(1 for row in results if row["status"] == "outdated"),
        "missing_source": sum(1 for row in results if row["status"] == "missing_source"),
        "missing_target": sum(1 for row in results if row["status"] == "missing_target"),
    }
    return {"summary": summary, "entries": results}


def _refresh_instructions(
    config_root: Path,
    vault_root: Path,
    project_id: str | None,
    apply: bool,
) -> dict[str, Any]:
    status = _instruction_status(config_root, vault_root, project_id=project_id)
    actions: list[dict[str, Any]] = []
    updated = 0
    now_date = datetime.now(UTC).date().isoformat()

    for row in status["entries"]:
        current = row["status"]
        if current not in {"outdated", "missing_target"}:
            continue
        source_path = Path(row["source"])
        if not source_path.exists():
            continue
        target_path = Path(row["target"])
        action = "update" if target_path.exists() else "create"

        if apply:
            source_text = source_path.read_text(encoding="utf-8", errors="replace")
            source_hash = _sha256_file(source_path)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_text = (
                "---\n"
                "type: claude-context\n"
                f"id: {row['id']}\n"
                f"project_id: {row['project_id']}\n"
                f"source_path: {row['source']}\n"
                f"last_synced: {now_date}\n"
                f"source_hash: {source_hash}\n"
                "---\n\n"
                f"{source_text}"
            )
            target_path.write_text(target_text, encoding="utf-8")
            updated += 1

        actions.append(
            {
                "id": row["id"],
                "project_id": row["project_id"],
                "action": action,
                "source": row["source"],
                "target": row["target"],
                "applied": apply,
            }
        )

    return {
        "apply": apply,
        "updated_count": updated,
        "pending_count": len(actions) if not apply else 0,
        "actions": actions,
    }


def _status_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    return {
        "projects_active": _count(conn, "projects", "status='active'"),
        "sessions_open": _count(conn, "sessions", "status='open'"),
        "sessions_24h": _count(conn, "sessions", "started_at > datetime('now', '-1 day')"),
        "open_bugs": _count(conn, "bug_log", "status='open'"),
        "run_status_counts": _run_status_counts(conn),
        "last_session": _last_session(conn),
    }


def _health_payload(conn: sqlite3.Connection, logs_dir: Path) -> dict[str, Any]:
    status = _status_payload(conn)
    log_files = []
    for source, file_name in LOG_SOURCE_FILES.items():
        file_path = logs_dir / file_name
        log_files.append(
            {
                "source": source,
                "path": str(file_path),
                "exists": file_path.exists(),
                "bytes": file_path.stat().st_size if file_path.exists() else 0,
            }
        )
    return {
        "status_snapshot": status,
        "log_files": log_files,
        "checks": {
            "db_reachable": True,
            "runs_active": status["run_status_counts"].get("in_progress", 0),
            "open_bugs": status["open_bugs"],
        },
    }


def _logs_payload(logs_dir: Path, sources: list[str], last: int) -> dict[str, Any]:
    selected = sources if sources else sorted(LOG_SOURCE_FILES)
    lines: list[dict[str, Any]] = []
    for source in selected:
        file_name = LOG_SOURCE_FILES.get(source)
        if not file_name:
            raise CLIError("invalid-source", f"Unknown log source: {source}", EXIT_USAGE)
        file_path = logs_dir / file_name
        tailed = _tail_lines(file_path, last)
        for line in tailed:
            stripped = line.rstrip("\n")
            lines.append(
                {
                    "source": source,
                    "path": str(file_path),
                    "line": stripped,
                }
            )
    return {"count": len(lines), "lines": lines[-last:]}


def _recent_failures_payload(conn: sqlite3.Connection, logs_dir: Path, last: int) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []

    if _table_exists(conn, "orchestration_run_events"):
        rows = conn.execute(
            """
            SELECT run_id, to_status, summary, reason_json, created_at
            FROM orchestration_run_events
            WHERE to_status IN ('failed', 'canceled')
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (last,),
        ).fetchall()
        for row in rows:
            failures.append(
                {
                    "source": "orchestration",
                    "kind": str(row["to_status"]),
                    "occurred_at": row["created_at"],
                    "summary": row["summary"],
                    "details": {
                        "run_id": row["run_id"],
                        "reason_json": row["reason_json"],
                    },
                }
            )

    if _table_exists(conn, "bug_log"):
        rows = conn.execute(
            """
            SELECT id, symptom, status, created_at, project_id
            FROM bug_log
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (last,),
        ).fetchall()
        for row in rows:
            failures.append(
                {
                    "source": "bug_log",
                    "kind": str(row["status"]),
                    "occurred_at": row["created_at"],
                    "summary": row["symptom"],
                    "details": {
                        "bug_id": row["id"],
                        "project_id": row["project_id"],
                    },
                }
            )

    hooks_path = logs_dir / LOG_SOURCE_FILES["hooks"]
    for line in _tail_lines(hooks_path, last * 3):
        lowered = line.lower()
        if "error" not in lowered and "failed" not in lowered:
            continue
        ts = line.split(" ", 1)[0].strip()
        failures.append(
            {
                "source": "hooks-log",
                "kind": "log-error",
                "occurred_at": ts if _parse_iso(ts) else None,
                "summary": line.strip(),
                "details": {},
            }
        )

    failures.sort(
        key=lambda item: _parse_iso(item.get("occurred_at")) or datetime.min.replace(tzinfo=UTC),
        reverse=True,
    )
    return {"count": min(len(failures), last), "failures": failures[:last]}


def _metadata_payload(
    conn: sqlite3.Connection,
    db_path: Path,
    logs_dir: Path,
    config_root: Path,
    vault_root: Path,
    project_id: str | None,
) -> dict[str, Any]:
    linked_projects = _linked_projects(config_root)
    instructions = _instruction_status(config_root, vault_root, project_id=project_id)
    current_session_path = logs_dir / "current_session"
    current_session = current_session_path.read_text(encoding="utf-8").strip() if current_session_path.exists() else None
    run_counts = _run_status_counts(conn)
    latest_criteria_eval = _latest_success_criteria_evaluation(conn)
    latest_workflow_report = _latest_workflow_execution_report(conn)

    return {
        "system": {
            "cwd": str(Path.cwd()),
            "db_path": str(db_path),
            "logs_dir": str(logs_dir),
            "vault_root": str(vault_root),
            "config_root": str(config_root),
        },
        "linked_projects": {
            "count": len(linked_projects),
            "items": linked_projects,
        },
        "runtime": {
            "current_session_id": current_session,
            "last_session": _last_session(conn),
            "run_status_counts": run_counts,
        },
        "instructions": instructions,
        "success_criteria": {
            "catalog": _criteria_catalog_summary(config_root),
            "latest_evaluation": latest_criteria_eval,
        },
        "workflow_orchestration": {
            "registry": _workflow_registry_summary(config_root),
            "latest_execution_report": latest_workflow_report,
        },
        "execution_strategies": _execution_strategy_summary(config_root),
        "health": _health_payload(conn, logs_dir),
        "recent_failures_preview": _recent_failures_payload(conn, logs_dir, last=5),
        "available_commands": [
            "aios status --json",
            "aios health --json",
            "aios metadata --json",
            "aios logs --json --last 50",
            "aios recent-failures --json --last 20",
            "aios skills status --json",
            "aios skills refresh --json --apply",
        ],
    }


def _render_human(command: str, data: dict[str, Any]) -> None:
    if command == "status":
        print(
            "projects_active={projects_active} sessions_open={sessions_open} open_bugs={open_bugs}".format(
                **data
            )
        )
        return
    if command == "health":
        checks = data["checks"]
        print(
            f"db_reachable={checks['db_reachable']} runs_active={checks['runs_active']} open_bugs={checks['open_bugs']}"
        )
        return
    if command == "metadata":
        print(
            f"linked_projects={data['linked_projects']['count']} "
            f"instructions_outdated={data['instructions']['summary']['outdated']}"
        )
        return
    if command == "logs":
        print(f"lines={data['count']}")
        return
    if command == "recent-failures":
        print(f"failures={data['count']}")
        return
    if command == "skills-status":
        summary = data["summary"]
        print(
            f"in_sync={summary['in_sync']} outdated={summary['outdated']} missing_target={summary['missing_target']}"
        )
        return
    if command == "skills-refresh":
        print(f"updated={data['updated_count']} pending={data['pending_count']}")
        return


def _command_name(args: argparse.Namespace) -> str:
    if args.command == "skills":
        return f"skills-{args.skills_command}"
    return args.command


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AIOS unified JSON-first CLI")
    parser.add_argument("--json", action="store_true", help="Emit JSON envelope")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="SQLite database path")
    parser.add_argument("--logs-dir", default=str(DEFAULT_LOGS_DIR), help="Logs directory")
    parser.add_argument("--config-root", default=str(DEFAULT_CONFIG_ROOT), help="Config root directory")
    parser.add_argument("--vault-root", default=None, help="Override vault root path")

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Compact control-plane status snapshot")
    subparsers.add_parser("health", help="Health summary with status + log file checks")

    metadata_parser = subparsers.add_parser("metadata", help="One-shot metadata snapshot")
    metadata_parser.add_argument("--project", default=None, help="Optional project id filter")

    logs_parser = subparsers.add_parser("logs", help="Read AIOS logs")
    logs_parser.add_argument("--source", action="append", default=[], help="Log source filter")
    logs_parser.add_argument("--last", type=int, default=50, help="Last N log lines")

    failures_parser = subparsers.add_parser("recent-failures", help="Recent failures across control-plane surfaces")
    failures_parser.add_argument("--last", type=int, default=20, help="Max failures to return")

    skills_parser = subparsers.add_parser("skills", help="Instruction/skills registry surfaces")
    skills_subparsers = skills_parser.add_subparsers(dest="skills_command", required=True)

    skills_status = skills_subparsers.add_parser("status", help="Show instruction sync status")
    skills_status.add_argument("--project", default=None, help="Optional project id filter")

    skills_refresh = skills_subparsers.add_parser("refresh", help="Refresh instruction files from registry sources")
    skills_refresh.add_argument("--project", default=None, help="Optional project id filter")
    skills_refresh.add_argument("--apply", action="store_true", help="Apply updates instead of dry-run")

    return parser


def run_cli(argv: Sequence[str] | None = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    db_path = Path(args.db).expanduser().resolve()
    logs_dir = Path(args.logs_dir).expanduser().resolve()
    config_root = Path(args.config_root).expanduser().resolve()
    vault_root = _resolve_vault_root(args.vault_root)
    command = _command_name(args)

    try:
        if args.command in {"status", "health", "metadata", "recent-failures"}:
            conn = _connect_db(db_path)
        else:
            conn = None

        if args.command == "status":
            assert conn is not None
            data = _status_payload(conn)
        elif args.command == "health":
            assert conn is not None
            data = _health_payload(conn, logs_dir)
        elif args.command == "metadata":
            assert conn is not None
            data = _metadata_payload(
                conn,
                db_path=db_path,
                logs_dir=logs_dir,
                config_root=config_root,
                vault_root=vault_root,
                project_id=args.project,
            )
        elif args.command == "logs":
            data = _logs_payload(logs_dir, sources=args.source, last=max(1, args.last))
        elif args.command == "recent-failures":
            assert conn is not None
            data = _recent_failures_payload(conn, logs_dir, last=max(1, args.last))
        elif args.command == "skills" and args.skills_command == "status":
            data = _instruction_status(config_root, vault_root, project_id=args.project)
        elif args.command == "skills" and args.skills_command == "refresh":
            data = _refresh_instructions(
                config_root=config_root,
                vault_root=vault_root,
                project_id=args.project,
                apply=bool(args.apply),
            )
        else:
            raise CLIError("unknown-command", f"Unsupported command: {args.command}", EXIT_USAGE)

        if conn is not None:
            conn.close()

        if args.json:
            print(json.dumps(_json_envelope(command, data), indent=2, sort_keys=True))
        else:
            _render_human(command, data)
        return EXIT_OK
    except CLIError as err:
        if conn is not None:
            conn.close()
        if args.json:
            print(json.dumps(_error_envelope(command, err), indent=2, sort_keys=True))
        else:
            print(f"{err.code}: {err.message}", file=sys.stderr)
        return err.exit_code


def main() -> None:
    raise SystemExit(run_cli())


if __name__ == "__main__":
    main()
