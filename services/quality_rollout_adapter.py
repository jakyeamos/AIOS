from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path

from quality_runner.rollout import rollout_payload

from services.evidence_artifacts import EvidenceStatus, record_evidence_artifact

AIOS_ROLLOUT_ADAPTER_SCHEMA = "aios-quality-rollout-adapter-v0.1"

RolloutPayloadFunc = Callable[..., dict[str, object]]


def launch_quality_rollout(
    *,
    conn: sqlite3.Connection | None,
    repo_list_path: Path | None,
    repos: Sequence[str],
    run_id_prefix: str | None,
    output_dir: Path | None,
    profile: str | None,
    ci_status_json: Path | None,
    timeout_seconds: int,
    workflow_timeout_seconds: int | None,
    verify_timeout_seconds: int | None,
    workflow_timeout_reason: str | None,
    total_timeout_seconds: int | None,
    total_timeout_reason: str | None,
    checkout_most_advanced_branch: bool,
    allow_mutating_gates: bool,
    task_id: str | None = None,
    run_id: str | None = None,
    session_id: str | None = None,
    rollout_func: RolloutPayloadFunc = rollout_payload,
) -> dict[str, object]:
    resolved_run_id_prefix = run_id_prefix or _default_aios_rollout_id()
    resolved_output_dir = (
        output_dir.expanduser().resolve()
        if output_dir
        else (Path.home() / "AIOS" / "artifacts" / "quality-rollouts" / resolved_run_id_prefix)
    )

    rollout_result = rollout_func(
        repo_list_path=repo_list_path.expanduser().resolve() if repo_list_path else None,
        repos=list(repos),
        run_id_prefix=resolved_run_id_prefix,
        output_dir=resolved_output_dir,
        profile=profile,
        ci_status_json=ci_status_json.expanduser().resolve() if ci_status_json else None,
        timeout_seconds=timeout_seconds,
        workflow_timeout_seconds=workflow_timeout_seconds,
        verify_timeout_seconds=verify_timeout_seconds,
        workflow_timeout_reason=workflow_timeout_reason,
        total_timeout_seconds=total_timeout_seconds,
        total_timeout_reason=total_timeout_reason,
        checkout_most_advanced_branch=checkout_most_advanced_branch,
        allow_mutating_gates=allow_mutating_gates,
    )
    artifact_index = _write_artifact_index(
        output_dir=resolved_output_dir,
        rollout_result=rollout_result,
        run_id_prefix=resolved_run_id_prefix,
    )
    evidence_id = _record_rollout_evidence(
        conn,
        rollout_result=rollout_result,
        artifact_index=artifact_index,
        task_id=task_id,
        run_id=run_id or resolved_run_id_prefix,
        session_id=session_id,
    )
    return {
        "schema": AIOS_ROLLOUT_ADAPTER_SCHEMA,
        "status": rollout_result.get("status", "unknown"),
        "run_id_prefix": resolved_run_id_prefix,
        "output_dir": str(resolved_output_dir),
        "ledger_path": rollout_result.get("ledger_path"),
        "repo_count": rollout_result.get("repo_count", 0),
        "accepted_reports": rollout_result.get("accepted_reports", 0),
        "rejected_reports": rollout_result.get("rejected_reports", 0),
        "failed_repos": rollout_result.get("failed_repos", []),
        "controller_report_paths": artifact_index["controller_report_paths"],
        "validation_paths": artifact_index["validation_paths"],
        "fleet_documents": rollout_result.get("fleet_documents", {}),
        "artifact_index_path": artifact_index["artifact_index_path"],
        "evidence_id": evidence_id,
        "rollout_result": rollout_result,
    }


def _write_artifact_index(
    *,
    output_dir: Path,
    rollout_result: dict[str, object],
    run_id_prefix: str,
) -> dict[str, object]:
    results = _result_rows(rollout_result)
    controller_report_paths = _string_values(results, "report_path")
    validation_paths = _string_values(results, "validation_path")
    artifact_paths = _string_values(results, "artifact_path")
    index = {
        "schema": AIOS_ROLLOUT_ADAPTER_SCHEMA,
        "run_id_prefix": run_id_prefix,
        "rollout_status": rollout_result.get("status", "unknown"),
        "ledger_path": rollout_result.get("ledger_path"),
        "controller_report_paths": controller_report_paths,
        "validation_paths": validation_paths,
        "repo_artifact_paths": artifact_paths,
        "fleet_documents": rollout_result.get("fleet_documents", {}),
        "created_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    index_path = output_dir / "aios-rollout-artifact-index.json"
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        **index,
        "artifact_index_path": str(index_path),
    }


def _record_rollout_evidence(
    conn: sqlite3.Connection | None,
    *,
    rollout_result: dict[str, object],
    artifact_index: dict[str, object],
    task_id: str | None,
    run_id: str,
    session_id: str | None,
) -> str | None:
    if conn is None:
        return None
    status = _evidence_status(rollout_result)
    summary = {
        "schema": AIOS_ROLLOUT_ADAPTER_SCHEMA,
        "rollout_status": rollout_result.get("status", "unknown"),
        "ledger_path": rollout_result.get("ledger_path"),
        "artifact_index_path": artifact_index.get("artifact_index_path"),
        "accepted_reports": rollout_result.get("accepted_reports", 0),
        "rejected_reports": rollout_result.get("rejected_reports", 0),
        "controller_report_paths": artifact_index.get("controller_report_paths", []),
    }
    return record_evidence_artifact(
        conn,
        task_id=task_id,
        run_id=run_id,
        session_id=session_id,
        phase="quality-rollout",
        agent="aios-quality-rollout-adapter",
        command=_recorded_command(rollout_result),
        output_hash=_artifact_hash(artifact_index),
        parsed_summary=json.dumps(summary, sort_keys=True),
        status=status,
        caveats=["controller-reports-captured-in-artifact-index"],
    )


def _result_rows(rollout_result: dict[str, object]) -> list[dict[str, object]]:
    rows = rollout_result.get("results", [])
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _string_values(rows: Sequence[dict[str, object]], key: str) -> list[str]:
    values: list[str] = []
    for row in rows:
        value = row.get(key)
        if isinstance(value, str) and value:
            values.append(value)
    return values


def _evidence_status(rollout_result: dict[str, object]) -> EvidenceStatus:
    rejected_reports = rollout_result.get("rejected_reports")
    rejected_count = rejected_reports if isinstance(rejected_reports, int) else 0
    if rejected_count > 0:
        return "fail"
    if rollout_result.get("status") == "completed":
        return "pass"
    return "unknown"


def _artifact_hash(artifact_index: dict[str, object]) -> str:
    encoded = json.dumps(artifact_index, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _recorded_command(rollout_result: dict[str, object]) -> str:
    run_id_prefix = rollout_result.get("run_id_prefix", "")
    output_dir = rollout_result.get("output_dir", "")
    return f"aios quality rollout --run-id-prefix {run_id_prefix} --output-dir {output_dir}"


def _default_aios_rollout_id() -> str:
    return f"aios-qr-rollout-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
