from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.meta_learning_router import route_scored_signal, route_scored_signals  # noqa: E402
from services.meta_learning_scoring import (  # noqa: E402
    ScoredMetaLearningSignal,
    score_meta_learning_signal,
)
from services.meta_learning_signals import MetaLearningSignal  # noqa: E402


def _score(
    *,
    signal_type: str = "explicit_correction",
    summary: str = "User correction: Always use pnpm in this repo",
    target: str = "project_rule",
    frequency: int = 1,
    sessions: list[str] | None = None,
    evidence: list[dict[str, str]] | None = None,
) -> ScoredMetaLearningSignal:
    signal = MetaLearningSignal(
        signal_id=f"sig-{signal_type}-{target}",
        type=signal_type,  # type: ignore[arg-type]
        summary=summary,
        evidence=evidence
        or [{"session_id": "s1", "kind": "message:user", "summary": summary}],
        source_sessions=sessions or ["s1"],
        frequency=frequency,
        recency="2026-06-23T00:00:00Z",
        confidence_points=["test fixture"],
        recommended_target_layer=target,
        risk_level="low",
    )
    return score_meta_learning_signal(signal)


def test_project_specific_signals_route_away_from_global_rules() -> None:
    route = route_scored_signal(
        _score(summary="User correction: Always use pnpm in this repo.", target="project_rule")
    )

    assert route.target_layer == "project"
    assert route.target_scope == "project"
    assert "away from global" in route.justification


def test_multi_project_evidence_can_route_to_global_review() -> None:
    route = route_scored_signal(
        _score(
            summary="User correction: Always prefer intent-specific pointers over agent rules.",
            target="observe_only",
            frequency=2,
            sessions=["s1", "s2"],
            evidence=[
                {"session_id": "s1", "kind": "message:user", "summary": "Always use pointers", "project": "AIOS"},
                {"session_id": "s2", "kind": "message:user", "summary": "Always use pointers", "project": "BidCamp"},
            ],
        )
    )

    assert route.target_layer == "global"
    assert route.requires_manual_review


def test_command_and_skill_routes_use_recommended_target_layer() -> None:
    command = route_scored_signal(
        _score(
            signal_type="command_repetition",
            summary="Repeated command: pnpm test",
            target="command_suggestion",
            frequency=2,
        )
    )
    skill = route_scored_signal(
        _score(
            summary="User correction: Always adjust the skill instructions for this workflow.",
            target="skill_or_agent_suggestion",
        )
    )

    assert command.target_layer == "command"
    assert skill.target_layer == "skill"


def test_context_miss_routes_to_eval_when_confident() -> None:
    route = route_scored_signal(
        _score(
            signal_type="context_miss",
            summary="Context miss: loaded unrelated context twice",
            target="context_packet_or_retrieval_policy",
            frequency=2,
            sessions=["s1", "s2"],
        )
    )

    assert route.target_layer == "eval"
    assert "regression evidence" in route.justification


def test_rejected_quality_filter_routes_observe_only() -> None:
    route = route_scored_signal(
        _score(summary="User correction: Use best practice clean code.", target="project_rule")
    )

    assert route.target_layer == "observe_only"
    assert route.target_hint == "rejected by quality filter"


def test_batch_routing_preserves_signal_count() -> None:
    routes = route_scored_signals(
        [
            _score(summary="User correction: Always use pnpm in this repo."),
            _score(
                signal_type="command_repetition",
                summary="Repeated command: pnpm test",
                target="command_suggestion",
            ),
        ]
    )

    assert len(routes) == 2
