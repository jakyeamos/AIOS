from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.asset_recommendation import (  # noqa: E402
    AssetUsageEvidence,
    build_asset_usage_evidence,
    recommend_assets_for_packet,
)


def _conn() -> sqlite3.Connection:
    return sqlite3.connect(":memory:")


def _seed_evidence_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE prompts_used (
          id TEXT PRIMARY KEY,
          session_id TEXT NOT NULL,
          prompt_text TEXT,
          classification TEXT,
          outcome_score INTEGER
        );
        CREATE TABLE workflow_execution_reports (
          id TEXT PRIMARY KEY,
          run_id TEXT,
          invocation_id TEXT,
          workflow_key TEXT NOT NULL,
          status TEXT NOT NULL,
          report_json TEXT NOT NULL DEFAULT '{}',
          artifact_path TEXT,
          created_at TEXT NOT NULL
        );
        CREATE TABLE success_criteria_findings (
          id TEXT PRIMARY KEY,
          evaluation_id TEXT NOT NULL,
          criterion_id TEXT NOT NULL,
          criterion_title TEXT NOT NULL,
          criterion_scope TEXT NOT NULL,
          level TEXT NOT NULL,
          summary TEXT NOT NULL,
          evidence_json TEXT NOT NULL DEFAULT '[]',
          metadata_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL
        );
        CREATE TABLE workflow_skill_experiments (
          id TEXT PRIMARY KEY,
          workflow_key TEXT NOT NULL,
          skill_key TEXT NOT NULL,
          baseline_score REAL,
          candidate_score REAL,
          outcome TEXT,
          created_at TEXT NOT NULL
        );
        """
    )


def test_build_asset_usage_evidence_joins_all_sources_for_prompts() -> None:
    conn = _conn()
    _seed_evidence_tables(conn)
    for index, score in enumerate((1, 1, 0)):
        conn.execute(
            """
            INSERT INTO prompts_used (id, session_id, prompt_text, classification, outcome_score)
            VALUES (?, 's1', 'research prompt', 'research', ?)
            """,
            (f"p{index}", score),
        )
    conn.execute(
        """
        INSERT INTO workflow_execution_reports
        (id, run_id, invocation_id, workflow_key, status, report_json, artifact_path, created_at)
        VALUES ('r1', 'run-1', NULL, 'implementation-delivery', 'completed', '{}', NULL, '2026-05-24T00:00:00Z')
        """
    )
    conn.execute(
        """
        INSERT INTO success_criteria_findings
        (id, evaluation_id, criterion_id, criterion_title, criterion_scope, level, summary, created_at)
        VALUES ('f1', 'e1', 'code-simplicity', 'Code', 'global', 'blocker', 'blocked', '2026-05-24T00:00:00Z')
        """
    )

    evidence = build_asset_usage_evidence(conn, asset_kind="prompt", asset_key="research")
    assert evidence.sample_size == 3
    assert evidence.success_count == 2
    assert evidence.blocker_count == 1
    assert evidence.per_workflow["implementation-delivery"]["used"] == 1
    assert evidence.per_task_family["research"]["used"] == 3


def test_build_asset_usage_evidence_for_skills_includes_workflow_skill_experiments() -> None:
    conn = _conn()
    _seed_evidence_tables(conn)
    conn.execute(
        """
        INSERT INTO workflow_execution_reports
        (id, run_id, invocation_id, workflow_key, status, report_json, artifact_path, created_at)
        VALUES (?, ?, NULL, ?, ?, ?, NULL, ?)
        """,
        (
            "r1",
            "run-1",
            "agentize",
            "completed",
            json.dumps({"stages": [{"skills": [{"skill_key": "agentize_intent_compiler"}]}]}),
            "2026-05-24T00:00:00Z",
        ),
    )
    conn.execute(
        """
        INSERT INTO workflow_skill_experiments
        (id, workflow_key, skill_key, baseline_score, candidate_score, outcome, created_at)
        VALUES ('x1', 'agentize', 'agentize_intent_compiler', 0.4, 0.9, 'improved', '2026-05-24T00:00:01Z')
        """
    )

    evidence = build_asset_usage_evidence(
        conn,
        asset_kind="skill",
        asset_key="agentize_intent_compiler",
    )
    assert evidence.sample_size == 2
    assert evidence.success_count == 2
    assert evidence.per_workflow["agentize"]["used"] == 2


def test_build_asset_usage_evidence_for_workflows_filters_by_workflow_key() -> None:
    conn = _conn()
    _seed_evidence_tables(conn)
    for index, workflow_key in enumerate(
        ["implementation-delivery", "implementation-delivery", "failure-recovery"]
    ):
        conn.execute(
            """
            INSERT INTO workflow_execution_reports
            (id, run_id, invocation_id, workflow_key, status, report_json, artifact_path, created_at)
            VALUES (?, ?, NULL, ?, 'completed', '{}', NULL, '2026-05-24T00:00:00Z')
            """,
            (f"r{index}", f"run-{index}", workflow_key),
        )

    evidence = build_asset_usage_evidence(
        conn,
        asset_kind="workflow",
        asset_key="implementation-delivery",
    )
    assert evidence.sample_size == 2
    assert evidence.success_count == 2


def test_recommendation_filters_out_draft_and_deprecated(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    conn = _conn()
    monkeypatch.setattr(
        "services.asset_recommendation._load_candidates",
        lambda asset_kind: [
            _candidate(asset_kind, "active", "active"),
            _candidate(asset_kind, "candidate", "candidate"),
            _candidate(asset_kind, "deprecated", "deprecated"),
            _candidate(asset_kind, "draft", "draft"),
        ],
    )
    recs = recommend_assets_for_packet(
        conn,
        task_classifications=(),
        workflow_family=None,
        project_id=None,
        asset_kind="skill",
    )
    assert [rec.asset_key for rec in recs] == ["active", "candidate"]


def test_recommendation_orders_by_lifecycle_state_then_success_rate(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    conn = _conn()
    monkeypatch.setattr(
        "services.asset_recommendation._load_candidates",
        lambda asset_kind: [
            _candidate(asset_kind, "a", "active"),
            _candidate(asset_kind, "b", "approved"),
            _candidate(asset_kind, "c", "candidate"),
        ],
    )
    monkeypatch.setattr(
        "services.asset_recommendation.build_asset_usage_evidence",
        lambda conn, asset_kind, asset_key, since=None: AssetUsageEvidence(
            asset_kind,
            asset_key,
            20,
            {"a": 16, "b": 19, "c": 20}[asset_key],
            0,
            None,
            {"wf": {"used": 1, "succeeded": 1, "failed": 0}},
            {},
        ),
    )
    recs = recommend_assets_for_packet(
        conn,
        task_classifications=(),
        workflow_family=None,
        project_id=None,
        asset_kind="skill",
    )
    assert [rec.asset_key for rec in recs] == ["a", "b", "c"]


def test_recommendation_exploration_fallback_below_threshold(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    conn = _conn()
    monkeypatch.setattr(
        "services.asset_recommendation._load_candidates",
        lambda asset_kind: [
            _candidate(asset_kind, "a", "active"),
            _candidate(asset_kind, "c", "candidate"),
        ],
    )
    recs = recommend_assets_for_packet(
        conn,
        task_classifications=(),
        workflow_family=None,
        project_id=None,
        asset_kind="skill",
    )
    assert any("exploration" in rec.rationale for rec in recs if rec.lifecycle_state == "candidate")


def test_recommendation_rationale_cites_sample_size_and_workflow(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    conn = _conn()
    monkeypatch.setattr(
        "services.asset_recommendation._load_candidates",
        lambda asset_kind: [_candidate(asset_kind, "a", "active")],
    )
    monkeypatch.setattr(
        "services.asset_recommendation.build_asset_usage_evidence",
        lambda conn, asset_kind, asset_key, since=None: AssetUsageEvidence(
            asset_kind,
            asset_key,
            1,
            1,
            0,
            None,
            {"implementation-delivery": {"used": 1, "succeeded": 1, "failed": 0}},
            {},
        ),
    )
    rec = recommend_assets_for_packet(
        conn,
        task_classifications=(),
        workflow_family=None,
        project_id=None,
        asset_kind="skill",
    )[0]
    assert "sample_size=1" in rec.rationale
    assert "implementation-delivery" in rec.rationale


def test_recommend_assets_filters_by_applicability_overlap(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    conn = _conn()
    monkeypatch.setattr(
        "services.asset_recommendation._load_candidates",
        lambda asset_kind: [
            _candidate(asset_kind, "audit", "active", ("audit_only",)),
            _candidate(asset_kind, "humanizer", "active", ("humanizing",)),
        ],
    )
    recs = recommend_assets_for_packet(
        conn,
        task_classifications=(),
        workflow_family="audit_only",
        project_id=None,
        asset_kind="prompt",
    )
    assert [rec.asset_key for rec in recs] == ["audit"]


def _candidate(
    asset_kind: str,
    asset_key: str,
    lifecycle_state: str,
    applicability: tuple[str, ...] = (),
):
    from services.asset_recommendation import _CandidateAsset

    return _CandidateAsset(
        asset_kind=asset_kind,
        asset_key=asset_key,
        lifecycle_state=lifecycle_state,  # type: ignore[arg-type]
        applicability=applicability,
    )
