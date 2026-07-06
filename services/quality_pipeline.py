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
GateTier = Literal["tier_1_core", "production_app", "domain_specific"]


class PipelineGateSummary(TypedDict):
    key: str
    label: str
    tier: GateTier
    applicable: bool
    applicability: list[str]
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
    repo_class: str | None
    strict_readiness_status: str | None
    maturation_blockers: list[str]
    non_remote_ci_exception: dict[str, Any] | None
    full_pipeline: bool
    overall_status: OverallStatus
    blocked_reason: str | None
    coverage: dict[str, int]
    coverage_by_tier: dict[str, dict[str, int]]
    gates: list[PipelineGateSummary]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object JSON at {path}")
    return payload


def _load_project_row(conn: sqlite3.Connection, project_id: str) -> tuple[str, str] | None:
    row = conn.execute(
        "SELECT name, repo_path FROM projects WHERE id = ? LIMIT 1",
        (project_id,),
    ).fetchone()
    if row is None:
        return None
    return str(row[0]).strip(), str(row[1]).strip()


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
    row = _load_project_row(conn, project_id)
    if row is None:
        return keys
    name, repo_path = row
    if name:
        keys.add(name)
        keys.add(name.lower())
    if repo_path:
        basename = Path(repo_path).name.strip()
        if basename:
            keys.add(basename)
            keys.add(basename.lower())
    return keys


def _load_package_scripts(repo_path: Path) -> dict[str, Any]:
    package_path = repo_path / "package.json"
    if not package_path.exists():
        return {}
    try:
        payload = json.loads(package_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    scripts = payload.get("scripts")
    return scripts if isinstance(scripts, dict) else {}


def _detect_install_command(repo_path: Path) -> str | None:
    if (repo_path / "pnpm-lock.yaml").exists():
        return "pnpm install --frozen-lockfile"
    if (repo_path / "package-lock.json").exists() or (repo_path / "package.json").exists():
        return "npm ci"
    if (repo_path / "uv.lock").exists() or (repo_path / "pyproject.toml").exists():
        return "uv sync"
    if (repo_path / "requirements.txt").exists():
        return "python -m pip install -r requirements.txt"
    return None


def _script_command(scripts: dict[str, Any], key: str) -> str | None:
    value = scripts.get(key)
    if isinstance(value, str):
        if key == "test":
            return "npm test"
        return f"npm run {key}"
    return None


def _infer_project_config(conn: sqlite3.Connection, project_id: str) -> dict[str, Any]:
    row = _load_project_row(conn, project_id)
    if row is None:
        return {
            "project_id": project_id,
            "applies_to": ["all"],
            "full_pipeline": False,
            "gates": {},
        }
    name, repo_path_raw = row
    repo_path = Path(repo_path_raw).expanduser()
    scripts = _load_package_scripts(repo_path)
    applies_to: list[str] = []
    if (repo_path / "package.json").exists():
        applies_to.append("typescript_app")
    if (repo_path / "pyproject.toml").exists() or (repo_path / "requirements.txt").exists():
        applies_to.append("python_service")
    if not applies_to:
        applies_to.append("all")

    gates: dict[str, dict[str, str]] = {}
    install = _detect_install_command(repo_path)
    if install:
        gates["install"] = {"command": install, "working_directory": "."}
    for key in ("lint", "typecheck", "build"):
        command = _script_command(scripts, key)
        if command:
            gates[key] = {"command": command, "working_directory": "."}
    if isinstance(scripts.get("test"), str):
        gates["test"] = {"command": "npm test", "working_directory": "."}
    if (repo_path / "scripts" / "aios-architecture-check.mjs").exists():
        gates["architecture"] = {
            "command": "node scripts/aios-architecture-check.mjs",
            "working_directory": ".",
        }
    workflow_dir = repo_path / ".github" / "workflows"
    if workflow_dir.exists() and any(
        path.suffix in {".yml", ".yaml"} for path in workflow_dir.iterdir()
    ):
        gates["ci"] = {"command": ".github/workflows", "working_directory": "."}
    return {
        "project_id": name or project_id,
        "applies_to": applies_to,
        "full_pipeline": False,
        "gates": gates,
    }


def _string_list(value: Any, fallback: list[str]) -> list[str]:
    if not isinstance(value, list):
        return fallback
    items = [str(item).strip() for item in value if isinstance(item, str) and str(item).strip()]
    return items or fallback


def _optional_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _optional_object(value: Any) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


def _required_gates_for_class(standard: dict[str, Any], repo_class: str | None) -> set[str] | None:
    if repo_class is None:
        return None
    classes = standard.get("classes")
    if not isinstance(classes, dict):
        return None
    class_config = classes.get(repo_class)
    if not isinstance(class_config, dict):
        return None
    required_gates = class_config.get("required_gates")
    if not isinstance(required_gates, list):
        return None
    return {str(gate).strip() for gate in required_gates if isinstance(gate, str) and gate.strip()}


def _gate_tier(value: Any) -> GateTier:
    if value in {"tier_1_core", "production_app", "domain_specific"}:
        return value
    return "tier_1_core"


def _is_applicable(gate_applicability: list[str], project_applicability: list[str]) -> bool:
    if "all" in gate_applicability:
        return True
    project_keys = set(project_applicability)
    return any(item in project_keys for item in gate_applicability)


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
    standard_raw = payload.get("standard")
    standard = standard_raw if isinstance(standard_raw, dict) else {}
    standard_gates_raw = standard.get("gates")
    standard_gates = standard_gates_raw if isinstance(standard_gates_raw, list) else []
    projects_raw = payload.get("projects")
    projects = projects_raw if isinstance(projects_raw, list) else []
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
    if not project_config:
        project_config = _infer_project_config(conn, project_id)
    project_gates_raw = project_config.get("gates")
    project_gates = project_gates_raw if isinstance(project_gates_raw, dict) else {}
    project_applicability = _string_list(project_config.get("applies_to"), ["all"])
    repo_class = _optional_string(project_config.get("repo_class"))
    class_required_gates = _required_gates_for_class(standard, repo_class)
    latest = _latest_runs(conn, project_id)
    blocked_reason = (
        project_config.get("blocked_reason")
        if isinstance(project_config.get("blocked_reason"), str)
        else None
    )

    gates: list[PipelineGateSummary] = []
    for gate in standard_gates:
        if not isinstance(gate, dict):
            continue
        gate_key = str(gate.get("key", "")).strip()
        if not gate_key:
            continue
        applicability = _string_list(gate.get("applicability"), ["all"])
        applicable = _is_applicable(applicability, project_applicability)
        if not applicable:
            continue
        required = (
            gate_key in class_required_gates
            if class_required_gates is not None
            else bool(gate.get("required", False))
        )
        gate_config_raw = project_gates.get(gate_key)
        gate_config = gate_config_raw if isinstance(gate_config_raw, dict) else None
        latest_run = latest.get(gate_key)
        configured = gate_config is not None
        status = "missing" if required and not configured else "stale"
        if blocked_reason and not configured:
            status = "blocked"
        if latest_run:
            raw_status = str(latest_run["status"])
            status = (
                raw_status
                if raw_status in {"pass", "fail", "running", "stale", "blocked", "unknown"}
                else "unknown"
            )
        gates.append(
            {
                "key": gate_key,
                "label": str(gate.get("label", gate_key)),
                "tier": _gate_tier(gate.get("tier")),
                "applicable": applicable,
                "applicability": applicability,
                "required": required,
                "configured": configured,
                "status": status,  # type: ignore[typeddict-item]
                "command": str(gate_config.get("command"))
                if gate_config and gate_config.get("command")
                else latest_run.get("command")
                if latest_run
                else None,
                "working_directory": str(gate_config.get("working_directory"))
                if gate_config and gate_config.get("working_directory")
                else None,
                "latest_run_id": latest_run["id"] if latest_run else None,
                "source": latest_run["source"]
                if latest_run
                else "configured"
                if configured
                else None,
                "evidence": latest_run["evidence"] if latest_run else [],
                "completed_at": latest_run["completed_at"] if latest_run else None,
                "blocked_reason": blocked_reason if status == "blocked" else None,
            }
        )

    required = [gate for gate in gates if gate["required"]]
    configured_required = [gate for gate in required if gate["configured"]]
    passing_required = [gate for gate in required if gate["status"] == "pass"]
    coverage_by_tier: dict[str, dict[str, int]] = {}
    for tier in ("tier_1_core", "production_app", "domain_specific"):
        tier_gates = [gate for gate in gates if gate["tier"] == tier]
        tier_required = [gate for gate in tier_gates if gate["required"]]
        coverage_by_tier[tier] = {
            "required": len(tier_required),
            "configured_required": len([gate for gate in tier_required if gate["configured"]]),
            "passing_required": len([gate for gate in tier_required if gate["status"] == "pass"]),
            "total": len(tier_gates),
        }

    return {
        "project_id": project_id,
        "standard_version": str(standard.get("version", "unknown")),
        "repo_class": repo_class,
        "strict_readiness_status": _optional_string(project_config.get("strict_readiness_status")),
        "maturation_blockers": _string_list(project_config.get("maturation_blockers"), []),
        "non_remote_ci_exception": _optional_object(project_config.get("non_remote_ci_exception")),
        "full_pipeline": bool(project_config.get("full_pipeline", False)),
        "overall_status": _overall_status(gates, blocked_reason),
        "blocked_reason": blocked_reason,
        "coverage": {
            "required": len(required),
            "configured_required": len(configured_required),
            "passing_required": len(passing_required),
            "total": len(gates),
        },
        "coverage_by_tier": coverage_by_tier,
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
