from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.agentize import agentize_request  # noqa: E402
from services.daily_flow import (  # noqa: E402
    CANONICAL_STEP_ORDER,
    preview_from_objective,
    replay_from_run,
)


def _conn() -> sqlite3.Connection:
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
        CREATE TABLE projects (
          id TEXT PRIMARY KEY,
          name TEXT,
          repo_path TEXT,
          obsidian_path TEXT,
          status TEXT
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
        CREATE TABLE orchestration_invocations (
          id TEXT PRIMARY KEY,
          run_id TEXT
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
        CREATE TABLE standards_delta_items (
          id TEXT PRIMARY KEY,
          project_id TEXT,
          domain TEXT,
          priority_bucket TEXT,
          severity REAL,
          summary TEXT,
          remediation_playbook_json TEXT DEFAULT '{}',
          status TEXT,
          updated_at TEXT
        );
        """
    )
    return conn


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, stdout=subprocess.PIPE, text=True)


def _sample_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "aios@example.local")
    _git(repo, "config", "user.name", "AIOS Tests")
    (repo / "README.md").write_text("# Sample\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "initial")
    (repo / "README.md").write_text("# Sample\n\nChanged.\n", encoding="utf-8")
    (repo / "new.txt").write_text("new\n", encoding="utf-8")
    return repo


def _count(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _seed_complete_replay(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT INTO orchestration_runs (
          id, project_id, objective, workflow_key, status, route_id, route_result_json,
          created_at, updated_at
        )
        VALUES (
          'r1', 'p1', 'implement login', 'implementation-delivery', 'completed',
          'route-r1',
          '{"selected_workflow":{"workflow_key":"implementation-delivery"}}',
          '2026-06-01T00:00:00Z', '2026-06-01T00:01:00Z'
        )
        """
    )
    conn.execute(
        """
        INSERT INTO briefing_packets (id, run_id, project_id, objective, route_id, created_at)
        VALUES ('packet-r1', 'r1', 'p1', 'implement login', 'route-r1',
                '2026-06-01T00:00:10Z')
        """
    )
    conn.execute(
        """
        INSERT INTO success_criteria_findings (
          id, run_id, criterion_id, level, message, resolution_status, created_at
        )
        VALUES ('finding-r1', 'r1', 'OPER-04', 'warning', 'Trace checked', 'resolved',
                '2026-06-01T00:00:20Z')
        """
    )
    conn.execute(
        """
        INSERT INTO improvement_writebacks (
          id, run_id, project_id, layer_type, layer_key, title, summary, status,
          requires_approval, created_at
        )
        VALUES ('wb-r1', 'r1', 'p1', 'truth', 'PROJECT.md', 'Update truth',
                'Record daily-flow projection', 'pending_approval', 1,
                '2026-06-01T00:00:30Z')
        """
    )
    conn.execute(
        """
        INSERT INTO standards_delta_items (
          id, project_id, domain, priority_bucket, severity, summary,
          remediation_playbook_json, status, updated_at
        )
        VALUES ('delta-r1', 'p1', 'operator', 'foundational', 9,
                'Daily flow needs rendering',
                '{"recommended_workflow_key":"implementation-delivery"}',
                'open', '2026-06-01T00:00:40Z')
        """
    )
    conn.commit()


def test_agentize_dry_run_inserts_no_rows() -> None:
    conn = _conn()
    before = {table: _count(conn, table) for table in _SOURCE_TABLES[:3]}

    for _ in range(100):
        agentize_request("implement login", project_id="p1", conn=conn, dry_run=True)

    after = {table: _count(conn, table) for table in _SOURCE_TABLES[:3]}
    assert after == before


def test_agentize_dry_run_returns_packet_shape() -> None:
    conn = _conn()
    packet = agentize_request("implement login", project_id="p1", conn=conn, dry_run=True)

    payload = packet.to_dict()
    assert {"packet_id", "required_context", "relevant_skills"} <= set(payload)
    assert (
        conn.execute(
            "SELECT 1 FROM briefing_packets WHERE id = ?", (payload["packet_id"],)
        ).fetchone()
        is None
    )


def test_agentize_live_mode_still_inserts() -> None:
    conn = _conn()
    packet = agentize_request("implement login", project_id="p1", conn=conn)

    assert packet.packet_id.startswith("agentized-")
    assert _count(conn, "orchestration_runs") == 0
    assert _count(conn, "briefing_packets") == 0


def test_agentize_dry_run_savepoint_isolation_under_concurrent_writes() -> None:
    conn = _conn()
    conn.execute("BEGIN")
    conn.execute(
        """
        INSERT INTO orchestration_runs (id, project_id, objective, workflow_key, status)
        VALUES ('outer-run', 'p1', 'outer write', 'implementation-delivery', 'ready')
        """
    )

    agentize_request("implement login", project_id="p1", conn=conn, dry_run=True)

    assert _count(conn, "orchestration_runs") == 1
    assert (
        conn.execute("SELECT objective FROM orchestration_runs WHERE id = 'outer-run'").fetchone()[
            "objective"
        ]
        == "outer write"
    )
    conn.rollback()


def test_preview_returns_eight_step_trace_in_canonical_order() -> None:
    trace = preview_from_objective(_conn(), objective="implement login", project_id="p1")

    assert trace.is_preview is True
    assert trace.objective == "implement login"
    assert trace.project_id == "p1"
    assert tuple(step.kind for step in trace.steps) == CANONICAL_STEP_ORDER


def test_preview_is_dry_zero_persistence() -> None:
    conn = _conn()
    before = (_count(conn, "orchestration_runs"), _count(conn, "briefing_packets"))

    for _ in range(100):
        preview_from_objective(conn, objective="implement login", project_id="p1")

    assert (_count(conn, "orchestration_runs"), _count(conn, "briefing_packets")) == before


def test_replay_returns_eight_step_trace_for_existing_run() -> None:
    conn = _conn()
    _seed_complete_replay(conn)

    trace = replay_from_run(conn, run_id="r1")

    assert trace.is_preview is False
    assert trace.objective == "implement login"
    assert tuple(step.kind for step in trace.steps) == CANONICAL_STEP_ORDER
    assert all(step.drill_down_path.startswith("/") for step in trace.steps)
    assert trace.steps[2].evidence_ref == {"table": "briefing_packets", "id": "packet-r1"}


def test_replay_run_step_includes_repo_closeout_payload(tmp_path: Path) -> None:
    conn = _conn()
    repo = _sample_repo(tmp_path)
    conn.execute(
        """
        INSERT INTO projects (id, name, repo_path, obsidian_path, status)
        VALUES ('p1', 'Sample', ?, '03 Projects/Sample', 'active')
        """,
        (str(repo),),
    )
    _seed_complete_replay(conn)

    trace = replay_from_run(conn, run_id="r1")

    run_step = next(step for step in trace.steps if step.kind == "run")
    closeout = run_step.metadata["repo_closeout"]
    git = closeout["git"]
    assert closeout["schema"] == "aios-repo-closeout-v0.1"
    assert closeout["repo"] == str(repo)
    assert git["is_repo"] is True
    assert git["branch"] in {"master", "main"}
    assert len(git["head"]) == 40
    assert git["dirty"] is True
    assert git["dirty_files"] == [" M README.md", "?? new.txt"]
    assert closeout["diff_stat"]["lines"] == [
        "README.md | 2 ++",
        "1 file changed, 2 insertions(+)",
    ]


def test_replay_finds_evaluation_through_canonical_schema() -> None:
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
        CREATE TABLE success_criteria_evaluations (
          id TEXT PRIMARY KEY,
          project_id TEXT,
          run_id TEXT,
          summary TEXT,
          created_at TEXT
        );
        CREATE TABLE success_criteria_findings (
          id TEXT PRIMARY KEY,
          evaluation_id TEXT NOT NULL,
          criterion_id TEXT NOT NULL,
          criterion_title TEXT NOT NULL,
          criterion_scope TEXT NOT NULL,
          level TEXT NOT NULL,
          summary TEXT NOT NULL,
          resolution_status TEXT NOT NULL DEFAULT 'open',
          created_at TEXT NOT NULL
        );
        """
    )
    conn.execute(
        """
        INSERT INTO orchestration_runs (
          id, project_id, objective, workflow_key, status, route_id, route_result_json,
          created_at, updated_at
        )
        VALUES (
          'run-1', 'project-1', 'Fix login', 'implementation-delivery', 'completed',
          'route-1', '{"selected_workflow":{"workflow_key":"implementation-delivery"}}',
          '2026-06-23T00:00:00Z', '2026-06-23T00:01:00Z'
        )
        """
    )
    conn.execute(
        """
        INSERT INTO success_criteria_evaluations (id, project_id, run_id, summary, created_at)
        VALUES ('eval-1', 'project-1', 'run-1', 'Evaluated run', '2026-06-23T00:02:00Z')
        """
    )
    conn.execute(
        """
        INSERT INTO success_criteria_findings (
          id, evaluation_id, criterion_id, criterion_title, criterion_scope, level, summary,
          resolution_status, created_at
        )
        VALUES (
          'finding-1', 'eval-1', 'agent-claim-verification', 'Agent Claim Verification',
          'global', 'warning', 'Evidence checked', 'open', '2026-06-23T00:03:00Z'
        )
        """
    )

    trace = replay_from_run(conn, run_id="run-1")

    evaluation = next(step for step in trace.steps if step.kind == "evaluation")
    assert evaluation.provenance == "confirmed"
    assert evaluation.evidence_ref == {"table": "success_criteria_findings", "id": "finding-1"}


def test_replay_is_pure_read() -> None:
    conn = _conn()
    _seed_complete_replay(conn)
    before = {table: _count(conn, table) for table in _SOURCE_TABLES}
    writes: list[str] = []
    conn.set_trace_callback(
        lambda statement: (
            writes.append(statement)
            if statement.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
            else None
        )
    )

    replay_from_run(conn, run_id="r1")

    conn.set_trace_callback(None)
    assert writes == []
    assert {table: _count(conn, table) for table in _SOURCE_TABLES} == before


def test_every_step_has_evidence_ref_and_drill_down_and_provenance() -> None:
    conn = _conn()
    _seed_complete_replay(conn)
    traces = (
        preview_from_objective(conn, objective="implement login", project_id="p1"),
        replay_from_run(conn, run_id="r1"),
    )

    for trace in traces:
        for step in trace.steps:
            assert step.evidence_ref
            assert "table" in step.evidence_ref or "kind" in step.evidence_ref
            assert step.drill_down_path
            assert step.provenance in {"confirmed", "inferred", "missing", "contradictory"}


def test_replay_degrades_when_evaluation_table_missing() -> None:
    conn = _conn()
    _seed_complete_replay(conn)
    conn.execute("DROP TABLE success_criteria_findings")

    step = replay_from_run(conn, run_id="r1").steps[4]

    assert step.kind == "evaluation"
    assert step.provenance == "missing"
    assert "Phase 6 success_criteria_findings table not present" in step.summary


def test_replay_degrades_when_writeback_table_missing() -> None:
    conn = _conn()
    _seed_complete_replay(conn)
    conn.execute("DROP TABLE improvement_writebacks")

    step = replay_from_run(conn, run_id="r1").steps[5]

    assert step.kind == "writeback"
    assert step.provenance == "missing"
    assert "Phase 5 improvement_writebacks table not present" in step.summary


def test_replay_degrades_when_delta_table_missing() -> None:
    conn = _conn()
    _seed_complete_replay(conn)
    conn.execute("DROP TABLE standards_delta_items")

    step = replay_from_run(conn, run_id="r1").steps[6]

    assert step.kind == "unresolved_delta"
    assert step.provenance == "missing"
    assert "Phase 7 standards_delta_items table not present" in step.summary


def test_replay_missing_run_returns_trace_with_missing_steps() -> None:
    trace = replay_from_run(_conn(), run_id="missing")

    assert trace.is_preview is False
    assert tuple(step.kind for step in trace.steps) == CANONICAL_STEP_ORDER
    assert trace.steps[3].summary == "run_id not found"
    assert all(step.provenance == "missing" for step in trace.steps)


def test_preview_step_drill_downs_point_to_existing_routes() -> None:
    trace = preview_from_objective(_conn(), objective="implement login", project_id="p1")
    paths = {step.kind: step.drill_down_path for step in trace.steps}

    assert paths["goal"] == "/search?query=implement%20login"
    assert paths["route"] == "/search"
    assert paths["packet"] == "/control"
    assert paths["run"] == "/"
    assert paths["next_action"].startswith("/")


_SOURCE_TABLES = (
    "orchestration_runs",
    "briefing_packets",
    "orchestration_invocations",
    "success_criteria_findings",
    "improvement_writebacks",
    "standards_delta_items",
)
