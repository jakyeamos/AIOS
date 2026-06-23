"""Durable verifier artifact helpers for independent closeout checks."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

VerifierResult = Literal["pass", "fail", "needs_work"]
NextPhase = Literal["closeout", "implementation_retry", "human_review"]


def ensure_verifier_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS verifier_artifacts (
          verifier_id TEXT PRIMARY KEY,
          task_id TEXT,
          run_id TEXT,
          session_id TEXT,
          verifier_agent TEXT,
          model TEXT,
          inputs_reviewed_json TEXT NOT NULL DEFAULT '[]',
          checks_performed_json TEXT NOT NULL DEFAULT '[]',
          result TEXT NOT NULL,
          blocking_issues_json TEXT NOT NULL DEFAULT '[]',
          non_blocking_issues_json TEXT NOT NULL DEFAULT '[]',
          recommended_next_phase TEXT NOT NULL,
          evidence_refs_json TEXT NOT NULL DEFAULT '[]',
          created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_verifier_artifacts_run
          ON verifier_artifacts(run_id, created_at DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_verifier_artifacts_session
          ON verifier_artifacts(session_id, created_at DESC)
        """
    )


def record_verifier_artifact(
    conn: sqlite3.Connection,
    *,
    task_id: str | None = None,
    run_id: str | None = None,
    session_id: str | None = None,
    verifier_agent: str | None = None,
    model: str | None = None,
    inputs_reviewed: list[str] | None = None,
    checks_performed: list[str] | None = None,
    result: VerifierResult,
    blocking_issues: list[Any] | None = None,
    non_blocking_issues: list[Any] | None = None,
    recommended_next_phase: NextPhase | None = None,
    evidence_refs: list[str] | None = None,
    verifier_id: str | None = None,
    created_at: str | None = None,
) -> str:
    ensure_verifier_schema(conn)
    normalized_result = _normalize_result(result)
    normalized_next = recommended_next_phase or _default_next_phase(normalized_result)
    artifact_id = verifier_id or str(uuid.uuid4())
    observed_at = created_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        """
        INSERT INTO verifier_artifacts (
          verifier_id, task_id, run_id, session_id, verifier_agent, model,
          inputs_reviewed_json, checks_performed_json, result, blocking_issues_json,
          non_blocking_issues_json, recommended_next_phase, evidence_refs_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            artifact_id,
            task_id,
            run_id,
            session_id,
            verifier_agent,
            model,
            json.dumps(inputs_reviewed or []),
            json.dumps(checks_performed or []),
            normalized_result,
            json.dumps(blocking_issues or []),
            json.dumps(non_blocking_issues or []),
            normalized_next,
            json.dumps(evidence_refs or []),
            observed_at,
        ),
    )
    return artifact_id


def list_verifier_artifacts(
    conn: sqlite3.Connection,
    *,
    run_id: str | None = None,
    session_id: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if run_id:
        clauses.append("run_id = ?")
        params.append(run_id)
    if session_id:
        clauses.append("session_id = ?")
        params.append(session_id)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    try:
        rows = conn.execute(
            f"""
            SELECT verifier_id, task_id, run_id, session_id, verifier_agent, model,
                   inputs_reviewed_json, checks_performed_json, result, blocking_issues_json,
                   non_blocking_issues_json, recommended_next_phase, evidence_refs_json, created_at
            FROM verifier_artifacts
            {where}
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (*params, max(1, min(limit, 500))),
        ).fetchall()
    except sqlite3.Error:
        return []
    columns = [
        "verifier_id",
        "task_id",
        "run_id",
        "session_id",
        "verifier_agent",
        "model",
        "inputs_reviewed_json",
        "checks_performed_json",
        "result",
        "blocking_issues_json",
        "non_blocking_issues_json",
        "recommended_next_phase",
        "evidence_refs_json",
        "created_at",
    ]
    return [dict(zip(columns, row, strict=True)) for row in rows]


def validate_closeout_verification(
    conn: sqlite3.Connection,
    *,
    task_id: str | None = None,
    run_id: str | None = None,
    session_id: str | None = None,
    workflow_key: str | None = None,
    implementation_bearing: bool,
    verification_exempt: bool = False,
    exemption_reason: str | None = None,
) -> dict[str, Any]:
    if not implementation_bearing:
        return _allowed("not_required", "Workflow is not implementation-bearing.")
    if verification_exempt:
        if exemption_reason:
            return _allowed("exempt", exemption_reason)
        return _blocked("verification_exemption_missing_reason", "Verification exemption lacks a reason.")

    rows = list_verifier_artifacts(conn, run_id=run_id, session_id=session_id, limit=20)
    if task_id:
        rows = [row for row in rows if not row.get("task_id") or row.get("task_id") == task_id]
    if not rows:
        return _blocked(
            "missing_verifier_artifact",
            f"Workflow {workflow_key or '<unknown>'} requires a fresh verifier artifact.",
        )

    row = rows[0]
    problems = _artifact_problems(row)
    if problems:
        return _blocked(
            "invalid_verifier_artifact",
            "; ".join(problems),
            row=row,
        )
    result = str(row.get("result") or "")
    next_phase = str(row.get("recommended_next_phase") or "")
    if result == "pass" and next_phase == "closeout":
        return _allowed("passed", "Fresh verifier artifact passed closeout.", row=row)
    return _blocked(
        f"verifier_{result or 'unknown'}",
        f"Verifier result {result or '<missing>'} routes to {next_phase or '<missing>'}.",
        row=row,
    )


def fresh_verifier_refs(
    conn: sqlite3.Connection,
    *,
    run_id: str | None = None,
    session_id: str | None = None,
) -> list[str]:
    refs: list[str] = []
    for row in list_verifier_artifacts(conn, run_id=run_id, session_id=session_id, limit=20):
        if not _artifact_problems(row):
            refs.append(format_verifier_ref(row))
    return refs


def format_verifier_ref(row: dict[str, Any]) -> str:
    return (
        f"verifier artifact: {row.get('verifier_id')} result={row.get('result')} "
        f"next={row.get('recommended_next_phase')}"
    )


def _artifact_problems(row: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    result = str(row.get("result") or "")
    next_phase = str(row.get("recommended_next_phase") or "")
    evidence_refs = _json_list(row.get("evidence_refs_json"))
    inputs = set(_json_list(row.get("inputs_reviewed_json")))
    blocking_issues = _json_list(row.get("blocking_issues_json"))
    if result not in {"pass", "fail", "needs_work"}:
        problems.append("result must be pass, fail, or needs_work")
    if next_phase not in {"closeout", "implementation_retry", "human_review"}:
        problems.append("recommended_next_phase is invalid")
    if result == "pass" and next_phase != "closeout":
        problems.append("pass verifier artifacts must route to closeout")
    if result in {"fail", "needs_work"} and next_phase == "closeout":
        problems.append("fail and needs_work verifier artifacts cannot route to closeout")
    required_inputs = {"task_spec", "changed_files", "evidence_artifacts"}
    missing_inputs = sorted(required_inputs - inputs)
    if missing_inputs:
        problems.append(f"missing reviewed inputs: {', '.join(missing_inputs)}")
    if not evidence_refs:
        problems.append("verifier artifact must cite evidence_refs")
    if blocking_issues and not all(_issue_has_citation(issue) for issue in blocking_issues):
        problems.append("blocking issues must cite files, commands, evidence IDs, or output paths")
    return problems


def _issue_has_citation(issue: Any) -> bool:
    if isinstance(issue, dict):
        citation_keys = {
            "file",
            "path",
            "command",
            "evidence_id",
            "evidence_ref",
            "output_path",
            "stdout_path",
            "stderr_path",
        }
        return any(str(issue.get(key) or "").strip() for key in citation_keys)
    text = str(issue)
    return any(token in text for token in ("evidence", "command", ".py", ".ts", ".md", "/"))


def _json_list(value: Any) -> list[str]:
    try:
        payload = json.loads(str(value or "[]"))
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    return [str(item) if not isinstance(item, dict) else json.dumps(item) for item in payload]


def _normalize_result(result: str) -> VerifierResult:
    if result not in {"pass", "fail", "needs_work"}:
        raise ValueError("Verifier result must be pass, fail, or needs_work.")
    return result


def _default_next_phase(result: VerifierResult) -> NextPhase:
    if result == "pass":
        return "closeout"
    if result == "needs_work":
        return "implementation_retry"
    return "human_review"


def _allowed(code: str, reason: str, row: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "allowed": True,
        "code": code,
        "reason": reason,
        "recommended_next_phase": row.get("recommended_next_phase") if row else "closeout",
        "verifier_id": row.get("verifier_id") if row else None,
        "evidence_refs": _json_list(row.get("evidence_refs_json")) if row else [],
    }


def _blocked(code: str, reason: str, row: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "allowed": False,
        "code": code,
        "reason": reason,
        "recommended_next_phase": row.get("recommended_next_phase") if row else "human_review",
        "verifier_id": row.get("verifier_id") if row else None,
        "evidence_refs": _json_list(row.get("evidence_refs_json")) if row else [],
    }
