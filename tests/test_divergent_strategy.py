from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.divergent_strategy import (  # noqa: E402
    approve_memory_writeback,
    classify_task,
    create_divergent_run,
    ensure_divergent_schema,
    load_candidate_registry,
    load_judge_registry,
    score_entropy,
    transition_promotion_lifecycle,
)


def test_task_classification_selects_standard_mode_for_architecture_decision() -> None:
    classification = classify_task(
        "Evaluate a workflow architecture and choose a durable memory writeback strategy"
    )

    assert classification["worthwhile"] is True
    assert classification["recommended_mode"] == "standard"
    assert "architecture" in classification["signals"]


def test_registries_expose_required_candidate_and_judge_profiles() -> None:
    candidates = load_candidate_registry()
    judges = load_judge_registry()

    assert {"conservative_integrator", "chaos_novelty", "standards_enforcer"} <= set(candidates)
    assert {"operator", "skeptic", "architect", "entropy", "standards"} <= set(judges)
    assert all(profile.output_contract for profile in candidates.values())
    assert all(profile.rubric for profile in judges.values())


def test_divergent_run_persists_portfolio_writebacks_and_entropy() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    ensure_divergent_schema(conn)

    result = create_divergent_run(
        conn,
        source_task="Design the next AIOS workflow for prompt-library promotion gates",
        mode="lightweight",
        project_id="aios",
    )

    assert result.run.status == "completed"
    assert result.run.mode == "lightweight"
    assert result.portfolio["best_overall"]
    assert result.portfolio["most_interesting_failure"]
    assert result.entropy_observation.diversity_score > 0
    assert result.entropy_observation.recommendation

    candidates = conn.execute("SELECT * FROM divergent_candidates").fetchall()
    judgments = conn.execute("SELECT * FROM divergent_judgments").fetchall()
    writebacks = conn.execute("SELECT * FROM memory_writeback_proposals").fetchall()

    assert len(candidates) == 3
    assert len(judgments) >= 6
    assert len(writebacks) >= 4
    assert {row["target_scope"] for row in writebacks} >= {"project", "prompt_library", "standards"}
    assert {row["proposal_type"] for row in writebacks} >= {
        "HOW",
        "WHAT",
        "FAILURE",
        "ENTROPY",
    }
    assert {row["status"] for row in writebacks} == {"proposed"}


def test_writeback_approval_does_not_promote_without_evidence() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    ensure_divergent_schema(conn)
    result = create_divergent_run(
        conn,
        source_task="Audit an existing repo idea for adoption risk",
        mode="audit",
    )
    proposal = conn.execute(
        "SELECT id FROM memory_writeback_proposals WHERE target_scope = 'skill_registry' LIMIT 1"
    ).fetchone()

    approved = approve_memory_writeback(conn, proposal["id"], reviewed_by="tester")

    assert approved["status"] == "approved"
    promotion = conn.execute(
        "SELECT status FROM promotion_lifecycle_items WHERE source_run_id = ?",
        (result.run.id,),
    ).fetchone()
    assert promotion["status"] == "candidate"


def test_entropy_scores_convergence_risk_for_repeated_shapes() -> None:
    observation = score_entropy(
        candidate_shapes=[
            "minimal implementation with approvals",
            "minimal implementation with approvals",
            "minimal implementation with approvals",
        ],
        judge_roles=["operator", "operator", "operator"],
    )

    assert observation.repeated_pattern_detected is True
    assert observation.diversity_score < 0.5
    assert "Rotate" in observation.recommendation


def test_promotion_lifecycle_requires_evidence_for_tested_and_approved() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    ensure_divergent_schema(conn)

    item = transition_promotion_lifecycle(
        conn,
        item_id="skill-divergent-strategy",
        item_kind="skill",
        item_key="divergent-strategy",
        requested_status="candidate",
        source_run_id="run-1",
        evidence=[],
    )
    assert item["status"] == "candidate"

    rejected = transition_promotion_lifecycle(
        conn,
        item_id="skill-divergent-strategy",
        item_kind="skill",
        item_key="divergent-strategy",
        requested_status="approved",
        source_run_id="run-1",
        evidence=[],
    )
    assert rejected["status"] == "candidate"
    assert "requires evidence" in rejected["status_reason"]

    approved = transition_promotion_lifecycle(
        conn,
        item_id="skill-divergent-strategy",
        item_kind="skill",
        item_key="divergent-strategy",
        requested_status="tested",
        source_run_id="run-1",
        evidence=["pytest tests/test_divergent_strategy.py"],
    )
    assert approved["status"] == "tested"
