from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.workflow_synthesis import (  # noqa: E402
    approve_workflow_proposal,
    ensure_workflow_synthesis_schema,
    synthesize_workflow_proposals,
)


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE patterns (
          id TEXT PRIMARY KEY,
          class TEXT NOT NULL,
          title TEXT NOT NULL,
          evidence TEXT,
          confidence REAL NOT NULL,
          status TEXT NOT NULL,
          domain TEXT,
          state TEXT,
          human_approved INTEGER NOT NULL DEFAULT 0,
          created_at TEXT
        )
        """
    )
    ensure_workflow_synthesis_schema(conn)
    return conn


def test_synthesizes_workflow_proposal_from_high_confidence_pattern() -> None:
    conn = _conn()
    conn.execute(
        """
        INSERT INTO patterns (id, class, title, evidence, confidence, status, domain, state, human_approved)
        VALUES (
          'pattern-1',
          'workflow',
          'Recurring workflow pattern: review pull request comments then patch tests',
          '["session-a", "session-b"]',
          0.86,
          'active',
          'workflow',
          'rule',
          1
        )
        """
    )
    proposals = synthesize_workflow_proposals(conn, min_confidence=0.75)

    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal["status"] == "pending_approval"
    assert proposal["proposal_key"].endswith("_v1")
    assert proposal["workflow_spec"]["required_validations"] == ["scope_check"]
    assert proposal["workflow_spec"]["stages"][0]["kind"] == "parse_request"
    assert proposal["skill_specs"][0]["execution_mode"] == "heuristic"
    assert proposal["validation_plan"]["acceptance_checks"]
    row = conn.execute("SELECT COUNT(*) FROM workflow_synthesis_proposals").fetchone()
    assert row[0] == 1


def test_approval_appends_workflow_and_skills_to_registries(tmp_path: Path) -> None:
    conn = _conn()
    conn.execute(
        """
        INSERT INTO patterns (id, class, title, evidence, confidence, status, domain, state, human_approved)
        VALUES (
          'pattern-1',
          'workflow',
          'Recurring workflow pattern: triage flaky test then isolate fixture',
          '["session-a", "session-b"]',
          0.9,
          'active',
          'workflow',
          'rule',
          1
        )
        """
    )
    proposal = synthesize_workflow_proposals(conn, min_confidence=0.75)[0]
    registry_path = tmp_path / "registry.json"
    skills_path = tmp_path / "skills.json"
    registry_path.write_text(
        json.dumps({"version": "test", "stage_kinds": ["parse_request"], "workflows": []}),
        encoding="utf-8",
    )
    skills_path.write_text(json.dumps({"version": "test", "skills": []}), encoding="utf-8")

    approved = approve_workflow_proposal(
        conn,
        proposal_id=proposal["id"],
        actor="operator",
        registry_path=registry_path,
        skills_path=skills_path,
        note="Approved as reusable flaky-test workflow.",
    )

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    skills = json.loads(skills_path.read_text(encoding="utf-8"))
    assert approved["status"] == "approved"
    assert registry["workflows"][0]["key"] == proposal["proposal_key"]
    assert skills["skills"][0]["key"] == proposal["skill_specs"][0]["key"]
    row = conn.execute(
        "SELECT status, reviewer, review_note FROM workflow_synthesis_proposals WHERE id = ?",
        (proposal["id"],),
    ).fetchone()
    assert row == ("approved", "operator", "Approved as reusable flaky-test workflow.")
