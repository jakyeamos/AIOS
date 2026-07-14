"""Capability, approval, egress, and closeout gates for durable effects."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from services.evidence_artifacts import is_usable_evidence, list_evidence_artifacts

EffectStatus = Literal[
    "proposed",
    "pending_approval",
    "approved",
    "rejected",
    "returned",
    "stale",
    "waived",
    "applied",
]

_EFFECT_STATUSES = {
    "proposed",
    "pending_approval",
    "approved",
    "rejected",
    "returned",
    "stale",
    "waived",
    "applied",
}
_TERMINAL_EFFECT_STATUSES = {"rejected", "stale", "applied"}
_ALLOWED_CAPABILITIES = {
    "aios.verify",
    "run.closeout",
    "writeback.propose",
    "writeback.review",
    "writeback.apply",
    "promotion.finalize",
}
_LOOPBACK_ORIGINS = {"loopback", "localhost", "127.0.0.1", "::1"}
_LOCAL_EGRESS_TARGETS = {"local", "loopback", "localhost"}


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


def _json_object(value: object) -> dict[str, Any]:
    if not isinstance(value, str):
        return value if isinstance(value, dict) else {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _json_list(value: object) -> list[Any]:
    if not isinstance(value, str):
        return value if isinstance(value, list) else []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ? LIMIT 1",
        (table,),
    ).fetchone()
    return row is not None


def ensure_governed_effect_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS governed_effect_events (
          event_id TEXT PRIMARY KEY,
          effect_id TEXT NOT NULL,
          run_id TEXT REFERENCES orchestration_runs(id),
          target TEXT NOT NULL,
          actor TEXT NOT NULL,
          capability TEXT NOT NULL,
          origin TEXT NOT NULL,
          egress_target TEXT NOT NULL,
          data_classification TEXT NOT NULL,
          redaction_status TEXT NOT NULL,
          rollback_ref TEXT,
          evidence_json TEXT NOT NULL DEFAULT '[]',
          from_status TEXT,
          to_status TEXT NOT NULL,
          note TEXT,
          created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_governed_effect_events_effect
          ON governed_effect_events(effect_id, created_at DESC)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS governed_closeout_reviews (
          review_id TEXT PRIMARY KEY,
          run_id TEXT NOT NULL REFERENCES orchestration_runs(id),
          status TEXT NOT NULL,
          actor TEXT NOT NULL,
          capability TEXT NOT NULL,
          origin TEXT NOT NULL,
          egress_target TEXT NOT NULL,
          data_classification TEXT NOT NULL,
          redaction_status TEXT NOT NULL,
          approval_state TEXT NOT NULL,
          verification_state TEXT NOT NULL,
          evidence_count INTEGER NOT NULL DEFAULT 0,
          changed_artifact_count INTEGER NOT NULL DEFAULT 0,
          unresolved_delta_count INTEGER NOT NULL DEFAULT 0,
          next_action TEXT,
          no_follow_up INTEGER NOT NULL DEFAULT 0,
          rollback_ref TEXT,
          blockers_json TEXT NOT NULL DEFAULT '[]',
          evidence_json TEXT NOT NULL DEFAULT '[]',
          created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_governed_closeout_reviews_run
          ON governed_closeout_reviews(run_id, created_at DESC)
        """
    )


def authorize_effect(
    *,
    capability: str,
    origin: str = "loopback",
    egress_target: str = "local",
    redaction_status: str = "not_required",
    egress_consent: bool = True,
    approval_state: str = "not_required",
    require_approval: bool = False,
) -> dict[str, Any]:
    normalized_capability = capability.strip().lower()
    normalized_origin = origin.strip().lower()
    normalized_target = egress_target.strip().lower()
    normalized_redaction = redaction_status.strip().lower()
    if normalized_capability not in _ALLOWED_CAPABILITIES:
        return _blocked("capability_denied", f"Capability is not allowed: {capability}")
    if normalized_origin not in _LOOPBACK_ORIGINS:
        return _blocked("loopback_required", "Privileged effects are loopback-only.")
    if normalized_target not in _LOCAL_EGRESS_TARGETS:
        return _blocked("egress_target_denied", "External egress is not enabled for AIOS.")
    if normalized_target not in {"local", "loopback"} and not egress_consent:
        return _blocked("egress_consent_required", "Egress requires explicit consent.")
    if normalized_target != "local" and normalized_redaction != "complete":
        return _blocked("redaction_incomplete", "Egress requires complete redaction evidence.")
    if require_approval and approval_state not in {"approved", "waived"}:
        return _blocked(
            "approval_required",
            f"Effect approval is {approval_state or 'missing'}, not approved or waived.",
        )
    return {"allowed": True, "code": "authorized", "reason": "Governed effect is authorized."}


def record_effect_event(
    conn: sqlite3.Connection,
    *,
    effect_id: str,
    run_id: str | None,
    target: str,
    actor: str,
    capability: str,
    origin: str,
    egress_target: str,
    data_classification: str,
    redaction_status: str,
    rollback_ref: str | None,
    evidence: list[str],
    from_status: str | None,
    to_status: EffectStatus,
    note: str | None,
) -> str:
    ensure_governed_effect_schema(conn)
    event_id = f"governed-effect-event-{uuid.uuid4()}"
    conn.execute(
        """
        INSERT INTO governed_effect_events (
          event_id, effect_id, run_id, target, actor, capability, origin,
          egress_target, data_classification, redaction_status, rollback_ref,
          evidence_json, from_status, to_status, note, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            effect_id,
            run_id,
            target,
            actor,
            capability,
            origin,
            egress_target,
            data_classification,
            redaction_status,
            rollback_ref,
            _json(evidence),
            from_status,
            to_status,
            note,
            _now_iso(),
        ),
    )
    return event_id


def transition_writeback(
    conn: sqlite3.Connection,
    *,
    writeback_id: str,
    to_status: EffectStatus,
    actor: str,
    note: str | None = None,
    capability: str = "writeback.review",
    origin: str = "loopback",
    egress_target: str = "local",
    egress_consent: bool = True,
    redaction_status: str = "not_required",
    data_classification: str = "internal",
    rollback_ref: str | None = None,
    evidence: list[str] | None = None,
) -> dict[str, Any]:
    ensure_governed_effect_schema(conn)
    if to_status not in _EFFECT_STATUSES:
        raise ValueError(f"Unsupported governed writeback status: {to_status}")
    row = conn.execute(
        """
        SELECT run_id, layer_type, layer_key, status, requires_approval,
               proposed_change_json, evidence_json
        FROM improvement_writebacks
        WHERE id = ?
        LIMIT 1
        """,
        (writeback_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Unknown writeback: {writeback_id}")
    run_id, layer_type, layer_key, current_status, requires_approval, proposed_json, evidence_json = row
    current = str(current_status or "")
    if current not in _EFFECT_STATUSES:
        raise ValueError(f"Writeback {writeback_id} has unsupported status: {current}")
    if current in _TERMINAL_EFFECT_STATUSES:
        raise ValueError(f"Writeback {writeback_id} is terminal at status {current!r}")
    if to_status == "approved" and current not in {"proposed", "pending_approval"}:
        raise ValueError(f"Writeback {writeback_id} cannot move {current!r} -> 'approved'")
    if to_status == "applied" and current != "approved":
        raise ValueError(f"Writeback {writeback_id} must be approved before it is applied")
    if to_status in {"returned", "stale", "waived", "rejected"} and not (note or "").strip():
        raise ValueError(f"A decision note is required for {to_status} writebacks")

    proposed = _json_object(proposed_json)
    governance = _json_object(proposed.get("governance"))
    effective_approval = "approved" if current == "approved" else current
    authorization = authorize_effect(
        capability=capability,
        origin=origin,
        egress_target=egress_target,
        egress_consent=egress_consent,
        redaction_status=redaction_status,
        approval_state=effective_approval,
        require_approval=to_status == "applied" and bool(requires_approval),
    )
    if not authorization["allowed"]:
        raise PermissionError(str(authorization["reason"]))

    now = _now_iso()
    effective_evidence = list(evidence or _json_list(evidence_json))
    governance_payload = {
        "target": governance.get("target") or f"{layer_type}:{layer_key}",
        "actor": actor,
        "capability": capability,
        "data_classification": data_classification,
        "redaction_status": redaction_status,
        "evidence_refs": effective_evidence,
        "approval_state": to_status,
        "rollback_ref": rollback_ref,
    }
    proposed["governance"] = governance_payload
    conn.execute(
        """
        UPDATE improvement_writebacks
        SET status = ?, proposed_change_json = ?, decision_note = ?,
            decision_actor = ?, decision_at = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            to_status,
            _json(proposed),
            note,
            actor,
            now,
            now,
            writeback_id,
        ),
    )
    event_id = record_effect_event(
        conn,
        effect_id=writeback_id,
        run_id=str(run_id) if run_id else None,
        target=str(governance_payload["target"]),
        actor=actor,
        capability=capability,
        origin=origin,
        egress_target=egress_target,
        data_classification=data_classification,
        redaction_status=redaction_status,
        rollback_ref=rollback_ref,
        evidence=effective_evidence,
        from_status=current,
        to_status=to_status,
        note=note,
    )
    return {
        "writeback_id": writeback_id,
        "event_id": event_id,
        "from_status": current,
        "to_status": to_status,
        "governance": governance_payload,
    }


def evaluate_governed_closeout(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    verification: dict[str, Any],
    actor: str = "aios-verify-run",
    capability: str = "aios.verify",
    origin: str = "loopback",
    egress_target: str = "local",
    egress_consent: bool = True,
    redaction_status: str = "not_required",
    data_classification: str = "internal",
    rollback_ref: str | None = None,
    no_follow_up: bool = False,
) -> dict[str, Any]:
    ensure_governed_effect_schema(conn)
    run_columns = {
        str(item[1]) for item in conn.execute("PRAGMA table_info(orchestration_runs)")
    }
    row = (
        conn.execute(
            "SELECT resume_snapshot_json FROM orchestration_runs WHERE id = ? LIMIT 1",
            (run_id,),
        ).fetchone()
        if "resume_snapshot_json" in run_columns
        else conn.execute(
            "SELECT id FROM orchestration_runs WHERE id = ? LIMIT 1",
            (run_id,),
        ).fetchone()
    )
    if row is None:
        return _blocked("run_not_found", f"Run not found: {run_id}")
    legacy_run_shape = "resume_snapshot_json" not in run_columns
    snapshot = _json_object(row[0]) if not legacy_run_shape else {}
    effective_no_follow_up = no_follow_up or legacy_run_shape
    next_action = str(snapshot.get("next_recommended_action") or "").strip()
    usable_evidence = [
        item for item in list_evidence_artifacts(conn, run_id=run_id, limit=200)
        if is_usable_evidence(item)
    ]
    changed_artifact_count = _changed_artifact_count(conn, run_id)
    unresolved_delta_count = _unresolved_delta_count(conn, run_id)
    approval_state = _approval_state(conn, run_id)
    blockers: list[str] = []
    authorization = authorize_effect(
        capability=capability,
        origin=origin,
        egress_target=egress_target,
        egress_consent=egress_consent,
        redaction_status=redaction_status,
        approval_state=approval_state,
        require_approval=False,
    )
    if not authorization["allowed"]:
        blockers.append(str(authorization["code"]))
    if not verification.get("allowed"):
        blockers.append(str(verification.get("code") or "verification_required"))
    if not usable_evidence:
        blockers.append("changed_artifacts_missing")
    if changed_artifact_count == 0:
        blockers.append("changed_files_not_reviewed")
    if unresolved_delta_count:
        blockers.append("unresolved_deltas")
    if not next_action and not effective_no_follow_up:
        blockers.append("next_action_missing")
    if approval_state == "pending":
        blockers.append("approval_required")
    elif approval_state in {"rejected", "returned", "stale"}:
        blockers.append(f"approval_{approval_state}")

    status = "closed" if not blockers else "needs_follow_up"
    review_id = f"closeout-review-{uuid.uuid4()}"
    conn.execute(
        """
        INSERT INTO governed_closeout_reviews (
          review_id, run_id, status, actor, capability, origin, egress_target,
          data_classification, redaction_status, approval_state, verification_state,
          evidence_count, changed_artifact_count, unresolved_delta_count,
          next_action, no_follow_up, rollback_ref, blockers_json, evidence_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            review_id,
            run_id,
            status,
            actor,
            capability,
            origin,
            egress_target,
            data_classification,
            redaction_status,
            approval_state,
            "passed" if verification.get("allowed") else "blocked",
            len(usable_evidence),
            changed_artifact_count,
            unresolved_delta_count,
            next_action or None,
            1 if effective_no_follow_up else 0,
            rollback_ref,
            _json(blockers),
            _json([str(item.get("evidence_id")) for item in usable_evidence]),
            _now_iso(),
        ),
    )
    return {
        "allowed": not blockers,
        "code": "closeout_allowed" if not blockers else "closeout_blocked",
        "reason": "Governed closeout is complete."
        if not blockers
        else "Closeout requires additional governed review.",
        "review_id": review_id,
        "status": status,
        "approval_state": approval_state,
        "evidence_count": len(usable_evidence),
        "changed_artifact_count": changed_artifact_count,
        "unresolved_delta_count": unresolved_delta_count,
        "next_action": next_action or None,
        "no_follow_up": effective_no_follow_up,
        "blockers": blockers,
    }


def _approval_state(conn: sqlite3.Connection, run_id: str) -> str:
    if not _table_exists(conn, "improvement_writebacks"):
        return "not_required"
    rows = conn.execute(
        """
        SELECT status, requires_approval
        FROM improvement_writebacks
        WHERE run_id = ? AND (requires_approval = 1 OR status IN ('pending_approval', 'proposed'))
        """,
        (run_id,),
    ).fetchall()
    if not rows:
        return "not_required"
    statuses = {str(row[0] or "") for row in rows}
    if "rejected" in statuses:
        return "rejected"
    if "returned" in statuses:
        return "returned"
    if "stale" in statuses:
        return "stale"
    if statuses and statuses <= {"approved", "waived"}:
        return "waived" if "waived" in statuses else "approved"
    return "pending"


def _changed_artifact_count(conn: sqlite3.Connection, run_id: str) -> int:
    if not _table_exists(conn, "verifier_artifacts"):
        return 0
    rows = conn.execute(
        """
        SELECT inputs_reviewed_json, result
        FROM verifier_artifacts
        WHERE run_id = ?
        ORDER BY created_at DESC
        LIMIT 20
        """,
        (run_id,),
    ).fetchall()
    return sum(
        1
        for inputs_json, result in rows
        if str(result) == "pass" and "changed_files" in {str(item) for item in _json_list(inputs_json)}
    )


def _unresolved_delta_count(conn: sqlite3.Connection, run_id: str) -> int:
    total = 0
    if _table_exists(conn, "success_criteria_stage_findings"):
        columns = {str(row[1]) for row in conn.execute("PRAGMA table_info(success_criteria_stage_findings)")}
        if "resolution_status" in columns:
            total += int(
                conn.execute(
                    "SELECT COUNT(*) FROM success_criteria_stage_findings WHERE run_id = ? AND resolution_status = 'open'",
                    (run_id,),
                ).fetchone()[0]
            )
        else:
            total += int(
                conn.execute(
                    "SELECT COUNT(*) FROM success_criteria_stage_findings WHERE run_id = ? AND level = 'blocker'",
                    (run_id,),
                ).fetchone()[0]
            )
    if _table_exists(conn, "success_criteria_findings"):
        columns = {str(row[1]) for row in conn.execute("PRAGMA table_info(success_criteria_findings)")}
        if "run_id" in columns and "resolution_status" in columns:
            total += int(
                conn.execute(
                    "SELECT COUNT(*) FROM success_criteria_findings WHERE run_id = ? AND resolution_status = 'open'",
                    (run_id,),
                ).fetchone()[0]
            )
        elif "run_id" in columns and "level" in columns:
            total += int(
                conn.execute(
                    "SELECT COUNT(*) FROM success_criteria_findings WHERE run_id = ? AND level = 'blocker'",
                    (run_id,),
                ).fetchone()[0]
            )
    return total


def _blocked(code: str, reason: str) -> dict[str, Any]:
    return {"allowed": False, "code": code, "reason": reason, "blockers": [code]}


__all__ = [
    "EffectStatus",
    "authorize_effect",
    "ensure_governed_effect_schema",
    "evaluate_governed_closeout",
    "record_effect_event",
    "transition_writeback",
]
