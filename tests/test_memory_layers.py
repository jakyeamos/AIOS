# ruff: noqa: E402

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "bin"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BIN))

from aios_orchestration_runtime import ensure_runtime_schema  # noqa: E402

from services.memory_layers import (  # noqa: E402
    ALLOWED_PREDICATES,
    VALIDITY_STATUSES,
    FactMemory,
    PacketReceiptLog,
    RawSourceMemory,
    RelationshipMemory,
    ensure_memory_layer_schema,
)


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


def test_raw_source_insert_and_get() -> None:
    conn = _connect()
    raw_sources = RawSourceMemory(conn)

    source_id = raw_sources.insert(
        id="raw-1",
        source_type="session",
        source_path="logs/session.md",
        project_id="aios",
        author="codex",
        confidence=0.9,
        original_content="A useful session artifact.",
    )

    row = raw_sources.get(source_id)
    assert row is not None
    assert row["id"] == "raw-1"
    assert row["source_type"] == "session"
    assert row["extraction_status"] == "pending"
    assert raw_sources.query(project_id="aios")[0]["source_path"] == "logs/session.md"


def test_fact_validity_status() -> None:
    conn = _connect()
    raw_sources = RawSourceMemory(conn)
    source_id = raw_sources.insert(source_type="project_truth")
    facts = FactMemory(conn)

    active_id = facts.insert(
        fact_text="AIOS has a layered memory model.",
        entity="AIOS",
        predicate="has_architecture",
        object_value="layered memory",
        project_scope="aios",
        source_id=source_id,
        confidence=0.85,
    )
    facts.insert(
        fact_text="Old memory shape was flat.",
        project_scope="aios",
        validity_status="superseded",
        source_id=source_id,
    )

    active = facts.get(active_id)
    assert active is not None
    assert active["validity_status"] == "active"
    assert "superseded" in VALIDITY_STATUSES
    assert [row["fact_text"] for row in facts.query(validity_status="active")] == [
        "AIOS has a layered memory model."
    ]


def test_fact_unknown_validity_status_raises() -> None:
    conn = _connect()
    facts = FactMemory(conn)

    with pytest.raises(ValueError, match="Unsupported memory fact validity_status"):
        facts.insert(fact_text="Unclear memory.", validity_status="maybe")


def test_relationship_predicate_validation() -> None:
    conn = _connect()
    raw_sources = RawSourceMemory(conn)
    source_id = raw_sources.insert(source_type="audit")
    relationships = RelationshipMemory(conn)

    relationship_id = relationships.insert(
        subject_id="fact-1",
        predicate="supports",
        object_id="decision-1",
        project_scope="aios",
        confidence=0.75,
        source_id=source_id,
    )

    row = relationships.get(relationship_id)
    assert row is not None
    assert row["predicate"] == "supports"
    assert "contradicts" in ALLOWED_PREDICATES
    assert relationships.query(predicate="supports")[0]["object_id"] == "decision-1"


def test_predicate_unknown_raises() -> None:
    conn = _connect()
    relationships = RelationshipMemory(conn)

    with pytest.raises(ValueError, match="Unsupported memory relationship predicate"):
        relationships.insert(subject_id="fact-1", predicate="handwaves", object_id="fact-2")


def test_packet_receipt_insert_get_and_query() -> None:
    conn = _connect()
    receipts = PacketReceiptLog(conn)

    receipt_id = receipts.insert(
        id="receipt-1",
        packet_id="packet-1",
        source_ids=["raw-1"],
        fact_ids=["fact-1"],
        relationship_ids=["rel-1"],
        token_count=321,
        mode="compact",
    )

    row = receipts.get(receipt_id)
    assert row is not None
    assert row["source_ids"] == ["raw-1"]
    assert row["fact_ids"] == ["fact-1"]
    assert row["relationship_ids"] == ["rel-1"]
    assert receipts.query(packet_id="packet-1", mode="compact")[0]["token_count"] == 321


def test_schema_migration_idempotent() -> None:
    conn = _connect()

    ensure_memory_layer_schema(conn)
    ensure_memory_layer_schema(conn)

    tables = {
        row["name"]
        for row in conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name LIKE 'memory_%'
            """
        ).fetchall()
    }
    assert {
        "memory_raw_sources",
        "memory_facts",
        "memory_relationships",
        "memory_packet_receipts",
    }.issubset(tables)


def test_runtime_schema_installs_memory_tables() -> None:
    conn = _connect()
    conn.execute("CREATE TABLE sessions (id TEXT PRIMARY KEY)")

    ensure_runtime_schema(conn)

    tables = {
        row["name"]
        for row in conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name LIKE 'memory_%'
            """
        ).fetchall()
    }
    assert {
        "memory_raw_sources",
        "memory_facts",
        "memory_relationships",
        "memory_packet_receipts",
    }.issubset(tables)
