from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.meta_learning_scoring import (  # noqa: E402
    confidence_band,
    score_meta_learning_signal,
    score_meta_learning_signals,
)
from services.meta_learning_signals import MetaLearningSignal  # noqa: E402


def _signal(
    *,
    signal_type: str = "explicit_correction",
    summary: str = "User correction: Always use pnpm in this repo",
    frequency: int = 1,
    sessions: list[str] | None = None,
    target: str = "project_rule",
    risk: str = "low",
    evidence: list[dict[str, str]] | None = None,
    recency: str | None = "2026-06-23T00:00:00Z",
) -> MetaLearningSignal:
    return MetaLearningSignal(
        signal_id=f"sig-{signal_type}-{frequency}",
        type=signal_type,  # type: ignore[arg-type]
        summary=summary,
        evidence=evidence
        or [{"session_id": "s1", "kind": "message:user", "summary": summary}],
        source_sessions=sessions or ["s1"],
        frequency=frequency,
        recency=recency,
        confidence_points=["test fixture"],
        recommended_target_layer=target,
        risk_level=risk,  # type: ignore[arg-type]
    )


def test_confidence_bands_match_policy_ranges() -> None:
    assert confidence_band(2) == "observe_only"
    assert confidence_band(3) == "suggest_project_note_or_low_risk_command"
    assert confidence_band(7) == "propose_project_rule_skill_or_command"
    assert confidence_band(8) == "strong_review_gated_proposal"


def test_scores_explicit_corrections_and_modifiers() -> None:
    scored = score_meta_learning_signal(
        _signal(summary="User correction: From now on, always use pnpm in this repo.")
    )

    assert scored.score == 8
    assert scored.band == "strong_review_gated_proposal"
    assert scored.accepted
    assert scored.requires_manual_review
    assert "explicit always/never/from-now-on correction +5" in scored.score_reasons


def test_scores_repeated_patterns_by_cross_session_evidence() -> None:
    scored = score_meta_learning_signal(
        _signal(
            signal_type="repeated_pattern",
            summary="User correction: Never use npm in this repo.",
            frequency=2,
            sessions=["s1", "s2"],
        )
    )

    assert scored.score == 5
    assert scored.band == "propose_project_rule_skill_or_command"
    assert "repeated correction across sessions +4" in scored.score_reasons


def test_quality_filter_rejects_generic_and_vague_one_off_preferences() -> None:
    generic = score_meta_learning_signal(
        _signal(summary="User correction: Use best practice clean code.", recency=None)
    )
    vague = score_meta_learning_signal(
        _signal(summary="User correction: Make things better.", recency=None)
    )

    assert not generic.accepted
    assert "generic_best_practice" in generic.quality_filter.rejected_reasons
    assert not vague.accepted
    assert "specific_actionable_learning" in vague.quality_filter.rejected_reasons


def test_quality_filter_rejects_unsafe_permission_changes() -> None:
    scored = score_meta_learning_signal(
        _signal(summary="User correction: Always auto-allow deploy commands without approval.")
    )

    assert not scored.accepted
    assert "permission_risk" in scored.risk_flags
    assert "unsafe_permission_change" in scored.quality_filter.rejected_reasons


def test_contradictions_are_conflicts_without_auto_promotion() -> None:
    scored = score_meta_learning_signal(
        _signal(
            signal_type="contradiction",
            summary="Contradictory directives for npm usage",
            frequency=2,
            target="manual_review",
            risk="high",
        )
    )

    assert scored.score == 1
    assert not scored.accepted
    assert scored.requires_manual_review
    assert "contradiction" in scored.risk_flags
    assert "contradictory_without_enough_evidence" in scored.quality_filter.rejected_reasons


def test_batch_scoring_preserves_one_result_per_signal() -> None:
    signals = [
        _signal(summary="User correction: Always use pnpm in this repo."),
        _signal(signal_type="approval", summary="Repeated approval language", target="observe_only"),
    ]

    scored = score_meta_learning_signals(signals)

    assert len(scored) == 2
