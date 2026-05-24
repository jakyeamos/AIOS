from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, get_args

AssetKind = Literal["prompt", "skill", "workflow"]
AssetLifecycleState = Literal["draft", "candidate", "approved", "active", "deprecated"]

LIFECYCLE_TRANSITIONS: dict[AssetLifecycleState, frozenset[AssetLifecycleState]] = {
    "draft": frozenset({"candidate"}),
    "candidate": frozenset({"approved", "draft"}),
    "approved": frozenset({"active"}),
    "active": frozenset({"candidate", "deprecated"}),
    "deprecated": frozenset(),
}

_ASSET_KINDS = set(get_args(AssetKind))
_LIFECYCLE_STATES = set(get_args(AssetLifecycleState))
ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class AssetRecord:
    kind: AssetKind
    key: str
    purpose: str
    applicability: tuple[str, ...]
    lifecycle_state: AssetLifecycleState
    usefulness_evidence: dict[str, Any]
    last_evaluated_at: str | None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LifecycleTransition:
    asset_kind: AssetKind
    asset_key: str
    from_state: AssetLifecycleState | None
    to_state: AssetLifecycleState
    actor: str
    rationale: str
    evidence_ids: tuple[str, ...]
    requires_approval: bool
    approval_writeback_id: str | None
    transitioned_at: str


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True)


def _coerce_asset_kind(value: str) -> AssetKind:
    if value not in _ASSET_KINDS:
        raise ValueError(f"Unsupported asset kind: {value}")
    return value  # type: ignore[return-value]


def _coerce_lifecycle_state(value: str) -> AssetLifecycleState:
    if value not in _LIFECYCLE_STATES:
        raise ValueError(f"Unsupported lifecycle state: {value}")
    return value  # type: ignore[return-value]


def _json_dict(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def ensure_asset_lifecycle_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS promotion_lifecycle_items (
          id TEXT PRIMARY KEY,
          item_kind TEXT NOT NULL,
          item_key TEXT NOT NULL,
          source_run_id TEXT,
          status TEXT NOT NULL CHECK (
            status IN ('draft', 'candidate', 'approved', 'active', 'deprecated')
          ),
          evidence_json TEXT NOT NULL DEFAULT '[]',
          status_reason TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          metadata_json TEXT NOT NULL DEFAULT '{}'
        )
        """
    )


def ensure_lifecycle_writeback_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS improvement_writebacks (
          id TEXT PRIMARY KEY,
          run_id TEXT,
          project_id TEXT,
          layer_type TEXT NOT NULL,
          layer_key TEXT NOT NULL,
          title TEXT NOT NULL,
          summary TEXT NOT NULL,
          evidence_json TEXT NOT NULL DEFAULT '[]',
          proposed_change_json TEXT NOT NULL DEFAULT '{}',
          impact_scope TEXT NOT NULL DEFAULT 'scoped',
          status TEXT NOT NULL DEFAULT 'proposed',
          requires_approval INTEGER NOT NULL DEFAULT 0,
          approval_reason TEXT,
          token_regressive INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          decision_note TEXT,
          decision_actor TEXT,
          decision_at TEXT
        )
        """
    )


def writeback_approval_policy_shim(
    *,
    layer_type: str,
    impact_scope: str,
    proposed_change: dict[str, Any],
) -> dict[str, Any]:
    # DUPLICATED FROM bin/aios_orchestration_runtime.writeback_approval_policy to respect
    # services -> bin import boundary. Consolidate in Phase 9 per RESEARCH.md A4.
    normalized_layer = layer_type.strip().lower()
    normalized_scope = impact_scope.strip().lower()
    high_impact_layers = {"truth", "standard", "standards", "prompt", "skill", "workflow", "packet"}
    high_impact_scopes = {
        "global",
        "project-truth",
        "workflow-default",
        "prompt-default",
        "skill-default",
    }
    destructive = bool(
        proposed_change.get("destructive") or proposed_change.get("destructive_action")
    )
    if destructive:
        policy_class = "destructive_action"
        reason = "Destructive or irreversible changes require approval before promotion."
    elif normalized_scope in high_impact_scopes:
        policy_class = f"{normalized_scope}_change"
        reason = f"{impact_scope} changes require approval before promotion."
    elif normalized_layer in high_impact_layers:
        policy_class = f"{normalized_layer}_asset_change"
        reason = f"{layer_type} changes require approval before promotion."
    else:
        policy_class = "scoped_project_memory"
        reason = None
    return {
        "policy_class": policy_class,
        "requires_approval": policy_class != "scoped_project_memory",
        "reason": reason,
    }


def _insert_lifecycle_writeback(
    conn: sqlite3.Connection,
    *,
    asset_kind: AssetKind,
    asset_key: str,
    proposed_change: dict[str, Any],
    rationale: str,
    actor: str,
    policy: dict[str, Any],
    now: str,
) -> str:
    ensure_lifecycle_writeback_schema(conn)
    writeback_id = f"writeback-{uuid.uuid4()}"
    payload = dict(proposed_change)
    payload.setdefault("approval_policy", policy)
    conn.execute(
        """
        INSERT INTO improvement_writebacks (
            id,
            run_id,
            project_id,
            layer_type,
            layer_key,
            title,
            summary,
            evidence_json,
            proposed_change_json,
            impact_scope,
            status,
            requires_approval,
            approval_reason,
            token_regressive,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            writeback_id,
            None,
            None,
            asset_kind,
            asset_key,
            f"Promote {asset_kind} {asset_key}",
            rationale,
            _json([]),
            _json({**payload, "actor": actor}),
            f"{asset_kind}-default",
            "pending_approval" if policy["requires_approval"] else "proposed",
            1 if policy["requires_approval"] else 0,
            policy.get("reason"),
            0,
            now,
            now,
        ),
    )
    return writeback_id


def promote_asset(
    conn: sqlite3.Connection,
    *,
    asset_kind: AssetKind,
    asset_key: str,
    from_state: AssetLifecycleState,
    to_state: AssetLifecycleState,
    actor: str,
    rationale: str,
    evidence_ids: tuple[str, ...] = (),
    proposed_change: dict[str, Any] | None = None,
) -> LifecycleTransition:
    ensure_asset_lifecycle_schema(conn)
    if to_state not in LIFECYCLE_TRANSITIONS.get(from_state, frozenset()):
        raise ValueError(
            f"Illegal transition {from_state} -> {to_state} for {asset_kind} {asset_key}"
        )

    now = _now_iso()
    policy: dict[str, Any] | None = None
    writeback_id: str | None = None
    if to_state == "active":
        change = proposed_change or {
            "asset_kind": asset_kind,
            "asset_key": asset_key,
            "to_state": to_state,
        }
        policy = writeback_approval_policy_shim(
            layer_type=asset_kind,
            impact_scope=f"{asset_kind}-default",
            proposed_change=change,
        )
        if policy["requires_approval"]:
            writeback_id = _insert_lifecycle_writeback(
                conn,
                asset_kind=asset_kind,
                asset_key=asset_key,
                proposed_change=change,
                rationale=rationale,
                actor=actor,
                policy=policy,
                now=now,
            )

    lifecycle_id = f"promo-asset-{uuid.uuid4()}"
    conn.execute(
        """
        INSERT INTO promotion_lifecycle_items (
          id,
          item_kind,
          item_key,
          source_run_id,
          status,
          evidence_json,
          status_reason,
          created_at,
          updated_at,
          metadata_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            lifecycle_id,
            asset_kind,
            asset_key,
            None,
            to_state,
            _json({"transition_evidence_ids": list(evidence_ids), "rationale": rationale}),
            rationale,
            now,
            now,
            _json(
                {
                    "actor": actor,
                    "from_state": from_state,
                    "approval_writeback_id": writeback_id,
                }
            ),
        ),
    )
    return LifecycleTransition(
        asset_kind=asset_kind,
        asset_key=asset_key,
        from_state=from_state,
        to_state=to_state,
        actor=actor,
        rationale=rationale,
        evidence_ids=evidence_ids,
        requires_approval=bool(policy["requires_approval"]) if policy else False,
        approval_writeback_id=writeback_id,
        transitioned_at=now,
    )


def _prompt_registry_records() -> dict[str, dict[str, Any]]:
    path = ROOT / "prompts" / "registry.json"
    try:
        with path.open("r", encoding="utf-8") as handle:
            loaded = json.load(handle)
    except FileNotFoundError:
        return {}
    templates = loaded.get("templates", []) if isinstance(loaded, dict) else []
    if not isinstance(templates, list):
        return {}
    return {str(row.get("id")): row for row in templates if isinstance(row, dict) and row.get("id")}


def _registry_metadata(
    kind: AssetKind, key: str
) -> tuple[str, tuple[str, ...], dict[str, Any], str | None]:
    try:
        if kind == "prompt":
            row = _prompt_registry_records().get(key, {})
            purpose = str(row.get("purpose", ""))
            applicability = tuple(
                str(item)
                for item in (
                    row.get("applicability") or row.get("applicable_workflow_families") or []
                )
                if isinstance(item, str)
            )
            evidence = row.get("usefulness_evidence") or {}
            last_evaluated_at = row.get("last_evaluated_at")
            return (
                purpose,
                applicability,
                evidence if isinstance(evidence, dict) else {},
                str(last_evaluated_at) if last_evaluated_at else None,
            )
        if kind == "skill":
            from services.workflow_orchestration import load_skill_registry

            spec = load_skill_registry().get(key)
            if spec is None:
                return "", (), {}, None
            return spec.purpose, spec.applicability, {}, None
        from services.workflow_orchestration import load_workflow_registry

        workflow = load_workflow_registry().get(key)
        if workflow is None:
            return "", (), {}, None
        return workflow.purpose, workflow.applicability, {}, None
    except (OSError, ValueError):
        return "", (), {}, None


def list_assets(
    conn: sqlite3.Connection,
    *,
    kind: AssetKind | None = None,
    state: AssetLifecycleState | None = None,
) -> list[AssetRecord]:
    ensure_asset_lifecycle_schema(conn)
    rows = conn.execute(
        """
        SELECT item_kind, item_key, status, evidence_json, updated_at, metadata_json
        FROM promotion_lifecycle_items
        WHERE (? IS NULL OR item_kind = ?)
          AND (? IS NULL OR status = ?)
        ORDER BY updated_at DESC
        """,
        (kind, kind, state, state),
    ).fetchall()
    assets: list[AssetRecord] = []
    for row in rows:
        item_kind = str(row[0])
        status = str(row[2])
        if item_kind not in _ASSET_KINDS or status not in _LIFECYCLE_STATES:
            continue
        asset_kind = _coerce_asset_kind(item_kind)
        lifecycle_state = _coerce_lifecycle_state(status)
        purpose, applicability, usefulness_evidence, last_evaluated_at = _registry_metadata(
            asset_kind,
            str(row[1]),
        )
        evidence_json = _json_dict(row[3])
        assets.append(
            AssetRecord(
                kind=asset_kind,
                key=str(row[1]),
                purpose=purpose,
                applicability=applicability,
                lifecycle_state=lifecycle_state,
                usefulness_evidence=usefulness_evidence or evidence_json,
                last_evaluated_at=last_evaluated_at,
                metadata=_json_dict(row[5]),
            )
        )
    return assets
