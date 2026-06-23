from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.meta_learning_proposals import (  # noqa: E402
    generate_meta_learning_proposal,
    generate_meta_learning_proposals,
    read_proposals_jsonl,
    stable_proposal_id,
    write_proposals_jsonl,
)
from services.meta_learning_router import route_scored_signal  # noqa: E402
from services.meta_learning_scoring import score_meta_learning_signal  # noqa: E402
from services.meta_learning_signals import MetaLearningSignal  # noqa: E402


def _scored(
    *,
    signal_type: str = "explicit_correction",
    summary: str = "User correction: Always use pnpm in this repo.",
    target: str = "project_rule",
    risk: str = "low",
    sessions: list[str] | None = None,
) :
    signal = MetaLearningSignal(
        signal_id=f"sig-{signal_type}-{target}",
        type=signal_type,  # type: ignore[arg-type]
        summary=summary,
        evidence=[{"session_id": "s1", "kind": "message:user", "summary": summary}],
        source_sessions=sessions or ["s1"],
        frequency=len(sessions or ["s1"]),
        recency="2026-06-23T00:00:00Z",
        confidence_points=["test fixture"],
        recommended_target_layer=target,
        risk_level=risk,  # type: ignore[arg-type]
    )
    return score_meta_learning_signal(signal)


def test_formats_required_reviewable_proposal_fields() -> None:
    scored = _scored()
    route = route_scored_signal(scored)

    proposal = generate_meta_learning_proposal(scored, route)
    payload = proposal.to_dict()

    assert payload["proposal_id"].startswith("meta-proposal-")
    assert payload["title"] == "Route explicit correction to project"
    assert payload["target_layer"] == "project"
    assert payload["target_file"] == "AGENTS.md or project context packet after review"
    assert payload["confidence_score"] == scored.score
    assert payload["risk_level"] == "low"
    assert payload["evidence"] == scored.signal.evidence
    assert payload["why_this_layer"] == route.justification
    assert "Review action" in payload["proposed_patch"]
    assert "Do not apply automatically" in payload["rollback"]
    assert payload["requires_manual_approval"] is True


def test_proposal_ids_are_stable() -> None:
    first = stable_proposal_id("sig-1", "project", "AGENTS.md")
    second = stable_proposal_id("sig-1", "project", "AGENTS.md")

    assert first == second


def test_generate_proposals_skips_non_conflict_observe_only_routes() -> None:
    scored = _scored(summary="User correction: Use best practice clean code.")
    route = route_scored_signal(scored)

    assert route.target_layer == "observe_only"
    assert generate_meta_learning_proposals([scored], [route]) == []


def test_conflict_proposal_formats_existing_rule_and_action() -> None:
    scored = _scored(summary="User correction: Always use npm for scripts.")
    route = route_scored_signal(scored)

    proposal = generate_meta_learning_proposal(
        scored,
        route,
        existing_rules=["Never use npm for JavaScript dependency management."],
    )

    assert proposal.conflict is not None
    assert proposal.conflict.older_rule == "Never use npm for JavaScript dependency management."
    assert proposal.conflict.recommended_action in {"narrow", "split_by_context"}
    assert "Conflict:" in proposal.proposed_patch
    assert proposal.requires_manual_approval is True


def test_contradictory_signals_can_generate_manual_review_conflict_records() -> None:
    scored = _scored(
        signal_type="contradiction",
        summary="Contradictory directives for command policy",
        target="manual_review",
        risk="high",
        sessions=["s1", "s2"],
    )
    route = route_scored_signal(scored)

    proposals = generate_meta_learning_proposals([scored], [route])

    assert len(proposals) == 1
    assert proposals[0].target_layer == "observe_only"
    assert proposals[0].conflict is not None
    assert proposals[0].conflict.recommended_action == "ask_user"


def test_jsonl_persistence_round_trips_review_proposals(tmp_path: Path) -> None:
    scored = _scored()
    route = route_scored_signal(scored)
    proposal = generate_meta_learning_proposal(scored, route)

    path = write_proposals_jsonl([proposal], root=tmp_path)
    loaded = read_proposals_jsonl(path)

    assert path == tmp_path / "proposals.jsonl"
    assert len(loaded) == 1
    assert loaded[0].proposal_id == proposal.proposal_id
    assert loaded[0].requires_manual_approval is True
