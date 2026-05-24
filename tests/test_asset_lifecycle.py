from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bin.aios_orchestration_runtime import writeback_approval_policy  # noqa: E402
from services.asset_lifecycle import (  # noqa: E402
    LIFECYCLE_TRANSITIONS,
    ensure_asset_lifecycle_schema,
    list_assets,
    promote_asset,
    writeback_approval_policy_shim,
)
from services.divergent_strategy import (  # noqa: E402
    ensure_divergent_schema,
    transition_promotion_lifecycle,
)


def _load_migration_module() -> Any:
    path = ROOT / "bin" / "migrate-lifecycle-statuses.py"
    spec = importlib.util.spec_from_file_location("migrate_lifecycle_statuses", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _conn() -> sqlite3.Connection:
    return sqlite3.connect(":memory:")


def _legacy_lifecycle_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE promotion_lifecycle_items (
          id TEXT PRIMARY KEY,
          item_kind TEXT NOT NULL,
          item_key TEXT NOT NULL,
          source_run_id TEXT,
          status TEXT NOT NULL,
          evidence_json TEXT NOT NULL DEFAULT '[]',
          status_reason TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          metadata_json TEXT NOT NULL DEFAULT '{}'
        )
        """
    )


def test_lifecycle_transitions_table_enforces_legal_moves() -> None:
    assert LIFECYCLE_TRANSITIONS == {
        "draft": frozenset({"candidate"}),
        "candidate": frozenset({"approved", "draft"}),
        "approved": frozenset({"active"}),
        "active": frozenset({"candidate", "deprecated"}),
        "deprecated": frozenset(),
    }


def test_promote_asset_rejects_invalid_transition() -> None:
    conn = _conn()
    ensure_asset_lifecycle_schema(conn)

    with pytest.raises(ValueError, match="Illegal transition draft -> active"):
        promote_asset(
            conn,
            asset_kind="prompt",
            asset_key="research",
            from_state="draft",
            to_state="active",
            actor="op",
            rationale="skip states",
        )

    count = conn.execute("SELECT COUNT(*) FROM promotion_lifecycle_items").fetchone()[0]
    assert count == 0


def test_promote_asset_writes_lifecycle_transition_row() -> None:
    conn = _conn()
    transition = promote_asset(
        conn,
        asset_kind="prompt",
        asset_key="research",
        from_state="candidate",
        to_state="approved",
        actor="op",
        rationale="validated",
        evidence_ids=("eval-1",),
    )

    row = conn.execute(
        """
        SELECT item_kind, item_key, status, evidence_json, status_reason, created_at, updated_at
        FROM promotion_lifecycle_items
        """
    ).fetchone()
    assert transition.to_state == "approved"
    assert row[0] == "prompt"
    assert row[1] == "research"
    assert row[2] == "approved"
    assert json.loads(row[3])["transition_evidence_ids"] == ["eval-1"]
    assert row[4] == "validated"
    assert row[5]
    assert row[6]


def test_promote_asset_to_active_requires_writeback() -> None:
    conn = _conn()
    transition = promote_asset(
        conn,
        asset_kind="workflow",
        asset_key="implementation-delivery",
        from_state="approved",
        to_state="active",
        actor="op",
        rationale="make default",
    )

    assert transition.requires_approval is True
    assert transition.approval_writeback_id is not None
    writebacks = conn.execute("SELECT COUNT(*) FROM improvement_writebacks").fetchone()[0]
    lifecycle_rows = conn.execute("SELECT COUNT(*) FROM promotion_lifecycle_items").fetchone()[0]
    assert writebacks == 1
    assert lifecycle_rows == 1


def test_writeback_approval_policy_shim_matches_phase_5_for_three_scopes() -> None:
    for layer_type, impact_scope in (
        ("prompt", "prompt-default"),
        ("skill", "skill-default"),
        ("workflow", "workflow-default"),
    ):
        change = {"asset_key": "x"}
        assert writeback_approval_policy_shim(
            layer_type=layer_type,
            impact_scope=impact_scope,
            proposed_change=change,
        ) == writeback_approval_policy(
            layer_type=layer_type,
            impact_scope=impact_scope,
            proposed_change=change,
        )


def test_list_assets_filters_by_kind_and_state() -> None:
    conn = _conn()
    ensure_asset_lifecycle_schema(conn)
    for item_kind, item_key, status in (
        ("prompt", "research", "active"),
        ("skill", "agentize_intent_compiler", "candidate"),
        ("workflow", "implementation-delivery", "deprecated"),
    ):
        conn.execute(
            """
            INSERT INTO promotion_lifecycle_items (
              id, item_kind, item_key, source_run_id, status, evidence_json,
              status_reason, created_at, updated_at, metadata_json
            )
            VALUES (?, ?, ?, NULL, ?, '{}', 'seed', '2026-05-24T00:00:00Z',
                    '2026-05-24T00:00:00Z', '{}')
            """,
            (f"id-{item_key}", item_kind, item_key, status),
        )

    assert [asset.key for asset in list_assets(conn, kind="prompt")] == ["research"]
    assert [asset.key for asset in list_assets(conn, state="candidate")] == [
        "agentize_intent_compiler"
    ]
    assert len(list_assets(conn)) == 3


def test_ensure_asset_lifecycle_schema_is_idempotent() -> None:
    conn = _conn()
    ensure_asset_lifecycle_schema(conn)
    ensure_asset_lifecycle_schema(conn)
    columns = {
        row[1] for row in conn.execute("PRAGMA table_info(promotion_lifecycle_items)").fetchall()
    }
    assert {
        "id",
        "item_kind",
        "item_key",
        "source_run_id",
        "status",
        "evidence_json",
        "status_reason",
        "created_at",
        "updated_at",
        "metadata_json",
    } <= columns


def test_migration_remaps_legacy_statuses() -> None:
    conn = _conn()
    _legacy_lifecycle_schema(conn)
    statuses = [
        "promoted",
        "rejected",
        "pending",
        "candidate",
        "approved",
        "active",
        "deprecated",
        "draft",
    ]
    for status in statuses:
        conn.execute(
            """
            INSERT INTO promotion_lifecycle_items (
              id, item_kind, item_key, status, evidence_json, status_reason,
              created_at, updated_at, metadata_json
            )
            VALUES (?, 'prompt', ?, ?, '{}', 'seed', 'old', 'old', '{}')
            """,
            (f"id-{status}", status, status),
        )

    module = _load_migration_module()
    module.migrate_lifecycle_statuses(conn, dry_run=False)
    found = dict(conn.execute("SELECT item_key, status FROM promotion_lifecycle_items").fetchall())
    assert found["promoted"] == "candidate"
    assert found["rejected"] == "deprecated"
    assert found["pending"] == "candidate"
    assert found["candidate"] == "candidate"
    assert found["approved"] == "approved"
    assert found["active"] == "active"
    assert found["deprecated"] == "deprecated"
    assert found["draft"] == "draft"


def test_migration_is_idempotent() -> None:
    conn = _conn()
    _legacy_lifecycle_schema(conn)
    conn.execute(
        """
        INSERT INTO promotion_lifecycle_items (
          id, item_kind, item_key, status, evidence_json, status_reason,
          created_at, updated_at, metadata_json
        )
        VALUES ('id-promoted', 'prompt', 'research', 'promoted', '{}', 'seed', 'old', 'old', '{}')
        """
    )
    module = _load_migration_module()
    module.migrate_lifecycle_statuses(conn, dry_run=False)
    first = conn.execute("SELECT status, updated_at FROM promotion_lifecycle_items").fetchone()
    module.migrate_lifecycle_statuses(conn, dry_run=False)
    second = conn.execute("SELECT status, updated_at FROM promotion_lifecycle_items").fetchone()
    assert first == second


def test_migration_leaves_non_asset_item_kind_untouched() -> None:
    conn = _conn()
    _legacy_lifecycle_schema(conn)
    conn.execute(
        """
        INSERT INTO promotion_lifecycle_items (
          id, item_kind, item_key, status, evidence_json, status_reason,
          created_at, updated_at, metadata_json
        )
        VALUES ('id-memory', 'memory', 'memory-1', 'promoted', '{}', 'seed', 'old', 'old', '{}')
        """
    )
    module = _load_migration_module()
    module.migrate_lifecycle_statuses(conn, dry_run=False)
    assert conn.execute("SELECT status FROM promotion_lifecycle_items").fetchone()[0] == "promoted"


def test_migration_emits_dry_run_summary() -> None:
    conn = _conn()
    _legacy_lifecycle_schema(conn)
    conn.execute(
        """
        INSERT INTO promotion_lifecycle_items (
          id, item_kind, item_key, status, evidence_json, status_reason,
          created_at, updated_at, metadata_json
        )
        VALUES ('id-pending', 'skill', 'skill-1', 'pending', '{}', 'seed', 'old', 'old', '{}')
        """
    )
    module = _load_migration_module()
    summary = module.migrate_lifecycle_statuses(conn, dry_run=True)
    assert summary["dry_run"] is True
    assert summary["remapped"] == {"pending": 1}
    assert conn.execute("SELECT status FROM promotion_lifecycle_items").fetchone()[0] == "pending"


def test_divergent_strategy_writer_uses_five_state_literal() -> None:
    conn = _conn()
    conn.row_factory = sqlite3.Row
    ensure_divergent_schema(conn)
    with pytest.raises(ValueError, match="Unsupported lifecycle status"):
        transition_promotion_lifecycle(
            conn,
            item_id="item-1",
            item_kind="skill",
            item_key="candidate-skill",
            requested_status="promoted",  # type: ignore[arg-type]
            source_run_id=None,
            evidence=[],
        )
    accepted = transition_promotion_lifecycle(
        conn,
        item_id="item-1",
        item_kind="skill",
        item_key="candidate-skill",
        requested_status="candidate",
        source_run_id=None,
        evidence=[],
    )
    assert accepted["status"] == "candidate"
