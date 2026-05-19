from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import subprocess
import sys
import uuid
from collections import deque
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from services.automation_history import sync_pipeline_automation_history
from services.capability_truth import capability_truth_payload
from services.harness import (
    active_readiness,
    brief_task,
    replay_session,
    shadow_evaluate_session,
    simulate_fixture,
)
from services.harness_eval import (
    DEFAULT_CONFIG_PATH as DEFAULT_HARNESS_EVAL_CONFIG_PATH,
)
from services.harness_eval import (
    score_suite,
    suite_result_to_dict,
)
from services.invocation_backends import (
    INVOCATION_CONTRACT_FIELDS,
    get_invocation_backend,
    list_invocation_backends,
)
from services.path_resolution import get_vault_root
from services.pre_pr_readiness import (
    DEFAULT_PRE_CR_REPO,
    pre_pr_readiness_payload,
)
from services.pre_pr_readiness import (
    DEFAULT_TIMEOUT_SECONDS as DEFAULT_PRE_PR_TIMEOUT_SECONDS,
)
from services.project_health_proof import DEFAULT_PROVING_PROJECTS, prove_project_health
from services.rtk_integration import (
    classify_rtk_metrics,
    ensure_rtk_schema,
    load_compression_rules,
    rtk_metrics_log,
)
from services.success_criteria import preview_applicable_criteria
from services.task_routing import route_objective
from services.workflow_orchestration import load_workflow_registry

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

DEFAULT_START_WORKFLOW_KEY = "implementation-delivery"
DEFAULT_START_AGENT_KEY = "implementation-lead"
DEFAULT_START_BACKEND_KEY = "codex-managed-runtime"
CANONICAL_RUN_STATUSES = [
    "planned",
    "ready",
    "in_progress",
    "blocked",
    "waiting_for_user",
    "waiting_for_tool",
    "failed_validation",
    "partial",
    "needs_follow_up",
    "completed",
    "failed",
    "canceled",
    "superseded",
]
ATTENTION_RUN_STATUSES = [
    "blocked",
    "waiting_for_user",
    "waiting_for_tool",
    "failed_validation",
    "partial",
    "needs_follow_up",
]
TERMINAL_RUN_STATUSES = ["partial", "needs_follow_up", "completed", "failed", "canceled", "superseded"]
RESUMABLE_RUN_STATUSES = [
    "ready",
    "in_progress",
    "blocked",
    "waiting_for_user",
    "waiting_for_tool",
    "failed_validation",
    "partial",
    "needs_follow_up",
]
TRUTH_REQUIRED_FACETS = [
    "goals",
    "architecture",
    "risks",
    "completed_work",
    "unresolved_deltas",
    "next_actions",
    "decisions",
]
KNOWLEDGE_OBJECT_CONTRACT_FIELDS = [
    "stable_id",
    "kind",
    "title",
    "summary",
    "source_refs",
    "backlinks",
    "freshness",
    "confidence",
    "retrieval_trace_count",
]
VALID_KNOWLEDGE_KINDS = [
    "agent",
    "agent_behavior_note",
    "concept",
    "decision",
    "external_reference",
    "hypothesis",
    "personal_corpus_reference",
    "policy",
    "project",
    "project_memory",
    "rule",
    "task_type",
    "workflow",
]
EVALUATION_FINDING_LIFECYCLE_STATES = ["open", "accepted", "resolved", "waived", "stale"]
WORKFLOW_LEARNING_EVIDENCE_TYPES = [
    "workflow_evidence",
    "prompt_template_evidence",
    "standards_health_evidence",
    "bug_quality_evidence",
    "no_learning_signal",
]
GOVERNED_HANDOFF_CONTRACT_VERSION = "governed-handoff-v1"


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


def _relation_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table', 'view') AND name=? LIMIT 1",
        (name,),
    ).fetchone()
    return row is not None


def _table_columns(conn: sqlite3.Connection, name: str) -> set[str]:
    if not _table_exists(conn, name):
        return set()
    return {str(row["name"]) for row in conn.execute(f"PRAGMA table_info({name})").fetchall()}


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    if column not in _table_columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


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


def _extract_markdown_headings(content: str) -> list[str]:
    headings: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        title = stripped.lstrip("#").strip()
        if title:
            headings.append(title)
    return headings


def _truth_last_updated(content: str) -> str | None:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("last updated:"):
            return stripped.split(":", 1)[1].strip()
    return None


def _truth_facet_coverage(headings: Sequence[str]) -> dict[str, bool]:
    heading_text = " ".join(headings).lower()
    aliases = {
        "goals": ("goal", "target", "what aios is", "project"),
        "architecture": ("architecture", "system", "runtime", "stack"),
        "risks": ("risk", "gap", "missing", "blocker"),
        "completed_work": ("implemented", "current reality", "shipped", "completed"),
        "unresolved_deltas": ("unresolved", "delta", "still missing", "gap"),
        "next_actions": ("next", "follow-up", "roadmap", "phase"),
        "decisions": ("decision", "guardrail", "constraint"),
    }
    return {
        facet: any(alias in heading_text for alias in facet_aliases)
        for facet, facet_aliases in aliases.items()
    }


def _resolve_vault_root(explicit: str | None = None) -> Path:
    return get_vault_root(explicit)


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


def _parse_json_object(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _resumable_runs(conn: sqlite3.Connection, limit: int = 5) -> list[dict[str, Any]]:
    if not _table_exists(conn, "orchestration_runs"):
        return []
    columns = _table_columns(conn, "orchestration_runs")
    if "resume_snapshot_json" not in columns:
        return []

    placeholders = ", ".join("?" for _ in RESUMABLE_RUN_STATUSES)
    rows = conn.execute(
        f"""
        SELECT id, project_id, objective, workflow_key, status, packet_id, session_id, resume_snapshot_json, updated_at
        FROM orchestration_runs
        WHERE status IN ({placeholders})
        ORDER BY updated_at DESC, created_at DESC
        LIMIT ?
        """,
        (*RESUMABLE_RUN_STATUSES, limit),
    ).fetchall()

    resumable: list[dict[str, Any]] = []
    for row in rows:
        snapshot = _parse_json_object(row["resume_snapshot_json"])
        resumable.append(
            {
                "run_id": row["id"],
                "project_id": row["project_id"],
                "objective": row["objective"],
                "workflow_key": row["workflow_key"],
                "status": row["status"],
                "packet_id": row["packet_id"],
                "session_id": row["session_id"],
                "current_stage": snapshot.get("current_stage"),
                "next_recommended_action": snapshot.get("next_recommended_action"),
                "pending_approval_count": int(snapshot.get("pending_approval_count") or 0),
                "approval_targets": snapshot.get("approval_targets") or [],
                "updated_at": snapshot.get("updated_at") or row["updated_at"],
            }
        )
    return resumable


def _recent_closeouts(conn: sqlite3.Connection, limit: int = 5) -> list[dict[str, Any]]:
    if not _table_exists(conn, "workflow_execution_reports"):
        return []
    columns = _table_columns(conn, "workflow_execution_reports")
    if "report_json" not in columns:
        return []

    rows = conn.execute(
        """
        SELECT run_id, invocation_id, workflow_key, status, report_json, artifact_path, created_at
        FROM workflow_execution_reports
        ORDER BY created_at DESC
        LIMIT 50
        """
    ).fetchall()

    closeouts: list[dict[str, Any]] = []
    for row in rows:
        report = _parse_json_object(row["report_json"])
        if report.get("report_type") != "governed_closeout":
            continue
        approvals = report.get("approvals") or {}
        unresolved = report.get("unresolved_deltas") or {}
        closeouts.append(
            {
                "run_id": row["run_id"],
                "invocation_id": row["invocation_id"],
                "workflow_key": row["workflow_key"],
                "status": row["status"],
                "artifact_path": row["artifact_path"],
                "created_at": row["created_at"],
                "outcome": report.get("outcome"),
                "result_summary": report.get("result_summary"),
                "pending_approval_count": int(approvals.get("pending_approval_count") or 0),
                "changed_artifact_count": len(report.get("changed_artifacts") or []),
                "open_question_count": len(unresolved.get("open_questions") or []),
                "risk_count": len(unresolved.get("risks") or []),
                "checks_run": report.get("checks_run") or {},
            }
        )
        if len(closeouts) >= limit:
            break
    return closeouts


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


def _handshake_coverage(conn: sqlite3.Connection) -> dict[str, Any]:
    if not _table_exists(conn, "sessions"):
        return {
            "total_sessions": 0,
            "explicitly_linked_sessions": 0,
            "coverage": 0.0,
            "legacy_fallback_policy": "disabled_by_default",
            "emergency_flag": "AIOS_ALLOW_LEGACY_RUN_LINK",
        }
    columns = _table_columns(conn, "sessions")
    if not {"run_id", "invocation_id"}.issubset(columns):
        total = _count(conn, "sessions")
        return {
            "total_sessions": total,
            "explicitly_linked_sessions": 0,
            "coverage": 0.0,
            "target_coverage": 0.9,
            "legacy_fallback_policy": "disabled_by_default",
            "emergency_flag": "AIOS_ALLOW_LEGACY_RUN_LINK",
            "ready_to_remove_fallback": False,
        }
    row = conn.execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN run_id IS NOT NULL AND invocation_id IS NOT NULL THEN 1 ELSE 0 END) AS explicit_count
        FROM sessions
        """
    ).fetchone()
    total = int(row["total"] or 0) if row else 0
    explicit_count = int(row["explicit_count"] or 0) if row else 0
    coverage = round(explicit_count / total, 4) if total else 0.0
    return {
        "total_sessions": total,
        "explicitly_linked_sessions": explicit_count,
        "coverage": coverage,
        "target_coverage": 0.9,
        "legacy_fallback_policy": "disabled_by_default",
        "emergency_flag": "AIOS_ALLOW_LEGACY_RUN_LINK",
        "ready_to_remove_fallback": coverage >= 0.9,
    }


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


def _standards_registry_summary(config_root: Path) -> dict[str, Any]:
    registry_path = config_root / "standards" / "registry.json"
    if not registry_path.exists():
        return {
            "profile_id": None,
            "profile_version": None,
            "standard_count": 0,
            "domains": [],
            "registry_path": str(registry_path),
        }

    loaded = _load_json(registry_path)
    profile = loaded.get("profile", {})
    standards = loaded.get("standards", [])
    if not isinstance(profile, dict):
        profile = {}
    if not isinstance(standards, list):
        standards = []
    domains = sorted(
        {
            str(item.get("domain", ""))
            for item in standards
            if isinstance(item, dict) and item.get("domain")
        }
    )
    return {
        "profile_id": profile.get("id"),
        "profile_version": profile.get("version"),
        "default_attached_version": profile.get("default_attached_version"),
        "standard_count": len([item for item in standards if isinstance(item, dict) and item.get("id")]),
        "domains": domains,
        "registry_path": str(registry_path),
    }


def _latest_standards_snapshot(conn: sqlite3.Connection) -> dict[str, Any] | None:
    if not _table_exists(conn, "standards_health_snapshots"):
        return None
    row = conn.execute(
        """
        SELECT
            id,
            project_id,
            profile_id,
            attached_version,
            latest_version,
            overall_score,
            critical_delta_count,
            regression_count,
            unknown_count,
            evaluation_confidence,
            created_at
        FROM standards_health_snapshots
        ORDER BY created_at DESC
        LIMIT 1
        """
    ).fetchone()
    if row is None:
        return None
    return {
        "id": row["id"],
        "project_id": row["project_id"],
        "profile_id": row["profile_id"],
        "attached_version": row["attached_version"],
        "latest_version": row["latest_version"],
        "overall_score": row["overall_score"],
        "critical_delta_count": row["critical_delta_count"],
        "regression_count": row["regression_count"],
        "unknown_count": row["unknown_count"],
        "evaluation_confidence": row["evaluation_confidence"],
        "created_at": row["created_at"],
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


def _ensure_start_work_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS orchestration_runs (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            session_id TEXT,
            objective TEXT,
            workflow_key TEXT,
            agent_key TEXT,
            status TEXT,
            rationale TEXT,
            assumptions_json TEXT DEFAULT '[]',
            context_trace_json TEXT DEFAULT '[]',
            backend_key TEXT,
            route_id TEXT,
            route_status TEXT,
            route_result_json TEXT DEFAULT '{}',
            active_invocation_id TEXT,
            packet_id TEXT,
            status_reason_json TEXT DEFAULT '{}',
            created_at TEXT,
            updated_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS orchestration_invocations (
            id TEXT PRIMARY KEY,
            run_id TEXT,
            backend_key TEXT,
            backend_label TEXT,
            status TEXT,
            handshake_token TEXT,
            session_id TEXT,
            command_json TEXT DEFAULT '[]',
            metadata_json TEXT DEFAULT '{}',
            created_at TEXT,
            started_at TEXT,
            updated_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS orchestration_run_events (
            id TEXT PRIMARY KEY,
            run_id TEXT,
            project_id TEXT,
            session_id TEXT,
            invocation_id TEXT,
            event_type TEXT,
            from_status TEXT,
            to_status TEXT,
            summary TEXT,
            reason_json TEXT DEFAULT '{}',
            metadata_json TEXT DEFAULT '{}',
            created_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS briefing_packets (
            id TEXT PRIMARY KEY,
            run_id TEXT,
            project_id TEXT,
            objective TEXT,
            workflow_key TEXT,
            agent_key TEXT,
            packet_markdown TEXT,
            sections_json TEXT DEFAULT '[]',
            policy_mode TEXT DEFAULT 'compact-ranked',
            token_budget INTEGER DEFAULT 900,
            route_id TEXT,
            route_result_json TEXT DEFAULT '{}',
            selection_trace_json TEXT DEFAULT '[]',
            omitted_context_json TEXT DEFAULT '[]',
            created_at TEXT
        )
        """
    )
    for column, definition in {
        "project_id": "TEXT",
        "session_id": "TEXT",
        "objective": "TEXT",
        "workflow_key": "TEXT",
        "agent_key": "TEXT",
        "rationale": "TEXT",
        "assumptions_json": "TEXT DEFAULT '[]'",
        "context_trace_json": "TEXT DEFAULT '[]'",
        "backend_key": "TEXT",
        "route_id": "TEXT",
        "route_status": "TEXT",
        "route_result_json": "TEXT DEFAULT '{}'",
        "active_invocation_id": "TEXT",
        "packet_id": "TEXT",
        "status_reason_json": "TEXT DEFAULT '{}'",
        "resume_snapshot_json": "TEXT DEFAULT '{}'",
        "created_at": "TEXT",
        "updated_at": "TEXT",
    }.items():
        _ensure_column(conn, "orchestration_runs", column, definition)
    for column, definition in {
        "backend_key": "TEXT",
        "backend_label": "TEXT",
        "status": "TEXT",
        "handshake_token": "TEXT",
        "session_id": "TEXT",
        "command_json": "TEXT DEFAULT '[]'",
        "metadata_json": "TEXT DEFAULT '{}'",
        "created_at": "TEXT",
        "started_at": "TEXT",
        "updated_at": "TEXT",
    }.items():
        _ensure_column(conn, "orchestration_invocations", column, definition)
    for column, definition in {
        "project_id": "TEXT",
        "session_id": "TEXT",
        "invocation_id": "TEXT",
        "event_type": "TEXT",
        "from_status": "TEXT",
        "metadata_json": "TEXT DEFAULT '{}'",
    }.items():
        _ensure_column(conn, "orchestration_run_events", column, definition)
    for column, definition in {
        "project_id": "TEXT",
        "objective": "TEXT",
        "workflow_key": "TEXT",
        "agent_key": "TEXT",
        "packet_markdown": "TEXT",
        "sections_json": "TEXT DEFAULT '[]'",
        "policy_mode": "TEXT DEFAULT 'compact-ranked'",
        "token_budget": "INTEGER DEFAULT 900",
        "route_id": "TEXT",
        "route_result_json": "TEXT DEFAULT '{}'",
        "selection_trace_json": "TEXT DEFAULT '[]'",
        "omitted_context_json": "TEXT DEFAULT '[]'",
        "created_at": "TEXT",
    }.items():
        _ensure_column(conn, "briefing_packets", column, definition)
    if _table_exists(conn, "sessions"):
        _ensure_column(conn, "sessions", "objective", "TEXT")
        _ensure_column(conn, "sessions", "run_id", "TEXT")
        _ensure_column(conn, "sessions", "invocation_id", "TEXT")
        _ensure_column(conn, "sessions", "runtime_metadata_json", "TEXT DEFAULT '{}'")


def _current_session_id(logs_dir: Path) -> str | None:
    current_path = logs_dir / "current_session"
    if not current_path.exists():
        return None
    session_id = current_path.read_text(encoding="utf-8", errors="replace").strip()
    return session_id or None


def _project_name(conn: sqlite3.Connection, project_id: str | None) -> str:
    if not project_id or not _table_exists(conn, "projects"):
        return "unlinked project"
    row = conn.execute("SELECT name FROM projects WHERE id = ? LIMIT 1", (project_id,)).fetchone()
    return str(row["name"]) if row and row["name"] else project_id


def _active_rule_rows(conn: sqlite3.Connection, limit: int = 5) -> list[dict[str, Any]]:
    if not _relation_exists(conn, "active_rules"):
        return []
    rows = conn.execute(
        """
        SELECT title, body, domain, confidence
        FROM active_rules
        ORDER BY confidence DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def _knowledge_topic_rows(
    conn: sqlite3.Connection,
    *,
    project_id: str | None,
    objective: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    if not _table_exists(conn, "knowledge_topics"):
        return []
    tokens = [token for token in objective.lower().split() if len(token) >= 4]
    like_terms = [f"%{token}%" for token in tokens[:5]]
    if not like_terms:
        return []
    if _table_exists(conn, "knowledge_references"):
        clauses = " OR ".join(
            [
                """
                LOWER(
                    t.title || ' ' || t.summary || ' ' ||
                    COALESCE(r.label, '') || ' ' || COALESCE(r.excerpt, '') || ' ' || COALESCE(r.source_kind, '')
                ) LIKE ?
                """
            ]
            * len(like_terms)
        )
        rows = conn.execute(
            f"""
            SELECT
                t.id,
                t.title,
                t.summary,
                t.canonical_href,
                t.confidence,
                t.updated_at,
                COUNT(r.id) AS reference_match_count
            FROM knowledge_topics t
            LEFT JOIN knowledge_references r ON r.topic_id = t.id
            WHERE (? IS NULL OR t.project_id IS NULL OR t.project_id = ?)
              AND ({clauses})
            GROUP BY t.id
            ORDER BY t.confidence DESC, t.updated_at DESC
            LIMIT ?
            """,
            (project_id, project_id, *like_terms, limit),
        ).fetchall()
        return [dict(row) for row in rows]
    clauses = " OR ".join(["LOWER(title || ' ' || summary) LIKE ?"] * len(like_terms))
    rows = conn.execute(
        f"""
        SELECT id, title, summary, canonical_href, confidence, updated_at, 0 AS reference_match_count
        FROM knowledge_topics
        WHERE (? IS NULL OR project_id IS NULL OR project_id = ?)
          AND ({clauses})
        ORDER BY confidence DESC, updated_at DESC
        LIMIT ?
        """,
        (project_id, project_id, *like_terms, limit),
    ).fetchall()
    return [dict(row) for row in rows]


def _recent_writeback_rows(conn: sqlite3.Connection, project_id: str | None, limit: int = 5) -> list[dict[str, Any]]:
    if not _table_exists(conn, "improvement_writebacks"):
        return []
    where = "WHERE (? IS NULL OR project_id = ?)"
    rows = conn.execute(
        f"""
        SELECT id, title, summary, status, requires_approval, created_at
        FROM improvement_writebacks
        {where}
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (project_id, project_id, limit),
    ).fetchall()
    return [dict(row) for row in rows]


def _workflow_contract(workflow_key: str) -> dict[str, Any] | None:
    try:
        workflow = load_workflow_registry().get(workflow_key)
    except ValueError:
        return None
    if workflow is None:
        return None
    return {
        "workflow_key": workflow.key,
        "workflow_family": workflow.workflow_family,
        "purpose": workflow.purpose,
        "output_contract": list(workflow.output_contract),
        "required_validations": list(workflow.required_validations),
        "stages": [
            {
                "key": stage.key,
                "kind": stage.kind,
                "required_skills": list(stage.required_skills),
            }
            for stage in workflow.stages
        ],
    }


def _criteria_instruction_lines(criteria_rows: Sequence[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for row in criteria_rows[:8]:
        criterion_id = str(row.get("id", "")).strip()
        if not criterion_id:
            continue
        title = str(row.get("title", criterion_id)).strip()
        severity = "blocker" if row.get("blocking") else "advisory"
        path = str(row.get("path", "")).strip()
        detail = f"{criterion_id} [{severity}]: {title}"
        if path:
            detail = f"{detail} ({path})"
        lines.append(detail)
    return lines or ["No success criteria matched this objective."]


def _workflow_stage_lines(workflow_contract: dict[str, Any] | None) -> list[str]:
    if workflow_contract is None:
        return ["Workflow stages unavailable; use the routed workflow key as the governing contract."]

    lines: list[str] = []
    for index, stage in enumerate(workflow_contract.get("stages", []), start=1):
        if not isinstance(stage, dict):
            continue
        stage_key = str(stage.get("key", "")).strip() or f"stage-{index}"
        stage_kind = str(stage.get("kind", "")).strip() or "unknown"
        required_skills = stage.get("required_skills") or []
        if isinstance(required_skills, list) and required_skills:
            skill_text = ", ".join(str(skill) for skill in required_skills)
        else:
            skill_text = "none"
        lines.append(f"{index}. {stage_key} [{stage_kind}] using skills: {skill_text}.")

    output_contract = workflow_contract.get("output_contract") or []
    if isinstance(output_contract, list) and output_contract:
        lines.append("Deliverables: " + "; ".join(str(item) for item in output_contract))
    return lines or ["Workflow stages unavailable; use the routed workflow key as the governing contract."]


def _prompt_contract_lines(route_payload: dict[str, Any], backend_key: str) -> list[str]:
    prompt = route_payload.get("prompt_recommendation")
    workflow = route_payload.get("selected_workflow")
    backend = route_payload.get("backend_recommendation")

    prompt_family = None
    template_id = None
    route_status = None
    prompt_rationale = None
    if isinstance(prompt, dict):
        prompt_family = prompt.get("prompt_family")
        template_id = prompt.get("template_id")
        route_status = prompt.get("route_status")
        prompt_rationale = prompt.get("rationale")

    workflow_key = None
    if isinstance(workflow, dict):
        workflow_key = workflow.get("workflow_key")

    backend_label = None
    if isinstance(backend, dict):
        backend_label = backend.get("selected_backend_label")

    lines = [
        f"Use packet contract version {GOVERNED_HANDOFF_CONTRACT_VERSION} before opening broad exploration.",
        (
            f"Prompt family: {prompt_family or 'unresolved'}"
            + (f" via template {template_id}" if template_id else "")
            + (f" [{route_status}]" if route_status else "")
            + "."
        ),
        f"Workflow handoff target: {workflow_key or 'unresolved'} on backend {backend_key}{f' ({backend_label})' if backend_label else ''}.",
        "Summarize intended edits, non-goals, and risks before making code changes.",
        "Ask for targeted packet expansion when the current packet lacks a required source, file surface, or policy.",
    ]
    if prompt_rationale:
        lines.append(f"Prompt rationale: {prompt_rationale}")
    return lines


def _required_check_lines(
    workflow_contract: dict[str, Any] | None,
    criteria_rows: Sequence[dict[str, Any]],
) -> list[str]:
    lines: list[str] = []
    if workflow_contract is not None:
        validations = workflow_contract.get("required_validations") or []
        if isinstance(validations, list) and validations:
            lines.append("Workflow validations: " + ", ".join(str(item) for item in validations))
    blocker_ids = [str(row.get("id")) for row in criteria_rows if row.get("blocking") and row.get("id")]
    if blocker_ids:
        lines.append("Blocker criteria to satisfy before completion: " + ", ".join(blocker_ids))
    lines.extend(
        [
            "Run the exact modified path before claiming completion when shared logic or side effects are involved.",
            "Do not mark the run complete while blocker-level criteria are failing without an accepted tradeoff record.",
            "Escalate when project resolution, workflow fit, or packet evidence becomes ambiguous during execution.",
        ]
    )
    return lines


def _closeout_lines() -> list[str]:
    return [
        "Update the relevant project truth and memory surfaces after meaningful state changes.",
        "Record unresolved risks, follow-up work, and approval-gated writeback proposals before closeout.",
        "Keep run, invocation, and session identifiers linked through verification and stop-hook evaluation.",
    ]


def _packet_sections(
    conn: sqlite3.Connection,
    *,
    objective: str,
    project_id: str | None,
    project_name: str,
    workflow_key: str,
    agent_key: str,
    route_payload: dict[str, Any],
    backend_key: str,
) -> list[dict[str, Any]]:
    workflow_contract = _workflow_contract(workflow_key)
    criteria = preview_applicable_criteria(
        project_id=project_id,
        project_name=project_name,
        objective=objective,
    )
    criteria_rows = criteria.get("criteria", [])
    sections: list[dict[str, Any]] = [
        {
            "title": "Objective Summary",
            "body": "Use this governed handoff packet before implementation or broad exploration.",
            "items": [
                objective,
                f"Project: {project_name}",
                f"Workflow: {workflow_key}",
                f"Agent profile: {agent_key}",
                f"Task family: {route_payload.get('task_family') or 'unclassified'}",
            ],
        }
    ]

    sections.append(
        {
            "title": "Workflow Stages",
            "body": (
                str(workflow_contract.get("purpose"))
                if workflow_contract is not None and workflow_contract.get("purpose")
                else "Follow the routed workflow stages in order and preserve artifacts at each gate."
            ),
            "items": _workflow_stage_lines(workflow_contract),
        }
    )

    sections.append(
        {
            "title": "Prompt And Handoff Contract",
            "body": "The routed prompt family and backend are part of the governed packet contract.",
            "items": _prompt_contract_lines(route_payload, backend_key),
        }
    )

    sections.append(
        {
            "title": "Applicable Success Criteria",
            "items": _criteria_instruction_lines(criteria_rows if isinstance(criteria_rows, list) else []),
        }
    )

    rules = _active_rule_rows(conn)
    sections.append(
        {
            "title": "Active Rules",
            "items": [
                f"{row['title']}: {row['body'] or row['title']}"
                for row in rules
                if row.get("title")
            ]
            or ["No active rules were found."],
        }
    )

    writebacks = _recent_writeback_rows(conn, project_id)
    sections.append(
        {
            "title": "Recent Improvements",
            "items": [
                f"{row['title']} [{row['status']}]: {row['summary']}"
                for row in writebacks
                if row.get("title")
            ]
            or ["No recent improvement writebacks were found."],
        }
    )

    topics = _knowledge_topic_rows(conn, project_id=project_id, objective=objective)
    sections.append(
        {
            "title": "Knowledge Matches",
            "items": [
                f"{row['title']}: {row['summary']} ({row['canonical_href']})"
                for row in topics
                if row.get("title")
            ]
            or ["No indexed knowledge topics matched this objective."],
        }
    )

    sections.append(
        {
            "title": "Required Checks And Escalations",
            "body": "Verification and escalation conditions are part of the default serious-work contract.",
            "items": _required_check_lines(
                workflow_contract,
                criteria_rows if isinstance(criteria_rows, list) else [],
            ),
        }
    )

    sections.append(
        {
            "title": "Closeout And Writeback",
            "body": "Completion requires governed writeback, not just a passing implementation diff.",
            "items": _closeout_lines(),
        }
    )
    return sections


def _packet_retrieval_trace(
    conn: sqlite3.Connection,
    *,
    objective: str,
    project_id: str | None,
    token_budget: int,
) -> dict[str, Any]:
    topic_matches = _knowledge_topic_rows(conn, project_id=project_id, objective=objective, limit=6)
    matched_objects = [
        {
            "stable_id": row.get("id"),
            "title": row.get("title"),
            "href": row.get("canonical_href"),
            "confidence": row.get("confidence"),
            "ranking_reason": "Matched objective terms across title, summary, reference label, excerpt, or source kind.",
        }
        for row in topic_matches
    ]
    omitted_context_count = max(0, len(topic_matches) - len(matched_objects))
    return {
        "query": objective,
        "matched_objects": matched_objects,
        "omitted_context_count": omitted_context_count,
        "expansion_path": ["objective", "knowledge_topics", "knowledge_references"],
        "citations": [
            {
                "label": row.get("title"),
                "href": row.get("canonical_href"),
            }
            for row in topic_matches
            if row.get("canonical_href")
        ],
        "token_budget": token_budget,
        "ranking_reason": "Compact-ranked packet assembly prefers project-local matches, confidence, and freshness.",
    }


def _packet_markdown(sections: list[dict[str, Any]]) -> str:
    rendered: list[str] = ["# AIOS Routed Work Packet"]
    for section in sections:
        rendered.append("")
        rendered.append(f"## {section['title']}")
        for item in section.get("items", []):
            rendered.append(f"- {item}")
    return "\n".join(rendered)


def _record_run_event(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    project_id: str | None,
    session_id: str | None,
    invocation_id: str | None,
    event_type: str,
    from_status: str | None,
    to_status: str,
    summary: str,
    reason: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO orchestration_run_events (
            id, run_id, project_id, session_id, invocation_id, event_type, from_status, to_status,
            summary, reason_json, metadata_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"run-event-{uuid.uuid4()}",
            run_id,
            project_id,
            session_id,
            invocation_id,
            event_type,
            from_status,
            to_status,
            summary,
            json.dumps(reason or {}),
            json.dumps(metadata or {}),
            _now_iso(),
        ),
    )


def _start_work_payload(
    conn: sqlite3.Connection,
    logs_dir: Path,
    *,
    objective: str,
    project_id: str | None,
    workflow_key: str | None,
    agent_key: str | None,
    backend_key: str | None,
    session_id: str | None,
) -> dict[str, Any]:
    _ensure_start_work_schema(conn)
    explicit_session_id = session_id is not None
    linked_session_id = session_id if explicit_session_id else _current_session_id(logs_dir)
    session_cwd: str | None = None
    if linked_session_id and _table_exists(conn, "sessions"):
        session = conn.execute(
            "SELECT id, project_id, status, cwd FROM sessions WHERE id = ? LIMIT 1",
            (linked_session_id,),
        ).fetchone()
        if session is None:
            raise CLIError("session-not-found", f"Session not found: {linked_session_id}", EXIT_NOT_FOUND)
        if session["status"] != "open":
            if explicit_session_id:
                raise CLIError(
                    "session-not-open",
                    f"Session is not open: {linked_session_id}",
                    EXIT_RUNTIME,
                )
            linked_session_id = None
        if linked_session_id is None:
            session = None
        else:
            session_cwd = str(session["cwd"]) if session["cwd"] else None
    if linked_session_id and _table_exists(conn, "sessions"):
        session = conn.execute(
            "SELECT id, project_id, cwd FROM sessions WHERE id = ? LIMIT 1",
            (linked_session_id,),
        ).fetchone()
        if session is None:
            raise CLIError("session-not-found", f"Session not found: {linked_session_id}", EXIT_NOT_FOUND)
        session_cwd = str(session["cwd"]) if session["cwd"] else session_cwd

    preferred_surface = "codex"
    if backend_key:
        preferred_surface = get_invocation_backend(backend_key).surface
    route = route_objective(
        conn,
        objective=objective,
        surface=preferred_surface,
        cwd=session_cwd,
        explicit_project_id=project_id,
    )
    route_payload = route.to_json()
    if route.status != "ready":
        raise CLIError("route-blocked", route.blocked_reason or "Routing blocked.", EXIT_USAGE)

    project_id = route.project.selected_project_id
    workflow_key = workflow_key or str(route.selected_workflow["workflow_key"])
    agent_key = agent_key or str(route.agent_recommendation["agent_key"])
    routed_backend_key = (
        str(route.backend_recommendation["selected_backend_key"])
        if route.backend_recommendation and route.backend_recommendation.get("selected_backend_key")
        else DEFAULT_START_BACKEND_KEY
    )
    backend = get_invocation_backend(backend_key or routed_backend_key)
    route_id = f"route-{uuid.uuid4()}"
    route_payload["route_id"] = route_id

    project_name = _project_name(conn, project_id)
    now = _now_iso()
    run_id = f"run-{uuid.uuid4()}"
    packet_id = f"packet-{uuid.uuid4()}"
    invocation_id = f"invoke-manual-{uuid.uuid4()}"
    sections = _packet_sections(
        conn,
        objective=objective,
        project_id=project_id,
        project_name=project_name,
        workflow_key=workflow_key,
        agent_key=agent_key,
        route_payload=route_payload,
        backend_key=backend.key,
    )
    packet_markdown = _packet_markdown(sections)
    retrieval_trace = _packet_retrieval_trace(
        conn,
        objective=objective,
        project_id=project_id,
        token_budget=900,
    )
    retrieval_trace["route"] = route_payload
    retrieval_trace["packet_contract"] = {
        "version": GOVERNED_HANDOFF_CONTRACT_VERSION,
        "workflow_key": workflow_key,
        "prompt_family": (
            route_payload.get("prompt_recommendation", {}).get("prompt_family")
            if isinstance(route_payload.get("prompt_recommendation"), dict)
            else None
        ),
        "template_id": (
            route_payload.get("prompt_recommendation", {}).get("template_id")
            if isinstance(route_payload.get("prompt_recommendation"), dict)
            else None
        ),
        "stage_count": sum(1 for section in sections if section.get("title") == "Workflow Stages"),
        "required_check_section": "Required Checks And Escalations",
    }
    status = "in_progress" if linked_session_id else "ready"
    invocation_status = "running" if linked_session_id else "prepared"

    conn.execute(
        """
        INSERT INTO orchestration_runs (
            id, project_id, session_id, objective, workflow_key, agent_key, status, rationale,
            assumptions_json, context_trace_json, backend_key, route_id, route_status,
            route_result_json, active_invocation_id, packet_id, resume_snapshot_json,
            status_reason_json, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            project_id,
            linked_session_id,
            objective,
            workflow_key,
            agent_key,
            status,
            "Started from AIOS CLI so rules, improvements, knowledge, and criteria are visible before implementation.",
            json.dumps(["Current implementation sessions should attach via explicit run/invocation/session handshake."]),
            json.dumps(
                [
                    {"source": "success-criteria", "reason": "criteria preview added to packet"},
                    {"source": "active-rules", "reason": "approved rules added to packet"},
                    {"source": "improvement-writebacks", "reason": "recent improvements added to packet"},
                ]
            ),
            backend.key,
            route_id,
            route.status,
            json.dumps(route_payload),
            invocation_id,
            packet_id,
            json.dumps(
                {
                    "packet_id": packet_id,
                    "current_stage": "packet_ready",
                    "next_recommended_action": "Start the routed runtime with this packet and keep run/invocation/session linkage intact.",
                    "pending_approval_count": 0,
                    "approval_targets": [],
                    "updated_at": now,
                }
            ),
            json.dumps(
                {
                    "kind": "strict_manual_handshake" if linked_session_id else "packet_ready",
                    "route_id": route_id,
                }
            ),
            now,
            now,
        ),
    )
    _record_run_event(
        conn,
        run_id=run_id,
        project_id=project_id,
        session_id=None,
        invocation_id=None,
        event_type="planned",
        from_status=None,
        to_status="planned",
        summary="Run record created from AIOS start-work.",
        metadata={"backendKey": backend.key},
    )
    conn.execute(
        """
        INSERT INTO briefing_packets (
            id, run_id, project_id, objective, workflow_key, agent_key, packet_markdown,
            sections_json, policy_mode, token_budget, route_id, route_result_json, selection_trace_json,
            omitted_context_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'compact-ranked', 900, ?, ?, ?, '[]', ?)
        """,
        (
            packet_id,
            run_id,
            project_id,
            objective,
            workflow_key,
            agent_key,
            packet_markdown,
            json.dumps(sections),
            route_id,
            json.dumps(route_payload),
            json.dumps(retrieval_trace),
            now,
        ),
    )
    _record_run_event(
        conn,
        run_id=run_id,
        project_id=project_id,
        session_id=None,
        invocation_id=None,
        event_type="ready",
        from_status="planned",
        to_status="ready",
        summary="Briefing packet persisted for routed work.",
        reason={"kind": "packet_ready", "policyMode": "compact-ranked"},
        metadata={"packetId": packet_id},
    )
    conn.execute(
        """
        INSERT INTO orchestration_invocations (
            id, run_id, backend_key, backend_label, status, handshake_token, session_id,
            command_json, metadata_json, created_at, started_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            invocation_id,
            run_id,
            backend.key,
            backend.label,
            invocation_status,
            run_id,
            linked_session_id,
            json.dumps(["aios", "start-work", "strict-handshake"]),
            json.dumps(
                {
                    "strictHandshake": True,
                    "source": "aios-cli",
                    "route_id": route_id,
                    "route_status": route.status,
                    "prompt_family": (
                        route.prompt_recommendation.get("prompt_family")
                        if route.prompt_recommendation
                        else None
                    ),
                }
            ),
            now,
            now if linked_session_id else None,
            now,
        ),
    )

    if linked_session_id:
        conn.execute(
            """
            UPDATE sessions
            SET run_id = ?,
                invocation_id = ?,
                runtime_metadata_json = ?,
                objective = COALESCE(objective, ?)
            WHERE id = ?
            """,
            (
                run_id,
                invocation_id,
                json.dumps(
                    {
                        "backend_key": backend.key,
                        "strict_manual_handshake": True,
                        "packet_id": packet_id,
                        "route_id": route_id,
                    }
                ),
                objective,
                linked_session_id,
            ),
        )
        _record_run_event(
            conn,
            run_id=run_id,
            project_id=project_id,
            session_id=linked_session_id,
            invocation_id=invocation_id,
            event_type="strict_manual_invocation_registered",
            from_status="ready",
            to_status="in_progress",
            summary="Current session linked to AIOS run and invocation.",
            reason={"kind": "current_session_linked", "backendKey": backend.key},
        )

    conn.commit()
    return {
        "run": {
            "id": run_id,
            "project_id": project_id,
            "session_id": linked_session_id,
            "objective": objective,
            "workflow_key": workflow_key,
            "agent_key": agent_key,
            "backend_key": backend.key,
            "route_id": route_id,
            "route_status": route.status,
            "status": status,
            "packet_id": packet_id,
            "active_invocation_id": invocation_id,
        },
        "packet": {
            "id": packet_id,
            "policy_mode": "compact-ranked",
            "markdown": packet_markdown,
            "sections": sections,
            "contract_version": GOVERNED_HANDOFF_CONTRACT_VERSION,
        },
        "invocation": {
            "id": invocation_id,
            "status": invocation_status,
            "backend_key": backend.key,
            "backend_label": backend.label,
            "session_id": linked_session_id,
        },
        "next_agent_context": {
            "run_id": run_id,
            "invocation_id": invocation_id,
            "packet_id": packet_id,
            "session_id": linked_session_id,
        },
        "route": route_payload,
    }


def _invocation_audit_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    coverage = _handshake_coverage(conn)
    backends = [backend.to_json() for backend in list_invocation_backends()]
    invocation_count = _count(conn, "orchestration_invocations")
    run_count = _count(conn, "orchestration_runs")
    return {
        "summary": {
            "backend_count": len(backends),
            "run_count": run_count,
            "invocation_count": invocation_count,
            "strict_handshake_required": True,
        },
        "contract": {
            "required_fields": INVOCATION_CONTRACT_FIELDS,
            "legacy_fallback_policy": "disabled_by_default",
            "legacy_emergency_flag": "AIOS_ALLOW_LEGACY_RUN_LINK",
        },
        "handshake_coverage": coverage,
        "backends": backends,
    }


def _lifecycle_audit_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    observed_counts = _run_status_counts(conn)
    canonical_statuses = set(CANONICAL_RUN_STATUSES)
    unsupported_states = {status for status in observed_counts if status not in canonical_statuses}
    attention_count = sum(observed_counts.get(status, 0) for status in ATTENTION_RUN_STATUSES)
    recent_attention_events: list[dict[str, Any]] = []

    if _table_exists(conn, "orchestration_run_events"):
        rows = conn.execute(
            """
            SELECT run_id, to_status, summary, reason_json, created_at
            FROM orchestration_run_events
            WHERE to_status IN (
                'blocked',
                'waiting_for_user',
                'waiting_for_tool',
                'failed_validation',
                'partial',
                'needs_follow_up'
            )
            ORDER BY created_at DESC
            LIMIT 20
            """
        ).fetchall()
        recent_attention_events = [
            {
                "run_id": row["run_id"],
                "to_status": row["to_status"],
                "summary": row["summary"],
                "reason_json": row["reason_json"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

        event_rows = conn.execute(
            """
            SELECT DISTINCT to_status
            FROM orchestration_run_events
            WHERE to_status IS NOT NULL
            """
        ).fetchall()
        event_states = {str(row["to_status"]) for row in event_rows}
        unsupported_states.update(status for status in event_states if status not in canonical_statuses)

    return {
        "summary": {
            "canonical_state_count": len(CANONICAL_RUN_STATUSES),
            "observed_run_count": sum(observed_counts.values()),
            "attention_count": attention_count,
            "unsupported_state_count": len(unsupported_states),
        },
        "contract": {
            "canonical_states": CANONICAL_RUN_STATUSES,
            "attention_states": ATTENTION_RUN_STATUSES,
            "terminal_states": TERMINAL_RUN_STATUSES,
            "authoritative_current_state": "orchestration_runs.status",
            "authoritative_history": "orchestration_run_events.to_status",
        },
        "observed_run_status_counts": observed_counts,
        "unsupported_states": sorted(unsupported_states),
        "recent_attention_events": recent_attention_events,
    }


def _knowledge_reference_rows(conn: sqlite3.Connection, topic_id: str) -> list[dict[str, Any]]:
    if not _table_exists(conn, "knowledge_references"):
        return []
    rows = conn.execute(
        """
        SELECT *
        FROM knowledge_references
        WHERE topic_id = ?
        ORDER BY created_at DESC
        """,
        (topic_id,),
    ).fetchall()
    references = []
    for row in rows:
        item = dict(row)
        references.append(
            {
                "id": item.get("id"),
                "source_kind": item.get("source_kind") or "unknown",
                "source_id": item.get("source_id"),
                "label": item.get("label") or item.get("href") or "Untitled source",
                "href": item.get("href"),
                "excerpt": item.get("excerpt"),
                "freshness": item.get("freshness") or "unknown",
                "confidence": item.get("confidence"),
            }
        )
    return references


def _knowledge_relationship_counts(conn: sqlite3.Connection, topic_id: str) -> tuple[int, int]:
    if not _table_exists(conn, "knowledge_relationships"):
        return (0, 0)
    columns = _table_columns(conn, "knowledge_relationships")
    if not {"from_topic_id", "to_topic_id"}.issubset(columns):
        return (0, 0)
    outgoing = conn.execute(
        "SELECT COUNT(*) AS count FROM knowledge_relationships WHERE from_topic_id = ?",
        (topic_id,),
    ).fetchone()
    incoming = conn.execute(
        "SELECT COUNT(*) AS count FROM knowledge_relationships WHERE to_topic_id = ?",
        (topic_id,),
    ).fetchone()
    return (int(outgoing["count"] or 0), int(incoming["count"] or 0))


def _knowledge_retrieval_trace_count(conn: sqlite3.Connection, topic_id: str) -> int:
    total = 0
    if _table_exists(conn, "briefing_packets"):
        total += int(
            conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM briefing_packets
                WHERE selection_trace_json LIKE ?
                """,
                (f"%{topic_id}%",),
            ).fetchone()["count"]
            or 0
        )
    if _table_exists(conn, "packet_expansions"):
        total += int(
            conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM packet_expansions
                WHERE trace_json LIKE ? OR returned_context_json LIKE ?
                """,
                (f"%{topic_id}%", f"%{topic_id}%"),
            ).fetchone()["count"]
            or 0
        )
    return total


def _knowledge_objects_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    if not _table_exists(conn, "knowledge_topics"):
        return {
            "summary": {
                "object_count": 0,
                "source_ref_coverage": 0.0,
                "objects_without_sources": 0,
                "relationship_count": 0,
                "unknown_kind_count": 0,
            },
            "contract": {
                "required_fields": KNOWLEDGE_OBJECT_CONTRACT_FIELDS,
                "valid_kinds": VALID_KNOWLEDGE_KINDS,
                "source_table": "knowledge_topics",
                "reference_table": "knowledge_references",
                "relationship_table": "knowledge_relationships",
            },
            "findings": [],
            "objects": [],
        }

    topic_columns = _table_columns(conn, "knowledge_topics")
    kind_expr = "kind" if "kind" in topic_columns else "'concept'"
    freshness_expr = "freshness" if "freshness" in topic_columns else "updated_at"
    rows = conn.execute(
        f"""
        SELECT
            id,
            {kind_expr} AS kind,
            title,
            summary,
            canonical_href,
            confidence,
            project_id,
            {freshness_expr} AS freshness,
            updated_at
        FROM knowledge_topics
        ORDER BY updated_at DESC
        LIMIT 100
        """
    ).fetchall()

    objects: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    objects_with_sources = 0
    relationship_total = 0
    unknown_kind_count = 0
    for row in rows:
        source_refs = _knowledge_reference_rows(conn, str(row["id"]))
        outgoing_count, backlink_count = _knowledge_relationship_counts(conn, str(row["id"]))
        retrieval_trace_count = _knowledge_retrieval_trace_count(conn, str(row["id"]))
        kind = row["kind"] or "unknown"
        if kind not in VALID_KNOWLEDGE_KINDS:
            unknown_kind_count += 1
            findings.append(
                {
                    "code": "knowledge_unknown_kind",
                    "severity": "warning",
                    "stable_id": row["id"],
                    "title": row["title"],
                    "kind": kind,
                    "summary": "Knowledge object kind is outside the implemented contract.",
                }
            )
        if source_refs:
            objects_with_sources += 1
        relationship_total += outgoing_count + backlink_count
        objects.append(
            {
                "stable_id": row["id"],
                "kind": kind,
                "title": row["title"],
                "summary": row["summary"],
                "canonical_href": row["canonical_href"],
                "project_id": row["project_id"],
                "freshness": row["freshness"] or row["updated_at"] or "unknown",
                "confidence": row["confidence"],
                "source_ref_count": len(source_refs),
                "source_refs": source_refs,
                "relationship_count": outgoing_count,
                "backlinks": {"count": backlink_count},
                "retrieval_trace_count": retrieval_trace_count,
            }
        )

    object_count = len(objects)
    return {
        "summary": {
            "object_count": object_count,
            "source_ref_coverage": round(objects_with_sources / object_count, 4) if object_count else 0.0,
            "objects_without_sources": object_count - objects_with_sources,
            "relationship_count": relationship_total,
            "unknown_kind_count": unknown_kind_count,
        },
        "contract": {
            "required_fields": KNOWLEDGE_OBJECT_CONTRACT_FIELDS,
            "valid_kinds": VALID_KNOWLEDGE_KINDS,
            "source_table": "knowledge_topics",
            "reference_table": "knowledge_references",
            "relationship_table": "knowledge_relationships",
            "personal_corpus_source_kind": "personal_corpus",
            "project_memory_source_kind": "project_memory",
        },
        "findings": findings,
        "objects": objects,
    }


def _workflow_learning_kind(layer_type: str | None) -> str:
    if layer_type == "workflow":
        return "workflow_evidence"
    if layer_type == "prompt":
        return "prompt_template_evidence"
    if layer_type in {"standards", "standard", "standards_health"}:
        return "standards_health_evidence"
    if layer_type in {"bug", "quality", "quality_pipeline"}:
        return "bug_quality_evidence"
    return "workflow_evidence"


def _count_run_rows(conn: sqlite3.Connection, table: str, run_id: str) -> int:
    if not _table_exists(conn, table) or "run_id" not in _table_columns(conn, table):
        return 0
    row = conn.execute(f"SELECT COUNT(*) AS count FROM {table} WHERE run_id = ?", (run_id,)).fetchone()
    return int(row["count"] or 0) if row else 0


def _linked_artifact_count(conn: sqlite3.Connection, run_id: str) -> int:
    if not _table_exists(conn, "artifacts") or not _table_exists(conn, "sessions"):
        return 0
    artifact_columns = _table_columns(conn, "artifacts")
    session_columns = _table_columns(conn, "sessions")
    if "session_id" not in artifact_columns or "run_id" not in session_columns:
        return 0
    row = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM artifacts a
        INNER JOIN sessions s ON s.id = a.session_id
        WHERE s.run_id = ?
        """,
        (run_id,),
    ).fetchone()
    return int(row["count"] or 0) if row else 0


def _inferred_learning_evidence(conn: sqlite3.Connection, run: dict[str, Any]) -> dict[str, Any] | None:
    run_id = str(run["id"])
    workflow_reports = _count_run_rows(conn, "workflow_execution_reports", run_id)
    memory_updates = _count_run_rows(conn, "memory_updates", run_id)
    standards_snapshots = _count_run_rows(conn, "standards_health_snapshots", run_id)
    success_evaluations = _count_run_rows(conn, "success_criteria_evaluations", run_id)
    linked_artifacts = _linked_artifact_count(conn, run_id)
    if standards_snapshots > 0:
        return {
            "run_id": run_id,
            "evidence_type": "standards_health_evidence",
            "source": "standards_health_snapshots",
            "source_count": standards_snapshots,
            "status": run.get("status"),
            "workflow_key": run.get("workflow_key"),
        }
    if run.get("status") in {"failed", "canceled"} and (linked_artifacts > 0 or success_evaluations > 0):
        return {
            "run_id": run_id,
            "evidence_type": "bug_quality_evidence",
            "source": "artifacts_or_success_criteria",
            "source_count": linked_artifacts + success_evaluations,
            "status": run.get("status"),
            "workflow_key": run.get("workflow_key"),
        }
    if workflow_reports > 0:
        return {
            "run_id": run_id,
            "evidence_type": "workflow_evidence",
            "source": "workflow_execution_reports",
            "source_count": workflow_reports,
            "status": run.get("status"),
            "workflow_key": run.get("workflow_key"),
        }
    if memory_updates > 0:
        return {
            "run_id": run_id,
            "evidence_type": "workflow_evidence",
            "source": "memory_updates",
            "source_count": memory_updates,
            "status": run.get("status"),
            "workflow_key": run.get("workflow_key"),
        }
    if linked_artifacts > 0:
        return {
            "run_id": run_id,
            "evidence_type": "workflow_evidence",
            "source": "session_artifacts",
            "source_count": linked_artifacts,
            "status": run.get("status"),
            "workflow_key": run.get("workflow_key"),
        }
    return None


def _ensure_workflow_learning_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS workflow_learning_events (
          id TEXT PRIMARY KEY,
          run_id TEXT REFERENCES orchestration_runs(id),
          evidence_type TEXT NOT NULL,
          proposal_target TEXT,
          confidence REAL NOT NULL DEFAULT 0.5,
          approval_state TEXT NOT NULL DEFAULT 'not_required',
          rationale TEXT NOT NULL,
          source_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_workflow_learning_events_run
          ON workflow_learning_events(run_id, created_at DESC)
        """
    )


def _workflow_learning_event_exists(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    evidence_type: str,
    proposal_target: str | None,
) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM workflow_learning_events
        WHERE run_id = ?
          AND evidence_type = ?
          AND COALESCE(proposal_target, '') = COALESCE(?, '')
        LIMIT 1
        """,
        (run_id, evidence_type, proposal_target),
    ).fetchone()
    return row is not None


def _record_workflow_learning_event(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    evidence_type: str,
    proposal_target: str | None,
    confidence: float,
    approval_state: str,
    rationale: str,
    source: dict[str, Any],
) -> None:
    if _workflow_learning_event_exists(
        conn,
        run_id=run_id,
        evidence_type=evidence_type,
        proposal_target=proposal_target,
    ):
        return
    conn.execute(
        """
        INSERT INTO workflow_learning_events (
          id, run_id, evidence_type, proposal_target, confidence,
          approval_state, rationale, source_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"learning-{uuid.uuid4()}",
            run_id,
            evidence_type,
            proposal_target,
            confidence,
            approval_state,
            rationale,
            json.dumps(source, sort_keys=True),
            _now_iso(),
        ),
    )


def _no_learning_reason(conn: sqlite3.Connection, run: dict[str, Any]) -> str:
    if run.get("status") == "canceled":
        return "canceled_without_signal"
    if run.get("status") == "failed":
        return "failed_before_artifact"
    if not run.get("result_summary"):
        return "missing_closeout_summary"
    if _linked_artifact_count(conn, str(run["id"])) == 0:
        return "insufficient_evidence"
    return "one_off_task"


def _workflow_learning_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    _ensure_workflow_learning_schema(conn)
    classification_counts = {kind: 0 for kind in WORKFLOW_LEARNING_EVIDENCE_TYPES}
    if not _table_exists(conn, "orchestration_runs"):
        return {
            "summary": {
                "terminal_run_count": 0,
                "runs_with_learning": 0,
                "no_learning_count": 0,
                "proposal_count": 0,
                "pending_approval_count": 0,
            },
            "contract": {
                "evidence_types": WORKFLOW_LEARNING_EVIDENCE_TYPES,
                "run_source": "orchestration_runs",
                "proposal_source": "improvement_writebacks",
            },
            "classification_counts": classification_counts,
            "persisted_events": [],
            "inferred_evidence": [],
            "no_learning_runs": [],
            "proposals": [],
        }

    terminal_placeholders = ", ".join("?" for _ in TERMINAL_RUN_STATUSES)
    run_rows = conn.execute(
        f"""
        SELECT *
        FROM orchestration_runs
        WHERE status IN ({terminal_placeholders})
        ORDER BY updated_at DESC
        """,
        tuple(TERMINAL_RUN_STATUSES),
    ).fetchall()

    proposals: list[dict[str, Any]] = []
    no_learning_runs: list[dict[str, Any]] = []
    inferred_evidence: list[dict[str, Any]] = []
    pending_approval_count = 0
    writeback_exists = _table_exists(conn, "improvement_writebacks")

    for run_row in run_rows:
        run = dict(run_row)
        writebacks = []
        if writeback_exists:
            writebacks = [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT *
                    FROM improvement_writebacks
                    WHERE run_id = ?
                    ORDER BY created_at DESC
                    """,
                    (run["id"],),
                ).fetchall()
            ]

        if not writebacks:
            inferred = _inferred_learning_evidence(conn, run)
            if inferred:
                _record_workflow_learning_event(
                    conn,
                    run_id=str(run["id"]),
                    evidence_type=str(inferred["evidence_type"]),
                    proposal_target=str(inferred.get("workflow_key") or ""),
                    confidence=0.65,
                    approval_state="not_required",
                    rationale=f"Inferred from durable {inferred['source']} evidence.",
                    source=inferred,
                )
                classification_counts[str(inferred["evidence_type"])] += 1
                inferred_evidence.append(inferred)
                continue
            classification_counts["no_learning_signal"] += 1
            reason = _no_learning_reason(conn, run)
            _record_workflow_learning_event(
                conn,
                run_id=str(run["id"]),
                evidence_type="no_learning_signal",
                proposal_target=str(run.get("workflow_key") or ""),
                confidence=0.55,
                approval_state="not_required",
                rationale=reason,
                source={"reason": reason, "status": run.get("status"), "workflow_key": run.get("workflow_key")},
            )
            no_learning_runs.append(
                {
                    "run_id": run["id"],
                    "status": run.get("status"),
                    "workflow_key": run.get("workflow_key"),
                    "reason": reason,
                }
            )
            continue

        for writeback in writebacks:
            learning_kind = _workflow_learning_kind(writeback.get("layer_type"))
            _record_workflow_learning_event(
                conn,
                run_id=str(run["id"]),
                evidence_type=learning_kind,
                proposal_target=str(writeback.get("layer_key") or ""),
                confidence=0.8,
                approval_state="pending" if writeback.get("status") == "pending_approval" else "not_required",
                rationale=str(writeback.get("summary") or writeback.get("title") or "Workflow proposal evidence."),
                source={"source": "improvement_writebacks", "writeback_id": writeback.get("id")},
            )
            classification_counts[learning_kind] += 1
            requires_approval = int(writeback.get("requires_approval") or 0) == 1
            if requires_approval or writeback.get("status") == "pending_approval":
                pending_approval_count += 1
            proposals.append(
                {
                    "id": writeback.get("id"),
                    "run_id": writeback.get("run_id"),
                    "evidence_type": learning_kind,
                    "layer_type": writeback.get("layer_type"),
                    "layer_key": writeback.get("layer_key"),
                    "status": writeback.get("status"),
                    "requires_approval": requires_approval,
                    "title": writeback.get("title"),
                }
            )

    persisted_event_rows = [
        dict(row)
        for row in conn.execute(
            """
            SELECT run_id, evidence_type, proposal_target, confidence, approval_state, rationale, source_json, created_at
            FROM workflow_learning_events
            ORDER BY created_at DESC
            LIMIT 100
            """
        ).fetchall()
    ]
    persisted_learning_run_count = int(
        conn.execute(
            """
            SELECT COUNT(DISTINCT run_id) AS count
            FROM workflow_learning_events
            WHERE evidence_type != 'no_learning_signal'
            """
        ).fetchone()["count"]
        or 0
    )
    conn.commit()
    return {
        "summary": {
            "terminal_run_count": len(run_rows),
            "runs_with_learning": persisted_learning_run_count,
            "no_learning_count": len(no_learning_runs),
            "inferred_evidence_count": len(inferred_evidence),
            "persisted_event_count": _count(conn, "workflow_learning_events"),
            "proposal_count": len(proposals),
            "pending_approval_count": pending_approval_count,
        },
        "contract": {
            "evidence_types": WORKFLOW_LEARNING_EVIDENCE_TYPES,
            "run_source": "orchestration_runs",
            "event_source": "workflow_learning_events",
            "proposal_source": "improvement_writebacks",
            "promotion_gate": "status + requires_approval on improvement_writebacks",
        },
        "classification_counts": classification_counts,
        "persisted_events": persisted_event_rows[:50],
        "inferred_evidence": inferred_evidence[:50],
        "no_learning_runs": no_learning_runs[:20],
        "proposals": proposals[:50],
    }


def _ensure_evaluation_finding_schema(conn: sqlite3.Connection) -> None:
    if _table_exists(conn, "success_criteria_findings"):
        for column, definition in {
            "resolution_status": "TEXT NOT NULL DEFAULT 'open'",
            "resolution_actor": "TEXT",
            "resolution_rationale": "TEXT",
            "resolution_evidence_json": "TEXT NOT NULL DEFAULT '[]'",
            "resolved_at": "TEXT",
        }.items():
            _ensure_column(conn, "success_criteria_findings", column, definition)
    if _table_exists(conn, "consistency_findings"):
        for column, definition in {
            "resolution_status": "TEXT NOT NULL DEFAULT 'open'",
            "resolution_actor": "TEXT",
            "resolution_rationale": "TEXT",
            "resolution_evidence_json": "TEXT NOT NULL DEFAULT '[]'",
            "resolved_at": "TEXT",
        }.items():
            _ensure_column(conn, "consistency_findings", column, definition)


def _knowledge_contract_status(conn: sqlite3.Connection) -> str:
    if not _table_exists(conn, "knowledge_topics"):
        return "partial"
    topic_columns = _table_columns(conn, "knowledge_topics")
    required_columns = {"id", "kind", "title", "summary", "confidence", "freshness", "canonical_href"}
    if not required_columns.issubset(topic_columns):
        return "partial"
    if not _table_exists(conn, "knowledge_references") or not _table_exists(conn, "knowledge_relationships"):
        return "partial"
    unknown_kind = conn.execute(
        """
        SELECT 1
        FROM knowledge_topics
        WHERE kind NOT IN ({})
        LIMIT 1
        """.format(",".join("?" for _ in VALID_KNOWLEDGE_KINDS)),
        tuple(VALID_KNOWLEDGE_KINDS),
    ).fetchone()
    return "partial" if unknown_kind else "implemented"


def _retrieval_trace_contract_status(conn: sqlite3.Connection) -> str:
    if not _table_exists(conn, "briefing_packets") or not _table_exists(conn, "packet_expansions"):
        return "partial"
    packet_columns = _table_columns(conn, "briefing_packets")
    expansion_columns = _table_columns(conn, "packet_expansions")
    packet_required = {"selection_trace_json", "omitted_context_json", "token_budget"}
    expansion_required = {"trace_json", "returned_context_json", "token_budget"}
    if packet_required.issubset(packet_columns) and expansion_required.issubset(expansion_columns):
        return "implemented"
    return "partial"


def _evaluation_finding_contract_status(conn: sqlite3.Connection) -> str:
    lifecycle_columns = {
        "resolution_status",
        "resolution_actor",
        "resolution_rationale",
        "resolution_evidence_json",
        "resolved_at",
    }
    available_tables = [
        table
        for table in ("success_criteria_findings", "consistency_findings")
        if _table_exists(conn, table)
    ]
    if not available_tables:
        return "partial"
    if all(lifecycle_columns.issubset(_table_columns(conn, table)) for table in available_tables):
        return "implemented"
    return "partial"


def _contracts_audit_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    _ensure_workflow_learning_schema(conn)
    _ensure_evaluation_finding_schema(conn)
    contracts = [
        {
            "name": "TrustedSignal",
            "status": "implemented",
            "source": "aios-ui/lib/trusted-signals.ts",
            "storage": "derived per surface",
            "table_available": True,
        },
        {
            "name": "InvocationBackend",
            "status": "implemented",
            "source": "services/invocation_backends.py",
            "storage": "orchestration_invocations",
            "table_available": _table_exists(conn, "orchestration_invocations"),
        },
        {
            "name": "RunLifecycleEvent",
            "status": "implemented",
            "source": "aios lifecycle-audit",
            "storage": "orchestration_run_events",
            "table_available": _table_exists(conn, "orchestration_run_events"),
        },
        {
            "name": "KnowledgeObject",
            "status": _knowledge_contract_status(conn),
            "source": "aios knowledge-objects",
            "storage": "knowledge_topics + knowledge_references + knowledge_relationships",
            "table_available": _table_exists(conn, "knowledge_topics"),
            "valid_kinds": VALID_KNOWLEDGE_KINDS,
        },
        {
            "name": "RetrievalTrace",
            "status": _retrieval_trace_contract_status(conn),
            "source": "briefing_packets.selection_trace_json + packet_expansions.trace_json",
            "storage": "briefing_packets + packet_expansions",
            "table_available": _table_exists(conn, "briefing_packets"),
        },
        {
            "name": "WorkflowLearningEvent",
            "status": "implemented" if _table_exists(conn, "workflow_learning_events") else "partial",
            "source": "aios workflow-learning-audit",
            "storage": "workflow_learning_events + improvement_writebacks + improvement_writeback_events",
            "table_available": _table_exists(conn, "workflow_learning_events"),
        },
        {
            "name": "EvaluationFinding",
            "status": _evaluation_finding_contract_status(conn),
            "source": "success_criteria_findings + consistency_findings",
            "storage": "success_criteria_findings + consistency_findings",
            "table_available": _table_exists(conn, "success_criteria_findings")
            or _table_exists(conn, "consistency_findings"),
            "lifecycle_states": EVALUATION_FINDING_LIFECYCLE_STATES,
        },
    ]
    implemented_or_partial = [item for item in contracts if item["status"] in {"implemented", "partial"}]
    return {
        "summary": {
            "canonical_contract_count": len(contracts),
            "implemented_or_partial_count": len(implemented_or_partial),
            "implemented_count": len([item for item in contracts if item["status"] == "implemented"]),
            "partial_count": len([item for item in contracts if item["status"] == "partial"]),
        },
        "contracts": contracts,
    }


def _status_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    return {
        "projects_active": _count(conn, "projects", "status='active'"),
        "sessions_open": _count(conn, "sessions", "status='open'"),
        "sessions_24h": _count(conn, "sessions", "started_at > datetime('now', '-1 day')"),
        "open_bugs": _count(conn, "bug_log", "status='open'"),
        "run_status_counts": _run_status_counts(conn),
        "handshake_coverage": _handshake_coverage(conn),
        "last_session": _last_session(conn),
        "resumable_runs": _resumable_runs(conn),
        "recent_closeouts": _recent_closeouts(conn),
    }


def _truth_audit_payload(conn: sqlite3.Connection, truth_file: Path) -> dict[str, Any]:
    exists = truth_file.exists()
    content = truth_file.read_text(encoding="utf-8") if exists else ""
    headings = _extract_markdown_headings(content)
    last_updated_raw = _truth_last_updated(content)
    last_updated = _parse_iso(last_updated_raw)
    age_days = None
    if last_updated:
        age_days = (datetime.now(UTC) - last_updated).days
    facet_coverage = _truth_facet_coverage(headings)
    missing_facets = [facet for facet in TRUTH_REQUIRED_FACETS if not facet_coverage.get(facet)]
    recent_closeouts = _recent_closeouts(conn, limit=5)
    resumable_runs = _resumable_runs(conn, limit=5)

    findings: list[dict[str, Any]] = []
    if not exists:
        findings.append(
            {
                "severity": "blocker",
                "code": "truth_file_missing",
                "summary": f"Truth file does not exist: {truth_file}",
            }
        )
    if exists and not last_updated_raw:
        findings.append(
            {
                "severity": "warning",
                "code": "truth_last_updated_missing",
                "summary": "Truth file is missing a Last updated field.",
            }
        )
    if age_days is not None and age_days > 7:
        findings.append(
            {
                "severity": "warning",
                "code": "truth_stale",
                "summary": f"Truth file was last updated {age_days} days ago.",
            }
        )
    if missing_facets:
        findings.append(
            {
                "severity": "warning",
                "code": "truth_facets_missing",
                "summary": "Truth file is missing required operating facets.",
                "missing_facets": missing_facets,
            }
        )
    if recent_closeouts:
        findings.append(
            {
                "severity": "info",
                "code": "truth_update_evidence_available",
                "summary": "Recent governed closeout evidence is available for truth review.",
                "closeout_count": len(recent_closeouts),
            }
        )
    if resumable_runs:
        findings.append(
            {
                "severity": "info",
                "code": "truth_next_action_evidence_available",
                "summary": "Resumable runs can inform truth next-action updates.",
                "resumable_run_count": len(resumable_runs),
            }
        )

    return {
        "summary": {
            "truth_file": str(truth_file),
            "exists": exists,
            "last_updated": last_updated_raw,
            "age_days": age_days,
            "required_facet_count": len(TRUTH_REQUIRED_FACETS),
            "missing_facet_count": len(missing_facets),
            "recent_closeout_count": len(recent_closeouts),
            "resumable_run_count": len(resumable_runs),
            "finding_count": len(findings),
        },
        "contract": {
            "required_facets": TRUTH_REQUIRED_FACETS,
            "accepted_truth_source": str(truth_file),
            "proposal_sources": ["workflow_execution_reports.report_json", "orchestration_runs.resume_snapshot_json"],
            "important_updates_require_review": True,
            "truth_update_workflow": "project-truth-update",
        },
        "facet_coverage": facet_coverage,
        "recent_closeouts": recent_closeouts,
        "resumable_runs": resumable_runs,
        "findings": findings,
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
    latest_standards_snapshot = _latest_standards_snapshot(conn)
    ensure_rtk_schema(conn)
    rtk_metrics = rtk_metrics_log(conn)
    rtk_rules = load_compression_rules()

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
        "standards_delta": {
            "registry": _standards_registry_summary(config_root),
            "latest_snapshot": latest_standards_snapshot,
        },
        "rtk": {
            "default_mode": rtk_rules.get("default_mode", "compressed"),
            "rules_version": rtk_rules.get("version"),
            "metrics": rtk_metrics,
            "interface": rtk_rules.get(
                "interface",
                'rtk_run(command: string, mode: "compressed" | "raw" | "adaptive")',
            ),
        },
        "health": _health_payload(conn, logs_dir),
        "recent_failures_preview": _recent_failures_payload(conn, logs_dir, last=5),
        "available_commands": [
            "aios status --json",
            "aios health --json",
            "aios metadata --json",
            "aios capability-audit --json",
            "aios invocation-audit --json",
            "aios lifecycle-audit --json",
            "aios knowledge-objects --json",
            "aios workflow-learning-audit --json",
            "aios contracts-audit --json",
            "aios truth-audit --json",
            "aios logs --json --last 50",
            "aios recent-failures --json --last 20",
            "aios rtk --json",
            "aios start-work --json \"objective\"",
            "aios skills status --json",
            "aios skills refresh --json --apply",
        ],
    }


def _rtk_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    ensure_rtk_schema(conn)
    rules = load_compression_rules()
    rows = conn.execute(
        """
        SELECT workflow_key, COUNT(*) AS events,
               COALESCE(SUM(estimated_raw_tokens), 0) AS raw_tokens,
               COALESCE(SUM(estimated_compressed_tokens), 0) AS compressed_tokens,
               COALESCE(SUM(MAX(estimated_raw_tokens - estimated_compressed_tokens, 0)), 0) AS tokens_saved
        FROM rtk_compression_events
        GROUP BY workflow_key
        ORDER BY tokens_saved DESC
        LIMIT 20
        """
    ).fetchall()
    workflows = []
    for row in rows:
        raw_tokens = int(row["raw_tokens"])
        compressed_tokens = int(row["compressed_tokens"])
        reduction = round(max(0, raw_tokens - compressed_tokens) / raw_tokens * 100, 2) if raw_tokens else 0.0
        workflows.append(
            {
                "workflow_key": row["workflow_key"] or "unclassified",
                "events": int(row["events"]),
                "raw_tokens": raw_tokens,
                "compressed_tokens": compressed_tokens,
                "tokens_saved": int(row["tokens_saved"]),
                "efficiency_score": reduction,
            }
        )
    metrics = rtk_metrics_log(conn)
    classification = classify_rtk_metrics(metrics)
    findings = []
    if classification["benefit_state"] == "token_regressive":
        findings.append(
            {
                "severity": "warning",
                "code": "rtk_token_regressive",
                "summary": "RTK compressed-token totals exceed raw-token totals.",
            }
        )
    elif classification["benefit_state"] == "no_benefit":
        findings.append(
            {
                "severity": "info",
                "code": "rtk_no_benefit",
                "summary": "RTK has recorded events but no positive token savings.",
            }
        )
    return {
        "rules": rules,
        "state": classification["state"],
        "benefit_state": classification["benefit_state"],
        "explanation": classification["explanation"],
        "missing_reason": classification["missing_reason"],
        "metrics": metrics,
        "workflow_efficiency": workflows,
        "findings": findings,
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
    if command == "rtk":
        metrics = data["metrics"]
        print(
            f"rtk_events={metrics['event_count']} "
            f"tokens_saved={metrics['tokens_saved']} "
            f"reduction={metrics['weighted_reduction_percent']}%"
        )
        return
    if command == "capability-audit":
        summary = data["summary"]
        print(f"surfaces={summary['surfaces']} findings={summary['findings']}")
        return
    if command == "invocation-audit":
        summary = data["summary"]
        print(f"backends={summary['backend_count']} invocations={summary['invocation_count']}")
        return
    if command == "lifecycle-audit":
        summary = data["summary"]
        print(f"attention={summary['attention_count']} unsupported={summary['unsupported_state_count']}")
        return
    if command == "knowledge-objects":
        summary = data["summary"]
        print(f"objects={summary['object_count']} source_ref_coverage={summary['source_ref_coverage']}")
        return
    if command == "workflow-learning-audit":
        summary = data["summary"]
        print(f"terminal_runs={summary['terminal_run_count']} no_learning={summary['no_learning_count']}")
        return
    if command == "contracts-audit":
        summary = data["summary"]
        print(f"contracts={summary['canonical_contract_count']} partial={summary['partial_count']}")
        return
    if command == "truth-audit":
        summary = data["summary"]
        print(
            f"truth_file={summary['truth_file']} "
            f"missing_facets={summary['missing_facet_count']} "
            f"findings={summary['finding_count']}"
        )
        return
    if command == "prove-project-health":
        summary = data["summary"]
        print(
            f"targets={summary['target_count']} "
            f"snapshots={summary['snapshot_recorded_count']} "
            f"missing_source={summary['missing_source_count']}"
        )
        return
    if command == "sync-automation-history":
        summary = data["summary"]
        print(
            f"source={summary['source']} "
            f"parsed={summary['parsed_run_count']} "
            f"stored={summary['inserted_or_updated_count']}"
        )
        return
    if command == "start-work":
        print(
            f"run={data['run']['id']} status={data['run']['status']} "
            f"session={data['run']['session_id'] or 'unlinked'} packet={data['packet']['id']}"
        )
        return
    if command == "pre-pr-readiness":
        coverage = data.get("coverage") if isinstance(data.get("coverage"), dict) else None
        coverage_percent = coverage.get("coveragePercent") if coverage else None
        coverage_label = f"{coverage_percent}%" if coverage_percent is not None else "n/a"
        print(
            f"status={data['status']} "
            f"coverage={coverage_label} "
            f"unsupported={len(data['unsupported_changed_files'])}"
        )
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
    if command == "harness-eval-run":
        totals = data["totals"]
        print(
            f"fixtures={totals['fixture_count']} "
            f"runs={totals['run_count']} "
            f"failed={totals['failed_run_count']} "
            f"average={totals['average_score']}"
        )
        return


def _command_name(args: argparse.Namespace) -> str:
    if args.command == "skills":
        return f"skills-{args.skills_command}"
    if args.command == "corpus":
        return f"corpus-{args.corpus_command}"
    if args.command == "harness-eval":
        return f"harness-eval-{args.harness_eval_command}"
    return args.command


def _run_corpus_command(command: str, passthrough_args: Sequence[str]) -> int:
    script = REPO_ROOT / "scripts" / "aios-corpus-eval.cjs"
    if command == "run":
        argv = ["node", str(script), *passthrough_args]
    elif command == "report":
        argv = ["node", str(script), "--report-only", *passthrough_args]
    else:
        raise CLIError("unknown-corpus-command", f"Unsupported corpus command: {command}", EXIT_USAGE)
    try:
        completed = subprocess.run(argv, check=False)
    except FileNotFoundError as exc:
        raise CLIError("node-not-found", "Node.js is required for corpus evaluation", EXIT_DEPENDENCY) from exc
    return int(completed.returncode)


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

    subparsers.add_parser("rtk", help="RTK compression rules and metrics")
    subparsers.add_parser("capability-audit", help="Trusted-signal audit for core AIOS capability surfaces")
    subparsers.add_parser("invocation-audit", help="Invocation backend and strict-handshake audit")
    subparsers.add_parser("lifecycle-audit", help="Run lifecycle state contract and attention-state audit")
    subparsers.add_parser("knowledge-objects", help="Knowledge object contract and provenance audit")
    subparsers.add_parser("workflow-learning-audit", help="Workflow learning evidence and proposal audit")
    subparsers.add_parser("contracts-audit", help="Canonical AIOS interface contract audit")
    truth_audit = subparsers.add_parser(
        "truth-audit",
        help="Project truth freshness, facet coverage, and governed update contract audit",
    )
    truth_audit.add_argument(
        "--truth-file",
        default=str(REPO_ROOT / "PROJECT.md"),
        help="Canonical project truth file to audit",
    )

    prove_project_health_parser = subparsers.add_parser(
        "prove-project-health",
        help="Record standards-health snapshots for tier-one proving projects",
    )
    prove_project_health_parser.add_argument(
        "--project",
        action="append",
        default=[],
        help=f"Project name to prove; defaults to {', '.join(DEFAULT_PROVING_PROJECTS)}",
    )
    prove_project_health_parser.add_argument(
        "--all-inventory",
        action="store_true",
        help="Prove every project in inventory, plus missing configured proving projects",
    )

    subparsers.add_parser("sync-automation-history", help="Import durable automation history from local logs")

    harness_brief = subparsers.add_parser("harness-brief", help="Generate a backend-neutral harness briefing")
    harness_brief.add_argument("--task", required=True, help="Task to classify and brief")
    harness_brief.add_argument("--project", default=None, help="Optional project id")
    harness_brief.add_argument(
        "--context-root",
        default=str(REPO_ROOT / "aios" / "context"),
        help="Context compiler root",
    )

    harness_simulate = subparsers.add_parser("harness-simulate", help="Run a fake-agent harness fixture")
    harness_simulate.add_argument("--fixture", required=True, help="Harness fixture JSON path")
    harness_simulate.add_argument(
        "--context-root",
        default=str(REPO_ROOT / "aios" / "context"),
        help="Context compiler root",
    )

    harness_replay = subparsers.add_parser("harness-replay", help="Replay a historical session as harness events")
    harness_replay.add_argument("--session-id", required=True, help="Session id to replay")

    harness_shadow = subparsers.add_parser(
        "harness-shadow-evaluate",
        help="Read-only harness evaluation for an existing session",
    )
    harness_shadow.add_argument(
        "--session-id",
        default="latest",
        help="Session id to shadow evaluate, or latest",
    )

    subparsers.add_parser(
        "harness-active-readiness",
        help="Report readiness for active backend-neutral harness enforcement",
    )

    start_work = subparsers.add_parser("start-work", help="Create a routed AIOS run packet and session handshake")
    start_work.add_argument("objective", help="Work objective to route through AIOS")
    start_work.add_argument("--project", default=None, help="Project id to link to the run")
    start_work.add_argument("--session-id", default=None, help="Session id to link; defaults to logs/current_session")
    start_work.add_argument("--workflow", default=None, help="Workflow key override")
    start_work.add_argument("--agent", default=None, help="Agent profile key override")
    start_work.add_argument("--backend", default=None, help="Invocation backend key override")

    pre_pr = subparsers.add_parser("pre-pr-readiness", help="Run the AIOS Pre-CR readiness gate")
    pre_pr.add_argument("--workspace-root", default=".", help="Workspace root to evaluate")
    pre_pr.add_argument(
        "--pre-cr-repo",
        default=str(DEFAULT_PRE_CR_REPO),
        help="Path to the pre-cr-suite-lsp repository",
    )
    pre_pr.add_argument("--server-entry", default=None, help="Override the built pre-cr server entrypoint")
    pre_pr.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_PRE_PR_TIMEOUT_SECONDS,
        help="Timeout for the readiness run",
    )

    skills_parser = subparsers.add_parser("skills", help="Instruction/skills registry surfaces")
    skills_subparsers = skills_parser.add_subparsers(dest="skills_command", required=True)

    skills_status = skills_subparsers.add_parser("status", help="Show instruction sync status")
    skills_status.add_argument("--project", default=None, help="Optional project id filter")

    skills_refresh = skills_subparsers.add_parser("refresh", help="Refresh instruction files from registry sources")
    skills_refresh.add_argument("--project", default=None, help="Optional project id filter")
    skills_refresh.add_argument("--apply", action="store_true", help="Apply updates instead of dry-run")

    corpus_parser = subparsers.add_parser("corpus", help="Corpus evaluation harness")
    corpus_subparsers = corpus_parser.add_subparsers(dest="corpus_command", required=True)
    corpus_run = corpus_subparsers.add_parser("run", help="Run the AIOS corpus evaluation harness")
    corpus_run.add_argument("corpus_args", nargs=argparse.REMAINDER)
    corpus_report = corpus_subparsers.add_parser("report", help="Regenerate a corpus Markdown report")
    corpus_report.add_argument("corpus_args", nargs=argparse.REMAINDER)

    harness_eval_parser = subparsers.add_parser("harness-eval", help="AIOS harness evaluation")
    harness_eval_subparsers = harness_eval_parser.add_subparsers(
        dest="harness_eval_command",
        required=True,
    )
    harness_eval_run = harness_eval_subparsers.add_parser(
        "run",
        help="Run the deterministic AIOS harness eval suite",
    )
    harness_eval_run.add_argument(
        "--config",
        default=str(DEFAULT_HARNESS_EVAL_CONFIG_PATH),
        help="Harness eval config path",
    )

    return parser


def run_cli(argv: Sequence[str] | None = None) -> int:
    parser = create_parser()
    raw_argv = list(argv) if argv is not None else sys.argv[1:]
    args, unknown_args = parser.parse_known_args(raw_argv)
    if unknown_args:
        if args.command == "corpus":
            corpus_index = raw_argv.index("corpus")
            args.corpus_args = raw_argv[corpus_index + 2 :]
        else:
            parser.error(f"unrecognized arguments: {' '.join(unknown_args)}")

    db_path = Path(args.db).expanduser().resolve()
    logs_dir = Path(args.logs_dir).expanduser().resolve()
    config_root = Path(args.config_root).expanduser().resolve()
    vault_root = _resolve_vault_root(args.vault_root)
    command = _command_name(args)
    conn: sqlite3.Connection | None = None

    try:
        if args.command in {
            "status",
            "health",
            "metadata",
            "recent-failures",
            "rtk",
            "capability-audit",
            "invocation-audit",
            "lifecycle-audit",
            "knowledge-objects",
            "workflow-learning-audit",
            "contracts-audit",
            "truth-audit",
            "prove-project-health",
            "sync-automation-history",
            "start-work",
            "harness-brief",
            "harness-simulate",
            "harness-replay",
            "harness-shadow-evaluate",
        }:
            conn = _connect_db(db_path)
        else:
            conn = None

        if args.command == "corpus":
            return _run_corpus_command(args.corpus_command, args.corpus_args)
        if args.command == "status":
            assert conn is not None
            data = _status_payload(conn)
        elif args.command == "harness-eval" and args.harness_eval_command == "run":
            data = suite_result_to_dict(score_suite(Path(args.config)))
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
        elif args.command == "rtk":
            assert conn is not None
            data = _rtk_payload(conn)
        elif args.command == "capability-audit":
            assert conn is not None
            ensure_rtk_schema(conn)
            data = capability_truth_payload(conn)
        elif args.command == "invocation-audit":
            assert conn is not None
            data = _invocation_audit_payload(conn)
        elif args.command == "lifecycle-audit":
            assert conn is not None
            data = _lifecycle_audit_payload(conn)
        elif args.command == "knowledge-objects":
            assert conn is not None
            data = _knowledge_objects_payload(conn)
        elif args.command == "workflow-learning-audit":
            assert conn is not None
            data = _workflow_learning_payload(conn)
        elif args.command == "contracts-audit":
            assert conn is not None
            data = _contracts_audit_payload(conn)
        elif args.command == "truth-audit":
            assert conn is not None
            data = _truth_audit_payload(conn, Path(args.truth_file).expanduser().resolve())
        elif args.command == "prove-project-health":
            assert conn is not None
            data = prove_project_health(
                conn,
                config_root=config_root,
                project_names=list(args.project) if args.project else None,
                all_inventory=bool(args.all_inventory),
            )
        elif args.command == "sync-automation-history":
            assert conn is not None
            data = sync_pipeline_automation_history(conn, logs_dir=logs_dir)
        elif args.command == "harness-brief":
            assert conn is not None
            data = brief_task(
                conn,
                task=args.task,
                project_id=args.project,
                context_root=Path(args.context_root).expanduser().resolve(),
            )
        elif args.command == "harness-simulate":
            assert conn is not None
            data = simulate_fixture(
                conn,
                fixture_path=Path(args.fixture).expanduser().resolve(),
                context_root=Path(args.context_root).expanduser().resolve(),
            )
        elif args.command == "harness-replay":
            assert conn is not None
            data = replay_session(conn, session_id=args.session_id)
        elif args.command == "harness-shadow-evaluate":
            assert conn is not None
            data = shadow_evaluate_session(conn, session_id=args.session_id)
        elif args.command == "harness-active-readiness":
            data = active_readiness()
        elif args.command == "start-work":
            assert conn is not None
            data = _start_work_payload(
                conn,
                logs_dir,
                objective=args.objective,
                project_id=args.project,
                workflow_key=args.workflow,
                agent_key=args.agent,
                backend_key=args.backend,
                session_id=args.session_id,
            )
        elif args.command == "pre-pr-readiness":
            data = pre_pr_readiness_payload(
                workspace_root=args.workspace_root,
                pre_cr_repo=args.pre_cr_repo,
                server_entry=args.server_entry,
                timeout_seconds=max(1, int(args.timeout_seconds)),
            )
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
