from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, TypedDict

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "quality-pipeline.json"

GateStatus = Literal["pass", "fail", "running", "stale", "missing", "blocked", "unknown"]
OverallStatus = Literal["healthy", "warning", "error", "blocked", "unknown"]


class PipelineGateSummary(TypedDict):
    key: str
    label: str
    required: bool
    configured: bool
    status: GateStatus
    command: str | None
    working_directory: str | None
    latest_run_id: str | None
    source: str | None
    evidence: list[str]
    completed_at: str | None
    blocked_reason: str | None


class PipelineSummary(TypedDict):
    project_id: str
    standard_version: str
    full_pipeline: bool
    overall_status: OverallStatus
    blocked_reason: str | None
    coverage: dict[str, int]
    gates: list[PipelineGateSummary]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object JSON at {path}")
    return payload


def _json_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed if isinstance(item, str)]


def ensure_quality_pipeline_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS quality_pipeline_runs (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id),
            gate_key TEXT NOT NULL,
            command TEXT,
            status TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'manual',
            evidence_json TEXT NOT NULL DEFAULT '[]',
            started_at TEXT,
            completed_at TEXT,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_quality_pipeline_runs_project_gate
          ON quality_pipeline_runs(project_id, gate_key, completed_at DESC, created_at DESC)
        """
    )


def _latest_runs(conn: sqlite3.Connection, project_id: str) -> dict[str, dict[str, Any]]:
    ensure_quality_pipeline_schema(conn)
    rows = conn.execute(
        """
        SELECT id, gate_key, command, status, source, evidence_json, completed_at
        FROM quality_pipeline_runs
        WHERE project_id = ?
        ORDER BY COALESCE(completed_at, created_at) DESC
        """,
        (project_id,),
    ).fetchall()
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        gate_key = str(row[1])
        if gate_key in latest:
            continue
        latest[gate_key] = {
            "id": str(row[0]),
            "command": row[2],
            "status": str(row[3]),
            "source": str(row[4]),
            "evidence": _json_list(row[5]),
            "completed_at": row[6],
        }
    return latest


def _project_match_keys(conn: sqlite3.Connection, project_id: str) -> set[str]:
    keys = {project_id, project_id.lower()}
    row = conn.execute(
        "SELECT name, repo_path FROM projects WHERE id = ? LIMIT 1",
        (project_id,),
    ).fetchone()
    if row is None:
        return keys
    name = str(row[0]).strip()
    repo_path = str(row[1]).strip()
    if name:
        keys.add(name)
        keys.add(name.lower())
    if repo_path:
        basename = Path(repo_path).name.strip()
        if basename:
            keys.add(basename)
            keys.add(basename.lower())
    return keys


def _overall_status(gates: list[PipelineGateSummary], blocked_reason: str | None) -> OverallStatus:
    if blocked_reason:
        return "blocked"
    required = [gate for gate in gates if gate["required"]]
    if any(gate["status"] in {"fail", "missing", "blocked"} for gate in required):
        return "error"
    if any(gate["status"] in {"running", "stale", "unknown"} for gate in required):
        return "warning"
    if required and all(gate["status"] == "pass" for gate in required):
        return "healthy"
    return "unknown"


def get_project_quality_pipeline(
    conn: sqlite3.Connection,
    project_id: str,
    *,
    config_path: Path = DEFAULT_CONFIG_PATH,
) -> PipelineSummary:
    ensure_quality_pipeline_schema(conn)
    payload = _load_config(config_path)
    standard = payload.get("standard") if isinstance(payload.get("standard"), dict) else {}
    standard_gates = standard.get("gates") if isinstance(standard.get("gates"), list) else []
    projects = payload.get("projects") if isinstance(payload.get("projects"), list) else []
    match_keys = _project_match_keys(conn, project_id)
    project_config = next(
        (
            project
            for project in projects
            if isinstance(project, dict)
            and str(project.get("project_id", "")).strip() in match_keys
        ),
        {},
    )
    project_gates = project_config.get("gates") if isinstance(project_config.get("gates"), dict) else {}
    latest = _latest_runs(conn, project_id)
    blocked_reason = project_config.get("blocked_reason") if isinstance(project_config.get("blocked_reason"), str) else None

    gates: list[PipelineGateSummary] = []
    for gate in standard_gates:
        if not isinstance(gate, dict):
            continue
        gate_key = str(gate.get("key", "")).strip()
        if not gate_key:
            continue
        gate_config = project_gates.get(gate_key) if isinstance(project_gates.get(gate_key), dict) else None
        latest_run = latest.get(gate_key)
        configured = gate_config is not None
        status = "missing" if bool(gate.get("required", False)) and not configured else "stale"
        if blocked_reason and not configured:
            status = "blocked"
        if latest_run:
            raw_status = str(latest_run["status"])
            status = raw_status if raw_status in {"pass", "fail", "running", "stale", "blocked", "unknown"} else "unknown"
        gates.append(
            {
                "key": gate_key,
                "label": str(gate.get("label", gate_key)),
                "required": bool(gate.get("required", False)),
                "configured": configured,
                "status": status,  # type: ignore[typeddict-item]
                "command": str(gate_config.get("command")) if gate_config and gate_config.get("command") else latest_run.get("command") if latest_run else None,
                "working_directory": str(gate_config.get("working_directory")) if gate_config and gate_config.get("working_directory") else None,
                "latest_run_id": latest_run["id"] if latest_run else None,
                "source": latest_run["source"] if latest_run else "configured" if configured else None,
                "evidence": latest_run["evidence"] if latest_run else [],
                "completed_at": latest_run["completed_at"] if latest_run else None,
                "blocked_reason": blocked_reason if status == "blocked" else None,
            }
        )

    required = [gate for gate in gates if gate["required"]]
    configured_required = [gate for gate in required if gate["configured"]]
    passing_required = [gate for gate in required if gate["status"] == "pass"]

    return {
        "project_id": project_id,
        "standard_version": str(standard.get("version", "unknown")),
        "full_pipeline": bool(project_config.get("full_pipeline", False)),
        "overall_status": _overall_status(gates, blocked_reason),
        "blocked_reason": blocked_reason,
        "coverage": {
            "required": len(required),
            "configured_required": len(configured_required),
            "passing_required": len(passing_required),
            "total": len(gates),
        },
        "gates": gates,
    }


def record_quality_pipeline_run(
    conn: sqlite3.Connection,
    *,
    project_id: str,
    gate_key: str,
    command: str,
    status: GateStatus,
    source: str = "manual",
    evidence: list[str] | None = None,
    started_at: str | None = None,
    completed_at: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> str:
    ensure_quality_pipeline_schema(conn)
    run_id = f"quality-{project_id}-{gate_key}-{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}"
    conn.execute(
        """
        INSERT INTO quality_pipeline_runs (
          id, project_id, gate_key, command, status, source, evidence_json, started_at, completed_at, metadata_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            project_id,
            gate_key,
            command,
            status,
            source,
            json.dumps(evidence or [], sort_keys=True),
            started_at or _now_iso(),
            completed_at,
            json.dumps(metadata or {}, sort_keys=True),
        ),
    )
    return run_id
