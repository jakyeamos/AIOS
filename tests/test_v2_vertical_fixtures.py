from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.daily_flow import CANONICAL_STEP_ORDER, replay_from_run  # noqa: E402
from services.evidence_artifacts import (  # noqa: E402
    EvidenceStatus,
    ensure_evidence_schema,
    record_evidence_artifact,
)

FIXTURE_PATH = ROOT / "aios-ui" / "fixtures" / "v2-vertical-slice-fixtures.json"
REQUIRED_STATES = {"healthy", "empty", "blocked", "failed", "needs_review", "closed"}


def _load_document() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _fixture_by_id(fixture_id: str) -> dict[str, object]:
    document = _load_document()
    fixtures = document["fixtures"]
    assert isinstance(fixtures, list)
    fixture = next(item for item in fixtures if item["id"] == fixture_id)
    assert isinstance(fixture, dict)
    return fixture


def _projection_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE orchestration_runs (
          id TEXT PRIMARY KEY,
          project_id TEXT,
          objective TEXT,
          workflow_key TEXT,
          status TEXT,
          route_id TEXT,
          route_result_json TEXT DEFAULT '{}',
          created_at TEXT,
          updated_at TEXT
        );
        CREATE TABLE briefing_packets (
          id TEXT PRIMARY KEY,
          run_id TEXT,
          project_id TEXT,
          objective TEXT,
          route_id TEXT,
          selection_trace_json TEXT DEFAULT '[]',
          created_at TEXT
        );
        CREATE TABLE success_criteria_findings (
          id TEXT PRIMARY KEY,
          run_id TEXT,
          criterion_id TEXT,
          level TEXT,
          message TEXT,
          resolution_status TEXT,
          created_at TEXT
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
          requires_approval INTEGER,
          proposed_change_json TEXT DEFAULT '{}',
          created_at TEXT
        );
        CREATE TABLE workflow_learning_events (
          id TEXT PRIMARY KEY,
          run_id TEXT
        );
        """
    )
    ensure_evidence_schema(conn)
    return conn


def _persist_fixture(conn: sqlite3.Connection, fixture: dict[str, object]) -> None:
    route = fixture["route"]
    packet = fixture["packet"]
    run = fixture["run"]
    evidence = fixture["evidence"]
    approvals = fixture["approvals"]
    assert isinstance(route, dict)
    assert isinstance(packet, dict)
    assert isinstance(run, dict)
    assert isinstance(evidence, list)
    assert isinstance(approvals, list)

    conn.execute(
        """
        INSERT INTO orchestration_runs (
          id, project_id, objective, workflow_key, status, route_id, route_result_json,
          created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, '2026-07-13T00:00:00Z', '2026-07-13T00:01:00Z')
        """,
        (
            run["id"],
            route["project_id"],
            fixture["objective"],
            route["workflow_key"],
            run["status"],
            route["id"],
            json.dumps({"selected_workflow": {"workflow_key": route["workflow_key"]}}),
        ),
    )
    conn.execute(
        """
        INSERT INTO briefing_packets (
          id, run_id, project_id, objective, route_id, selection_trace_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, '2026-07-13T00:00:10Z')
        """,
        (
            packet["id"],
            run["id"],
            route["project_id"],
            fixture["objective"],
            route["id"],
            json.dumps(
                {"source_refs": packet["source_refs"], "omitted_refs": packet["omitted_refs"]}
            ),
        ),
    )
    for item in evidence:
        assert isinstance(item, dict)
        status_by_fixture: dict[str, EvidenceStatus] = {
            "verified": "pass",
            "failed": "fail",
            "pending": "unknown",
        }
        status = status_by_fixture[item["status"]]
        record_evidence_artifact(
            conn,
            evidence_id=item["id"],
            run_id=run["id"],
            command=item["source"],
            exit_code=0 if status == "pass" else 1 if status == "fail" else None,
            output_hash=f"fixture-{item['id']}",
            parsed_summary=item["summary"],
            status=status,
            timestamp="2026-07-13T00:00:20Z",
        )
        if item["kind"] == "check":
            conn.execute(
                """
                INSERT INTO success_criteria_findings (
                  id, run_id, criterion_id, level, message, resolution_status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, '2026-07-13T00:00:20Z')
                """,
                (
                    item["id"],
                    run["id"],
                    f"fixture-{item['id']}",
                    "blocker" if item["status"] == "failed" else "warning",
                    item["summary"],
                    "resolved" if item["status"] == "verified" else "open",
                ),
            )
    for item in approvals:
        assert isinstance(item, dict)
        conn.execute(
            """
            INSERT INTO improvement_writebacks (
              id, run_id, project_id, layer_type, layer_key, title, summary, status,
              requires_approval, created_at
            ) VALUES (?, ?, ?, 'truth', ?, 'Fixture approval', ?, ?, ?, '2026-07-13T00:00:30Z')
            """,
            (
                item["id"],
                run["id"],
                route["project_id"],
                item["target"],
                item["reason"],
                "pending_approval" if item["state"] == "pending" else item["state"],
                1 if item["state"] == "pending" else 0,
            ),
        )
    if run["status"] == "completed":
        conn.execute(
            "INSERT INTO workflow_learning_events (id, run_id) VALUES (?, ?)",
            (f"learning-{run['id']}", run["id"]),
        )
    conn.commit()


def test_v2_fixture_document_covers_the_vertical_state_contract() -> None:
    document = _load_document()
    assert document["schema_version"] == "aios-v2-vertical-fixtures-v0.1"
    assert document["owner"] == "python-control-plane"
    fixtures = document["fixtures"]
    assert isinstance(fixtures, list)
    assert {fixture["state"] for fixture in fixtures} == REQUIRED_STATES


def test_v2_fixture_references_are_internally_consistent() -> None:
    document = _load_document()
    fixtures = document["fixtures"]
    assert isinstance(fixtures, list)

    for fixture in fixtures:
        evidence = fixture["evidence"]
        approvals = fixture["approvals"]
        run = fixture["run"]
        assert isinstance(evidence, list)
        assert isinstance(approvals, list)
        assert isinstance(run, dict)
        evidence_ids = {item["id"] for item in evidence}
        approval_ids = {item["id"] for item in approvals}
        assert set(run["evidence_ids"]).issubset(evidence_ids)
        assert set(run["approval_ids"]).issubset(approval_ids)
        assert fixture["route"]["authority"] == "python-control-plane"
        assert fixture["projection"]["next_action"] is None or fixture["run"]["next_action_id"]


def test_closed_fixture_maps_to_persisted_rows_and_daily_flow_replay() -> None:
    fixture = _fixture_by_id("closed-success")
    run = fixture["run"]
    assert isinstance(run, dict)
    conn = _projection_conn()
    _persist_fixture(conn, fixture)

    trace = replay_from_run(conn, run_id=run["id"])
    steps = {step.kind: step for step in trace.steps}
    packet = fixture["packet"]
    route = fixture["route"]
    evidence = fixture["evidence"]
    approvals = fixture["approvals"]
    assert isinstance(packet, dict)
    assert isinstance(route, dict)
    assert isinstance(evidence, list)
    assert isinstance(approvals, list)

    assert trace.objective == fixture["objective"]
    assert tuple(step.kind for step in trace.steps) == CANONICAL_STEP_ORDER
    assert steps["route"].evidence_ref == {"table": "orchestration_runs", "id": run["id"]}
    assert steps["packet"].evidence_ref == {"table": "briefing_packets", "id": packet["id"]}
    assert steps["run"].summary == f"Run {run['id']} is completed"
    assert steps["evaluation"].evidence_ref == {
        "table": "success_criteria_findings",
        "id": evidence[0]["id"],
    }
    assert steps["writeback"].evidence_ref == {
        "table": "improvement_writebacks",
        "id": approvals[0]["id"],
    }
    assert steps["next_action"].provenance == "missing"
    assert {
        row[0]
        for row in conn.execute(
            "SELECT evidence_id FROM evidence_artifacts WHERE run_id = ?", (run["id"],)
        ).fetchall()
    } == {item["id"] for item in evidence}
    assert (
        conn.execute(
            "SELECT id FROM improvement_writebacks WHERE run_id = ?", (run["id"],)
        ).fetchone()[0]
        == approvals[0]["id"]
    )
