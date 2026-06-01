from __future__ import annotations

import json
import re
import sqlite3
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.operator_search import ENTITY_KINDS, OperatorSearchHit, search_entities  # noqa: E402


def _make_db(*, all_tables: bool = True) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE orchestration_runs (
          id TEXT PRIMARY KEY,
          objective TEXT,
          workflow_key TEXT,
          project_id TEXT,
          status TEXT,
          route_result_json TEXT,
          created_at TEXT,
          updated_at TEXT
        );
        """
    )
    if not all_tables:
        return conn
    conn.executescript(
        """
        CREATE TABLE briefing_packets (
          id TEXT PRIMARY KEY,
          run_id TEXT,
          project_id TEXT,
          summary TEXT,
          created_at TEXT,
          updated_at TEXT
        );
        CREATE TABLE improvement_writebacks (
          id TEXT PRIMARY KEY,
          run_id TEXT,
          project_id TEXT,
          layer_type TEXT,
          layer_key TEXT,
          title TEXT,
          summary TEXT,
          status TEXT,
          proposed_change_json TEXT,
          created_at TEXT,
          updated_at TEXT
        );
        CREATE TABLE success_criteria_findings (
          id TEXT PRIMARY KEY,
          run_id TEXT,
          criterion_id TEXT,
          level TEXT,
          message TEXT,
          resolution_status TEXT,
          created_at TEXT,
          updated_at TEXT
        );
        CREATE TABLE prompts (
          id TEXT PRIMARY KEY,
          title TEXT,
          classification TEXT,
          summary TEXT,
          created_at TEXT,
          updated_at TEXT
        );
        CREATE TABLE prompts_used (
          id TEXT PRIMARY KEY,
          template_id TEXT,
          classification TEXT,
          outcome_score REAL,
          created_at TEXT,
          updated_at TEXT
        );
        CREATE TABLE workflow_skill_experiments (
          id TEXT PRIMARY KEY,
          workflow_key TEXT,
          skill_key TEXT,
          created_at TEXT,
          updated_at TEXT
        );
        CREATE TABLE knowledge_objects (
          id TEXT PRIMARY KEY,
          kind TEXT,
          key TEXT,
          title TEXT,
          summary TEXT,
          project_id TEXT,
          created_at TEXT,
          updated_at TEXT
        );
        CREATE TABLE standards_delta_items (
          id TEXT PRIMARY KEY,
          project_id TEXT,
          domain TEXT,
          priority_bucket TEXT,
          summary TEXT,
          created_at TEXT,
          updated_at TEXT
        );
        CREATE TABLE standards_backfill_tasks (
          id TEXT PRIMARY KEY,
          project_id TEXT,
          summary TEXT,
          status TEXT,
          created_at TEXT,
          updated_at TEXT
        );
        CREATE TABLE automations (
          id TEXT PRIMARY KEY,
          key TEXT,
          summary TEXT,
          created_at TEXT,
          updated_at TEXT
        );
        CREATE TABLE experiments (
          id TEXT PRIMARY KEY,
          summary TEXT,
          created_at TEXT,
          updated_at TEXT
        );
        CREATE TABLE divergent_runs (
          id TEXT PRIMARY KEY,
          objective TEXT,
          project_id TEXT,
          summary TEXT,
          created_at TEXT,
          updated_at TEXT
        );
        CREATE TABLE workflow_learning_events (
          id TEXT PRIMARY KEY,
          run_id TEXT,
          signal_kind TEXT,
          rationale TEXT,
          created_at TEXT,
          updated_at TEXT
        );
        CREATE TABLE promotion_lifecycle_items (
          id TEXT PRIMARY KEY,
          item_kind TEXT,
          item_key TEXT,
          source_run_id TEXT,
          status TEXT,
          created_at TEXT,
          updated_at TEXT
        );
        """
    )
    return conn


def _seed_run(
    conn: sqlite3.Connection,
    *,
    id_: str = "run-alpha",
    objective: str = "alpha implementation",
    project_id: str | None = "p1",
    workflow_key: str | None = "implementation-delivery",
    status: str = "completed",
    route_result_json: str | None = None,
    created_at: str = "2026-06-01T00:00:00Z",
    updated_at: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO orchestration_runs (
          id, objective, workflow_key, project_id, status, route_result_json, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            id_,
            objective,
            workflow_key,
            project_id,
            status,
            route_result_json,
            created_at,
            updated_at or created_at,
        ),
    )


def _seed_all_kinds(conn: sqlite3.Connection) -> None:
    _seed_run(conn, route_result_json=json.dumps({"workflow_key": "alpha-route"}))
    conn.execute(
        "INSERT INTO briefing_packets VALUES (?, ?, ?, ?, ?, ?)",
        ("packet-alpha", "run-alpha", "p1", "alpha packet", "2026-06-01T00:00:00Z", None),
    )
    conn.execute(
        "INSERT INTO improvement_writebacks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "writeback-alpha",
            "run-alpha",
            "p1",
            "workflow",
            "alpha-workflow",
            "alpha writeback",
            "safe summary",
            "proposed",
            json.dumps({"secret": "do-not-return"}),
            "2026-06-01T00:00:00Z",
            None,
        ),
    )
    conn.execute(
        "INSERT INTO success_criteria_findings VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "finding-alpha",
            "run-alpha",
            "criterion-alpha",
            "blocker",
            "alpha finding",
            "open",
            "2026-06-01T00:00:00Z",
            None,
        ),
    )
    conn.execute(
        "INSERT INTO prompts VALUES (?, ?, ?, ?, ?, ?)",
        ("prompt-alpha", "alpha prompt", "alpha", "prompt summary", "2026-06-01T00:00:00Z", None),
    )
    conn.execute(
        "INSERT INTO prompts_used VALUES (?, ?, ?, ?, ?, ?)",
        ("prompt-use-alpha", "prompt-alpha", "alpha", 0.8, "2026-06-01T00:00:00Z", None),
    )
    conn.execute(
        "INSERT INTO workflow_skill_experiments VALUES (?, ?, ?, ?, ?)",
        (
            "skill-exp-alpha",
            "implementation-delivery",
            "alpha-skill",
            "2026-06-01T00:00:00Z",
            None,
        ),
    )
    conn.execute(
        "INSERT INTO knowledge_objects VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "knowledge-alpha",
            "note",
            "alpha-key",
            "alpha knowledge",
            "knowledge summary",
            "p1",
            "2026-06-01T00:00:00Z",
            None,
        ),
    )
    conn.execute(
        "INSERT INTO standards_delta_items VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "delta-alpha",
            "p1",
            "testing",
            "high",
            "alpha delta",
            "2026-06-01T00:00:00Z",
            None,
        ),
    )
    conn.execute(
        "INSERT INTO standards_backfill_tasks VALUES (?, ?, ?, ?, ?, ?)",
        ("backfill-alpha", "p1", "alpha backfill", "open", "2026-06-01T00:00:00Z", None),
    )
    conn.execute(
        "INSERT INTO automations VALUES (?, ?, ?, ?, ?)",
        (
            "automation-alpha",
            "alpha-automation",
            "automation summary",
            "2026-06-01T00:00:00Z",
            None,
        ),
    )
    conn.execute(
        "INSERT INTO experiments VALUES (?, ?, ?, ?)",
        ("experiment-alpha", "alpha experiment", "2026-06-01T00:00:00Z", None),
    )
    conn.execute(
        "INSERT INTO divergent_runs VALUES (?, ?, ?, ?, ?, ?)",
        ("divergent-alpha", "alpha divergent", "p1", "summary", "2026-06-01T00:00:00Z", None),
    )
    conn.execute(
        "INSERT INTO workflow_learning_events VALUES (?, ?, ?, ?, ?, ?)",
        (
            "learning-alpha",
            "run-alpha",
            "weak_workflow",
            "alpha learning pattern",
            "2026-06-01T00:00:00Z",
            None,
        ),
    )
    conn.execute(
        "INSERT INTO promotion_lifecycle_items VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "promotion-alpha",
            "skill",
            "alpha-skill",
            "run-alpha",
            "proposed",
            "2026-06-01T00:00:00Z",
            None,
        ),
    )


def test_search_returns_mixed_kind_hits() -> None:
    conn = _make_db()
    _seed_all_kinds(conn)

    hits = search_entities(conn, query="alpha")

    assert len({hit.kind for hit in hits}) >= 5
    assert all(hit.drill_down_path.startswith("/") for hit in hits)


def test_per_kind_dispatch_returns_kind_tagged_hits() -> None:
    conn = _make_db()
    _seed_run(conn, objective="shared text")
    conn.execute(
        "INSERT INTO improvement_writebacks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "writeback-1",
            "run-alpha",
            "p1",
            "workflow",
            "workflow-1",
            "shared text",
            "summary",
            "proposed",
            "{}",
            "2026-06-01T00:00:00Z",
            None,
        ),
    )

    run_hits = search_entities(conn, query="text", kinds=("run",))
    writeback_hits = search_entities(conn, query="text", kinds=("writeback",))

    assert {hit.kind for hit in run_hits} == {"run"}
    assert {hit.kind for hit in writeback_hits} == {"writeback"}


def test_search_honors_project_filter() -> None:
    conn = _make_db()
    _seed_run(conn, id_="run-p1", objective="needle", project_id="p1")
    _seed_run(conn, id_="run-p2", objective="needle", project_id="p2")

    hits = search_entities(conn, query="needle", project_id="p1", kinds=("run",))

    assert [hit.project_id for hit in hits] == ["p1"]


def test_search_ranking_boosts_recency() -> None:
    conn = _make_db()
    conn.execute(
        "INSERT INTO improvement_writebacks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "old",
            None,
            "p1",
            "workflow",
            "old-key",
            "same title",
            "same summary",
            "proposed",
            "{}",
            "2026-05-01T00:00:00Z",
            None,
        ),
    )
    conn.execute(
        "INSERT INTO improvement_writebacks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "new",
            None,
            "p1",
            "workflow",
            "new-key",
            "same title",
            "same summary",
            "proposed",
            "{}",
            "2026-05-31T00:00:00Z",
            None,
        ),
    )

    hits = search_entities(conn, query="same", kinds=("writeback",))

    assert hits[0].id == "new"
    assert hits[0].score > hits[1].score


def test_search_exact_key_boost() -> None:
    conn = _make_db()
    _seed_run(
        conn,
        id_="run-workflow",
        objective="workflow observed",
        workflow_key="implementation-delivery",
    )
    _seed_run(
        conn,
        id_="run-other",
        objective="implementation-delivery mentioned",
        workflow_key="other-workflow",
    )

    hits = search_entities(conn, query="implementation-delivery", kinds=("workflow", "run"))

    assert hits[0].kind == "workflow"
    assert hits[0].id == "implementation-delivery"


def test_search_all_hits_have_drill_down_path() -> None:
    conn = _make_db()
    _seed_all_kinds(conn)

    hits = search_entities(conn, query="alpha")
    paths_by_kind = {hit.kind: hit.drill_down_path for hit in hits}

    assert paths_by_kind["run"].startswith("/runs/")
    assert paths_by_kind["writeback"].startswith("/writebacks#")
    assert paths_by_kind["knowledge_object"].startswith("/knowledge#")
    assert paths_by_kind["delta_item"].startswith("/projects/p1?delta=")
    assert all(path for path in paths_by_kind.values())


def test_search_tolerates_missing_tables() -> None:
    conn = _make_db(all_tables=False)
    _seed_run(conn, objective="anything")

    hits = search_entities(conn, query="anything")

    assert [hit.kind for hit in hits] == ["run"]


def test_search_empty_query_returns_recent_activity() -> None:
    conn = _make_db(all_tables=False)
    for index in range(5):
        _seed_run(
            conn,
            id_=f"run-{index}",
            objective=f"objective {index}",
            created_at=f"2026-05-0{index + 1}T00:00:00Z",
        )

    hits = search_entities(conn, query="", kinds=("run",), limit=3)

    assert [hit.id for hit in hits] == ["run-4", "run-3", "run-2"]


def test_search_query_length_cap() -> None:
    conn = _make_db(all_tables=False)

    with pytest.raises(ValueError, match="exceeds max 200"):
        search_entities(conn, query="a" * 201)

    assert search_entities(conn, query="a" * 200) == []


def test_search_does_not_leak_sensitive_columns() -> None:
    conn = _make_db()
    conn.execute(
        "INSERT INTO improvement_writebacks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "writeback-sensitive",
            None,
            "p1",
            "workflow",
            "safe-key",
            "safe title",
            "safe summary",
            "proposed",
            json.dumps(
                {
                    "secret": "sk-live-secret",
                    "path": "/Users/example/private/path/that/should/not/appear",
                }
            ),
            "2026-06-01T00:00:00Z",
            None,
        ),
    )

    hits = search_entities(conn, query="safe", kinds=("writeback",))
    serialized = json.dumps([asdict(hit) for hit in hits], sort_keys=True)

    assert hits[0].summary == "safe summary"
    assert "sk-live-secret" not in serialized
    assert "/Users/example/private/path" not in serialized
    assert not re.search(r"/[A-Za-z0-9_./-]{20,}", serialized.replace("/writebacks#", ""))


def test_search_limit_truncates_results() -> None:
    conn = _make_db(all_tables=False)
    for index in range(60):
        _seed_run(
            conn,
            id_=f"run-{index}",
            objective="match objective",
            created_at=f"2026-05-{(index % 28) + 1:02d}T00:00:00Z",
        )

    hits = search_entities(conn, query="match", kinds=("run",), limit=10)

    assert len(hits) == 10
    assert [hit.score for hit in hits] == sorted((hit.score for hit in hits), reverse=True)


def test_entity_kind_dispatcher_count_matches_contract() -> None:
    assert len(ENTITY_KINDS) == 17
    assert all(isinstance(hit, OperatorSearchHit) for hit in search_entities(_make_db(), query=""))
