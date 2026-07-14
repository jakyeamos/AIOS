"""Independent run verification: run canonical gates, record verifier
artifacts, and gate orchestration-run completion on proven evidence.

This module is the single sanctioned path for transitioning an
orchestration run to ``completed``. It produces the verifier artifacts
that ``validate_closeout_verification`` (already enforced by hook-stop)
consumes, closing the loop between claimed and proven success.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from services.evidence_artifacts import record_evidence_artifact
from services.governed_effects import evaluate_governed_closeout
from services.quality_gates import (
    DEFAULT_REGISTRY_PATH,
    LOCAL_CONTRACT_NAME,
    run_gate,
)
from services.verifier_artifacts import (
    record_verifier_artifact,
    validate_closeout_verification,
)

VERIFIER_AGENT = "aios-verify-run"


class RunVerificationError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def verify_run(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    repo_root: str | Path | None = None,
    gate_ids: list[str] | None = None,
    registry_path: Path = DEFAULT_REGISTRY_PATH,
) -> dict[str, Any]:
    run = _load_run(conn, run_id)
    resolved_root, registry_project_id = _resolve_repo_root(
        conn,
        project_id=run["project_id"],
        explicit_root=repo_root,
        registry_path=registry_path,
    )
    selected_gates = list(gate_ids or _contract_gates(resolved_root))
    if not selected_gates:
        raise RunVerificationError(
            "no-gates-configured",
            f"No verifiable gates for {resolved_root}: pass --gate or declare "
            f"{LOCAL_CONTRACT_NAME} with fullGates or preCommitGates.",
        )

    gate_payloads: list[dict[str, Any]] = []
    evidence_refs: list[str] = []
    blocking_issues: list[dict[str, Any]] = []
    for gate_id in selected_gates:
        payload = run_gate(
            project_id=registry_project_id,
            gate_id=gate_id,
            mode="full",
            repo_root=resolved_root,
            registry_path=registry_path,
        )
        if payload["status"] == "skip":
            payload = run_gate(
                project_id=registry_project_id,
                gate_id=gate_id,
                mode="pre-commit",
                repo_root=resolved_root,
                registry_path=registry_path,
            )
        gate_payloads.append(payload)
        for command_result in payload.get("commands", []):
            argv = command_result.get("argv")
            command_text = " ".join(argv) if isinstance(argv, list) else str(argv or gate_id)
            exit_code = command_result.get("exitCode")
            evidence_id = record_evidence_artifact(
                conn,
                run_id=run_id,
                session_id=run["session_id"],
                phase="verification",
                agent=VERIFIER_AGENT,
                command=command_text,
                exit_code=exit_code if isinstance(exit_code, int) else None,
                parsed_summary=str(command_result.get("summary") or "")[:500],
                status="pass" if command_result.get("status") == "pass" else "fail",
                caveats=["output-absent:gate-inline-summary"],
            )
            evidence_refs.append(
                f"evidence-artifact: {evidence_id} gate={gate_id} "
                f"exit_code={exit_code} command={command_text[:180]}"
            )
        if payload["status"] == "fail":
            blocking_issues.append(
                {
                    "gate": payload["gateId"],
                    "command": _first_failing_command(payload),
                    "summary": str(payload.get("summary") or "")[:300],
                }
            )

    statuses = {payload["status"] for payload in gate_payloads}
    if "fail" in statuses:
        result = "fail"
    elif statuses == {"pass"}:
        result = "pass"
    else:
        result = "needs_work"
        for payload in gate_payloads:
            if payload["status"] == "skip":
                blocking_issues.append(
                    {
                        "gate": payload["gateId"],
                        "command": f"{LOCAL_CONTRACT_NAME}",
                        "summary": f"gate {payload['gateId']} has no runnable commands",
                    }
                )

    verifier_id = record_verifier_artifact(
        conn,
        run_id=run_id,
        session_id=run["session_id"],
        verifier_agent=VERIFIER_AGENT,
        inputs_reviewed=["task_spec", "changed_files", "evidence_artifacts"],
        checks_performed=selected_gates,
        result=result,
        blocking_issues=blocking_issues,
        evidence_refs=evidence_refs,
    )

    validation = validate_closeout_verification(
        conn,
        task_id=run_id,
        run_id=run_id,
        session_id=run["session_id"],
        workflow_key=run["workflow_key"],
        implementation_bearing=True,
    )
    governed_closeout = evaluate_governed_closeout(
        conn,
        run_id=run_id,
        verification=validation,
        actor=VERIFIER_AGENT,
        capability="aios.verify",
        origin="loopback",
        egress_target="local",
        redaction_status="not_required",
    )

    from_status = run["status"]
    to_status: str | None = None
    if result == "pass" and validation["allowed"] and governed_closeout["allowed"]:
        to_status = "completed"
    elif result == "fail":
        to_status = "failed_validation"
    elif result == "needs_work" or not validation["allowed"]:
        to_status = "partial"
    if to_status and to_status != from_status:
        _transition_run(
            conn,
            run_id=run_id,
            project_id=run["project_id"],
            session_id=run["session_id"],
            from_status=from_status,
            to_status=to_status,
            summary=f"verify-run {result}: {len(selected_gates)} gate(s), "
            f"{len(blocking_issues)} blocking issue(s).",
            verifier_id=verifier_id,
        )
    if to_status:
        _update_resume_snapshot(
            conn,
            run_id=run_id,
            current_stage="closeout" if to_status == "completed" else "verification",
            next_recommended_action=(
                "Review verifier evidence and record the closeout."
                if to_status == "completed"
                else "Resolve verifier blockers and resume verification."
            ),
            verification_result=result,
            verifier_id=verifier_id,
            evidence_ref_count=len(evidence_refs),
            blocking_issue_count=len(blocking_issues),
        )

    return {
        "run_id": run_id,
        "repo_root": str(resolved_root),
        "registry_project_id": registry_project_id,
        "gates": gate_payloads,
        "result": result,
        "verifier_id": verifier_id,
        "evidence_refs": evidence_refs,
        "blocking_issues": blocking_issues,
        "validation": validation,
        "governed_closeout": governed_closeout,
        "run_status": {"from": from_status, "to": to_status or from_status},
    }


def _load_run(conn: sqlite3.Connection, run_id: str) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT id, project_id, session_id, status, workflow_key
        FROM orchestration_runs
        WHERE id = ?
        LIMIT 1
        """,
        (run_id,),
    ).fetchone()
    if row is None:
        raise RunVerificationError("run-not-found", f"Run not found: {run_id}")
    keys = ["id", "project_id", "session_id", "status", "workflow_key"]
    values = list(row) if not isinstance(row, sqlite3.Row) else [row[key] for key in keys]
    run = dict(zip(keys, values, strict=True))
    if run["status"] == "canceled":
        raise RunVerificationError(
            "run-canceled", f"Run {run_id} is canceled and cannot be verified."
        )
    return run


def _resolve_repo_root(
    conn: sqlite3.Connection,
    *,
    project_id: str | None,
    explicit_root: str | Path | None,
    registry_path: Path,
) -> tuple[Path, str]:
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    projects = [project for project in registry.get("projects", []) if isinstance(project, dict)]

    if explicit_root is not None:
        resolved = Path(explicit_root).expanduser().resolve()
        if not resolved.is_dir():
            raise RunVerificationError("repo-root-missing", f"Repo root does not exist: {resolved}")
        for project in projects:
            for root in project.get("roots", []):
                if Path(str(root)).expanduser().resolve() == resolved:
                    return resolved, str(project["projectId"])
        raise RunVerificationError(
            "repo-root-unregistered",
            f"{resolved} is not a registered root in {registry_path.name}.",
        )

    project_name: str | None = None
    if project_id:
        row = conn.execute(
            "SELECT name FROM projects WHERE id = ? LIMIT 1", (project_id,)
        ).fetchone()
        if row is not None:
            project_name = str(row[0])
    if not project_name:
        raise RunVerificationError(
            "project-unresolved",
            "Run has no resolvable project; pass --repo-root explicitly.",
        )
    for project in projects:
        if str(project.get("projectId", "")).casefold() == project_name.casefold():
            for root in project.get("roots", []):
                candidate = Path(str(root)).expanduser()
                if candidate.is_dir():
                    return candidate.resolve(), str(project["projectId"])
    raise RunVerificationError(
        "project-unregistered",
        f"Project {project_name} has no registered quality-gate root; pass --repo-root explicitly.",
    )


def _contract_gates(repo_root: Path) -> list[str]:
    contract_path = repo_root / LOCAL_CONTRACT_NAME
    if not contract_path.exists():
        return []
    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(contract, dict):
        return []
    full_gates = contract.get("fullGates")
    if isinstance(full_gates, list) and full_gates:
        return [str(gate) for gate in full_gates]
    pre_commit_gates = contract.get("preCommitGates")
    if isinstance(pre_commit_gates, list):
        return [str(gate) for gate in pre_commit_gates]
    return []


def _first_failing_command(payload: dict[str, Any]) -> str:
    for command_result in payload.get("commands", []):
        if command_result.get("status") == "fail":
            argv = command_result.get("argv")
            return " ".join(argv) if isinstance(argv, list) else str(argv or "")
    return str(payload.get("gateId") or "")


def _transition_run(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    project_id: str | None,
    session_id: str | None,
    from_status: str,
    to_status: str,
    summary: str,
    verifier_id: str,
) -> None:
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    assignments = ["status = ?", "status_reason_json = ?", "updated_at = ?"]
    values: list[Any] = [
        to_status,
        json.dumps({"kind": "verify-run", "verifier_id": verifier_id}),
        now,
    ]
    if to_status == "completed":
        assignments.append("completed_at = ?")
        values.append(now)
    conn.execute(
        f"UPDATE orchestration_runs SET {', '.join(assignments)} WHERE id = ?",
        (*values, run_id),
    )
    conn.execute(
        """
        INSERT INTO orchestration_run_events (
            id, run_id, project_id, session_id, event_type, from_status,
            to_status, summary, reason_json, metadata_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"run-event-{uuid.uuid4()}",
            run_id,
            project_id,
            session_id,
            "verify_run",
            from_status,
            to_status,
            summary,
            json.dumps({"source": "verify-run"}),
            json.dumps({"verifier_id": verifier_id}),
            now,
        ),
    )


def _update_resume_snapshot(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    current_stage: str,
    next_recommended_action: str,
    verification_result: str,
    verifier_id: str,
    evidence_ref_count: int,
    blocking_issue_count: int,
) -> None:
    columns = {str(row[1]) for row in conn.execute("PRAGMA table_info(orchestration_runs)")}
    if "resume_snapshot_json" not in columns:
        return
    row = conn.execute(
        "SELECT resume_snapshot_json FROM orchestration_runs WHERE id = ? LIMIT 1",
        (run_id,),
    ).fetchone()
    if row is None:
        return
    try:
        snapshot = json.loads(str(row[0] or "{}"))
    except json.JSONDecodeError:
        snapshot = {}
    if not isinstance(snapshot, dict):
        snapshot = {}
    snapshot.update(
        {
            "current_stage": current_stage,
            "next_recommended_action": next_recommended_action,
            "verification_result": verification_result,
            "verifier_id": verifier_id,
            "evidence_ref_count": evidence_ref_count,
            "blocking_issue_count": blocking_issue_count,
            "updated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    )
    conn.execute(
        "UPDATE orchestration_runs SET resume_snapshot_json = ? WHERE id = ?",
        (json.dumps(snapshot), run_id),
    )
