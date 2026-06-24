#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, TypedDict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.aios_cli import DEFAULT_DB_PATH  # noqa: E402
from services.linked_repo_readiness import (  # noqa: E402
    DEFAULT_EXCLUDED_PROJECT_IDS,
    phase24_readiness_report,
)
from services.quality_pipeline import (  # noqa: E402
    DEFAULT_CONFIG_PATH,
    GateStatus,
    record_quality_pipeline_run,
)

RunnerMode = Literal["dry_run", "record_only", "execute"]


class ResolvedGate(TypedDict):
    project_id: str
    gate_key: str
    repo_class: str | None
    command: str
    working_directory: str
    source: str


def _load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object JSON at {path}")
    return payload


def _project_repo_path(db_path: Path, project_id: str) -> Path | None:
    if not db_path.exists():
        return None
    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute(
            "SELECT repo_path FROM projects WHERE id = ? OR name = ? LIMIT 1",
            (project_id, project_id),
        ).fetchone()
    if row is None or not row[0]:
        return None
    return Path(str(row[0])).expanduser()


def _resolve_working_directory(db_path: Path, project_id: str, configured: str) -> str:
    configured_path = Path(configured).expanduser()
    if configured_path.is_absolute():
        return str(configured_path)
    repo_path = _project_repo_path(db_path, project_id)
    if repo_path is None:
        return str(configured_path)
    return str(repo_path / configured_path)


def _resolve_gate(config_path: Path, db_path: Path, project_id: str, gate_key: str) -> ResolvedGate:
    if project_id in DEFAULT_EXCLUDED_PROJECT_IDS:
        raise ValueError(f"{project_id} is excluded from Phase 24 readiness execution")
    projects = _load_config(config_path).get("projects")
    if not isinstance(projects, list):
        raise ValueError("quality-pipeline config has no projects list")
    project = next(
        (
            item
            for item in projects
            if isinstance(item, dict) and str(item.get("project_id", "")).strip() == project_id
        ),
        None,
    )
    if project is None:
        raise ValueError(f"Unknown project: {project_id}")
    gates = project.get("gates")
    gate = gates.get(gate_key) if isinstance(gates, dict) else None
    if not isinstance(gate, dict):
        raise ValueError(f"Unknown gate for {project_id}: {gate_key}")
    command = gate.get("command")
    if not isinstance(command, str) or not command.strip():
        raise ValueError(f"Gate {gate_key} for {project_id} has no AIOS-owned command")
    working_directory = gate.get("working_directory")
    configured_working_directory = str(working_directory).strip() if working_directory else "."
    return {
        "project_id": project_id,
        "gate_key": gate_key,
        "repo_class": str(project.get("repo_class")) if project.get("repo_class") else None,
        "command": command.strip(),
        "working_directory": _resolve_working_directory(
            db_path,
            project_id,
            configured_working_directory,
        ),
        "source": "config/quality-pipeline.json",
    }


def _connect(db_path: Path) -> sqlite3.Connection:
    return sqlite3.connect(str(db_path))


def _record_result(
    conn: sqlite3.Connection,
    gate: ResolvedGate,
    *,
    status: GateStatus,
    evidence: list[str],
    started_at: str,
    completed_at: str,
) -> str:
    run_id = record_quality_pipeline_run(
        conn,
        project_id=gate["project_id"],
        gate_key=gate["gate_key"],
        command=gate["command"],
        status=status,
        source="phase24-local",
        evidence=evidence,
        started_at=started_at,
        completed_at=completed_at,
        metadata={
            "phase": 24,
            "repo_class": gate["repo_class"],
            "working_directory": gate["working_directory"],
        },
    )
    conn.commit()
    return run_id


def _run_gate(gate: ResolvedGate) -> tuple[GateStatus, list[str]]:
    started = datetime.now(UTC).isoformat()
    result = subprocess.run(
        gate["command"],
        cwd=Path(gate["working_directory"]).expanduser(),
        shell=True,
        text=True,
        capture_output=True,
        check=False,
    )
    status: GateStatus = "pass" if result.returncode == 0 else "fail"
    evidence = [
        f"started_at={started}",
        f"returncode={result.returncode}",
    ]
    if result.stdout.strip():
        evidence.append(f"stdout={result.stdout.strip()[-4000:]}")
    if result.stderr.strip():
        evidence.append(f"stderr={result.stderr.strip()[-4000:]}")
    return status, evidence


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run or report AIOS-owned Phase 24 linked-repo gates.")
    parser.add_argument("--project")
    parser.add_argument("--gate")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--record-only", action="store_true")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--status", choices=["pass", "fail", "running", "stale", "missing", "blocked", "unknown"], default="pass")
    parser.add_argument("--evidence", action="append", default=[])
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        if args.report:
            with _connect(args.db) as conn:
                _print_json(phase24_readiness_report(conn, config_path=args.config))
            return 0
        if not args.project or not args.gate:
            raise ValueError("--project and --gate are required unless --report is used")
        gate = _resolve_gate(args.config, args.db, args.project, args.gate)
        if args.dry_run:
            _print_json({**gate, "mode": "dry_run"})
            return 0
        started_at = datetime.now(UTC).isoformat()
        if args.record_only:
            status: GateStatus = args.status
            evidence = list(args.evidence)
        else:
            status, evidence = _run_gate(gate)
        completed_at = datetime.now(UTC).isoformat()
        with _connect(args.db) as conn:
            run_id = _record_result(
                conn,
                gate,
                status=status,
                evidence=evidence,
                started_at=started_at,
                completed_at=completed_at,
            )
        _print_json({**gate, "mode": "record_only" if args.record_only else "execute", "status": status, "run_id": run_id})
        return 0
    except (OSError, sqlite3.Error, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
