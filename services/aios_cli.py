from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shlex
import sqlite3
import subprocess
import sys
import uuid
from collections import deque
from collections.abc import Sequence
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import services.next_action as next_action_module
import services.operator_search as operator_search_module
from services.ablation_runner import compare_ablation_suite, run_ablation_suite
from services.asset_lifecycle import (
    AssetKind,
    AssetLifecycleState,
    list_assets,
    promote_asset,
)
from services.automation_history import sync_pipeline_automation_history
from services.capability_truth import capability_truth_payload
from services.context_loops import (
    DEFAULT_CONTEXT_LOOP_ROOT,
    apply_approved_candidates,
    context_loop_metrics,
    create_email_draft_run,
    create_inner_loop_run,
    propose_learning_candidates,
    record_review_event,
    write_metrics_report,
)
from services.context_loops import (
    approve_candidate as approve_context_loop_candidate,
)
from services.context_loops import (
    reject_candidate as reject_context_loop_candidate,
)
from services.daily_flow import preview_from_objective, replay_from_run
from services.eval_run_service import (
    create_eval_run,
    get_eval_summary,
    list_eval_runs,
)
from services.evidence_artifacts import list_evidence_artifacts, validate_fresh_evidence
from services.execution_strategy import list_model_selection_records
from services.external_benchmark_adapter import (
    normalize_external_result,
    to_swe_bench_format,
    to_terminal_bench_format,
)
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
from services.learning_taxonomy import LEARNING_SIGNAL_KINDS, LearningSignalKind
from services.meta_learning_signals import extract_meta_learning_signals, signals_to_dicts
from services.native_command_logging import native_command_metadata, write_native_command_metadata
from services.native_commands import (
    de_slopify as native_de_slopify,
)
from services.native_commands import (
    handoff as native_handoff,
)
from services.native_commands import (
    prototype as native_prototype,
)
from services.native_commands import (
    review_squad as native_review_squad,
)
from services.native_commands import (
    security_audit as native_security_audit,
)
from services.native_commands import (
    zoom_out as native_zoom_out,
)
from services.path_resolution import get_vault_root
from services.peer_trace import (
    end_peer_session,
    list_peer_sessions,
    start_peer_session,
)
from services.personalized_humanizer import (
    FeedbackVerdict,
    ensure_personalized_humanizer_schema,
    humanize_text,
    record_eval_result,
    record_feedback,
    record_rewrite_run,
    run_eval_suite,
)
from services.planning_lenses import select_planning_lenses
from services.portable_context_packet_generator import generate_packet
from services.pre_pr_readiness import (
    DEFAULT_PRE_CR_REPO,
    pre_pr_readiness_payload,
)
from services.pre_pr_readiness import (
    DEFAULT_TIMEOUT_SECONDS as DEFAULT_PRE_PR_TIMEOUT_SECONDS,
)
from services.project_health_proof import DEFAULT_PROVING_PROJECTS, prove_project_health
from services.quality_gates import run_gate as run_quality_gate
from services.repo_gate_adoption import write_adoption_doc_quality_report
from services.retrospective_artifacts import list_retrospective_artifacts
from services.rtk_integration import (
    classify_rtk_metrics,
    ensure_rtk_schema,
    load_compression_rules,
    rtk_metrics_log,
)
from services.second_brain_eval import (
    compute_retrieval_metrics,
    compute_second_brain_lift,
    evaluate_gold_set_run,
)
from services.session_intelligence_helpers import (
    HELPER_FAMILIES as SESSION_INTEL_HELPER_FAMILIES,
)
from services.session_intelligence_helpers import (
    list_session_intelligence_helpers,
    run_session_intelligence_helper,
)
from services.session_intelligence_loop import (
    SessionIntelligenceBackfillOptions,
    SessionIntelligenceOptions,
    implement_session_intelligence_candidates,
    list_session_intelligence_candidates,
    list_session_intelligence_clusters,
    list_session_intelligence_implementations,
    mark_session_intelligence_candidate,
    run_session_intelligence,
    run_session_intelligence_backfill,
)
from services.session_intelligence_tools import (
    codex_workflow_skill_payload,
    planning_state_payload,
    quality_ladder_payload,
    repo_closeout_payload,
    repo_inspect_payload,
    service_probe_payload,
    ship_guard_payload,
)
from services.session_providers.claude import ClaudeProvider
from services.session_providers.codex import CodexProvider
from services.shadow_automation import (
    approve_candidate,
    run_full_automation_pipeline,
    shadow_status,
)
from services.shadow_branch_runner import (
    cleanup_shadow_worktree,
    compare_shadow_runs,
    create_shadow_worktree,
    get_shadow_run,
    list_shadow_parity_metadata,
    record_shadow_branch_run,
    shadow_branch_name,
    verify_no_contamination,
)
from services.shadow_candidate_scorer import score_shadow_candidate
from services.shadow_codex_runner import (
    cancel_shadow_execution,
    launch_codex_shadow,
    shadow_execution_status,
)
from services.skills_harvest import HarvestOptions, harvest_skills_library, verify_tmcp_graph
from services.standards_health import (
    AssessmentStatus,
    ManualAssessmentOverride,
    latest_snapshot,
    persist_manual_override,
    project_delta_explanations,
)
from services.standards_health import (
    load_registry as load_standards_registry,
)
from services.success_criteria import (
    EVALUATION_FINDING_LIFECYCLE_STATES,
    preview_applicable_criteria,
    resolve_finding,
    resolve_task_standards,
)
from services.task_routing import route_objective
from services.tmcp_runtime import (
    compile_tmcp_packet,
    diff_tmcp_packets,
    evaluate_tmcp_packet_adherence,
    explain_tmcp_packet,
    persist_tmcp_packet_adherence,
    record_tmcp_intervention_event,
    record_tmcp_receipt_event,
    shortcut_governance_recommendation,
    tmcp_learning_summary,
    update_tmcp_receipt_feedback,
)
from services.verifier_artifacts import list_verifier_artifacts, validate_closeout_verification
from services.workflow_orchestration import (
    WorkflowExecutionContext,
    developer_experience_capability_report,
    execute_workflow,
    load_developer_experience_capability_pack,
    load_workflow_registry,
    recommend_workflow_from_health,
    workflow_stage_gate_report,
)
from services.workflow_promotion import (
    compare_workflow_effectiveness,
    propose_workflow_promotion,
)

DX_PACK_IMPLEMENTATION_REPORT_SECTIONS = (
    "Summary",
    "Files Added",
    "Files Modified",
    "Capabilities Added",
    "Routing Changes",
    "Eval Coverage",
    "Validation Results",
    "Assumptions Made",
    "Known Limitations",
    "Recommended Next Steps",
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_ROOT = REPO_ROOT / "config"
DEFAULT_DB_PATH = Path.home() / "AIOS" / "data" / "aios.db"
DEFAULT_LOGS_DIR = Path.home() / "AIOS" / "logs"
DAILY_CODEX_SESSION_INTEL_COMMAND = [
    ".venv/bin/python",
    str(Path.home() / "AIOS" / "bin" / "aios.py"),
    "session-intel",
    "run",
    "--provider",
    "codex",
    "--since",
    "last",
    "--write-report",
    "--json",
]
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

NATIVE_COMMAND_SAFETY_CLASSES = {
    "zoom-out": "read_only",
    "handoff": "artifact_write",
    "review-squad": "read_only",
    "audit-security": "read_only",
    "cleanup-de-slopify": "guarded_modify",
    "prototype": "sandbox_write",
}
ATTENTION_RUN_STATUSES = [
    "blocked",
    "waiting_for_user",
    "waiting_for_tool",
    "failed_validation",
    "partial",
    "needs_follow_up",
]
TERMINAL_RUN_STATUSES = [
    "partial",
    "needs_follow_up",
    "completed",
    "failed",
    "canceled",
    "superseded",
]
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


def _parse_json_value(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _parse_review_plan_evidence(raw: str) -> tuple[dict[str, Any], ...]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CLIError(
            "invalid-evidence-json",
            f"--evidence-json must be valid JSON: {exc.msg}",
            EXIT_USAGE,
        ) from exc
    if isinstance(parsed, dict):
        return (parsed,)
    if isinstance(parsed, list) and all(isinstance(item, dict) for item in parsed):
        return tuple(parsed)
    raise CLIError(
        "invalid-evidence-json",
        "--evidence-json must be a JSON object or an array of objects.",
        EXIT_USAGE,
    )


def _tmcp_review_plan_payload(args: argparse.Namespace) -> dict[str, Any]:
    run_id = f"tmcp-review-plan-{uuid.uuid4().hex[:8]}"
    project_path = Path(args.project_path).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    evidence_items = _parse_review_plan_evidence(args.evidence_json)
    packet = compile_tmcp_packet(
        objective=args.objective,
        project_path=str(project_path),
        phase="planning",
    )
    report = execute_workflow(
        WorkflowExecutionContext(
            objective=args.objective,
            workflow_key="expert_rubric_remediation_v1",
            repo_path=str(output_dir),
            run_id=run_id,
            tmcp_packet=packet,
            evidence_items=evidence_items,
            selected_slice_id=args.selected_slice_id,
        )
    )
    artifacts = report["artifacts"]
    remediation_plan = artifacts.get("expert_remediation_plan")
    remediation_slices = (
        remediation_plan.get("slices", []) if isinstance(remediation_plan, dict) else []
    )
    return {
        "schema": "aios-tmcp-review-plan-result-v0.1",
        "workflow_key": report["workflow_key"],
        "run_id": report["run_id"],
        "status": report["status"],
        "validations": report["validations"],
        "artifact_paths": artifacts.get("expert_review_artifact_paths", {}),
        "remediation_slices": remediation_slices,
        "implementation_handoff": artifacts.get("expert_implementation_handoff"),
    }


def _gate_adoption_plan_payload(args: argparse.Namespace) -> dict[str, Any]:
    run_id = args.run_id or f"repo-gate-adoption-{uuid.uuid4().hex[:8]}"
    repo_root = Path(args.repo_root).expanduser().resolve()
    report = execute_workflow(
        WorkflowExecutionContext(
            objective=(
                args.objective
                or "Create a repo quality gate adoption readiness matrix and rollout plan"
            ),
            workflow_key="repo_gate_adoption_v1",
            repo_path=str(repo_root),
            run_id=run_id,
        )
    )
    artifacts = report["artifacts"]
    gate_matrix = artifacts.get("repo_gate_matrix")
    rollout_plan = artifacts.get("repo_gate_rollout_plan")
    return {
        "schema": "aios-repo-gate-adoption-result-v0.1",
        "workflow_key": report["workflow_key"],
        "run_id": report["run_id"],
        "status": report["status"],
        "validations": report["validations"],
        "artifact_paths": artifacts.get("repo_gate_adoption_artifact_paths", {}),
        "gate_summary": gate_matrix.get("summary", {}) if isinstance(gate_matrix, dict) else {},
        "phase_scope_policy": rollout_plan.get("phase_scope_policy", "")
        if isinstance(rollout_plan, dict)
        else "",
        "phase_owner": rollout_plan.get("phase_owner", "")
        if isinstance(rollout_plan, dict)
        else "",
        "aios_role": rollout_plan.get("aios_role", "") if isinstance(rollout_plan, dict) else "",
        "repo_local_phases": rollout_plan.get("repo_local_phases", [])
        if isinstance(rollout_plan, dict)
        else [],
        "rollout_phases": rollout_plan.get("phases", []) if isinstance(rollout_plan, dict) else [],
    }


def _gate_adoption_doc_quality_payload(args: argparse.Namespace) -> dict[str, Any]:
    adoption_payload = _gate_adoption_plan_payload(args)
    artifact_paths = adoption_payload.get("artifact_paths")
    artifact_paths = artifact_paths if isinstance(artifact_paths, dict) else {}
    manifest_raw = artifact_paths.get("rubric_detail_manifest_json")
    output_dir = (
        Path(str(manifest_raw)).parent if manifest_raw else Path(args.repo_root).expanduser()
    )
    quality_paths = write_adoption_doc_quality_report(output_dir)
    quality_report = json.loads(
        quality_paths["adoption_doc_quality_json"].read_text(encoding="utf-8")
    )
    merged_artifact_paths = {
        **artifact_paths,
        **{key: str(path) for key, path in quality_paths.items()},
    }
    return {
        "schema": "aios-repo-gate-adoption-doc-quality-result-v0.1",
        "workflow_key": adoption_payload["workflow_key"],
        "run_id": adoption_payload["run_id"],
        "status": quality_report.get("status", "unknown"),
        "passed": quality_report.get("passed", False),
        "structurally_valid": quality_report.get("structurally_valid", False),
        "ready_for_phase_planning": quality_report.get("ready_for_phase_planning", False),
        "ready_for_execution": quality_report.get("ready_for_execution", False),
        "validations": adoption_payload["validations"],
        "artifact_paths": merged_artifact_paths,
        "gate_summary": adoption_payload["gate_summary"],
        "doc_quality": quality_report,
    }


def _resolve_route_project_override(
    conn: sqlite3.Connection, raw_project: str | None
) -> str | None:
    if raw_project is None:
        return None
    raw_project = raw_project.strip()
    if not raw_project:
        return None
    if not _table_exists(conn, "projects"):
        return raw_project
    rows = conn.execute(
        """
        SELECT id, name
        FROM projects
        WHERE status = 'active'
        ORDER BY name
        """
    ).fetchall()
    normalized = raw_project.lower()
    for row in rows:
        if normalized in {str(row["id"]).lower(), str(row["name"]).lower()}:
            return str(row["id"])
    return raw_project


def _route_next_fix(route_payload: dict[str, Any]) -> str | None:
    if route_payload.get("status") == "ready":
        return None
    project = route_payload.get("project") if isinstance(route_payload.get("project"), dict) else {}
    candidates = project.get("candidates") if isinstance(project, dict) else []
    if isinstance(candidates, list) and candidates:
        return "Pass --project with one of the candidate project ids."
    if isinstance(project, dict) and project.get("outcome") == "unsupported":
        return "Register the project in AIOS or run from a registered project workspace."
    return "Refine the objective so a governed workflow can be selected."


def _route_preview_payload(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    explicit_project_id = _resolve_route_project_override(conn, args.project)
    cwd = str(Path(args.cwd).expanduser().resolve()) if args.cwd else None
    route = route_objective(
        conn,
        objective=args.objective,
        surface=args.surface,
        cwd=cwd,
        explicit_project_id=explicit_project_id,
    )
    route_payload = route.to_json()
    project_payload = route_payload["project"]
    project_candidates = project_payload["candidates"]
    selected_project_id = project_payload["selected_project_id"]
    selected_project = next(
        (candidate for candidate in project_candidates if candidate["id"] == selected_project_id),
        None,
    )
    start_work_command = None
    if route_payload["status"] == "ready" and selected_project_id:
        start_work_command = [
            "aios",
            "start-work",
            args.objective,
            "--project",
            selected_project_id,
        ]
    return {
        "schema": "aios-route-preview-v0.1",
        "status": route_payload["status"],
        "objective": args.objective,
        "surface": args.surface,
        "cwd": cwd,
        "selected_project": selected_project,
        "selected_workflow": route_payload["selected_workflow"],
        "recommended_agent": route_payload["agent_recommendation"],
        "backend_recommendation": route_payload["backend_recommendation"],
        "prompt_recommendation": route_payload["prompt_recommendation"],
        "task_family": route_payload["task_family"],
        "blocked_reason": route_payload["blocked_reason"],
        "next_fix": _route_next_fix(route_payload),
        "start_work_command": start_work_command,
        "project_candidates": project_candidates,
        "workflow_candidates": route_payload["workflow_candidates"],
        "workflow_alternatives": route_payload["workflow_alternatives"],
        "skill_recommendations": route_payload["skill_recommendations"],
        "route": route_payload,
    }


def _add_expert_rubric_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("objective", help="Natural language review objective")
    parser.add_argument(
        "--project-path",
        default=".",
        help="Target project path used for TMCP packet compilation",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where review artifacts will be written",
    )
    parser.add_argument(
        "--evidence-json",
        default="[]",
        help="JSON object or array of evidence objects",
    )
    parser.add_argument(
        "--selected-slice-id",
        default=None,
        help="Optional remediation slice id to include in the implementation handoff",
    )
    parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS)


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
        str(item.get("id", "")) for item in criteria if isinstance(item, dict) and item.get("id")
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
        str(item.get("key", "")) for item in workflows if isinstance(item, dict) and item.get("key")
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
        "standard_count": len(
            [item for item in standards if isinstance(item, dict) and item.get("id")]
        ),
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
        "selected_criteria_json": "TEXT DEFAULT '[]'",
        "selected_standards_json": "TEXT DEFAULT '[]'",
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


def _recent_writeback_rows(
    conn: sqlite3.Connection, project_id: str | None, limit: int = 5
) -> list[dict[str, Any]]:
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
        return [
            "Workflow stages unavailable; use the routed workflow key as the governing contract."
        ]

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
    return lines or [
        "Workflow stages unavailable; use the routed workflow key as the governing contract."
    ]


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


def _planning_governance_sections(route_payload: dict[str, Any]) -> list[dict[str, Any]]:
    workflow = route_payload.get("selected_workflow")
    if not isinstance(workflow, dict) or workflow.get("workflow_key") != "planning-governance":
        return []

    selection = select_planning_lenses(workflow="planning-governance", phase="plan")
    lens_lines = [
        f"{lens.key}: {lens.purpose} Standards: {', '.join(lens.standard_refs) or 'none'}."
        for lens in selection.lenses
    ]
    candidate = next(
        (
            row
            for row in route_payload.get("workflow_candidates", [])
            if isinstance(row, dict) and row.get("workflow_key") == "planning-governance"
        ),
        {},
    )
    detection_rationale = str(candidate.get("rationale", "")).strip()

    return [
        {
            "title": "Planning Quality Contract",
            "items": [
                "Do not start implementation as the first action.",
                "Create planning artifacts that preserve scope, non-goals, standards, and verification before execution begins.",
                "Carry acceptance criteria, evidence expectations, and closeout rules into the executable plan.",
            ]
            + ([f"Route evidence: {detection_rationale}"] if detection_rationale else []),
        },
        {
            "title": "Required Planning Artifacts",
            "items": [
                "GSD-compatible PLAN.md or equivalent planning contract.",
                "Task-level acceptance criteria and validation commands.",
                "Evidence expectations for route decisions, changed artifacts, and final verification.",
                "Truth-file and SUMMARY.md writeback plan after evidence exists.",
            ],
        },
        {
            "title": "Standards Before Execution",
            "items": lens_lines
            or [
                "No planning lenses were selected; escalate before execution because standards are missing."
            ],
        },
        {
            "title": "Verification Handoff",
            "items": [
                "Hand off only after the plan names automated checks or explicit human verification.",
                "Verifier must inspect actual artifacts and command output, not just summary claims.",
                "Blockers, warnings, and accepted tradeoffs must remain visible in durable artifacts.",
            ],
        },
    ]


def _required_check_lines(
    workflow_contract: dict[str, Any] | None,
    criteria_rows: Sequence[dict[str, Any]],
) -> list[str]:
    lines: list[str] = []
    if workflow_contract is not None:
        validations = workflow_contract.get("required_validations") or []
        if isinstance(validations, list) and validations:
            lines.append("Workflow validations: " + ", ".join(str(item) for item in validations))
    blocker_ids = [
        str(row.get("id")) for row in criteria_rows if row.get("blocking") and row.get("id")
    ]
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


def _next_recommended_action(workflow_key: str) -> str:
    if workflow_key == "planning-governance":
        return (
            "Create planning artifacts from this packet, preserve standards-before-execution, "
            "and hand off only after verification commands are explicit."
        )
    return (
        "Start the routed runtime with this packet and keep run/invocation/session linkage intact."
    )


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

    sections.extend(_planning_governance_sections(route_payload))

    sections.append(
        {
            "title": "Applicable Success Criteria",
            "items": _criteria_instruction_lines(
                criteria_rows if isinstance(criteria_rows, list) else []
            ),
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
            raise CLIError(
                "session-not-found", f"Session not found: {linked_session_id}", EXIT_NOT_FOUND
            )
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
            raise CLIError(
                "session-not-found", f"Session not found: {linked_session_id}", EXIT_NOT_FOUND
            )
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
    if route.selected_workflow is None or route.agent_recommendation is None:
        raise CLIError(
            "route-incomplete", "Routing did not select a workflow and agent.", EXIT_RUNTIME
        )

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
    next_recommended_action = _next_recommended_action(workflow_key)
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
            json.dumps(
                [
                    "Current implementation sessions should attach via explicit run/invocation/session handshake."
                ]
            ),
            json.dumps(
                [
                    {"source": "success-criteria", "reason": "criteria preview added to packet"},
                    {"source": "active-rules", "reason": "approved rules added to packet"},
                    {
                        "source": "improvement-writebacks",
                        "reason": "recent improvements added to packet",
                    },
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
                    "next_recommended_action": next_recommended_action,
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
            "next_recommended_action": next_recommended_action,
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
        unsupported_states.update(
            status for status in event_states if status not in canonical_statuses
        )

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
            "source_ref_coverage": round(objects_with_sources / object_count, 4)
            if object_count
            else 0.0,
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
    row = conn.execute(
        f"SELECT COUNT(*) AS count FROM {table} WHERE run_id = ?", (run_id,)
    ).fetchone()
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


def _inferred_learning_evidence(
    conn: sqlite3.Connection, run: dict[str, Any]
) -> dict[str, Any] | None:
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
    if run.get("status") in {"failed", "canceled"} and (
        linked_artifacts > 0 or success_evaluations > 0
    ):
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
    columns = {
        str(row["name"])
        for row in conn.execute("PRAGMA table_info(workflow_learning_events)").fetchall()
    }
    if "signal_kind" not in columns:
        conn.execute("ALTER TABLE workflow_learning_events ADD COLUMN signal_kind TEXT")
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_workflow_learning_events_signal
          ON workflow_learning_events(signal_kind, created_at DESC)
        """
    )


def _workflow_learning_event_exists(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    evidence_type: str,
    proposal_target: str | None,
    signal_kind: LearningSignalKind | None = None,
) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM workflow_learning_events
        WHERE run_id = ?
          AND evidence_type = ?
          AND COALESCE(proposal_target, '') = COALESCE(?, '')
          AND COALESCE(signal_kind, '') = COALESCE(?, '')
        LIMIT 1
        """,
        (run_id, evidence_type, proposal_target, signal_kind),
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
    signal_kind: LearningSignalKind | None = None,
) -> None:
    if _workflow_learning_event_exists(
        conn,
        run_id=run_id,
        evidence_type=evidence_type,
        proposal_target=proposal_target,
        signal_kind=signal_kind,
    ):
        return
    conn.execute(
        """
        INSERT INTO workflow_learning_events (
          id, run_id, evidence_type, proposal_target, confidence,
          approval_state, rationale, source_json, signal_kind, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            signal_kind,
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
    signal_kind_counts = _workflow_learning_signal_kind_counts(conn)
    recurring_patterns = _recent_recurring_patterns(conn)
    conservative_proposals = _recent_conservative_proposals(conn)
    if not _table_exists(conn, "orchestration_runs"):
        return {
            "summary": {
                "terminal_run_count": 0,
                "runs_with_learning": 0,
                "no_learning_count": 0,
                "proposal_count": 0,
                "pending_approval_count": 0,
                "recurring_pattern_count": len(recurring_patterns),
                "conservative_proposal_count": len(conservative_proposals),
                "signal_kind_counts": signal_kind_counts,
            },
            "contract": {
                "evidence_types": WORKFLOW_LEARNING_EVIDENCE_TYPES,
                "run_source": "orchestration_runs",
                "proposal_source": "improvement_writebacks",
                "signal_kinds": list(LEARNING_SIGNAL_KINDS),
                "pattern_source": "services/learning_analysis.detect_recurring_patterns",
                "conservatism_policy_source": "config/learning/conservatism-policy.json",
            },
            "classification_counts": classification_counts,
            "persisted_events": [],
            "inferred_evidence": [],
            "no_learning_runs": [],
            "proposals": [],
            "recurring_patterns": recurring_patterns,
            "conservative_proposals": conservative_proposals,
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
                source={
                    "reason": reason,
                    "status": run.get("status"),
                    "workflow_key": run.get("workflow_key"),
                },
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
                approval_state="pending"
                if writeback.get("status") == "pending_approval"
                else "not_required",
                rationale=str(
                    writeback.get("summary")
                    or writeback.get("title")
                    or "Workflow proposal evidence."
                ),
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
            SELECT run_id, evidence_type, proposal_target, confidence, approval_state,
                   rationale, source_json, signal_kind, created_at
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
            "recurring_pattern_count": len(recurring_patterns),
            "conservative_proposal_count": len(conservative_proposals),
            "signal_kind_counts": signal_kind_counts,
        },
        "contract": {
            "evidence_types": WORKFLOW_LEARNING_EVIDENCE_TYPES,
            "run_source": "orchestration_runs",
            "event_source": "workflow_learning_events",
            "proposal_source": "improvement_writebacks",
            "promotion_gate": "status + requires_approval on improvement_writebacks",
            "signal_kinds": list(LEARNING_SIGNAL_KINDS),
            "pattern_source": "services/learning_analysis.detect_recurring_patterns",
            "conservatism_policy_source": "config/learning/conservatism-policy.json",
        },
        "classification_counts": classification_counts,
        "persisted_events": persisted_event_rows[:50],
        "inferred_evidence": inferred_evidence[:50],
        "no_learning_runs": no_learning_runs[:20],
        "proposals": proposals[:50],
        "recurring_patterns": recurring_patterns,
        "conservative_proposals": conservative_proposals,
    }


def _workflow_learning_signal_kind_counts(conn: sqlite3.Connection) -> dict[str, int]:
    if not _table_exists(conn, "workflow_learning_events") or "signal_kind" not in _table_columns(
        conn, "workflow_learning_events"
    ):
        return {}
    return {
        str(row["signal_kind"]): int(row["count"] or 0)
        for row in conn.execute(
            """
            SELECT signal_kind, COUNT(*) AS count
            FROM workflow_learning_events
            WHERE signal_kind IS NOT NULL
            GROUP BY signal_kind
            """
        ).fetchall()
    }


def _recent_recurring_patterns(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    try:
        from services.learning_analysis import detect_recurring_patterns

        return [
            asdict(pattern)
            for pattern in detect_recurring_patterns(conn, since="30d", project_id=None)[:50]
        ]
    except sqlite3.OperationalError:
        return []


def _recent_conservative_proposals(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    if not _table_exists(conn, "improvement_writebacks"):
        return []
    return [
        dict(row)
        for row in conn.execute(
            """
            SELECT id, layer_type, layer_key, impact_scope, status, requires_approval,
                   proposed_change_json, created_at
            FROM improvement_writebacks
            WHERE proposed_change_json LIKE '%"source": "learning_analysis"%'
            ORDER BY created_at DESC
            LIMIT 50
            """
        ).fetchall()
    ]


def _learning_analyze_payload(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    from services.learning_analysis import detect_recurring_patterns

    signal_kinds = tuple(args.signal_kind) if args.signal_kind else None
    patterns = detect_recurring_patterns(
        conn,
        since=str(args.since),
        project_id=args.project,
        signal_kinds=signal_kinds,
    )
    return {
        "recurring_patterns": [asdict(pattern) for pattern in patterns],
        "total_patterns": len(patterns),
        "since": str(args.since),
        "project_id": args.project,
        "dry_run": bool(args.dry_run),
        "policy_version": "config/learning/conservatism-policy.json",
    }


def _learning_propose_payload(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    from services.conservative_optimizer import (
        _classify_skip_reason,
        load_conservatism_policy,
        propose_from_all_patterns,
    )
    from services.learning_analysis import detect_recurring_patterns

    patterns = detect_recurring_patterns(conn, since=str(args.since), project_id=args.project)
    policy = load_conservatism_policy()
    if bool(args.dry_run):
        would_propose = []
        would_skip = []
        for pattern in patterns:
            reason = _classify_skip_reason(conn, pattern, policy)
            if reason is None:
                would_propose.append(asdict(pattern))
            else:
                would_skip.append(
                    {
                        "pattern_id": pattern.pattern_id,
                        "signal_kind": pattern.signal_kind,
                        "reason": reason,
                    }
                )
        return {
            "proposed_count": len(would_propose),
            "skipped_count": len(would_skip),
            "writebacks": [],
            "skipped": would_skip,
            "would_propose": would_propose,
            "would_skip": would_skip,
            "dry_run": True,
        }
    result = propose_from_all_patterns(conn, patterns, policy, actor=str(args.actor))
    conn.commit()
    result["dry_run"] = False
    return result


def _learning_impact_payload(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    from services.learning_impact import build_per_run_impact, build_rollup

    if args.run_id:
        impact = build_per_run_impact(conn, run_id=str(args.run_id))
        if impact is None:
            return {"run_id": args.run_id, "found": False}
        payload = asdict(impact)
        payload["found"] = True
        return payload
    if args.workflow:
        return asdict(
            build_rollup(
                conn,
                scope="workflow",
                key=str(args.workflow),
                since=str(args.since),
                project_id=args.project,
            )
        )
    if args.prompt:
        return asdict(
            build_rollup(
                conn,
                scope="prompt",
                key=str(args.prompt),
                since=str(args.since),
                project_id=args.project,
            )
        )
    if args.skill:
        return asdict(
            build_rollup(
                conn,
                scope="skill",
                key=str(args.skill),
                since=str(args.since),
                project_id=args.project,
            )
        )
    raise CLIError(
        "missing-learning-impact-target",
        "Specify --run-id, --workflow, --prompt, or --skill",
        EXIT_USAGE,
    )


def cmd_operator_search(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    query = str(args.query)
    try:
        hits = operator_search_module.search_entities(
            conn,
            query=query,
            kinds=tuple(args.kinds) if args.kinds else None,
            project_id=args.project,
            limit=int(args.limit),
        )
    except ValueError as exc:
        raise CLIError("operator-search-invalid-query", str(exc), EXIT_USAGE) from exc
    return {
        "hits": [asdict(hit) for hit in hits],
        "total_hits": len(hits),
        "query": query,
        "kinds": list(args.kinds) if args.kinds else None,
        "project_id": args.project,
        "limit": int(args.limit),
    }


def cmd_next_action(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    try:
        actions = next_action_module.get_next_actions(
            conn,
            project_id=args.project,
            limit=int(args.limit),
        )
    except ValueError as exc:
        raise CLIError("next-action-invalid-limit", str(exc), EXIT_USAGE) from exc
    return {
        "actions": [asdict(action) for action in actions],
        "total_actions": len(actions),
        "project_id": args.project,
        "limit": int(args.limit),
    }


def cmd_daily_flow(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    if args.objective:
        trace = preview_from_objective(
            conn,
            objective=str(args.objective),
            project_id=args.project,
        )
    else:
        trace = replay_from_run(conn, run_id=str(args.run_id))
    return {
        "trace": asdict(trace),
        "is_preview": trace.is_preview,
        "objective": trace.objective,
        "project_id": trace.project_id,
        "step_count": len(trace.steps),
    }


def cmd_eval_record_run(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    try:
        run_id = create_eval_run(
            conn,
            task_id=str(args.task_id),
            condition=str(args.condition),
            mode=str(args.mode),
            harness=args.harness,
            model=args.model,
            context_profile=str(args.context_profile),
            final_status=str(args.final_status),
            duration_ms=args.duration_ms,
            total_tokens=args.tokens,
            estimated_cost_usd=args.cost,
            files_changed=args.files_changed,
        )
    except ValueError as exc:
        raise CLIError("eval-record-invalid", str(exc), EXIT_USAGE) from exc
    conn.commit()
    return {"run_id": run_id, "task_id": args.task_id, "final_status": args.final_status}


def cmd_eval_list_runs(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    try:
        runs = list_eval_runs(
            conn,
            task_id=args.task_id,
            condition=args.condition,
            context_profile=args.context_profile,
            limit=int(args.limit),
        )
    except ValueError as exc:
        raise CLIError("eval-list-invalid", str(exc), EXIT_USAGE) from exc
    return {"runs": runs, "count": len(runs), "limit": int(args.limit)}


def cmd_eval_summary(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    return get_eval_summary(conn, project_id=args.project)


def cmd_eval_second_brain_lift(
    conn: sqlite3.Connection, args: argparse.Namespace
) -> dict[str, Any]:
    return compute_second_brain_lift(
        conn,
        full_run_id=str(args.full_run_id),
        repo_only_run_id=str(args.repo_only_run_id),
    )


def cmd_eval_retrieval_metrics(
    conn: sqlite3.Connection, args: argparse.Namespace
) -> dict[str, Any]:
    return compute_retrieval_metrics(conn, str(args.run_id))


def cmd_eval_gold_set_run(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    return evaluate_gold_set_run(
        conn,
        run_id=str(args.run_id),
        gold_task_id=str(args.gold_task_id),
    )


def _read_humanize_input(args: argparse.Namespace) -> str:
    sources = [
        bool(args.text),
        bool(args.input),
        bool(args.stdin),
    ]
    if sum(sources) != 1:
        raise CLIError(
            "humanize-input-required",
            "Specify exactly one of --text, --input, or --stdin.",
            EXIT_USAGE,
        )
    if args.text:
        return str(args.text)
    if args.stdin:
        return sys.stdin.read()
    input_path = Path(args.input).expanduser().resolve()
    try:
        return input_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise CLIError(
            "humanize-input-not-found", f"Input file not found: {input_path}", EXIT_NOT_FOUND
        ) from exc


def cmd_humanize_run(conn: sqlite3.Connection | None, args: argparse.Namespace) -> dict[str, Any]:
    text = _read_humanize_input(args)
    if not text.strip():
        raise CLIError("humanize-empty-input", "Input text is empty.", EXIT_USAGE)

    try:
        result = humanize_text(
            text,
            requested_mode=args.mode,
            pipeline_position=args.pipeline,
            debug=bool(args.debug),
        )
    except ValueError as exc:
        raise CLIError("humanize-invalid-request", str(exc), EXIT_USAGE) from exc

    output_path = Path(args.output).expanduser().resolve() if args.output else None
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result.output, encoding="utf-8")

    run_id = None
    if conn is not None and not args.no_record:
        ensure_personalized_humanizer_schema(conn)
        run_id = record_rewrite_run(conn, result, input_text=text)
        conn.commit()

    payload: dict[str, Any] = {
        "output": result.output,
        "mode": result.mode,
        "pipeline_position": result.pipeline_position,
        "changed": result.output != text,
        "scorecard": result.scorecard,
        "risks": result.risks,
        "run_id": run_id,
        "recorded": run_id is not None,
        "output_path": str(output_path) if output_path is not None else None,
    }
    if args.debug:
        payload["debug"] = result.debug
    return payload


def cmd_humanize_feedback(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    ensure_personalized_humanizer_schema(conn)
    revision_text = None
    if args.revision:
        revision_text = Path(args.revision).expanduser().resolve().read_text(encoding="utf-8")
    feedback = record_feedback(
        conn,
        run_id=str(args.run_id),
        verdict=cast(FeedbackVerdict, str(args.verdict)),
        notes=str(args.notes),
        user_revision=revision_text,
    )
    conn.commit()
    feedback["verdict"] = str(args.verdict)
    return feedback


def cmd_humanize_eval(conn: sqlite3.Connection | None, args: argparse.Namespace) -> dict[str, Any]:
    result = run_eval_suite()
    if conn is not None and args.record:
        ensure_personalized_humanizer_schema(conn)
        eval_id = record_eval_result(conn, result)
        conn.commit()
        result["eval_id"] = eval_id
        result["recorded"] = True
    else:
        result["recorded"] = False
    return result


def _meta_analyze_session_payload(args: argparse.Namespace) -> dict[str, Any]:
    input_path = Path(args.input).expanduser().resolve()
    with input_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    signals = signals_to_dicts(extract_meta_learning_signals(raw))
    return {
        "input_path": str(input_path),
        "signal_count": len(signals),
        "signals": signals,
    }


def cmd_native_zoom_out(args: argparse.Namespace) -> dict[str, Any]:
    try:
        return native_zoom_out(
            Path(args.target),
            repo_root=Path(args.repo_root).expanduser().resolve(),
            depth=max(0, int(args.depth)),
        )
    except FileNotFoundError as exc:
        raise CLIError("native-target-not-found", str(exc), EXIT_NOT_FOUND) from exc


def cmd_native_handoff(args: argparse.Namespace) -> dict[str, Any]:
    output_path = Path(args.output) if args.output else None
    try:
        return native_handoff(
            objective=args.objective,
            repo_root=Path(args.repo_root).expanduser().resolve(),
            output_path=output_path,
            decision=list(args.decision or []),
            test=list(args.test or []),
            worked=list(args.worked or []),
            failed=list(args.failed or []),
            blocker=list(args.blocker or []),
            reference=list(args.reference or []),
            next_action=list(args.next_action or []),
        )
    except ValueError as exc:
        raise CLIError("native-output-not-allowed", str(exc), EXIT_USAGE) from exc


def cmd_native_review_squad(args: argparse.Namespace) -> dict[str, Any]:
    try:
        return native_review_squad(
            repo_root=Path(args.repo_root).expanduser().resolve(),
            files=[Path(path) for path in args.file],
            base_ref=args.base,
        )
    except FileNotFoundError as exc:
        raise CLIError("native-target-not-found", str(exc), EXIT_NOT_FOUND) from exc


def cmd_native_audit_security(args: argparse.Namespace) -> dict[str, Any]:
    try:
        return native_security_audit(
            mode=args.mode,
            repo_root=Path(args.repo_root).expanduser().resolve(),
            files=[Path(path) for path in args.file],
            base_ref=args.base,
        )
    except FileNotFoundError as exc:
        raise CLIError("native-target-not-found", str(exc), EXIT_NOT_FOUND) from exc
    except ValueError as exc:
        raise CLIError("native-invalid-mode", str(exc), EXIT_USAGE) from exc


def cmd_native_cleanup_de_slopify(args: argparse.Namespace) -> dict[str, Any]:
    try:
        return native_de_slopify(
            repo_root=Path(args.repo_root).expanduser().resolve(),
            files=[Path(path) for path in args.file],
            base_ref=args.base,
            cleanup_goals=list(args.goal or []),
            apply=bool(args.apply),
        )
    except FileNotFoundError as exc:
        raise CLIError("native-target-not-found", str(exc), EXIT_NOT_FOUND) from exc


def cmd_native_prototype(args: argparse.Namespace) -> dict[str, Any]:
    try:
        return native_prototype(
            question=args.question,
            sandbox_path=Path(args.sandbox_path),
            repo_root=Path(args.repo_root).expanduser().resolve(),
            prototype_type=args.prototype_type,
            cleanup_mode=args.cleanup_mode,
        )
    except ValueError as exc:
        raise CLIError("native-prototype-path-not-allowed", str(exc), EXIT_USAGE) from exc


def _add_native_logging_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--log-metadata", action="store_true")
    parser.add_argument("--metadata-log-path", default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--session-id", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--reasoning-level", default=None)
    parser.add_argument("--token-cost-estimate", type=float, default=None)
    parser.add_argument("--runtime-ms", type=int, default=None)
    parser.add_argument("--test-run", action="append", default=[])


def _maybe_log_native_command(
    args: argparse.Namespace,
    command: str,
    data: dict[str, Any],
) -> None:
    if not getattr(args, "log_metadata", False):
        return
    repo_root = Path(getattr(args, "repo_root", ".")).expanduser().resolve()
    safety_class = NATIVE_COMMAND_SAFETY_CLASSES[command]
    record = native_command_metadata(
        command_name=command,
        repo_root=repo_root,
        scope=data.get("scope", {}),
        safety_class=safety_class,
        status="pass",
        read_only=safety_class == "read_only",
        modifying=safety_class != "read_only",
        reviewer_lanes=_native_reviewer_lanes(data),
        files_touched=_native_files_touched(data),
        tests_run=list(getattr(args, "test_run", []) or []),
        user_confirmation_required=safety_class in {"guarded_modify", "sandbox_write"},
        user_confirmation_received=bool(getattr(args, "apply", False) or command == "prototype"),
        model=args.model,
        reasoning_level=args.reasoning_level,
        token_cost_estimate=args.token_cost_estimate,
        runtime_ms=args.runtime_ms,
        run_id=args.run_id,
        session_id=args.session_id,
    )
    log_path = Path(args.metadata_log_path) if args.metadata_log_path else None
    try:
        written = write_native_command_metadata(record, repo_root=repo_root, log_path=log_path)
    except ValueError as exc:
        raise CLIError("native-metadata-log-path-not-allowed", str(exc), EXIT_USAGE) from exc
    data["metadata_log_path"] = str(written)
    data["metadata_record"] = record


def _native_reviewer_lanes(data: dict[str, Any]) -> list[str]:
    lanes = data.get("lanes")
    if isinstance(lanes, dict):
        return list(lanes)
    scope_lanes = data.get("reviewer_lanes")
    if isinstance(scope_lanes, list):
        return [str(lane) for lane in scope_lanes]
    return []


def _native_files_touched(data: dict[str, Any]) -> list[str]:
    touched = data.get("applied_changes", [])
    if not isinstance(touched, list):
        return []
    files: list[str] = []
    for item in touched:
        if isinstance(item, dict) and "file" in item:
            files.append(str(item["file"]))
        elif isinstance(item, str):
            files.append(item)
    return files


def _read_text_arg(value: str | None, file_value: str | None) -> str:
    if file_value:
        return Path(file_value).expanduser().read_text(encoding="utf-8")
    return value or ""


def cmd_context_loops_inner_run(
    conn: sqlite3.Connection,
    args: argparse.Namespace,
) -> dict[str, Any]:
    task_input = _read_text_arg(args.task_input, args.task_input_file)
    draft_output = _read_text_arg(args.draft_output, args.draft_output_file)
    context_root = Path(args.context_root).expanduser().resolve()

    def _draft(_context: object) -> str:
        return draft_output

    return create_inner_loop_run(
        conn,
        workflow=args.workflow,
        task_type=args.task_type,
        task_input=task_input,
        triggering_event=args.triggering_event,
        prompt_version=args.prompt_version,
        guidance_version=args.guidance_version,
        retrieved_context=[],
        context_sources=[],
        assumptions=list(args.assumption or []),
        draft_generator=_draft,
        handoff_notes=args.handoff_notes,
        context_loop_root=context_root,
    )


def cmd_context_loops_email_draft(
    conn: sqlite3.Connection,
    args: argparse.Namespace,
) -> dict[str, Any]:
    task_input = _read_text_arg(args.task_input, args.task_input_file)
    return create_email_draft_run(
        conn,
        task_input=task_input,
        recipient=args.recipient,
        subject=args.subject,
        context_loop_root=Path(args.context_root).expanduser().resolve(),
    )


def cmd_context_loops_record_review(
    conn: sqlite3.Connection,
    args: argparse.Namespace,
) -> dict[str, Any]:
    final_output = _read_text_arg(args.final_output, args.final_output_file)
    return record_review_event(
        conn,
        run_id=args.run_id,
        outcome=args.outcome,
        final_output=final_output if args.final_output or args.final_output_file else None,
        reviewer_notes=args.notes,
    )


def cmd_context_loops_review(
    conn: sqlite3.Connection,
    args: argparse.Namespace,
) -> dict[str, Any]:
    return propose_learning_candidates(conn, min_reviews=max(1, int(args.min_reviews)))


def cmd_context_loops_approve(
    conn: sqlite3.Connection,
    args: argparse.Namespace,
) -> dict[str, Any]:
    return approve_context_loop_candidate(
        conn,
        args.candidate_id,
        actor=args.actor,
        note=args.note,
    )


def cmd_context_loops_reject(
    conn: sqlite3.Connection,
    args: argparse.Namespace,
) -> dict[str, Any]:
    return reject_context_loop_candidate(
        conn,
        args.candidate_id,
        actor=args.actor,
        note=args.note,
        context_loop_root=Path(args.context_root).expanduser().resolve(),
    )


def cmd_context_loops_apply_approved(
    conn: sqlite3.Connection,
    args: argparse.Namespace,
) -> dict[str, Any]:
    return apply_approved_candidates(
        conn,
        context_loop_root=Path(args.context_root).expanduser().resolve(),
    )


def cmd_context_loops_metrics(
    conn: sqlite3.Connection,
    args: argparse.Namespace,
) -> dict[str, Any]:
    metrics = context_loop_metrics(conn)
    if args.write_report:
        path = write_metrics_report(
            conn,
            context_loop_root=Path(args.context_root).expanduser().resolve(),
        )
        metrics["report_path"] = str(path)
    return metrics


def cmd_shadow_create_worktree(
    conn: sqlite3.Connection, args: argparse.Namespace
) -> dict[str, Any]:
    repo_path = Path(args.repo_path).resolve()
    branch_name = shadow_branch_name(task_id=str(args.task_id), condition=str(args.condition))
    worktree_path = create_shadow_worktree(
        repo_path=repo_path,
        start_sha=str(args.start_sha),
        branch_name=branch_name,
    )
    contamination_check_passed = verify_no_contamination(
        baseline_branch=str(args.start_sha),
        shadow_branch=branch_name,
        repo_path=repo_path,
    )
    shadow_run_id = record_shadow_branch_run(
        conn,
        task_id=str(args.task_id),
        condition=str(args.condition),
        start_sha=str(args.start_sha),
        aios_branch=branch_name,
        worktree_path=worktree_path,
        no_evidence_reason=(
            "shadow worktree was created; no implementation, verification, or comparison "
            "evidence has been recorded yet"
        ),
        contamination_check_passed=contamination_check_passed,
    )
    conn.commit()
    return {
        "shadow_run_id": shadow_run_id,
        "task_id": args.task_id,
        "branch_name": branch_name,
        "worktree_path": worktree_path,
        "contamination_check_passed": contamination_check_passed,
        "parity_checklist_status": "no_evidence",
    }


def cmd_shadow_compare(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    result = compare_shadow_runs(
        conn,
        shadow_run_id=str(args.shadow_run_id),
        baseline_run_id=str(args.baseline_run_id),
    )
    conn.commit()
    return result


def _retrospective_payload(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    artifacts = list_retrospective_artifacts(conn, task_id=args.task_id)
    return {"artifacts": artifacts, "count": len(artifacts)}


def _model_selection_payload(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    records = list_model_selection_records(conn, task_id=args.task_id)
    return {"records": records, "count": len(records)}


def cmd_shadow_parity(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    rows = list_shadow_parity_metadata(conn, task_id=args.task_id)
    return {"shadow_parity": rows, "count": len(rows)}


def cmd_shadow_cleanup(args: argparse.Namespace) -> dict[str, Any]:
    cleanup_shadow_worktree(
        worktree_path=Path(args.worktree_path).resolve(),
        repo_path=Path(args.repo_path).resolve(),
    )
    return {"worktree_path": args.worktree_path, "removed": True}


def cmd_peer_trace_start(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    session_id = start_peer_session(
        conn,
        anonymous_peer_id=str(args.peer_id),
        harness_used=args.harness,
        repo_language=args.repo_language,
        repo_framework=args.repo_framework,
    )
    conn.commit()
    return {"session_id": session_id, "anonymous_peer_id": args.peer_id}


def cmd_peer_trace_stop(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    end_peer_session(conn, str(args.session_id))
    conn.commit()
    return {"session_id": args.session_id, "ended": True}


def cmd_peer_trace_list(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    sessions = list_peer_sessions(conn, limit=int(args.limit))
    return {"sessions": sessions, "count": len(sessions), "limit": int(args.limit)}


def cmd_shadow_score(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    trace_row = conn.execute(
        "SELECT * FROM peer_traces WHERE id = ? LIMIT 1",
        (str(args.trace_id),),
    ).fetchone()
    if trace_row is None:
        raise CLIError(
            "shadow-score-not-found", f"Peer trace not found: {args.trace_id}", EXIT_NOT_FOUND
        )
    trace_record = dict(trace_row)
    score = score_shadow_candidate(trace_record)
    candidate_id = f"shadow-candidate-{uuid.uuid4()}"
    now = _now_iso()
    conn.execute(
        """
        INSERT INTO shadow_candidates (
          id, peer_session_id, peer_trace_id, score, recommendation, reasons_json,
          blockers_json, automation_state, state_updated_at, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            candidate_id,
            trace_record.get("peer_session_id"),
            args.trace_id,
            score["score"],
            score["recommendation"],
            json.dumps(score["reasons"], sort_keys=True),
            json.dumps(score["blockers"], sort_keys=True),
            "TRACE_ONLY",
            now,
            now,
        ),
    )
    conn.commit()
    return {"candidate_id": candidate_id, **score}


def cmd_shadow_queue(conn: sqlite3.Connection) -> dict[str, Any]:
    rows = conn.execute(
        """
        SELECT * FROM shadow_candidates
        WHERE recommendation != 'trace_only'
        ORDER BY score DESC, created_at DESC
        """
    ).fetchall()
    candidates = []
    for row in rows:
        item = dict(row)
        item["reasons"] = json.loads(item.pop("reasons_json") or "[]")
        item["blockers"] = json.loads(item.pop("blockers_json") or "[]")
        candidates.append(item)
    return {"candidates": candidates, "count": len(candidates)}


def cmd_ablation_run(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    policy_paths: list[str | Path] = [item for item in str(args.policies).split(",") if item]
    run_ids = run_ablation_suite(
        conn,
        task_id=str(args.task_id),
        start_sha=str(args.start_sha),
        policy_paths=policy_paths,
        repo_path=Path(args.repo_path).resolve(),
        base_run_id=args.base_run_id,
    )
    conn.commit()
    return {"run_ids": run_ids, "count": len(run_ids), "task_id": args.task_id}


def cmd_ablation_compare(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    return compare_ablation_suite(
        conn,
        task_id=str(args.task_id),
        base_run_id=str(args.base_run_id),
    )


def cmd_shadow_approve(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    state = approve_candidate(conn, str(args.candidate_id))
    conn.commit()
    return {"candidate_id": args.candidate_id, "automation_state": state}


def cmd_shadow_run_pipeline(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    result = run_full_automation_pipeline(
        conn,
        candidate_id=str(args.candidate_id),
        repo_path=Path(args.repo_path).resolve(),
    )
    conn.commit()
    return result


def cmd_shadow_run(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    shadow = get_shadow_run(conn, str(args.shadow_run_id))
    objective = str(args.objective or shadow.get("task_id") or args.shadow_run_id)
    execution = launch_codex_shadow(
        conn,
        shadow_run_id=str(args.shadow_run_id),
        objective=objective,
        run_id=args.run_id,
        packet_id=args.packet_id,
        route_id=args.route_id,
    )
    conn.commit()
    return {"shadow_run_id": args.shadow_run_id, "shadow_execution": execution}


def cmd_shadow_status(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    if getattr(args, "shadow_run_id", None):
        execution = shadow_execution_status(conn, shadow_run_id=str(args.shadow_run_id))
        conn.commit()
        return {"shadow_run_id": args.shadow_run_id, "shadow_execution": execution}
    if not getattr(args, "candidate_id", None):
        raise CLIError(
            "shadow-status-target-required",
            "Provide --shadow-run-id for execution status or --candidate-id for candidate status.",
            EXIT_USAGE,
        )
    return shadow_status(conn, str(args.candidate_id))


def cmd_shadow_cancel(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    execution = cancel_shadow_execution(conn, shadow_run_id=str(args.shadow_run_id))
    conn.commit()
    return {"shadow_run_id": args.shadow_run_id, "shadow_execution": execution}


def cmd_shadow(conn: sqlite3.Connection | None, args: argparse.Namespace) -> dict[str, Any]:
    if args.shadow_command == "cleanup":
        return cmd_shadow_cleanup(args)
    if conn is None:
        raise CLIError("db-required", "Shadow command requires a SQLite database.", EXIT_USAGE)
    if args.shadow_command == "create-worktree":
        return cmd_shadow_create_worktree(conn, args)
    if args.shadow_command == "compare":
        return cmd_shadow_compare(conn, args)
    if args.shadow_command == "parity":
        return cmd_shadow_parity(conn, args)
    if args.shadow_command == "score":
        return cmd_shadow_score(conn, args)
    if args.shadow_command == "queue":
        return cmd_shadow_queue(conn)
    if args.shadow_command == "approve":
        return cmd_shadow_approve(conn, args)
    if args.shadow_command == "run-pipeline":
        return cmd_shadow_run_pipeline(conn, args)
    if args.shadow_command == "run":
        return cmd_shadow_run(conn, args)
    if args.shadow_command == "status":
        return cmd_shadow_status(conn, args)
    if args.shadow_command == "cancel":
        return cmd_shadow_cancel(conn, args)
    raise CLIError(
        "unknown-shadow-command",
        f"Unknown shadow command: {args.shadow_command}",
        EXIT_USAGE,
    )


def cmd_eval(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    if args.eval_command == "record-run":
        return cmd_eval_record_run(conn, args)
    if args.eval_command == "list-runs":
        return cmd_eval_list_runs(conn, args)
    if args.eval_command == "summary":
        return cmd_eval_summary(conn, args)
    if args.eval_command == "second-brain-lift":
        return cmd_eval_second_brain_lift(conn, args)
    if args.eval_command == "retrieval-metrics":
        return cmd_eval_retrieval_metrics(conn, args)
    if args.eval_command == "gold-set-run":
        return cmd_eval_gold_set_run(conn, args)
    raise CLIError("unknown-eval-command", f"Unknown eval command: {args.eval_command}", EXIT_USAGE)


def cmd_context_loops(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    if args.context_loops_command == "inner-run":
        data = cmd_context_loops_inner_run(conn, args)
    elif args.context_loops_command == "email-draft":
        data = cmd_context_loops_email_draft(conn, args)
    elif args.context_loops_command == "record-review":
        data = cmd_context_loops_record_review(conn, args)
    elif args.context_loops_command == "review":
        data = cmd_context_loops_review(conn, args)
    elif args.context_loops_command == "approve":
        data = cmd_context_loops_approve(conn, args)
    elif args.context_loops_command == "reject":
        data = cmd_context_loops_reject(conn, args)
    elif args.context_loops_command == "apply-approved":
        data = cmd_context_loops_apply_approved(conn, args)
    elif args.context_loops_command == "metrics":
        return cmd_context_loops_metrics(conn, args)
    else:
        raise CLIError(
            "unknown-context-loops-command",
            f"Unknown context-loops command: {args.context_loops_command}",
            EXIT_USAGE,
        )
    conn.commit()
    return data


def cmd_peer_trace(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    if args.peer_trace_command == "start":
        return cmd_peer_trace_start(conn, args)
    if args.peer_trace_command == "stop":
        return cmd_peer_trace_stop(conn, args)
    if args.peer_trace_command == "list":
        return cmd_peer_trace_list(conn, args)
    raise CLIError(
        "unknown-peer-trace-command",
        f"Unknown peer-trace command: {args.peer_trace_command}",
        EXIT_USAGE,
    )


def cmd_ablation(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    if args.ablation_command == "run":
        return cmd_ablation_run(conn, args)
    if args.ablation_command == "compare":
        return cmd_ablation_compare(conn, args)
    raise CLIError(
        "unknown-ablation-command",
        f"Unknown ablation command: {args.ablation_command}",
        EXIT_USAGE,
    )


def cmd_packet_generate(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    return generate_packet(
        conn,
        task_description=str(args.task),
        repo_path=Path(args.repo_path).resolve(),
        packet_id=args.packet_id,
    )


def _eval_task_dict(conn: sqlite3.Connection, task_id: str) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM eval_tasks WHERE id = ? LIMIT 1", (task_id,)).fetchone()
    if row is None:
        raise CLIError("eval-task-not-found", f"Eval task not found: {task_id}", EXIT_NOT_FOUND)
    return dict(row)


def cmd_benchmark_to_swe_bench(
    conn: sqlite3.Connection, args: argparse.Namespace
) -> dict[str, Any]:
    return to_swe_bench_format(_eval_task_dict(conn, str(args.task_id)))


def cmd_benchmark_to_terminal_bench(
    conn: sqlite3.Connection, args: argparse.Namespace
) -> dict[str, Any]:
    return to_terminal_bench_format(_eval_task_dict(conn, str(args.task_id)))


def cmd_benchmark_normalize_result(args: argparse.Namespace) -> dict[str, Any]:
    result = json.loads(Path(args.result_file).read_text(encoding="utf-8"))
    return normalize_external_result(
        result,
        eval_task_id=str(args.task_id),
        harness=str(args.harness),
        model=str(args.model),
    )


def _json_has_content(raw: Any) -> bool:
    if raw is None:
        return False
    try:
        parsed = json.loads(str(raw))
    except json.JSONDecodeError:
        return bool(str(raw).strip())
    return parsed not in (None, "", [], {})


def _governance_proposal_rows(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if _table_exists(conn, "improvement_writebacks"):
        rows.extend(
            {
                "id": row["id"],
                "source": "improvement_writebacks",
                "run_id": row["run_id"],
                "target_type": row["layer_type"],
                "target_key": row["layer_key"],
                "title": row["title"],
                "status": row["status"],
                "requires_approval": bool(row["requires_approval"]),
                "created_at": row["created_at"],
            }
            for row in conn.execute(
                """
                SELECT id, run_id, layer_type, layer_key, title, status, requires_approval, created_at
                FROM improvement_writebacks
                ORDER BY created_at DESC
                LIMIT 100
                """
            ).fetchall()
        )
    if _table_exists(conn, "memory_writeback_proposals"):
        rows.extend(
            {
                "id": row["id"],
                "source": "memory_writeback_proposals",
                "run_id": row["source_run_id"],
                "target_type": row["target_scope"],
                "target_key": row["proposal_type"],
                "title": row["proposal_type"],
                "status": row["status"],
                "requires_approval": row["status"] in {"proposed", "pending_approval"},
                "created_at": row["created_at"],
            }
            for row in conn.execute(
                """
                SELECT id, source_run_id, target_scope, proposal_type, status, created_at
                FROM memory_writeback_proposals
                ORDER BY created_at DESC
                LIMIT 100
                """
            ).fetchall()
        )
    if _table_exists(conn, "workflow_synthesis_proposals"):
        rows.extend(
            {
                "id": row["id"],
                "source": "workflow_synthesis_proposals",
                "run_id": None,
                "target_type": "workflow",
                "target_key": row["proposal_key"],
                "title": row["title"],
                "status": row["status"],
                "requires_approval": row["status"] == "pending_approval",
                "created_at": row["created_at"],
            }
            for row in conn.execute(
                """
                SELECT id, proposal_key, title, status, created_at
                FROM workflow_synthesis_proposals
                ORDER BY created_at DESC
                LIMIT 100
                """
            ).fetchall()
        )
    if _table_exists(conn, "promotion_lifecycle_items"):
        rows.extend(
            {
                "id": row["id"],
                "source": "promotion_lifecycle_items",
                "run_id": row["source_run_id"],
                "target_type": row["item_kind"],
                "target_key": row["item_key"],
                "title": f"{row['item_kind']}:{row['item_key']}",
                "status": row["status"],
                "requires_approval": row["status"] in {"candidate", "pending_approval", "tested"},
                "created_at": row["created_at"],
            }
            for row in conn.execute(
                """
                SELECT id, item_kind, item_key, source_run_id, status, created_at
                FROM promotion_lifecycle_items
                ORDER BY created_at DESC
                LIMIT 100
                """
            ).fetchall()
        )
    return rows


def _run_has_governance_evidence(conn: sqlite3.Connection, run_id: str) -> bool:
    checks = [
        ("improvement_writebacks", "run_id"),
        ("workflow_learning_events", "run_id"),
        ("workflow_execution_reports", "run_id"),
    ]
    for table, column in checks:
        if _table_exists(conn, table) and column in _table_columns(conn, table):
            row = conn.execute(
                f"SELECT 1 FROM {table} WHERE {column} = ? LIMIT 1", (run_id,)
            ).fetchone()
            if row is not None:
                return True
    return False


def _governance_closeout_rows(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    if not _table_exists(conn, "workflow_execution_reports"):
        return []
    closeouts: list[dict[str, Any]] = []
    rows = conn.execute(
        """
        SELECT id, run_id, workflow_key, status, report_json, created_at
        FROM workflow_execution_reports
        ORDER BY created_at DESC
        LIMIT 100
        """
    ).fetchall()
    for row in rows:
        report = _parse_json_object(row["report_json"])
        if report.get("report_type") != "governed_closeout":
            continue
        approvals_raw = report.get("approvals")
        approvals: dict[str, Any] = approvals_raw if isinstance(approvals_raw, dict) else {}
        unresolved_raw = report.get("unresolved_deltas")
        unresolved: dict[str, Any] = unresolved_raw if isinstance(unresolved_raw, dict) else {}
        closeouts.append(
            {
                "id": row["id"],
                "run_id": row["run_id"],
                "workflow_key": row["workflow_key"],
                "status": row["status"],
                "pending_approval_count": int(approvals.get("pending_approval_count") or 0),
                "has_unresolved_deltas": _json_has_content(json.dumps(unresolved, sort_keys=True)),
                "created_at": row["created_at"],
            }
        )
    return closeouts


def _governance_stage_findings(conn: sqlite3.Connection) -> dict[str, Any]:
    if not _table_exists(conn, "success_criteria_stage_findings"):
        return {
            "open_count": 0,
            "stale_open_count": 0,
            "blocker_open_count": 0,
            "recent": [],
        }
    summary = conn.execute(
        """
        SELECT
          SUM(CASE WHEN resolution_status = 'open' THEN 1 ELSE 0 END) AS open_count,
          SUM(
            CASE
              WHEN resolution_status = 'open'
               AND julianday('now') - julianday(created_at) > 14
              THEN 1 ELSE 0
            END
          ) AS stale_open_count,
          SUM(
            CASE
              WHEN resolution_status = 'open' AND level = 'blocker'
              THEN 1 ELSE 0
            END
          ) AS blocker_open_count
        FROM success_criteria_stage_findings
        """
    ).fetchone()
    recent = [
        dict(row)
        for row in conn.execute(
            """
            SELECT id, run_id, stage_key, criterion_id, level, summary, created_at
            FROM success_criteria_stage_findings
            WHERE resolution_status = 'open'
            ORDER BY created_at DESC
            LIMIT 5
            """
        ).fetchall()
    ]
    return {
        "open_count": int(summary["open_count"] or 0) if summary else 0,
        "stale_open_count": int(summary["stale_open_count"] or 0) if summary else 0,
        "blocker_open_count": int(summary["blocker_open_count"] or 0) if summary else 0,
        "recent": recent,
    }


def _standards_delta_items_for_snapshot(
    conn: sqlite3.Connection,
    snapshot_id: str,
) -> list[dict[str, Any]]:
    if not _table_exists(conn, "standards_delta_items"):
        return []
    return [
        {
            "standard_id": str(row["standard_id"]),
            "domain": str(row["domain"]),
            "status": str(row["status"]),
            "priority_bucket": str(row["priority_bucket"]),
            "priority_score": float(row["priority_score"] or 0.0),
            "remediation_playbook": _parse_json_object(row["remediation_playbook_json"]),
        }
        for row in conn.execute(
            """
            SELECT standard_id, domain, status, priority_bucket, priority_score, remediation_playbook_json
            FROM standards_delta_items
            WHERE snapshot_id = ?
            ORDER BY priority_score DESC, created_at DESC
            LIMIT 200
            """,
            (snapshot_id,),
        ).fetchall()
    ]


def _recommend_workflows_for_project(
    conn: sqlite3.Connection,
    project_id: str,
    *,
    limit: int = 5,
) -> list[dict[str, Any]]:
    snapshot = latest_snapshot(conn, project_id)
    if snapshot is None:
        return []
    delta_items = _standards_delta_items_for_snapshot(conn, str(snapshot["id"]))
    if not delta_items:
        return []
    registry_workflows = set(load_workflow_registry().keys())
    return recommend_workflow_from_health(
        delta_items=delta_items,
        registry_workflows=registry_workflows,
    )[:limit]


def _recommended_workflows_by_project(conn: sqlite3.Connection) -> dict[str, list[dict[str, Any]]]:
    if not _table_exists(conn, "standards_health_snapshots"):
        return {}
    rows = conn.execute(
        """
        SELECT project_id, MAX(created_at) AS latest_created_at
        FROM standards_health_snapshots
        GROUP BY project_id
        ORDER BY latest_created_at DESC
        LIMIT 50
        """
    ).fetchall()
    recommendations: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        project_id = str(row["project_id"])
        project_recommendations = _recommend_workflows_for_project(conn, project_id)
        if project_recommendations:
            recommendations[project_id] = project_recommendations
    return recommendations


def _governance_audit_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    proposals = _governance_proposal_rows(conn)
    pending = [
        proposal
        for proposal in proposals
        if proposal["requires_approval"]
        or proposal["status"] in {"pending", "pending_approval", "proposed"}
    ]
    terminal_runs: list[dict[str, Any]] = []
    if _table_exists(conn, "orchestration_runs"):
        placeholders = ", ".join("?" for _ in TERMINAL_RUN_STATUSES)
        terminal_runs = [
            dict(row)
            for row in conn.execute(
                f"""
                SELECT id, status, workflow_key, objective, updated_at
                FROM orchestration_runs
                WHERE status IN ({placeholders})
                ORDER BY updated_at DESC
                LIMIT 100
                """,
                tuple(TERMINAL_RUN_STATUSES),
            ).fetchall()
        ]
    missing_evidence_runs = [
        {
            "run_id": run["id"],
            "status": run.get("status"),
            "workflow_key": run.get("workflow_key"),
            "objective": run.get("objective"),
        }
        for run in terminal_runs
        if not _run_has_governance_evidence(conn, str(run["id"]))
    ]
    closeouts = _governance_closeout_rows(conn)
    unresolved_closeouts = [closeout for closeout in closeouts if closeout["has_unresolved_deltas"]]
    stage_findings = _governance_stage_findings(conn)
    recommended_workflows = _recommended_workflows_by_project(conn)

    source_counts: dict[str, int] = {}
    target_counts: dict[str, int] = {}
    for proposal in proposals:
        source_counts[proposal["source"]] = source_counts.get(proposal["source"], 0) + 1
        target_counts[proposal["target_type"]] = target_counts.get(proposal["target_type"], 0) + 1

    findings: list[dict[str, Any]] = []
    if pending:
        findings.append(
            {
                "severity": "warning",
                "code": "pending_governance_approvals",
                "summary": f"{len(pending)} proposal(s) require approval or review.",
            }
        )
    if missing_evidence_runs:
        findings.append(
            {
                "severity": "blocker",
                "code": "terminal_runs_missing_governance_evidence",
                "summary": "Terminal run(s) lack writeback, follow-up, closeout, or no-learning evidence.",
                "run_count": len(missing_evidence_runs),
            }
        )
    if not proposals:
        findings.append(
            {
                "severity": "warning",
                "code": "no_governance_proposals",
                "summary": "No cross-asset writeback or promotion proposals were found.",
            }
        )

    return {
        "summary": {
            "proposal_count": len(proposals),
            "pending_approval_count": len(pending),
            "terminal_run_count": len(terminal_runs),
            "terminal_runs_missing_evidence_count": len(missing_evidence_runs),
            "governed_closeout_count": len(closeouts),
            "unresolved_closeout_count": len(unresolved_closeouts),
            "finding_count": len(findings),
        },
        "contract": {
            "proposal_sources": [
                "improvement_writebacks",
                "memory_writeback_proposals",
                "workflow_synthesis_proposals",
                "promotion_lifecycle_items",
            ],
            "terminal_run_evidence_sources": [
                "improvement_writebacks",
                "workflow_learning_events",
                "workflow_execution_reports",
            ],
            "reviewable_target_types": [
                "truth",
                "prompt",
                "skill",
                "workflow",
                "standards",
                "packet",
                "memory",
            ],
            "meaningful_terminal_run_rule": "terminal runs need writeback, follow-up, closeout, or no-learning evidence",
        },
        "source_counts": source_counts,
        "target_counts": target_counts,
        "pending_approvals": pending[:50],
        "missing_evidence_runs": missing_evidence_runs[:50],
        "governed_closeouts": closeouts[:50],
        "stage_findings": stage_findings,
        "recommended_workflows": recommended_workflows,
        "findings": findings,
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
    if _table_exists(conn, "success_criteria_stage_findings"):
        for column, definition in {
            "resolution_status": "TEXT NOT NULL DEFAULT 'open'",
            "resolution_actor": "TEXT",
            "resolution_rationale": "TEXT",
            "resolution_evidence_json": "TEXT NOT NULL DEFAULT '[]'",
            "resolved_at": "TEXT",
        }.items():
            _ensure_column(conn, "success_criteria_stage_findings", column, definition)
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
    required_columns = {
        "id",
        "kind",
        "title",
        "summary",
        "confidence",
        "freshness",
        "canonical_href",
    }
    if not required_columns.issubset(topic_columns):
        return "partial"
    if not _table_exists(conn, "knowledge_references") or not _table_exists(
        conn, "knowledge_relationships"
    ):
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
        for table in (
            "success_criteria_findings",
            "success_criteria_stage_findings",
            "consistency_findings",
        )
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
            "status": "implemented"
            if _table_exists(conn, "workflow_learning_events")
            else "partial",
            "source": "aios workflow-learning-audit",
            "storage": "workflow_learning_events + improvement_writebacks + improvement_writeback_events",
            "table_available": _table_exists(conn, "workflow_learning_events"),
        },
        {
            "name": "LearningSignal",
            "status": "implemented" if _learning_signal_contract_implemented(conn) else "partial",
            "source": "services/learning_taxonomy.py",
            "source_of_truth": [
                "services/learning_taxonomy.py",
                "services/learning_analysis.py",
                "services/conservative_optimizer.py",
                "services/learning_impact.py",
                "config/learning/conservatism-policy.json",
                "workflow_learning_events.signal_kind",
            ],
            "storage": "workflow_learning_events.signal_kind + improvement_writebacks.proposed_change_json",
            "table_available": _table_exists(conn, "workflow_learning_events"),
            "notes": (
                "Two-axis classification with cross-run pattern detection, conservative "
                "approval-required proposals, and impact projections."
            ),
        },
        {
            "name": "OperatorSurface",
            "status": "implemented"
            if (REPO_ROOT / "aios-ui" / "server" / "aios" / "operator-search.ts").exists()
            else "partial",
            "source": "services/operator_search.py",
            "source_of_truth": [
                "services/operator_search.py",
                "services/aios_cli.py:cmd_operator_search",
            ],
            "storage": "read-only projection across existing control-plane tables",
            "table_available": True,
            "notes": (
                "Cross-entity search backend (Phase 10, Plan 01). UI mirror lands in "
                "Plan 04; tRPC router in Plan 05; UI rendering in Plan 06."
            ),
        },
        {
            "name": "NextAction",
            "status": "implemented"
            if (REPO_ROOT / "aios-ui" / "server" / "aios" / "next-action.ts").exists()
            else "partial",
            "source": "services/next_action.py",
            "source_of_truth": [
                "services/next_action.py",
                "services/aios_cli.py:cmd_next_action",
            ],
            "storage": "read-only fusion across existing control-plane tables",
            "table_available": True,
            "notes": (
                "Next-action fusion backend (Phase 10, Plan 02). Fuses health deltas, "
                "pending writebacks, open blockers, terminal-run gaps, backfill tasks, "
                "promotion candidates, and learning proposals. UI mirror lands in Plan "
                "04; tRPC router in Plan 05; rendered surfaces in Plan 06."
            ),
        },
        {
            "name": "DailyFlow",
            "status": "implemented"
            if (REPO_ROOT / "aios-ui" / "server" / "aios" / "daily-flow.ts").exists()
            else "partial",
            "source": "services/daily_flow.py",
            "source_of_truth": [
                "services/daily_flow.py",
                "services/session_intelligence_tools.py:repo_closeout_payload",
                "services/agentize.py:agentize_request(dry_run=True)",
                "services/aios_cli.py:cmd_daily_flow",
            ],
            "storage": "read-only projection across route, packet, run, repo closeout, evaluation, writeback, delta, and next-action sources",
            "table_available": True,
            "notes": (
                "Daily-flow trace backend (Phase 10, Plan 03). Preview is dry via "
                "SAVEPOINT; replay uses persisted run evidence plus read-only repo "
                "closeout state when a project repo path is known. UI mirror lands "
                "in Plan 04; tRPC router in Plan 05; DailyFlowTrace component on "
                "/runs/[id] and Command Center in Plan 06."
            ),
        },
        {
            "name": "EvaluationFinding",
            "status": _evaluation_finding_contract_status(conn),
            "source": "success_criteria_findings + consistency_findings",
            "storage": "success_criteria_findings + consistency_findings",
            "stage_evidence_table": "success_criteria_stage_findings",
            "table_available": _table_exists(conn, "success_criteria_findings")
            or _table_exists(conn, "success_criteria_stage_findings")
            or _table_exists(conn, "consistency_findings"),
            "lifecycle_states": EVALUATION_FINDING_LIFECYCLE_STATES,
        },
        {
            "name": "DeltaExplanation",
            "status": "implemented",
            "source": "services.standards_health:DeltaExplanation",
            "storage": "standards_assessments + standards_delta_items + success_criteria_findings",
            "table_available": _table_exists(conn, "standards_assessments")
            and _table_exists(conn, "standards_delta_items"),
            "contract": (
                "DeltaExplanation(standard_id, domain, status, provenance, confidence, "
                "freshness, evidence, contradiction, remediation, priority_score, priority_bucket)"
            ),
            "consumers": [
                "aios delta-explain",
                "aios-ui standards-health surface",
                "aios governance-audit recommended_workflows",
            ],
        },
        {
            "name": "AssetLifecycle",
            "status": "implemented",
            "source": "services/asset_lifecycle.py",
            "source_of_truth": [
                "services/asset_lifecycle.py",
                "config/workflows/registry.json",
                "prompts/registry.json",
                "config/workflows/skills.json",
                "promotion_lifecycle_items",
            ],
            "storage": "promotion_lifecycle_items",
            "table_available": _table_exists(conn, "promotion_lifecycle_items"),
            "notes": "Five-state lifecycle across prompts, skills, and workflows.",
        },
        {
            "name": "WorkflowComparison",
            "status": "implemented",
            "source": "services/workflow_promotion.py",
            "source_of_truth": [
                "services/workflow_promotion.py",
                "workflow_execution_reports",
                "success_criteria_stage_findings",
                "improvement_writebacks",
            ],
            "storage": "workflow_execution_reports + success_criteria_stage_findings + improvement_writebacks",
            "table_available": _table_exists(conn, "workflow_execution_reports"),
            "notes": "Stage- and run-level effectiveness comparison for workflow promotion.",
        },
    ]
    implemented_or_partial = [
        item for item in contracts if item["status"] in {"implemented", "partial"}
    ]
    return {
        "summary": {
            "canonical_contract_count": len(contracts),
            "implemented_or_partial_count": len(implemented_or_partial),
            "implemented_count": len(
                [item for item in contracts if item["status"] == "implemented"]
            ),
            "partial_count": len([item for item in contracts if item["status"] == "partial"]),
        },
        "contracts": contracts,
    }


def _learning_signal_contract_implemented(conn: sqlite3.Connection) -> bool:
    return (
        "signal_kind" in _table_columns(conn, "workflow_learning_events")
        and (REPO_ROOT / "services" / "learning_taxonomy.py").exists()
        and (REPO_ROOT / "services" / "learning_analysis.py").exists()
        and (REPO_ROOT / "services" / "conservative_optimizer.py").exists()
        and (REPO_ROOT / "services" / "learning_impact.py").exists()
        and (REPO_ROOT / "config" / "learning" / "conservatism-policy.json").exists()
    )


def _resolve_since_argument(value: str | None) -> str:
    if not value:
        return "1970-01-01T00:00:00Z"
    normalized = value.strip()
    if normalized.endswith("d") and normalized[:-1].isdigit():
        days = int(normalized[:-1])
        return (datetime.now(UTC) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return normalized


def _asset_lifecycle_list_payload(
    conn: sqlite3.Connection, args: argparse.Namespace
) -> dict[str, Any]:
    assets = list_assets(
        conn,
        kind=cast(AssetKind | None, args.kind),
        state=cast(AssetLifecycleState | None, args.state),
    )
    return {"assets": [asdict(asset) for asset in assets]}


def _asset_lifecycle_promote_payload(
    conn: sqlite3.Connection, args: argparse.Namespace
) -> dict[str, Any]:
    transition = promote_asset(
        conn,
        asset_kind=cast(AssetKind, args.kind),
        asset_key=args.key,
        from_state=cast(AssetLifecycleState, args.from_state),
        to_state=cast(AssetLifecycleState, args.to_state),
        actor=args.actor,
        rationale=args.rationale,
        evidence_ids=tuple(args.evidence_id or []),
    )
    return asdict(transition)


def _workflow_compare_payload(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    result = compare_workflow_effectiveness(
        conn,
        workflow_key=args.workflow_key,
        since=_resolve_since_argument(args.since),
    )
    return asdict(result)


def _promote_asset_payload(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    if args.kind == "workflow":
        evidence = compare_workflow_effectiveness(
            conn,
            workflow_key=args.key,
            since=_resolve_since_argument(args.since),
        )
        return propose_workflow_promotion(
            conn,
            workflow_key=args.key,
            to_state=cast(AssetLifecycleState, args.to_state),
            evidence=evidence,
            actor=args.actor,
            rationale=args.rationale,
        )
    transition = promote_asset(
        conn,
        asset_kind=cast(AssetKind, args.kind),
        asset_key=args.key,
        from_state=cast(AssetLifecycleState, args.from_state),
        to_state=cast(AssetLifecycleState, args.to_state),
        actor=args.actor,
        rationale=args.rationale,
        evidence_ids=tuple(args.evidence_id or []),
    )
    return asdict(transition)


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
            "proposal_sources": [
                "workflow_execution_reports.report_json",
                "orchestration_runs.resume_snapshot_json",
            ],
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


def _doctor_check(
    check_id: str,
    status: str,
    summary: str,
    remediation: str | None = None,
    **metadata: Any,
) -> dict[str, Any]:
    return {
        "id": check_id,
        "status": status,
        "summary": summary,
        "remediation": remediation,
        "metadata": metadata,
    }


def _doctor_dependency_check(module_name: str, package_label: str) -> dict[str, Any]:
    spec = importlib.util.find_spec(module_name)
    if spec is None:
        return _doctor_check(
            f"python_dependency_{module_name}",
            "fail",
            f"{package_label} is not importable from the current Python environment.",
            f"Run `uv sync` in {REPO_ROOT} or invoke AIOS through `uv run python bin/aios.py`.",
        )
    return _doctor_check(
        f"python_dependency_{module_name}",
        "pass",
        f"{package_label} is importable.",
        origin=str(spec.origin) if spec.origin else None,
    )


def _doctor_sqlite_check(db_path: Path) -> dict[str, Any]:
    if not db_path.exists():
        return _doctor_check(
            "sqlite_db",
            "fail",
            f"SQLite database does not exist at {db_path}.",
            "Run the AIOS DB initialization or point --db at an existing AIOS database.",
            path=str(db_path),
        )
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("SELECT 1").fetchone()
            required_tables = ("projects", "orchestration_runs", "briefing_packets")
            missing_tables = [table for table in required_tables if not _table_exists(conn, table)]
        finally:
            conn.close()
    except sqlite3.Error as exc:
        return _doctor_check(
            "sqlite_db",
            "fail",
            f"SQLite database is not readable: {exc}",
            "Repair the DB path or restore a valid AIOS SQLite database.",
            path=str(db_path),
        )
    if missing_tables:
        return _doctor_check(
            "sqlite_db",
            "fail",
            f"SQLite database is reachable but missing required tables: {', '.join(missing_tables)}.",
            "Run AIOS schema initialization or migrations before daily use.",
            path=str(db_path),
            missing_tables=missing_tables,
        )
    return _doctor_check("sqlite_db", "pass", "SQLite database is reachable.", path=str(db_path))


def _doctor_directory_check(check_id: str, path: Path, label: str) -> dict[str, Any]:
    if path.exists() and path.is_dir():
        return _doctor_check(check_id, "pass", f"{label} exists.", path=str(path))
    return _doctor_check(
        check_id,
        "fail",
        f"{label} does not exist at {path}.",
        f"Create {path} or pass the correct path with the relevant CLI flag.",
        path=str(path),
    )


def _doctor_package_manager_check(root: Path, label: str, check_id: str) -> dict[str, Any]:
    package_json = root / "package.json"
    pnpm_lock = root / "pnpm-lock.yaml"
    package_lock = root / "package-lock.json"
    if not package_json.exists():
        return _doctor_check(
            check_id,
            "warning",
            f"{label} has no package.json; JavaScript checks are not available.",
            None,
            path=str(root),
        )
    try:
        package_data = json.loads(package_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return _doctor_check(
            check_id,
            "fail",
            f"{label} package.json is not valid JSON: {exc.msg}.",
            f"Repair {package_json}.",
            path=str(package_json),
        )
    package_manager = str(package_data.get("packageManager", ""))
    failures: list[str] = []
    if not package_manager.startswith("pnpm@"):
        failures.append("packageManager must start with pnpm@")
    if not pnpm_lock.exists():
        failures.append("pnpm-lock.yaml is missing")
    if package_lock.exists():
        failures.append("package-lock.json is present")
    if failures:
        remediation_parts = []
        if package_lock.exists():
            remediation_parts.append(f"Remove {package_lock.relative_to(REPO_ROOT)}")
        if not pnpm_lock.exists():
            remediation_parts.append(f"run `pnpm install` in {root.relative_to(REPO_ROOT)}")
        if not package_manager.startswith("pnpm@"):
            remediation_parts.append(
                f"set packageManager to pnpm in {package_json.relative_to(REPO_ROOT)}"
            )
        return _doctor_check(
            check_id,
            "fail",
            f"{label} package-manager contract failed: {', '.join(failures)}.",
            "; ".join(remediation_parts) + ".",
            path=str(root),
            package_manager=package_manager or None,
            has_pnpm_lock=pnpm_lock.exists(),
            has_package_lock=package_lock.exists(),
        )
    return _doctor_check(
        check_id,
        "pass",
        f"{label} uses pnpm only.",
        path=str(root),
        package_manager=package_manager,
    )


def _doctor_context_compiler_contract_check() -> dict[str, Any]:
    package_json = REPO_ROOT / "package.json"
    if not package_json.exists():
        return _doctor_check(
            "context_compiler_contract",
            "warning",
            "Root package.json is missing; context compiler package access was not checked.",
            None,
        )
    try:
        package_data = json.loads(package_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return _doctor_check(
            "context_compiler_contract",
            "fail",
            f"Root package.json is not valid JSON: {exc.msg}.",
            "Repair package.json before running context compiler checks.",
        )
    dependencies = package_data.get("dependencies", {})
    has_dependency = isinstance(dependencies, dict) and "context-compiler-contract" in dependencies
    installed_path = REPO_ROOT / "node_modules" / "context-compiler-contract"
    if has_dependency and installed_path.exists():
        return _doctor_check(
            "context_compiler_contract",
            "pass",
            "context-compiler-contract is declared and installed.",
            dependency=str(dependencies["context-compiler-contract"]),
            installed_path=str(installed_path),
        )
    status = "fail" if has_dependency else "warning"
    summary = (
        "context-compiler-contract is declared but not installed."
        if has_dependency
        else "context-compiler-contract is not declared in root package.json."
    )
    remediation = "Run `pnpm install` at the AIOS repo root." if has_dependency else None
    return _doctor_check(
        "context_compiler_contract",
        status,
        summary,
        remediation,
        dependency=dependencies.get("context-compiler-contract")
        if isinstance(dependencies, dict)
        else None,
        installed_path=str(installed_path),
    )


def _doctor_audit_surface_check() -> dict[str, Any]:
    required_commands = {
        "contracts-audit",
        "capability-audit",
        "invocation-audit",
        "lifecycle-audit",
        "daily-flow",
        "next-action",
        "start-work",
    }
    parser = create_parser()
    subparser_action = next(
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    )
    missing = sorted(required_commands - set(subparser_action.choices))
    if missing:
        return _doctor_check(
            "audit_command_surface",
            "fail",
            f"Required daily-use commands are missing: {', '.join(missing)}.",
            "Restore the daily-use CLI commands before release.",
            missing_commands=missing,
        )
    return _doctor_check(
        "audit_command_surface",
        "pass",
        "Daily-use and audit command surfaces are registered.",
        commands=sorted(required_commands),
    )


def _doctor_payload(
    *,
    db_path: Path,
    logs_dir: Path,
    config_root: Path,
    vault_root: Path,
) -> dict[str, Any]:
    checks = [
        _doctor_dependency_check("quality_evidence_contract", "quality-evidence-contract"),
        _doctor_dependency_check("repo_quality_certifier", "repo-quality-certifier"),
        _doctor_context_compiler_contract_check(),
        _doctor_sqlite_check(db_path),
        _doctor_directory_check("logs_dir", logs_dir, "Logs directory"),
        _doctor_directory_check("vault_root", vault_root, "Vault root"),
        _doctor_directory_check("config_root", config_root, "Config root"),
        _doctor_package_manager_check(REPO_ROOT, "AIOS root", "root_package_manager"),
        _doctor_package_manager_check(REPO_ROOT / "aios-ui", "AIOS UI", "ui_package_manager"),
        _doctor_audit_surface_check(),
    ]
    failed = [check for check in checks if check["status"] == "fail"]
    warnings = [check for check in checks if check["status"] == "warning"]
    return {
        "schema": "aios-doctor-v0.1",
        "ok": not failed,
        "summary": {
            "status": "pass" if not failed else "fail",
            "pass_count": len([check for check in checks if check["status"] == "pass"]),
            "warning_count": len(warnings),
            "fail_count": len(failed),
        },
        "daily_use_loop": [
            "doctor",
            "start-work",
            "daily-flow --run-id",
            "next-action --project",
            "closeout evidence",
        ],
        "checks": checks,
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
    current_session = (
        current_session_path.read_text(encoding="utf-8").strip()
        if current_session_path.exists()
        else None
    )
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
            "aios governance-audit --json",
            "aios standards-resolution preview --json",
            "aios criteria-finding resolve --json --id <finding> --status accepted",
            "aios delta-explain --json --project <project>",
            "aios recommend-workflow --json --project <project>",
            "aios standards-override --json --project <project> --standard <standard> --status pass --rationale <reason>",
            "aios logs --json --last 50",
            "aios recent-failures --json --last 20",
            "aios rtk --json",
            'aios start-work --json "objective"',
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
        reduction = (
            round(max(0, raw_tokens - compressed_tokens) / raw_tokens * 100, 2)
            if raw_tokens
            else 0.0
        )
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


def _criteria_finding_resolve_payload(
    conn: sqlite3.Connection, args: argparse.Namespace
) -> dict[str, Any]:
    evidence = [str(item) for item in (args.evidence or [])]
    try:
        result = resolve_finding(
            conn,
            finding_id=str(args.id),
            status=str(args.status),
            actor=str(args.actor),
            rationale=args.rationale,
            evidence=evidence,
        )
        conn.commit()
        return result
    except ValueError as exc:
        raise CLIError("finding-resolution-failed", str(exc), EXIT_USAGE) from exc


def _standards_resolution_preview_payload(
    conn: sqlite3.Connection,
    args: argparse.Namespace,
) -> dict[str, Any]:
    return resolve_task_standards(
        conn=conn,
        project_id=args.project_id,
        project_name=args.project_name,
        objective=args.objective,
        prompt_classifications=args.classification,
        changed_files=args.changed_file,
        skills=args.skill,
        workflow_key=args.workflow_key,
    )


def _delta_explain_payload(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    snapshot = latest_snapshot(conn, str(args.project_id))
    explanations = project_delta_explanations(conn, str(args.project_id))
    return {
        "project_id": str(args.project_id),
        "snapshot_id": snapshot["id"] if snapshot else None,
        "delta_explanations": [asdict(explanation) for explanation in explanations],
    }


def _recommend_workflow_payload(
    conn: sqlite3.Connection, args: argparse.Namespace
) -> dict[str, Any]:
    limit = max(1, min(int(args.limit), 10))
    return {
        "project_id": str(args.project_id),
        "recommendations": _recommend_workflows_for_project(
            conn,
            str(args.project_id),
            limit=limit,
        ),
    }


def _standards_override_payload(
    conn: sqlite3.Connection, args: argparse.Namespace
) -> dict[str, Any]:
    _, standards = load_standards_registry()
    known_standard_ids = {standard.id for standard in standards}
    standard_id = str(args.standard)
    if standard_id not in known_standard_ids:
        raise CLIError(
            "unknown-standard",
            f"Unknown standards registry id: {standard_id}",
            EXIT_USAGE,
        )
    status = str(args.status)
    valid_statuses = {"pass", "partial", "fail", "unknown", "waived", "not_applicable"}
    if status not in valid_statuses:
        raise CLIError("invalid-status", f"Invalid standards override status: {status}", EXIT_USAGE)
    rationale = str(args.rationale or "").strip()
    if status == "waived" and not rationale:
        raise CLIError(
            "missing-rationale", "--rationale is required for waived standards", EXIT_USAGE
        )
    confidence = max(0.0, min(1.0, float(args.confidence)))
    reason = rationale or f"Operator override via aios standards-override at {_now_iso()}"
    override: ManualAssessmentOverride = {
        "status": cast(AssessmentStatus, status),
        "reason": reason,
        "evidence": [str(item) for item in (args.evidence or [])],
        "confidence": confidence,
    }
    if status == "waived":
        override["waiver_rationale"] = reason
        override["waiver_owner"] = str(args.actor)
        if args.waiver_review_at:
            override["waiver_review_at"] = str(args.waiver_review_at)
    result = persist_manual_override(
        conn,
        project_id=str(args.project_id),
        standard_id=standard_id,
        override=override,
        actor=str(args.actor),
    )
    conn.commit()
    return result


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
        print(
            f"attention={summary['attention_count']} unsupported={summary['unsupported_state_count']}"
        )
        return
    if command == "knowledge-objects":
        summary = data["summary"]
        print(
            f"objects={summary['object_count']} source_ref_coverage={summary['source_ref_coverage']}"
        )
        return
    if command == "workflow-learning-audit":
        summary = data["summary"]
        print(
            f"terminal_runs={summary['terminal_run_count']} no_learning={summary['no_learning_count']}"
        )
        return
    if command == "session-intel-run":
        summary = data["summary"]
        print(
            f"sources={summary['source_count']} sessions={summary['session_count']} "
            f"candidates={summary['candidate_count']} report={data.get('report_path') or 'none'}"
        )
        return
    if command == "session-intel-daily-codex":
        summary = data["summary"]
        report_paths = data["report_paths"]
        print(
            f"sources={summary['source_count']} sessions={summary['session_count']} "
            f"candidates={summary['candidate_count']} "
            f"report={report_paths['markdown']} "
            f"json={report_paths['json']} "
            f"decision={report_paths['decision']}"
        )
        return
    if command == "session-intel-backfill":
        summary = data["summary"]
        print(
            f"providers={summary['provider_count']} "
            f"processed={summary['processed_source_count']} "
            f"skipped={summary['skipped_source_count']} "
            f"batches={summary['batch_count']} "
            f"candidates={summary['candidate_count']}"
        )
        return
    if command == "session-intel-candidates":
        print(f"candidates={data['count']}")
        return
    if command == "session-intel-clusters":
        print(f"clusters={data['count']}")
        return
    if command == "session-intel-mark":
        print(f"candidate={data['id']} status={data['status']}")
        return
    if command == "repo-inspect":
        git_info = data["git"]
        print(
            f"repo={data['repo']['root']} branch={git_info['branch'] or 'unknown'} "
            f"dirty={git_info['dirty']}"
        )
        return
    if command == "quality-ladder":
        print(f"profile={data['profile']} steps={len(data['steps'])} mode=plan_only")
        return
    if command == "ship-guard":
        decision = data["decision"]
        print(f"ready={decision['ready']} blockers={len(decision['blockers'])}")
        return
    if command == "service-probe":
        print(f"probes={len(data['probes'])}")
        return
    if command == "workflow-skill-codex":
        print(f"skill={data['skill']['name']} review_gated={data['promotion']['review_gated']}")
        return
    if command == "planning-state":
        decision = data["decision"]
        print(f"ready={decision['ready_for_agent_work']} blockers={len(decision['blockers'])}")
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
    if command == "governance-audit":
        summary = data["summary"]
        print(
            f"proposals={summary['proposal_count']} "
            f"pending={summary['pending_approval_count']} "
            f"missing_evidence={summary['terminal_runs_missing_evidence_count']}"
        )
        return
    if command == "criteria-finding-resolve":
        print(f"{data['finding_id']} {data['previous_status']}->{data['new_status']}")
        return
    if command == "standards-resolution-preview":
        print(
            f"criteria={len(data['criteria'])} standards={len(data['standards'])} "
            f"status={data['resolution_status']}"
        )
        return
    if command == "delta-explain":
        print(f"project={data['project_id']} explanations={len(data['delta_explanations'])}")
        return
    if command.startswith("context-loops-"):
        if "run_id" in data:
            print(
                f"run={data['run_id']} workflow={data.get('workflow', 'unknown')} "
                f"unsupported={len(data.get('unsupported_claims', []))}"
            )
            return
        if "review_event_id" in data:
            print(
                f"review={data['review_event_id']} outcome={data['outcome']} "
                f"edit_distance={data['edit_distance_ratio']}"
            )
            return
        if "proposed_count" in data:
            print(f"proposed={data['proposed_count']}")
            return
        if "applied_count" in data:
            print(f"applied={data['applied_count']} path={data['approved_lessons_path']}")
            return
        if "inner_loop_runs" in data:
            print(
                f"runs={data['inner_loop_runs']} drafts={data['drafts_created']} "
                f"avg_edit={data['average_edit_distance']}"
            )
            return
        if "candidate_id" in data:
            print(f"candidate={data['candidate_id']} status={data['status']}")
            return
    if command == "recommend-workflow":
        print(f"project={data['project_id']} recommendations={len(data['recommendations'])}")
        return
    if command == "standards-override":
        print(f"{data['project_id']} {data['standard_id']}={data['status']}")
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
    if command == "skills-harvest":
        summary = data["summary"]
        git_data = data.get("git", {})
        print(
            f"sources={summary['candidate_count']} "
            f"skills={summary['skill_count']} "
            f"instructions={summary['project_instruction_count'] + summary['global_instruction_count']} "
            f"conflicts={summary['conflict_count']} "
            f"validation={data['validation']['status']} "
            f"committed={git_data.get('committed', False)} "
            f"pushed={git_data.get('pushed', False)}"
        )
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
    if command == "eval-record-run":
        print(f"run={data['run_id']} task={data['task_id']} status={data['final_status']}")
        return
    if command == "eval-list-runs":
        print(f"runs={data['count']} limit={data['limit']}")
        return
    if command == "eval-summary":
        print(f"runs={data['run_count']} average_score={data['average_score']}")
        return
    if command == "eval-second-brain-lift":
        print(f"available={data['available']} overall_lift={data.get('overall_lift')}")
        return
    if command == "eval-retrieval-metrics":
        print(f"retrievals={data['count_total']} precision={data['precision']}")
        return
    if command == "eval-gold-set-run":
        print(f"recall={data['recall']} missed_sources={len(data['missed_sources'])}")
        return
    if command == "humanize-run":
        if data.get("output_path"):
            print(
                f"run={data.get('run_id') or 'unrecorded'} "
                f"changed={data['changed']} output={data['output_path']}"
            )
        else:
            print(data["output"])
        return
    if command == "humanize-feedback":
        proposal = data.get("proposal") if isinstance(data.get("proposal"), dict) else None
        print(
            f"feedback={data['feedback_id']} verdict={data['verdict']} "
            f"proposal={proposal.get('id') if proposal else 'none'}"
        )
        return
    if command == "humanize-eval":
        summary = data["summary"]
        print(
            f"cases={summary['case_count']} passed={summary['passed_count']} "
            f"recorded={data.get('recorded', False)}"
        )
        return
    if command == "meta-analyze-session":
        print(f"signals={data['signal_count']} input={data['input_path']}")
        return
    if command == "route":
        if data["status"] == "ready":
            project = data["selected_project"] or {}
            workflow = data["selected_workflow"] or {}
            agent = data["recommended_agent"] or {}
            backend = data["backend_recommendation"] or {}
            prompt = data["prompt_recommendation"] or {}
            workflow_label = workflow.get("workflow_key")
            if workflow.get("name"):
                workflow_label = f"{workflow_label} ({workflow['name']})"
            print("status=ready")
            print(f"project={project.get('name')} ({project.get('id')})")
            print(
                f"workflow={workflow_label} "
                f"family={workflow.get('workflow_family') or data.get('task_family')}"
            )
            print(f"agent={agent.get('agent_key')}")
            print(
                f"backend={backend.get('selected_backend_key')} "
                f"surface={backend.get('selected_surface') or data.get('surface')}"
            )
            print(f"prompt={prompt.get('prompt_family')}")
            print(f"run={shlex.join(data['start_work_command'])}")
            return
        print("status=blocked")
        print(f"reason={data['blocked_reason']}")
        print(f"next={data['next_fix']}")
        for candidate in data["project_candidates"]:
            print(
                f"candidate={candidate['id']} {candidate['name']} "
                f"score={candidate['score']} match={candidate['match_kind']}"
            )
        return
    if command in {
        "zoom-out",
        "handoff",
        "review-squad",
        "audit-security",
        "cleanup-de-slopify",
        "prototype",
    }:
        print(data["markdown"])
        return
    if command == "shadow-create-worktree":
        print(f"shadow_run={data['shadow_run_id']} branch={data['branch_name']}")
        return
    if command == "shadow-compare":
        print(f"shadow_run={data['shadow_run_id']} delta={data['delta']}")
        return
    if command == "shadow-cleanup":
        print(f"worktree={data['worktree_path']} removed={data['removed']}")
        return
    if command == "shadow-score":
        print(f"candidate={data['candidate_id']} score={data['score']}")
        return
    if command == "shadow-queue":
        print(f"candidates={data['count']}")
        return
    if command == "peer-trace-start":
        print(f"session={data['session_id']} peer={data['anonymous_peer_id']}")
        return
    if command == "peer-trace-stop":
        print(f"session={data['session_id']} ended={data['ended']}")
        return
    if command == "peer-trace-list":
        print(f"sessions={data['count']} limit={data['limit']}")
        return
    if command == "ablation-run":
        print(f"runs={data['count']} task={data['task_id']}")
        return
    if command == "ablation-compare":
        print(f"conditions={len(data['feature_lift'])} task={data['task_id']}")
        return
    if command == "shadow-approve":
        print(f"candidate={data['candidate_id']} state={data['automation_state']}")
        return
    if command == "shadow-run-pipeline":
        print(f"candidate={data['candidate_id']} state={data['final_state']}")
        return
    if command == "shadow-status":
        print(f"candidate={data['candidate_id']} state={data['automation_state']}")
        return
    if command == "packet-generate":
        print(f"packet={data['packet_id']} files={len(data['included_files'])}")
        return
    if command.startswith("benchmark-"):
        print(json.dumps(data, sort_keys=True))
        return
    if command == "gate-run":
        print(f"status={data['status']} gate={data['gateId']} summary={data['summary']}")
        return
    if command == "repo-closeout":
        git_data = data["git"]
        diff_stat = data["diff_stat"]
        print("AIOS Repo Closeout")
        print(f"repo: {data['repo']}")
        print(f"branch: {git_data['branch'] or 'unknown'}")
        print(f"head: {git_data['head'] or 'unknown'}")
        print(f"dirty: {str(git_data['dirty']).lower()}")
        print("dirty_files:")
        for line in git_data["dirty_files"]:
            print(line)
        print("diff_stat:")
        for line in diff_stat["lines"]:
            print(line)
        print("recent_commits:")
        for commit in git_data["recent_commits"]:
            print(commit["title"])
        return


def _command_name(args: argparse.Namespace) -> str:
    if args.command == "eval":
        return f"eval-{args.eval_command}"
    if args.command == "humanize":
        return f"humanize-{args.humanize_command}"
    if args.command == "meta":
        return f"meta-{args.meta_command}"
    if args.command == "review":
        return f"review-{args.review_command}"
    if args.command == "audit":
        return f"audit-{args.audit_command}"
    if args.command == "cleanup":
        return f"cleanup-{args.cleanup_command}"
    if args.command == "shadow":
        return f"shadow-{args.shadow_command}"
    if args.command == "peer-trace":
        return f"peer-trace-{args.peer_trace_command}"
    if args.command == "ablation":
        return f"ablation-{args.ablation_command}"
    if args.command == "packet":
        return f"packet-{args.packet_command}"
    if args.command == "benchmark":
        return f"benchmark-{args.benchmark_command}"
    if args.command == "context-loops":
        return f"context-loops-{args.context_loops_command}"
    if args.command == "session-intel":
        return f"session-intel-{args.session_intel_command}"
    if args.command == "repo":
        return f"repo-{args.repo_command}"
    if args.command == "quality":
        return f"quality-{args.quality_command}"
    if args.command == "ship":
        return f"ship-{args.ship_command}"
    if args.command == "service":
        return f"service-{args.service_command}"
    if args.command == "workflow-skill":
        return f"workflow-skill-{args.workflow_skill_command}"
    if args.command == "planning":
        return f"planning-{args.planning_command}"
    if args.command == "gate":
        return f"gate-{args.gate_command}"
    if args.command == "skills":
        return f"skills-{args.skills_command}"
    if args.command == "tmcp":
        return f"tmcp-{args.tmcp_command}"
    if args.command == "corpus":
        return f"corpus-{args.corpus_command}"
    if args.command == "harness-eval":
        return f"harness-eval-{args.harness_eval_command}"
    if args.command == "criteria-finding":
        return f"criteria-finding-{args.criteria_finding_command}"
    if args.command == "standards-resolution":
        return f"standards-resolution-{args.standards_resolution_command}"
    return args.command


def _command_requires_db(args: argparse.Namespace) -> bool:
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
        "retrospectives",
        "model-selection",
        "route",
        "evidence",
        "verifier",
        "learning-analyze",
        "learning-propose",
        "learning-impact",
        "operator-search",
        "next-action",
        "daily-flow",
        "session-intel",
        "contracts-audit",
        "governance-audit",
        "criteria-finding",
        "standards-resolution",
        "delta-explain",
        "recommend-workflow",
        "standards-override",
        "asset-lifecycle",
        "workflow-compare",
        "promote-asset",
        "truth-audit",
        "prove-project-health",
        "sync-automation-history",
        "start-work",
        "harness-brief",
        "harness-simulate",
        "harness-replay",
        "harness-shadow-evaluate",
        "eval",
        "context-loops",
        "shadow",
        "peer-trace",
        "ablation",
        "packet",
        "benchmark",
    }:
        return True
    return bool(
        args.command == "humanize"
        and (
            args.humanize_command == "feedback"
            or (args.humanize_command == "eval" and args.record)
            or (args.humanize_command == "run" and not args.no_record)
        )
    )


def _evidence_payload(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    run_id = str(args.run_id).strip() if args.run_id else None
    session_id = str(args.session_id).strip() if args.session_id else None
    return {
        "artifacts": list_evidence_artifacts(
            conn,
            run_id=run_id,
            session_id=session_id,
            limit=max(1, int(args.limit)),
        ),
        "validation": validate_fresh_evidence(conn, run_id=run_id, session_id=session_id),
    }


def _verifier_payload(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    run_id = str(args.run_id).strip() if args.run_id else None
    session_id = str(args.session_id).strip() if args.session_id else None
    workflow_key = str(args.workflow_key).strip() if args.workflow_key else None
    artifacts = list_verifier_artifacts(
        conn,
        run_id=run_id,
        session_id=session_id,
        limit=max(1, int(args.limit)),
    )
    validation = None
    if workflow_key:
        validation = validate_closeout_verification(
            conn,
            task_id=run_id or session_id,
            run_id=run_id,
            session_id=session_id,
            workflow_key=workflow_key,
            implementation_bearing=bool(args.implementation_bearing),
            verification_exempt=bool(args.verification_exempt),
            exemption_reason=args.exemption_reason,
        )
    return {"artifacts": artifacts, "validation": validation}


def _workflow_gates_payload(args: argparse.Namespace) -> dict[str, Any]:
    workflows = load_workflow_registry()
    rows = workflow_stage_gate_report(workflows)
    if args.workflow:
        rows = [row for row in rows if row["workflow_key"] == args.workflow]
    return {"gates": rows, "count": len(rows)}


def _session_intel_payload(conn: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    if args.session_intel_command == "run":
        report_root = Path(args.report_root).expanduser() if args.report_root else None
        provider = _session_intel_provider(args.provider, source_root=args.source_root)
        return run_session_intelligence(
            conn,
            provider=provider,
            options=SessionIntelligenceOptions(
                since=args.since,
                lane=args.lane,
                write_report=bool(args.write_report),
                report_root=report_root,
                config_path=Path(getattr(args, "config_root", DEFAULT_CONFIG_ROOT)).expanduser()
                / "session-provider-config.yaml",
            ),
        )
    if args.session_intel_command == "daily-codex":
        report_root_arg = getattr(args, "report_root", None)
        source_root_arg = getattr(args, "source_root", None)
        report_root = Path(report_root_arg).expanduser() if report_root_arg else None
        provider = _session_intel_provider("codex", source_root=source_root_arg)
        result = run_session_intelligence(
            conn,
            provider=provider,
            options=SessionIntelligenceOptions(
                since="last",
                lane="all",
                write_report=True,
                report_root=report_root,
                config_path=Path(getattr(args, "config_root", DEFAULT_CONFIG_ROOT)).expanduser()
                / "session-provider-config.yaml",
            ),
        )
        return {
            **result,
            "scanned_range": "last",
            "review_only": True,
            "wrapped_command": list(DAILY_CODEX_SESSION_INTEL_COMMAND),
            "report_paths": {
                "markdown": result["report_path"],
                "json": result["report_json_path"],
                "decision": result["decision_report_path"],
            },
        }
    if args.session_intel_command == "backfill":
        report_root = Path(args.report_root).expanduser() if args.report_root else None
        providers = _session_intel_providers(args)
        provider_results = [
            run_session_intelligence_backfill(
                conn,
                provider=provider,
                options=SessionIntelligenceBackfillOptions(
                    since=args.since,
                    lane=args.lane,
                    batch_size=args.batch_size,
                    write_report=bool(args.write_report),
                    report_root=report_root,
                    config_path=Path(getattr(args, "config_root", DEFAULT_CONFIG_ROOT)).expanduser()
                    / "session-provider-config.yaml",
                ),
            )
            for provider in providers
        ]
        return {
            "summary": {
                "provider_count": len(provider_results),
                "eligible_source_count": sum(
                    result["summary"]["eligible_source_count"] for result in provider_results
                ),
                "processed_source_count": sum(
                    result["summary"]["processed_source_count"] for result in provider_results
                ),
                "skipped_source_count": sum(
                    result["summary"]["skipped_source_count"] for result in provider_results
                ),
                "batch_count": sum(result["summary"]["batch_count"] for result in provider_results),
                "session_count": sum(
                    result["summary"]["session_count"] for result in provider_results
                ),
                "candidate_count": sum(
                    result["summary"]["candidate_count"] for result in provider_results
                ),
            },
            "providers": provider_results,
            "report_paths": [
                path for result in provider_results for path in result["report_paths"]
            ],
            "report_json_paths": [
                path for result in provider_results for path in result["report_json_paths"]
            ],
        }
    if args.session_intel_command == "candidates":
        candidates = list_session_intelligence_candidates(
            conn,
            status=None if args.status == "all" else args.status,
            lane=args.lane,
        )
        return {"count": len(candidates), "candidates": candidates}
    if args.session_intel_command == "clusters":
        status = None if args.status == "all" else args.status
        total_clusters = list_session_intelligence_clusters(
            conn,
            status=status,
            lane=args.lane,
        )
        clusters = list_session_intelligence_clusters(
            conn,
            status=status,
            lane=args.lane,
            limit=args.limit,
        )
        return {"count": len(clusters), "total_count": len(total_clusters), "clusters": clusters}
    if args.session_intel_command == "implement":
        result = implement_session_intelligence_candidates(
            conn,
            status=args.status,
            lane=args.lane,
            actor_note=args.note,
        )
        implementations = list_session_intelligence_implementations(conn)
        return {**result, "implementations": implementations}
    if args.session_intel_command == "mark":
        return mark_session_intelligence_candidate(
            conn,
            candidate_id=args.candidate_id,
            status=args.status,
            note=args.note,
        )
    if args.session_intel_command == "helper":
        if args.session_intel_helper_command == "list":
            helpers = list_session_intelligence_helpers(conn)
            return {"count": len(helpers), "helpers": helpers}
        if args.session_intel_helper_command == "run":
            return run_session_intelligence_helper(
                conn,
                family=args.family,
                path=args.path,
                repo=args.repo,
                start_line=args.start_line,
                end_line=args.end_line,
            )
    raise CLIError(
        "unsupported-session-intel-command",
        f"Unsupported session-intel command: {args.session_intel_command}",
        EXIT_USAGE,
    )


def _repo_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.repo_command == "inspect":
        return repo_inspect_payload(
            Path(args.repo),
            include_processes=bool(args.include_processes),
        )
    if args.repo_command == "closeout":
        return repo_closeout_payload(Path(args.repo), commit_limit=int(args.commits))
    raise CLIError(
        "unsupported-repo-command", f"Unsupported repo command: {args.repo_command}", EXIT_USAGE
    )


def _quality_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.quality_command == "ladder":
        return quality_ladder_payload(Path(args.repo), profile=args.profile)
    raise CLIError(
        "unsupported-quality-command",
        f"Unsupported quality command: {args.quality_command}",
        EXIT_USAGE,
    )


def _ship_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.ship_command == "guard":
        return ship_guard_payload(Path(args.repo))
    raise CLIError(
        "unsupported-ship-command", f"Unsupported ship command: {args.ship_command}", EXIT_USAGE
    )


def _service_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.service_command == "probe":
        return service_probe_payload(ports=args.port, names=args.name)
    raise CLIError(
        "unsupported-service-command",
        f"Unsupported service command: {args.service_command}",
        EXIT_USAGE,
    )


def _workflow_skill_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.workflow_skill_command == "codex":
        return codex_workflow_skill_payload()
    raise CLIError(
        "unsupported-workflow-skill-command",
        f"Unsupported workflow-skill command: {args.workflow_skill_command}",
        EXIT_USAGE,
    )


def _planning_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.planning_command == "state":
        return planning_state_payload(Path(args.repo))
    raise CLIError(
        "unsupported-planning-command",
        f"Unsupported planning command: {args.planning_command}",
        EXIT_USAGE,
    )


def _session_intel_provider(
    provider_name: str,
    *,
    source_root: str | None = None,
) -> ClaudeProvider | CodexProvider:
    root = Path(source_root).expanduser() if source_root else None
    if provider_name == "codex":
        return CodexProvider(source_root=root, db_path=DEFAULT_DB_PATH)
    if provider_name == "claude":
        return ClaudeProvider(source_root=root, db_path=DEFAULT_DB_PATH)
    raise CLIError(
        "unsupported-session-intel-provider",
        f"Unsupported session intelligence provider: {provider_name}",
        EXIT_USAGE,
    )


def _session_intel_providers(args: argparse.Namespace) -> list[ClaudeProvider | CodexProvider]:
    if args.provider == "all":
        return [
            CodexProvider(
                source_root=Path(args.codex_source_root).expanduser()
                if args.codex_source_root
                else None,
                db_path=DEFAULT_DB_PATH,
            ),
            ClaudeProvider(
                source_root=Path(args.claude_source_root).expanduser()
                if args.claude_source_root
                else None,
                db_path=DEFAULT_DB_PATH,
            ),
        ]
    return [
        _session_intel_provider(
            args.provider,
            source_root=args.source_root,
        )
    ]


def _dx_pack_report_template() -> dict[str, Any]:
    return {
        "title": "Developer Experience Pack Implementation Report",
        "format": "markdown",
        "sections": list(DX_PACK_IMPLEMENTATION_REPORT_SECTIONS),
        "markdown": "\n".join(
            [
                "## Developer Experience Pack Implementation Report",
                "",
                *[f"### {section}\n" for section in DX_PACK_IMPLEMENTATION_REPORT_SECTIONS],
            ]
        ).rstrip(),
    }


def _dx_pack_payload(args: argparse.Namespace) -> dict[str, Any]:
    payload = developer_experience_capability_report(load_developer_experience_capability_pack())
    if bool(getattr(args, "report_template", False)):
        payload["implementation_report_template"] = _dx_pack_report_template()
    return payload


def _run_corpus_command(command: str, passthrough_args: Sequence[str]) -> int:
    script = REPO_ROOT / "scripts" / "aios-corpus-eval.cjs"
    if command == "run":
        argv = ["node", str(script), *passthrough_args]
    elif command == "report":
        argv = ["node", str(script), "--report-only", *passthrough_args]
    else:
        raise CLIError(
            "unknown-corpus-command", f"Unsupported corpus command: {command}", EXIT_USAGE
        )
    try:
        completed = subprocess.run(argv, check=False)
    except FileNotFoundError as exc:
        raise CLIError(
            "node-not-found", "Node.js is required for corpus evaluation", EXIT_DEPENDENCY
        ) from exc
    return int(completed.returncode)


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AIOS unified JSON-first CLI")
    parser.add_argument("--json", action="store_true", help="Emit JSON envelope")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="SQLite database path")
    parser.add_argument("--logs-dir", default=str(DEFAULT_LOGS_DIR), help="Logs directory")
    parser.add_argument(
        "--config-root", default=str(DEFAULT_CONFIG_ROOT), help="Config root directory"
    )
    parser.add_argument("--vault-root", default=None, help="Override vault root path")

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Compact control-plane status snapshot")
    subparsers.add_parser("health", help="Health summary with status + log file checks")
    subparsers.add_parser("doctor", help="Daily-use release-readiness preflight")

    metadata_parser = subparsers.add_parser("metadata", help="One-shot metadata snapshot")
    metadata_parser.add_argument("--project", default=None, help="Optional project id filter")

    session_intel = subparsers.add_parser(
        "session-intel", help="Run and review Codex session intelligence candidates"
    )
    session_intel_subparsers = session_intel.add_subparsers(
        dest="session_intel_command", required=True
    )
    session_intel_run = session_intel_subparsers.add_parser(
        "run", help="Analyze new Codex sessions and emit review-gated candidates"
    )
    session_intel_run.add_argument("--provider", choices=["codex", "claude"], default="codex")
    session_intel_run.add_argument("--since", default="last")
    session_intel_run.add_argument(
        "--lane",
        choices=["all", "friction_tool", "workflow_skill", "impact_idea"],
        default="all",
    )
    session_intel_run.add_argument("--write-report", action="store_true")
    session_intel_run.add_argument("--source-root", default=None)
    session_intel_run.add_argument("--report-root", default=None)
    session_intel_run.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    session_intel_daily_codex = session_intel_subparsers.add_parser(
        "daily-codex",
        help="Run the daily review-only Codex session intelligence report wrapper",
    )
    session_intel_daily_codex.add_argument(
        "--json", action="store_true", default=argparse.SUPPRESS
    )

    session_intel_backfill = session_intel_subparsers.add_parser(
        "backfill", help="Backfill historical Codex and Claude sessions in resumable batches"
    )
    session_intel_backfill.add_argument(
        "--provider", choices=["codex", "claude", "all"], default="all"
    )
    session_intel_backfill.add_argument("--since", default="all")
    session_intel_backfill.add_argument(
        "--lane",
        choices=["all", "friction_tool", "workflow_skill", "impact_idea"],
        default="all",
    )
    session_intel_backfill.add_argument("--batch-size", type=int, default=250)
    session_intel_backfill.add_argument("--write-report", action="store_true")
    session_intel_backfill.add_argument("--source-root", default=None)
    session_intel_backfill.add_argument("--codex-source-root", default=None)
    session_intel_backfill.add_argument("--claude-source-root", default=None)
    session_intel_backfill.add_argument("--report-root", default=None)
    session_intel_backfill.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    session_intel_candidates = session_intel_subparsers.add_parser(
        "candidates", help="List review-gated session intelligence candidates"
    )
    session_intel_candidates.add_argument(
        "--status",
        choices=[
            "all",
            "pending_review",
            "approved",
            "implemented",
            "rejected",
            "observed",
            "superseded",
        ],
        default="pending_review",
    )
    session_intel_candidates.add_argument(
        "--lane",
        choices=["all", "friction_tool", "workflow_skill", "impact_idea"],
        default="all",
    )
    session_intel_candidates.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    session_intel_clusters = session_intel_subparsers.add_parser(
        "clusters", help="Group candidates into reviewable triage clusters"
    )
    session_intel_clusters.add_argument(
        "--status",
        choices=[
            "all",
            "pending_review",
            "approved",
            "implemented",
            "rejected",
            "observed",
            "superseded",
        ],
        default="pending_review",
    )
    session_intel_clusters.add_argument(
        "--lane",
        choices=["all", "friction_tool", "workflow_skill", "impact_idea"],
        default="all",
    )
    session_intel_clusters.add_argument("--limit", type=int, default=50)
    session_intel_clusters.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    session_intel_implement = session_intel_subparsers.add_parser(
        "implement",
        help="Adopt session intelligence candidates as telemetry-tracked helper families",
    )
    session_intel_implement.add_argument(
        "--status",
        choices=["all", "pending_review", "approved", "implemented", "observed", "superseded"],
        default="pending_review",
    )
    session_intel_implement.add_argument(
        "--lane",
        choices=["all", "friction_tool", "workflow_skill", "impact_idea"],
        default="all",
    )
    session_intel_implement.add_argument("--note", default="")
    session_intel_implement.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    session_intel_mark = session_intel_subparsers.add_parser(
        "mark", help="Mark a session intelligence candidate review status"
    )
    session_intel_mark.add_argument("--candidate-id", required=True)
    session_intel_mark.add_argument(
        "--status",
        choices=["approved", "implemented", "rejected", "observed", "superseded"],
        required=True,
    )
    session_intel_mark.add_argument("--note", default="")
    session_intel_mark.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    session_intel_helper = session_intel_subparsers.add_parser(
        "helper", help="Run deterministic helper-family surfaces for adopted candidates"
    )
    session_intel_helper_subparsers = session_intel_helper.add_subparsers(
        dest="session_intel_helper_command", required=True
    )
    session_intel_helper_list = session_intel_helper_subparsers.add_parser(
        "list", help="List adopted deterministic helper families"
    )
    session_intel_helper_list.add_argument(
        "--json", action="store_true", default=argparse.SUPPRESS
    )
    session_intel_helper_run = session_intel_helper_subparsers.add_parser(
        "run", help="Run one deterministic helper family"
    )
    session_intel_helper_run.add_argument(
        "--family", choices=SESSION_INTEL_HELPER_FAMILIES, required=True
    )
    session_intel_helper_run.add_argument("--path", default=None)
    session_intel_helper_run.add_argument("--repo", default=None)
    session_intel_helper_run.add_argument("--start-line", type=int, default=None)
    session_intel_helper_run.add_argument("--end-line", type=int, default=None)
    session_intel_helper_run.add_argument(
        "--json", action="store_true", default=argparse.SUPPRESS
    )

    repo_parser = subparsers.add_parser("repo", help="Deterministic repository inspection tools")
    repo_subparsers = repo_parser.add_subparsers(dest="repo_command", required=True)
    repo_inspect = repo_subparsers.add_parser("inspect", help="Inspect repo state and context")
    repo_inspect.add_argument("--repo", default=".", help="Repository path")
    repo_inspect.add_argument(
        "--include-processes",
        action="store_true",
        help="Include default local service probes",
    )
    repo_inspect.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    repo_closeout = repo_subparsers.add_parser(
        "closeout",
        help="Print deterministic Codex repo-state closeout",
    )
    repo_closeout.add_argument("--repo", default=".", help="Repository path")
    repo_closeout.add_argument(
        "--commits",
        type=int,
        default=5,
        help="Number of recent commits to include",
    )
    repo_closeout.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    quality_parser = subparsers.add_parser("quality", help="Quality ladder planning tools")
    quality_subparsers = quality_parser.add_subparsers(dest="quality_command", required=True)
    quality_ladder = quality_subparsers.add_parser(
        "ladder", help="Plan project-aware quality commands without running them"
    )
    quality_ladder.add_argument("--repo", default=".", help="Repository path")
    quality_ladder.add_argument(
        "--profile",
        choices=["auto", "python", "javascript", "mixed"],
        default="auto",
        help="Quality command profile",
    )
    quality_ladder.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    ship_parser = subparsers.add_parser("ship", help="Review-gated shipping tools")
    ship_subparsers = ship_parser.add_subparsers(dest="ship_command", required=True)
    ship_guard = ship_subparsers.add_parser(
        "guard", help="Inspect commit/publish readiness without mutating git state"
    )
    ship_guard.add_argument("--repo", default=".", help="Repository path")
    ship_guard.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    service_parser = subparsers.add_parser("service", help="Local service diagnostics")
    service_subparsers = service_parser.add_subparsers(dest="service_command", required=True)
    service_probe = service_subparsers.add_parser("probe", help="Probe local ports and processes")
    service_probe.add_argument("--port", type=int, action="append", default=None)
    service_probe.add_argument("--name", action="append", default=None)
    service_probe.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    workflow_skill_parser = subparsers.add_parser(
        "workflow-skill", help="Review-gated workflow skill promotion candidates"
    )
    workflow_skill_subparsers = workflow_skill_parser.add_subparsers(
        dest="workflow_skill_command", required=True
    )
    workflow_skill_codex = workflow_skill_subparsers.add_parser(
        "codex", help="Render the Codex tier-one workflow skill candidate"
    )
    workflow_skill_codex.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    planning_parser = subparsers.add_parser("planning", help="Planning and truth-state tools")
    planning_subparsers = planning_parser.add_subparsers(dest="planning_command", required=True)
    planning_state = planning_subparsers.add_parser(
        "state", help="Inspect planning and PROJECT_TRUTH readiness"
    )
    planning_state.add_argument("--repo", default=".", help="Repository path")
    planning_state.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    logs_parser = subparsers.add_parser("logs", help="Read AIOS logs")
    logs_parser.add_argument("--source", action="append", default=[], help="Log source filter")
    logs_parser.add_argument("--last", type=int, default=50, help="Last N log lines")

    failures_parser = subparsers.add_parser(
        "recent-failures", help="Recent failures across control-plane surfaces"
    )
    failures_parser.add_argument("--last", type=int, default=20, help="Max failures to return")

    subparsers.add_parser("rtk", help="RTK compression rules and metrics")
    subparsers.add_parser(
        "capability-audit", help="Trusted-signal audit for core AIOS capability surfaces"
    )
    subparsers.add_parser("invocation-audit", help="Invocation backend and strict-handshake audit")
    subparsers.add_parser(
        "lifecycle-audit", help="Run lifecycle state contract and attention-state audit"
    )
    subparsers.add_parser(
        "knowledge-objects", help="Knowledge object contract and provenance audit"
    )
    subparsers.add_parser(
        "workflow-learning-audit", help="Workflow learning evidence and proposal audit"
    )
    workflow_gates = subparsers.add_parser(
        "workflow-gates", help="Inspect deterministic workflow stage gate metadata"
    )
    workflow_gates.add_argument("--workflow", default=None)
    workflow_gates.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    retrospective_parser = subparsers.add_parser(
        "retrospectives", help="Inspect structured retrospective artifacts"
    )
    retrospective_parser.add_argument("--task-id", default=None)
    retrospective_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    model_selection_parser = subparsers.add_parser(
        "model-selection", help="Inspect model-selection telemetry records"
    )
    model_selection_parser.add_argument("--task-id", default=None)
    model_selection_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    dx_pack = subparsers.add_parser(
        "dx-pack", help="Inspect Developer Experience capability pack metadata"
    )
    dx_pack.add_argument(
        "--report-template",
        action="store_true",
        help="Include the standard DX pack implementation report format",
    )
    dx_pack.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    evidence_parser = subparsers.add_parser(
        "evidence", help="Inspect durable command evidence artifacts"
    )
    evidence_parser.add_argument("--run-id", default=None)
    evidence_parser.add_argument("--session-id", default=None)
    evidence_parser.add_argument("--limit", type=int, default=50)
    evidence_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    verifier_parser = subparsers.add_parser("verifier", help="Inspect durable verifier artifacts")
    verifier_parser.add_argument("--run-id", default=None)
    verifier_parser.add_argument("--session-id", default=None)
    verifier_parser.add_argument("--workflow-key", default=None)
    verifier_parser.add_argument("--implementation-bearing", action="store_true")
    verifier_parser.add_argument("--verification-exempt", action="store_true")
    verifier_parser.add_argument("--exemption-reason", default=None)
    verifier_parser.add_argument("--limit", type=int, default=50)
    verifier_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    learning_analyze = subparsers.add_parser(
        "learning-analyze", help="Analyze recurring learning patterns"
    )
    learning_analyze.add_argument("--since", default="30d")
    learning_analyze.add_argument("--project", default=None)
    learning_analyze.add_argument("--signal-kind", action="append", default=[])
    learning_analyze.add_argument("--json", action="store_true")
    learning_analyze.add_argument("--dry-run", action="store_true")

    learning_propose = subparsers.add_parser(
        "learning-propose", help="Create governed proposals from recurring learning patterns"
    )
    learning_propose.add_argument("--since", default="30d")
    learning_propose.add_argument("--project", default=None)
    learning_propose.add_argument("--actor", default="operator-cli")
    learning_propose.add_argument("--json", action="store_true")
    learning_propose.add_argument("--dry-run", action="store_true")

    learning_impact = subparsers.add_parser(
        "learning-impact", help="Project per-run or per-asset learning impact"
    )
    learning_impact_target = learning_impact.add_mutually_exclusive_group(required=True)
    learning_impact_target.add_argument("--run-id", default=None)
    learning_impact_target.add_argument("--workflow", default=None)
    learning_impact_target.add_argument("--prompt", default=None)
    learning_impact_target.add_argument("--skill", default=None)
    learning_impact.add_argument("--since", default="30d")
    learning_impact.add_argument("--project", default=None)
    learning_impact.add_argument("--json", action="store_true")

    operator_search = subparsers.add_parser(
        "operator-search", help="Search across operator-visible AIOS entities"
    )
    operator_search.add_argument("--query", required=True)
    operator_search.add_argument(
        "--kinds",
        action="append",
        default=[],
        choices=operator_search_module.ENTITY_KINDS,
    )
    operator_search.add_argument("--project", default=None)
    operator_search.add_argument("--limit", type=int, default=operator_search_module.DEFAULT_LIMIT)
    operator_search.add_argument("--json", action="store_true")

    next_action = subparsers.add_parser("next-action", help="Rank fused next actions")
    next_action.add_argument("--project", default=None)
    next_action.add_argument("--limit", type=int, default=next_action_module.DEFAULT_LIMIT)
    next_action.add_argument("--json", action="store_true")

    daily_flow = subparsers.add_parser("daily-flow", help="Preview or replay daily-flow trace")
    daily_flow_mode = daily_flow.add_mutually_exclusive_group(required=True)
    daily_flow_mode.add_argument("--objective", default=None)
    daily_flow_mode.add_argument("--run-id", dest="run_id", default=None)
    daily_flow.add_argument("--project", default=None)
    daily_flow.add_argument("--dry-run", action="store_true")
    daily_flow.add_argument("--json", action="store_true", default=True)

    zoom_out = subparsers.add_parser("zoom-out", help="Read-only orientation for a target")
    zoom_out.add_argument("target")
    zoom_out.add_argument("--repo-root", default=".")
    zoom_out.add_argument("--depth", type=int, default=2)
    zoom_out.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    _add_native_logging_args(zoom_out)

    handoff_parser = subparsers.add_parser("handoff", help="Generate an AIOS handoff packet")
    handoff_parser.add_argument("--objective", required=True)
    handoff_parser.add_argument("--repo-root", default=".")
    handoff_parser.add_argument("--output", default=None)
    handoff_parser.add_argument("--decision", action="append", default=[])
    handoff_parser.add_argument("--test", action="append", default=[])
    handoff_parser.add_argument("--worked", action="append", default=[])
    handoff_parser.add_argument("--failed", action="append", default=[])
    handoff_parser.add_argument("--blocker", action="append", default=[])
    handoff_parser.add_argument("--reference", action="append", default=[])
    handoff_parser.add_argument("--next-action", action="append", default=[])
    handoff_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    _add_native_logging_args(handoff_parser)

    review_parser = subparsers.add_parser("review", help="Run native review commands")
    review_subparsers = review_parser.add_subparsers(dest="review_command", required=True)
    review_squad = review_subparsers.add_parser("squad", help="Read-only squad review")
    review_squad.add_argument("--repo-root", default=".")
    review_squad.add_argument("--file", action="append", default=[])
    review_squad.add_argument("--base", default="HEAD")
    review_squad.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    _add_native_logging_args(review_squad)

    audit_parser = subparsers.add_parser("audit", help="Run native audit commands")
    audit_subparsers = audit_parser.add_subparsers(dest="audit_command", required=True)
    audit_security = audit_subparsers.add_parser("security", help="Read-only security audit")
    audit_security.add_argument("--mode", choices=["strict", "practical"], default="practical")
    audit_security.add_argument("--repo-root", default=".")
    audit_security.add_argument("--file", action="append", default=[])
    audit_security.add_argument("--base", default="HEAD")
    audit_security.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    _add_native_logging_args(audit_security)

    cleanup_parser = subparsers.add_parser("cleanup", help="Run guarded cleanup commands")
    cleanup_subparsers = cleanup_parser.add_subparsers(dest="cleanup_command", required=True)
    cleanup_de_slopify = cleanup_subparsers.add_parser(
        "de-slopify", help="Plan or apply low-risk cleanup"
    )
    cleanup_de_slopify.add_argument("--repo-root", default=".")
    cleanup_de_slopify.add_argument("--file", action="append", default=[])
    cleanup_de_slopify.add_argument("--base", default="HEAD")
    cleanup_de_slopify.add_argument("--goal", action="append", default=[])
    cleanup_de_slopify.add_argument("--apply", action="store_true")
    cleanup_de_slopify.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    _add_native_logging_args(cleanup_de_slopify)

    prototype_parser = subparsers.add_parser("prototype", help="Create an isolated prototype")
    prototype_parser.add_argument("--question", required=True)
    prototype_parser.add_argument("--sandbox-path", required=True)
    prototype_parser.add_argument("--repo-root", default=".")
    prototype_parser.add_argument("--prototype-type", default="notes")
    prototype_parser.add_argument("--cleanup-mode", default="delete_when_done")
    prototype_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    _add_native_logging_args(prototype_parser)

    eval_parser = subparsers.add_parser("eval", help="Record and inspect AIOS eval runs")
    eval_subparsers = eval_parser.add_subparsers(dest="eval_command", required=True)
    eval_record_run = eval_subparsers.add_parser("record-run", help="Record an eval run")
    eval_record_run.add_argument("--task-id", required=True)
    eval_record_run.add_argument("--condition", required=True)
    eval_record_run.add_argument("--mode", required=True)
    eval_record_run.add_argument("--context-profile", required=True)
    eval_record_run.add_argument("--final-status", required=True)
    eval_record_run.add_argument("--harness", default=None)
    eval_record_run.add_argument("--model", default=None)
    eval_record_run.add_argument("--duration-ms", type=int, default=None)
    eval_record_run.add_argument("--tokens", type=int, default=None)
    eval_record_run.add_argument("--cost", type=float, default=None)
    eval_record_run.add_argument("--files-changed", type=int, default=0)
    eval_record_run.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    eval_list_runs = eval_subparsers.add_parser("list-runs", help="List eval runs")
    eval_list_runs.add_argument("--task-id", default=None)
    eval_list_runs.add_argument("--condition", default=None)
    eval_list_runs.add_argument("--context-profile", default=None)
    eval_list_runs.add_argument("--limit", type=int, default=50)
    eval_list_runs.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    eval_summary = eval_subparsers.add_parser("summary", help="Summarize eval runs")
    eval_summary.add_argument("--project", default=None)
    eval_summary.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    eval_second_brain_lift = eval_subparsers.add_parser(
        "second-brain-lift", help="Compute lift between full second-brain and repo-only runs"
    )
    eval_second_brain_lift.add_argument("--full-run-id", required=True)
    eval_second_brain_lift.add_argument("--repo-only-run-id", required=True)
    eval_second_brain_lift.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    eval_retrieval_metrics = eval_subparsers.add_parser(
        "retrieval-metrics", help="Compute retrieval precision, recall, and staleness metrics"
    )
    eval_retrieval_metrics.add_argument("--run-id", required=True)
    eval_retrieval_metrics.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    eval_gold_set_run = eval_subparsers.add_parser(
        "gold-set-run", help="Evaluate a run against known required gold-set context"
    )
    eval_gold_set_run.add_argument("--run-id", required=True)
    eval_gold_set_run.add_argument("--gold-task-id", required=True)
    eval_gold_set_run.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    humanize_parser = subparsers.add_parser(
        "humanize", help="Run the personalized humanizer workflow"
    )
    humanize_subparsers = humanize_parser.add_subparsers(dest="humanize_command", required=True)
    humanize_run = humanize_subparsers.add_parser(
        "run", help="Rewrite text through the personalized humanizer"
    )
    humanize_input = humanize_run.add_mutually_exclusive_group(required=True)
    humanize_input.add_argument("--text", default=None)
    humanize_input.add_argument("--input", default=None, help="Input UTF-8 text file")
    humanize_input.add_argument("--stdin", action="store_true", help="Read input from stdin")
    humanize_run.add_argument(
        "--mode",
        choices=[
            "professional_outreach",
            "project_build_in_public",
            "academic_reflective",
            "prompt_prd",
            "creative_narrative",
        ],
        default=None,
    )
    humanize_run.add_argument(
        "--pipeline",
        choices=["standalone", "after_generic_humanizer"],
        default="standalone",
    )
    humanize_run.add_argument("--output", default=None, help="Optional output file")
    humanize_run.add_argument("--debug", action="store_true")
    humanize_run.add_argument("--no-record", action="store_true")
    humanize_run.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    humanize_feedback = humanize_subparsers.add_parser(
        "feedback", help="Record feedback for a personalized humanizer run"
    )
    humanize_feedback.add_argument("--run-id", required=True)
    humanize_feedback.add_argument(
        "--verdict", choices=["approved", "edited", "rejected"], required=True
    )
    humanize_feedback.add_argument("--notes", required=True)
    humanize_feedback.add_argument("--revision", default=None, help="Optional revised text file")
    humanize_feedback.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    humanize_eval = humanize_subparsers.add_parser(
        "eval", help="Run the personalized humanizer eval suite"
    )
    humanize_eval.add_argument("--record", action="store_true")
    humanize_eval.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    meta = subparsers.add_parser("meta", help="Analyze and review meta-learning signals")
    meta_subparsers = meta.add_subparsers(dest="meta_command", required=True)
    meta_analyze_session = meta_subparsers.add_parser(
        "analyze-session",
        help="Extract normalized meta-learning signals from a JSON session trace",
    )
    meta_analyze_session.add_argument("--input", required=True)
    meta_analyze_session.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    context_loops = subparsers.add_parser(
        "context-loops", help="Run inner/outer context learning loop commands"
    )
    context_loops_subparsers = context_loops.add_subparsers(
        dest="context_loops_command", required=True
    )

    def add_context_root(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--context-root", default=str(DEFAULT_CONTEXT_LOOP_ROOT))

    inner_run = context_loops_subparsers.add_parser(
        "inner-run", help="Record a reusable inner-loop run from supplied draft output"
    )
    inner_run.add_argument("--workflow", required=True)
    inner_run.add_argument("--task-type", required=True)
    inner_run.add_argument("--task-input", default=None)
    inner_run.add_argument("--task-input-file", default=None)
    inner_run.add_argument("--draft-output", default=None)
    inner_run.add_argument("--draft-output-file", default=None)
    inner_run.add_argument("--triggering-event", default="manual_command")
    inner_run.add_argument("--prompt-version", default="manual-v1")
    inner_run.add_argument("--guidance-version", default="approved-lessons.md")
    inner_run.add_argument("--assumption", action="append", default=[])
    inner_run.add_argument("--handoff-notes", default="")
    inner_run.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    add_context_root(inner_run)

    email_draft = context_loops_subparsers.add_parser(
        "email-draft", help="Create a local draft-only email pilot run"
    )
    email_draft.add_argument("--task-input", default=None)
    email_draft.add_argument("--task-input-file", default=None)
    email_draft.add_argument("--recipient", default="")
    email_draft.add_argument("--subject", default="")
    email_draft.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    add_context_root(email_draft)

    review_event = context_loops_subparsers.add_parser(
        "record-review", help="Record a human review event for an inner-loop run"
    )
    review_event.add_argument("--run-id", required=True)
    review_event.add_argument(
        "--outcome",
        required=True,
        choices=[
            "sent_unchanged",
            "edited_and_sent",
            "edited_not_sent",
            "deleted",
            "rejected",
            "left_pending",
            "replaced_manually",
            "human_judgment_only",
        ],
    )
    review_event.add_argument("--final-output", default=None)
    review_event.add_argument("--final-output-file", default=None)
    review_event.add_argument("--notes", default="")
    review_event.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    review = context_loops_subparsers.add_parser(
        "review", help="Propose learning candidates from reviewed context-loop outputs"
    )
    review.add_argument("--min-reviews", type=int, default=1)
    review.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    approve = context_loops_subparsers.add_parser(
        "approve", help="Approve one learning candidate for later application"
    )
    approve.add_argument("candidate_id")
    approve.add_argument("--actor", default="local-user")
    approve.add_argument("--note", default="")
    approve.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    reject = context_loops_subparsers.add_parser("reject", help="Reject one learning candidate")
    reject.add_argument("candidate_id")
    reject.add_argument("--actor", default="local-user")
    reject.add_argument("--note", default="")
    reject.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    add_context_root(reject)

    apply_approved = context_loops_subparsers.add_parser(
        "apply-approved", help="Append approved candidates to approved-lessons.md"
    )
    apply_approved.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    add_context_root(apply_approved)

    metrics = context_loops_subparsers.add_parser(
        "metrics", help="Summarize context-loop review and learning metrics"
    )
    metrics.add_argument("--write-report", action="store_true")
    metrics.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    add_context_root(metrics)

    shadow_parser = subparsers.add_parser("shadow", help="Create and compare eval shadow worktrees")
    shadow_subparsers = shadow_parser.add_subparsers(dest="shadow_command", required=True)
    shadow_create = shadow_subparsers.add_parser(
        "create-worktree", help="Create an isolated eval worktree"
    )
    shadow_create.add_argument("--task-id", required=True)
    shadow_create.add_argument("--start-sha", required=True)
    shadow_create.add_argument("--condition", required=True)
    shadow_create.add_argument("--repo-path", default=".")
    shadow_create.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    shadow_compare = shadow_subparsers.add_parser(
        "compare", help="Compare an AIOS shadow run against a baseline eval run"
    )
    shadow_compare.add_argument("--shadow-run-id", required=True)
    shadow_compare.add_argument("--baseline-run-id", required=True)
    shadow_compare.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    shadow_parity = shadow_subparsers.add_parser(
        "parity", help="Inspect shadow branch parity metadata"
    )
    shadow_parity.add_argument("--task-id", default=None)
    shadow_parity.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    shadow_cleanup = shadow_subparsers.add_parser(
        "cleanup", help="Remove an isolated eval worktree"
    )
    shadow_cleanup.add_argument("--worktree-path", required=True)
    shadow_cleanup.add_argument("--repo-path", default=".")
    shadow_cleanup.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    shadow_score = shadow_subparsers.add_parser("score", help="Score a peer trace")
    shadow_score.add_argument("--trace-id", required=True)
    shadow_score.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    shadow_queue = shadow_subparsers.add_parser("queue", help="List scored shadow candidates")
    shadow_queue.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    shadow_approve = shadow_subparsers.add_parser("approve", help="Approve a shadow candidate")
    shadow_approve.add_argument("--candidate-id", required=True)
    shadow_approve.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    shadow_run_pipeline = shadow_subparsers.add_parser(
        "run-pipeline", help="Run the approved shadow automation pipeline"
    )
    shadow_run_pipeline.add_argument("--candidate-id", required=True)
    shadow_run_pipeline.add_argument("--repo-path", default=".")
    shadow_run_pipeline.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    shadow_run = shadow_subparsers.add_parser(
        "run", help="Launch a headless Codex execution for a shadow worktree"
    )
    shadow_run.add_argument("--shadow-run-id", required=True)
    shadow_run.add_argument("--objective", default=None)
    shadow_run.add_argument("--run-id", default=None)
    shadow_run.add_argument("--packet-id", default=None)
    shadow_run.add_argument("--route-id", default=None)
    shadow_run.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    shadow_status_parser = shadow_subparsers.add_parser(
        "status", help="Show shadow execution or candidate status"
    )
    shadow_status_parser.add_argument("--shadow-run-id", default=None)
    shadow_status_parser.add_argument("--candidate-id", default=None)
    shadow_status_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    shadow_cancel = shadow_subparsers.add_parser(
        "cancel", help="Cancel a running headless Codex shadow execution"
    )
    shadow_cancel.add_argument("--shadow-run-id", required=True)
    shadow_cancel.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    peer_trace = subparsers.add_parser("peer-trace", help="Record privacy-safe peer trace metadata")
    peer_trace_subparsers = peer_trace.add_subparsers(dest="peer_trace_command", required=True)
    peer_trace_start = peer_trace_subparsers.add_parser("start", help="Start a peer trace session")
    peer_trace_start.add_argument("--peer-id", required=True)
    peer_trace_start.add_argument("--harness", default=None)
    peer_trace_start.add_argument("--repo-language", default=None)
    peer_trace_start.add_argument("--repo-framework", default=None)
    peer_trace_start.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    peer_trace_stop = peer_trace_subparsers.add_parser("stop", help="Stop a peer trace session")
    peer_trace_stop.add_argument("--session-id", required=True)
    peer_trace_stop.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    peer_trace_list = peer_trace_subparsers.add_parser("list", help="List peer trace sessions")
    peer_trace_list.add_argument("--limit", type=int, default=50)
    peer_trace_list.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    ablation = subparsers.add_parser("ablation", help="Run and compare AIOS feature ablations")
    ablation_subparsers = ablation.add_subparsers(dest="ablation_command", required=True)
    ablation_run = ablation_subparsers.add_parser("run", help="Run ablation policies")
    ablation_run.add_argument("--task-id", required=True)
    ablation_run.add_argument("--start-sha", required=True)
    ablation_run.add_argument("--policies", required=True)
    ablation_run.add_argument("--repo-path", default=".")
    ablation_run.add_argument("--base-run-id", default=None)
    ablation_run.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    ablation_compare = ablation_subparsers.add_parser("compare", help="Compare ablation scores")
    ablation_compare.add_argument("--task-id", required=True)
    ablation_compare.add_argument("--base-run-id", required=True)
    ablation_compare.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    packet = subparsers.add_parser("packet", help="Generate portable context packets")
    packet_subparsers = packet.add_subparsers(dest="packet_command", required=True)
    packet_generate = packet_subparsers.add_parser("generate", help="Generate a packet")
    packet_generate.add_argument("--task", required=True)
    packet_generate.add_argument("--repo-path", required=True)
    packet_generate.add_argument("--packet-id", default=None)
    packet_generate.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    benchmark = subparsers.add_parser("benchmark", help="External benchmark adapters")
    benchmark_subparsers = benchmark.add_subparsers(dest="benchmark_command", required=True)
    swe = benchmark_subparsers.add_parser("to-swe-bench", help="Convert eval task to SWE-bench")
    swe.add_argument("--task-id", required=True)
    swe.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    terminal = benchmark_subparsers.add_parser(
        "to-terminal-bench", help="Convert eval task to Terminal-Bench"
    )
    terminal.add_argument("--task-id", required=True)
    terminal.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    normalize = benchmark_subparsers.add_parser(
        "normalize-result", help="Normalize an external benchmark result"
    )
    normalize.add_argument("--task-id", required=True)
    normalize.add_argument("--harness", required=True)
    normalize.add_argument("--model", required=True)
    normalize.add_argument("--result-file", required=True)
    normalize.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    subparsers.add_parser("contracts-audit", help="Canonical AIOS interface contract audit")
    subparsers.add_parser(
        "governance-audit", help="Governed writeback, approval, and terminal-run evidence audit"
    )
    criteria_finding = subparsers.add_parser(
        "criteria-finding", help="Resolve success-criteria findings"
    )
    criteria_finding_subparsers = criteria_finding.add_subparsers(
        dest="criteria_finding_command", required=True
    )
    criteria_finding_resolve = criteria_finding_subparsers.add_parser(
        "resolve", help="Transition a criteria finding lifecycle state"
    )
    criteria_finding_resolve.add_argument("--id", required=True)
    criteria_finding_resolve.add_argument(
        "--status",
        required=True,
        choices=[status for status in EVALUATION_FINDING_LIFECYCLE_STATES if status != "open"],
    )
    criteria_finding_resolve.add_argument("--rationale", default=None)
    criteria_finding_resolve.add_argument("--evidence", action="append", default=[])
    criteria_finding_resolve.add_argument("--actor", default="operator-cli")
    criteria_finding_resolve.add_argument("--scope", choices=["run", "stage"], default=None)

    standards_resolution = subparsers.add_parser(
        "standards-resolution", help="Preview standards and criteria resolution"
    )
    standards_resolution_subparsers = standards_resolution.add_subparsers(
        dest="standards_resolution_command", required=True
    )
    standards_resolution_preview = standards_resolution_subparsers.add_parser(
        "preview", help="Preview resolved criteria and standards"
    )
    standards_resolution_preview.add_argument("--project-id", default=None)
    standards_resolution_preview.add_argument("--project-name", default=None)
    standards_resolution_preview.add_argument("--objective", default=None)
    standards_resolution_preview.add_argument("--classification", action="append", default=[])
    standards_resolution_preview.add_argument("--changed-file", action="append", default=[])
    standards_resolution_preview.add_argument("--skill", action="append", default=[])
    standards_resolution_preview.add_argument("--workflow-key", default=None)

    delta_explain = subparsers.add_parser(
        "delta-explain",
        help="Explainable delta drill-down for a project's latest health snapshot",
    )
    delta_explain.add_argument("--project", required=True, dest="project_id")
    delta_explain.add_argument("--format", choices=["json"], default="json")

    recommend_workflow = subparsers.add_parser(
        "recommend-workflow",
        help="Recommend workflows from health-state for a project",
    )
    recommend_workflow.add_argument("--project", required=True, dest="project_id")
    recommend_workflow.add_argument("--limit", type=int, default=5)

    standards_override = subparsers.add_parser(
        "standards-override",
        help="Record a manual assessment override for a standard",
    )
    standards_override.add_argument("--project", required=True, dest="project_id")
    standards_override.add_argument("--standard", required=True)
    standards_override.add_argument(
        "--status",
        required=True,
        choices=["pass", "partial", "fail", "unknown", "waived", "not_applicable"],
    )
    standards_override.add_argument("--rationale", default=None)
    standards_override.add_argument("--actor", default="operator-cli")
    standards_override.add_argument("--confidence", type=float, default=0.95)
    standards_override.add_argument("--evidence", action="append", default=[])
    standards_override.add_argument("--waiver-review-at", default=None)

    asset_lifecycle = subparsers.add_parser(
        "asset-lifecycle", help="List and transition prompt, skill, and workflow assets"
    )
    asset_lifecycle_subparsers = asset_lifecycle.add_subparsers(
        dest="asset_lifecycle_command", required=True
    )
    asset_lifecycle_list = asset_lifecycle_subparsers.add_parser(
        "list", help="List lifecycle-managed assets"
    )
    asset_lifecycle_list.add_argument(
        "--kind", choices=["prompt", "skill", "workflow"], default=None
    )
    asset_lifecycle_list.add_argument(
        "--state",
        choices=["draft", "candidate", "approved", "active", "deprecated"],
        default=None,
    )
    asset_lifecycle_promote = asset_lifecycle_subparsers.add_parser(
        "promote", help="Record a governed asset lifecycle transition"
    )
    asset_lifecycle_promote.add_argument(
        "--kind", required=True, choices=["prompt", "skill", "workflow"]
    )
    asset_lifecycle_promote.add_argument("--key", required=True)
    asset_lifecycle_promote.add_argument(
        "--from",
        required=True,
        dest="from_state",
        choices=["draft", "candidate", "approved", "active", "deprecated"],
    )
    asset_lifecycle_promote.add_argument(
        "--to",
        required=True,
        dest="to_state",
        choices=["draft", "candidate", "approved", "active", "deprecated"],
    )
    asset_lifecycle_promote.add_argument("--actor", required=True)
    asset_lifecycle_promote.add_argument("--rationale", required=True)
    asset_lifecycle_promote.add_argument("--evidence-id", action="append", default=[])

    workflow_compare = subparsers.add_parser(
        "workflow-compare", help="Compare workflow effectiveness from durable evidence"
    )
    workflow_compare.add_argument("--workflow-key", required=True)
    workflow_compare.add_argument("--since", default="30d")

    promote_asset_parser = subparsers.add_parser(
        "promote-asset", help="Propose or record an asset promotion"
    )
    promote_asset_parser.add_argument(
        "--kind", required=True, choices=["prompt", "skill", "workflow"]
    )
    promote_asset_parser.add_argument("--key", required=True)
    promote_asset_parser.add_argument(
        "--from",
        dest="from_state",
        default="candidate",
        choices=["draft", "candidate", "approved", "active", "deprecated"],
    )
    promote_asset_parser.add_argument(
        "--to",
        required=True,
        dest="to_state",
        choices=["draft", "candidate", "approved", "active", "deprecated"],
    )
    promote_asset_parser.add_argument("--actor", required=True)
    promote_asset_parser.add_argument("--rationale", required=True)
    promote_asset_parser.add_argument("--since", default="30d")
    promote_asset_parser.add_argument("--evidence-id", action="append", default=[])

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

    subparsers.add_parser(
        "sync-automation-history", help="Import durable automation history from local logs"
    )

    harness_brief = subparsers.add_parser(
        "harness-brief", help="Generate a backend-neutral harness briefing"
    )
    harness_brief.add_argument("--task", required=True, help="Task to classify and brief")
    harness_brief.add_argument("--project", default=None, help="Optional project id")
    harness_brief.add_argument(
        "--context-root",
        default=str(REPO_ROOT / "aios" / "context"),
        help="Context compiler root",
    )

    harness_simulate = subparsers.add_parser(
        "harness-simulate", help="Run a fake-agent harness fixture"
    )
    harness_simulate.add_argument("--fixture", required=True, help="Harness fixture JSON path")
    harness_simulate.add_argument(
        "--context-root",
        default=str(REPO_ROOT / "aios" / "context"),
        help="Context compiler root",
    )

    harness_replay = subparsers.add_parser(
        "harness-replay", help="Replay a historical session as harness events"
    )
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

    route_parser = subparsers.add_parser(
        "route", help="Preview the governed AIOS workflow route without creating a run"
    )
    route_parser.add_argument("objective", help="Work objective to route through AIOS")
    route_parser.add_argument("--project", default=None, help="Project id or name")
    route_parser.add_argument(
        "--cwd", default=None, help="Workspace path used for project inference"
    )
    route_parser.add_argument("--surface", default="codex", help="Preferred invocation surface")

    start_work = subparsers.add_parser(
        "start-work", help="Create a routed AIOS run packet and session handshake"
    )
    start_work.add_argument("objective", help="Work objective to route through AIOS")
    start_work.add_argument("--project", default=None, help="Project id to link to the run")
    start_work.add_argument(
        "--session-id", default=None, help="Session id to link; defaults to logs/current_session"
    )
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
    pre_pr.add_argument(
        "--server-entry", default=None, help="Override the built pre-cr server entrypoint"
    )
    pre_pr.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_PRE_PR_TIMEOUT_SECONDS,
        help="Timeout for the readiness run",
    )

    gate = subparsers.add_parser("gate", help="Run AIOS allowlisted project gates")
    gate_subparsers = gate.add_subparsers(dest="gate_command", required=True)
    gate_run = gate_subparsers.add_parser("run", help="Run one named quality gate")
    gate_run.add_argument("gate_id", help="Named gate id, e.g. test_quality")
    gate_run.add_argument("--project", required=True, help="AIOS quality-gates project id")
    gate_run.add_argument("--repo-root", default=".", help="Repository root to run from")
    gate_run.add_argument(
        "--mode",
        choices=["pre-commit", "full"],
        default="pre-commit",
        help="Gate command set to run",
    )
    gate_adoption_plan = gate_subparsers.add_parser(
        "adoption-plan",
        help="Write a repo quality-gate adoption matrix and rollout plan",
    )
    gate_adoption_plan.add_argument("--repo-root", default=".", help="Repository root to scan")
    gate_adoption_plan.add_argument("--run-id", default=None, help="Optional deterministic run id")
    gate_adoption_plan.add_argument(
        "--objective",
        default=None,
        help="Optional objective text for workflow reporting",
    )
    gate_adoption_doc_quality = gate_subparsers.add_parser(
        "adoption-doc-quality",
        help="Generate adoption docs and validate their agent/human quality",
    )
    gate_adoption_doc_quality.add_argument(
        "--repo-root",
        default=".",
        help="Repository root to scan",
    )
    gate_adoption_doc_quality.add_argument(
        "--run-id",
        default=None,
        help="Optional deterministic run id",
    )
    gate_adoption_doc_quality.add_argument(
        "--objective",
        default=None,
        help="Optional objective text for workflow reporting",
    )

    skills_parser = subparsers.add_parser("skills", help="Instruction/skills registry surfaces")
    skills_subparsers = skills_parser.add_subparsers(dest="skills_command", required=True)

    skills_status = skills_subparsers.add_parser("status", help="Show instruction sync status")
    skills_status.add_argument("--project", default=None, help="Optional project id filter")

    skills_refresh = skills_subparsers.add_parser(
        "refresh", help="Refresh instruction files from registry sources"
    )
    skills_refresh.add_argument("--project", default=None, help="Optional project id filter")
    skills_refresh.add_argument(
        "--apply", action="store_true", help="Apply updates instead of dry-run"
    )
    skills_harvest = skills_subparsers.add_parser(
        "harvest",
        help="Scan project roots and generate a reusable skills library with TMCP",
    )
    skills_harvest.add_argument(
        "--roots",
        nargs="+",
        required=True,
        help="Project root directories to scan",
    )
    skills_harvest.add_argument(
        "--out",
        required=True,
        help="Output path for the generated skills library repository",
    )
    skills_harvest.add_argument(
        "--dry-run",
        action="store_true",
        help="Plan the harvest and validation without writing files",
    )
    skills_harvest.add_argument(
        "--include-hidden",
        action="store_true",
        help="Scan hidden directories beyond known agent configuration directories",
    )
    skills_harvest.add_argument(
        "--max-file-size",
        type=int,
        default=250_000,
        help="Maximum candidate file size in bytes",
    )
    skills_harvest.add_argument(
        "--github-repo",
        default=None,
        help="GitHub repository name or URL to create/push when --push is used",
    )
    skills_harvest.add_argument("--push", action="store_true", help="Push generated repo with gh")
    skills_harvest.add_argument(
        "--tmcp",
        dest="tmcp",
        action="store_true",
        default=True,
        help="Generate the skills.tmcp layer",
    )
    skills_harvest.add_argument(
        "--no-tmcp",
        dest="tmcp",
        action="store_false",
        help="Skip TMCP generation",
    )
    skills_harvest.add_argument(
        "--no-rewrite",
        action="store_true",
        help="Copy reusable skill content without standardized rewrite sections",
    )
    skills_harvest.add_argument(
        "--interactive",
        action="store_true",
        help="Reserved for future human-in-the-loop merge decisions",
    )
    skills_harvest.add_argument(
        "--report-only",
        action="store_true",
        help="Generate reports without git initialization",
    )
    skills_harvest.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing generated harvest output repository",
    )
    skills_harvest.add_argument(
        "--graph-profile",
        default=None,
        help="Tracked TMCP graph profile JSON to persist in generated metadata",
    )
    skills_graph_verify = skills_subparsers.add_parser(
        "graph-verify",
        help="Verify or repair structured TMCP graph metadata for an existing skills library",
    )
    skills_graph_verify.add_argument(
        "--library",
        default=str(REPO_ROOT / "skills-library"),
        help="Existing skills library path",
    )
    skills_graph_verify.add_argument(
        "--graph-profile",
        default=None,
        help="Tracked TMCP graph profile JSON expected by the local graph",
    )
    skills_graph_verify.add_argument(
        "--repair",
        action="store_true",
        help="Write a missing skills.tmcp/graph.json from existing generated library metadata",
    )
    skills_graph_verify.add_argument(
        "--refresh",
        action="store_true",
        help="When used with --repair, rewrite skills.tmcp/graph.json from current library metadata",
    )

    tmcp_parser = subparsers.add_parser(
        "tmcp", help="Compile, inspect, and learn from TMCP packets"
    )
    tmcp_subparsers = tmcp_parser.add_subparsers(dest="tmcp_command", required=True)
    tmcp_explain = tmcp_subparsers.add_parser(
        "explain", help="Explain a prompt-specific TMCP packet"
    )
    tmcp_explain.add_argument("objective", help="Natural language task objective")
    tmcp_explain.add_argument("--project-path", default=None, help="Optional project path scope")
    tmcp_explain.add_argument("--phase", default=None, help="Optional TMCP phase hint")
    tmcp_explain.add_argument("--domain", default=None, help="Optional TMCP domain hint")
    tmcp_explain.add_argument(
        "--skills-library",
        default=str(REPO_ROOT / "skills-library"),
        help="Skills library path containing skills.tmcp",
    )
    tmcp_explain.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    tmcp_learning = tmcp_subparsers.add_parser(
        "learning-summary",
        help="Summarize TMCP node and behavior-atom ROI from receipts",
    )
    tmcp_learning.add_argument("--task-id", default=None, help="Optional task id filter")
    tmcp_learning.add_argument(
        "--limit", type=int, default=200, help="Maximum receipts to summarize"
    )
    tmcp_learning.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    tmcp_feedback = tmcp_subparsers.add_parser(
        "receipt-feedback",
        help="Record node usefulness and missed-requirement feedback for one receipt",
    )
    tmcp_feedback.add_argument("--receipt-id", required=True, help="TMCP traversal receipt id")
    tmcp_feedback.add_argument(
        "--node-usefulness-json",
        default="{}",
        help="JSON object keyed by node id with usefulness feedback",
    )
    tmcp_feedback.add_argument(
        "--omitted-requirement-json",
        action="append",
        default=[],
        help="JSON object describing one omitted requirement",
    )
    tmcp_feedback.add_argument(
        "--validation-evidence-json",
        action="append",
        default=[],
        help="JSON value describing one validation evidence item",
    )
    tmcp_feedback.add_argument("--execution-outcome", default=None, help="Optional updated outcome")
    tmcp_feedback.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    tmcp_adherence = tmcp_subparsers.add_parser(
        "adherence",
        help="Evaluate whether observed work adhered to a TMCP packet",
    )
    tmcp_adherence.add_argument("--packet-json", required=True, help="Compiled packet JSON object")
    tmcp_adherence.add_argument("--receipt-id", default=None, help="Optional receipt to update")
    tmcp_adherence.add_argument("--final-summary", default="", help="Final run summary text")
    tmcp_adherence.add_argument(
        "--validation-command",
        action="append",
        default=[],
        help="Validation command that ran during the task",
    )
    tmcp_adherence.add_argument(
        "--evidence-json",
        action="append",
        default=[],
        help="JSON value describing observed run evidence",
    )
    tmcp_adherence.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    tmcp_event = tmcp_subparsers.add_parser(
        "record-event", help="Record a granular TMCP receipt event"
    )
    tmcp_event.add_argument("--receipt-id", default=None)
    tmcp_event.add_argument("--run-id", default=None)
    tmcp_event.add_argument("--invocation-id", default=None)
    tmcp_event.add_argument("--event-type", required=True)
    tmcp_event.add_argument("--summary", required=True)
    tmcp_event.add_argument("--node", default=None)
    tmcp_event.add_argument("--behavior-atom", default=None)
    tmcp_event.add_argument("--metadata-json", default="{}")
    tmcp_event.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    tmcp_intervention = tmcp_subparsers.add_parser(
        "record-intervention",
        help="Record a TMCP blocker/intervention event",
    )
    tmcp_intervention.add_argument("--receipt-id", default=None)
    tmcp_intervention.add_argument("--run-id", default=None)
    tmcp_intervention.add_argument("--invocation-id", default=None)
    tmcp_intervention.add_argument("--intervention-type", required=True)
    tmcp_intervention.add_argument("--summary", required=True)
    tmcp_intervention.add_argument("--node", default=None)
    tmcp_intervention.add_argument("--behavior-atom", default=None)
    tmcp_intervention.add_argument("--outcome", default="recorded")
    tmcp_intervention.add_argument("--metadata-json", default="{}")
    tmcp_intervention.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    tmcp_diff = tmcp_subparsers.add_parser("packet-diff", help="Diff two compiled TMCP packets")
    tmcp_diff.add_argument("--before-json", required=True)
    tmcp_diff.add_argument("--after-json", required=True)
    tmcp_diff.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    tmcp_shortcut = tmcp_subparsers.add_parser(
        "shortcut-governance",
        help="Evaluate shortcut lifecycle governance for a shortcut JSON object",
    )
    tmcp_shortcut.add_argument("--shortcut-json", required=True)
    tmcp_shortcut.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    tmcp_review_plan = tmcp_subparsers.add_parser(
        "review-plan",
        help="Compile TMCP expertise and write expert rubric remediation artifacts",
    )
    _add_expert_rubric_arguments(tmcp_review_plan)
    expert_rubric = subparsers.add_parser(
        "expert-rubric",
        help="Run the TMCP expert-rubric remediation workflow",
    )
    _add_expert_rubric_arguments(expert_rubric)

    corpus_parser = subparsers.add_parser("corpus", help="Corpus evaluation harness")
    corpus_subparsers = corpus_parser.add_subparsers(dest="corpus_command", required=True)
    corpus_run = corpus_subparsers.add_parser("run", help="Run the AIOS corpus evaluation harness")
    corpus_run.add_argument("corpus_args", nargs=argparse.REMAINDER)
    corpus_report = corpus_subparsers.add_parser(
        "report", help="Regenerate a corpus Markdown report"
    )
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
        conn = _connect_db(db_path) if _command_requires_db(args) else None

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
        elif args.command == "doctor":
            data = _doctor_payload(
                db_path=db_path,
                logs_dir=logs_dir,
                config_root=config_root,
                vault_root=vault_root,
            )
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
        elif args.command == "workflow-gates":
            data = _workflow_gates_payload(args)
        elif args.command == "session-intel":
            assert conn is not None
            data = _session_intel_payload(conn, args)
            conn.commit()
        elif args.command == "repo":
            data = _repo_payload(args)
        elif args.command == "quality":
            data = _quality_payload(args)
        elif args.command == "ship":
            data = _ship_payload(args)
        elif args.command == "service":
            data = _service_payload(args)
        elif args.command == "workflow-skill":
            data = _workflow_skill_payload(args)
        elif args.command == "planning":
            data = _planning_payload(args)
        elif args.command == "retrospectives":
            assert conn is not None
            data = _retrospective_payload(conn, args)
        elif args.command == "model-selection":
            assert conn is not None
            data = _model_selection_payload(conn, args)
        elif args.command == "dx-pack":
            data = _dx_pack_payload(args)
        elif args.command == "evidence":
            assert conn is not None
            data = _evidence_payload(conn, args)
        elif args.command == "verifier":
            assert conn is not None
            data = _verifier_payload(conn, args)
        elif args.command == "learning-analyze":
            assert conn is not None
            data = _learning_analyze_payload(conn, args)
        elif args.command == "learning-propose":
            assert conn is not None
            data = _learning_propose_payload(conn, args)
        elif args.command == "learning-impact":
            assert conn is not None
            data = _learning_impact_payload(conn, args)
        elif args.command == "operator-search":
            assert conn is not None
            data = cmd_operator_search(conn, args)
        elif args.command == "next-action":
            assert conn is not None
            data = cmd_next_action(conn, args)
        elif args.command == "daily-flow":
            assert conn is not None
            data = cmd_daily_flow(conn, args)
        elif args.command == "zoom-out":
            data = cmd_native_zoom_out(args)
        elif args.command == "handoff":
            data = cmd_native_handoff(args)
        elif args.command == "review" and args.review_command == "squad":
            data = cmd_native_review_squad(args)
        elif args.command == "audit" and args.audit_command == "security":
            data = cmd_native_audit_security(args)
        elif args.command == "cleanup" and args.cleanup_command == "de-slopify":
            data = cmd_native_cleanup_de_slopify(args)
        elif args.command == "prototype":
            data = cmd_native_prototype(args)
        elif args.command == "contracts-audit":
            assert conn is not None
            data = _contracts_audit_payload(conn)
        elif args.command == "governance-audit":
            assert conn is not None
            data = _governance_audit_payload(conn)
        elif args.command == "criteria-finding" and args.criteria_finding_command == "resolve":
            assert conn is not None
            data = _criteria_finding_resolve_payload(conn, args)
        elif (
            args.command == "standards-resolution"
            and args.standards_resolution_command == "preview"
        ):
            assert conn is not None
            data = _standards_resolution_preview_payload(conn, args)
        elif args.command == "delta-explain":
            assert conn is not None
            data = _delta_explain_payload(conn, args)
        elif args.command == "recommend-workflow":
            assert conn is not None
            data = _recommend_workflow_payload(conn, args)
        elif args.command == "standards-override":
            assert conn is not None
            data = _standards_override_payload(conn, args)
        elif args.command == "asset-lifecycle" and args.asset_lifecycle_command == "list":
            assert conn is not None
            data = _asset_lifecycle_list_payload(conn, args)
        elif args.command == "asset-lifecycle" and args.asset_lifecycle_command == "promote":
            assert conn is not None
            data = _asset_lifecycle_promote_payload(conn, args)
        elif args.command == "workflow-compare":
            assert conn is not None
            data = _workflow_compare_payload(conn, args)
        elif args.command == "promote-asset":
            assert conn is not None
            data = _promote_asset_payload(conn, args)
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
        elif args.command == "eval":
            assert conn is not None
            data = cmd_eval(conn, args)
        elif args.command == "humanize" and args.humanize_command == "run":
            data = cmd_humanize_run(conn, args)
        elif args.command == "humanize" and args.humanize_command == "feedback":
            assert conn is not None
            data = cmd_humanize_feedback(conn, args)
        elif args.command == "humanize" and args.humanize_command == "eval":
            data = cmd_humanize_eval(conn, args)
        elif args.command == "meta" and args.meta_command == "analyze-session":
            data = _meta_analyze_session_payload(args)
        elif args.command == "context-loops":
            assert conn is not None
            data = cmd_context_loops(conn, args)
        elif args.command == "shadow":
            data = cmd_shadow(conn, args)
        elif args.command == "peer-trace":
            assert conn is not None
            data = cmd_peer_trace(conn, args)
        elif args.command == "ablation":
            assert conn is not None
            data = cmd_ablation(conn, args)
        elif args.command == "packet" and args.packet_command == "generate":
            assert conn is not None
            data = cmd_packet_generate(conn, args)
        elif args.command == "benchmark" and args.benchmark_command == "to-swe-bench":
            assert conn is not None
            data = cmd_benchmark_to_swe_bench(conn, args)
        elif args.command == "benchmark" and args.benchmark_command == "to-terminal-bench":
            assert conn is not None
            data = cmd_benchmark_to_terminal_bench(conn, args)
        elif args.command == "benchmark" and args.benchmark_command == "normalize-result":
            data = cmd_benchmark_normalize_result(args)
        elif args.command == "tmcp" and args.tmcp_command == "explain":
            packet = compile_tmcp_packet(
                objective=args.objective,
                project_path=args.project_path,
                skills_library_path=Path(args.skills_library).expanduser().resolve(),
                phase=args.phase,
                domain=args.domain,
            )
            data = explain_tmcp_packet(packet)
        elif args.command == "tmcp" and args.tmcp_command == "learning-summary":
            if conn is None:
                conn = _connect_db(db_path)
            assert conn is not None
            data = tmcp_learning_summary(
                conn,
                task_id=args.task_id,
                limit=max(1, int(args.limit)),
            )
        elif args.command == "tmcp" and args.tmcp_command == "receipt-feedback":
            if conn is None:
                conn = _connect_db(db_path)
            assert conn is not None
            omitted_requirements = [
                _parse_json_object(raw)
                for raw in args.omitted_requirement_json
                if _parse_json_object(raw)
            ]
            validation_evidence = [_parse_json_value(raw) for raw in args.validation_evidence_json]
            data = update_tmcp_receipt_feedback(
                conn,
                receipt_id=args.receipt_id,
                node_usefulness=_parse_json_object(args.node_usefulness_json),
                omitted_requirements=omitted_requirements,
                validation_evidence=validation_evidence,
                execution_outcome=args.execution_outcome,
            )
            conn.commit()
        elif args.command == "tmcp" and args.tmcp_command == "adherence":
            evidence = [_parse_json_value(raw) for raw in args.evidence_json]
            data = evaluate_tmcp_packet_adherence(
                packet=_parse_json_object(args.packet_json),
                evidence=evidence,
                final_summary=args.final_summary,
                validation_commands=list(args.validation_command),
            )
            if args.receipt_id:
                if conn is None:
                    conn = _connect_db(db_path)
                persist_tmcp_packet_adherence(
                    conn,
                    receipt_id=args.receipt_id,
                    adherence=data,
                )
                conn.commit()
        elif args.command == "tmcp" and args.tmcp_command == "record-event":
            if conn is None:
                conn = _connect_db(db_path)
            event_id = record_tmcp_receipt_event(
                conn,
                receipt_id=args.receipt_id,
                event_type=args.event_type,
                summary=args.summary,
                run_id=args.run_id,
                invocation_id=args.invocation_id,
                node=args.node,
                behavior_atom=args.behavior_atom,
                metadata=_parse_json_object(args.metadata_json),
            )
            conn.commit()
            data = {"schema": "tmcp-record-event-result-v0.1", "event_id": event_id}
        elif args.command == "tmcp" and args.tmcp_command == "record-intervention":
            if conn is None:
                conn = _connect_db(db_path)
            intervention_id = record_tmcp_intervention_event(
                conn,
                receipt_id=args.receipt_id,
                intervention_type=args.intervention_type,
                summary=args.summary,
                run_id=args.run_id,
                invocation_id=args.invocation_id,
                node=args.node,
                behavior_atom=args.behavior_atom,
                outcome=args.outcome,
                metadata=_parse_json_object(args.metadata_json),
            )
            conn.commit()
            data = {
                "schema": "tmcp-record-intervention-result-v0.1",
                "intervention_id": intervention_id,
            }
        elif args.command == "tmcp" and args.tmcp_command == "packet-diff":
            data = diff_tmcp_packets(
                _parse_json_object(args.before_json),
                _parse_json_object(args.after_json),
            )
        elif args.command == "tmcp" and args.tmcp_command == "shortcut-governance":
            data = shortcut_governance_recommendation(_parse_json_object(args.shortcut_json))
        elif args.command == "expert-rubric" or (
            args.command == "tmcp" and args.tmcp_command == "review-plan"
        ):
            data = _tmcp_review_plan_payload(args)
        elif args.command == "harness-active-readiness":
            data = active_readiness()
        elif args.command == "route":
            assert conn is not None
            data = _route_preview_payload(conn, args)
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
        elif args.command == "gate" and args.gate_command == "run":
            data = run_quality_gate(
                project_id=args.project,
                gate_id=args.gate_id,
                mode=args.mode,
                repo_root=Path(args.repo_root).expanduser().resolve(),
            )
            if data["status"] == "fail":
                raise CLIError(
                    "gate-failed",
                    str(data["summary"]),
                    EXIT_RUNTIME,
                )
        elif args.command == "gate" and args.gate_command == "adoption-plan":
            data = _gate_adoption_plan_payload(args)
        elif args.command == "gate" and args.gate_command == "adoption-doc-quality":
            data = _gate_adoption_doc_quality_payload(args)
        elif args.command == "skills" and args.skills_command == "status":
            data = _instruction_status(config_root, vault_root, project_id=args.project)
        elif args.command == "skills" and args.skills_command == "refresh":
            data = _refresh_instructions(
                config_root=config_root,
                vault_root=vault_root,
                project_id=args.project,
                apply=bool(args.apply),
            )
        elif args.command == "skills" and args.skills_command == "harvest":
            data = harvest_skills_library(
                HarvestOptions(
                    roots=tuple(Path(root) for root in args.roots),
                    out=Path(args.out),
                    include_hidden=bool(args.include_hidden),
                    max_file_size=max(1, int(args.max_file_size)),
                    dry_run=bool(args.dry_run),
                    github_repo=args.github_repo,
                    push=bool(args.push),
                    tmcp=bool(args.tmcp),
                    no_rewrite=bool(args.no_rewrite),
                    interactive=bool(args.interactive),
                    report_only=bool(args.report_only),
                    force=bool(args.force),
                    graph_profile_path=(
                        Path(args.graph_profile).expanduser().resolve()
                        if args.graph_profile
                        else None
                    ),
                )
            )
        elif args.command == "skills" and args.skills_command == "graph-verify":
            data = verify_tmcp_graph(
                Path(args.library),
                graph_profile_path=(
                    Path(args.graph_profile).expanduser().resolve() if args.graph_profile else None
                ),
                repair=bool(args.repair),
                refresh=bool(args.refresh),
            )
        else:
            raise CLIError("unknown-command", f"Unsupported command: {args.command}", EXIT_USAGE)

        if command in NATIVE_COMMAND_SAFETY_CLASSES:
            _maybe_log_native_command(args, command, data)

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
