from __future__ import annotations

from services.shadow_candidate_scorer import score_shadow_candidate


def test_hard_blocker_caps_score_at_zero() -> None:
    result = score_shadow_candidate({"components": {"complexity": 100}, "blockers": ["dirty_repo"]})

    assert result["score"] == 0.0
    assert result["recommendation"] == "trace_only"
    assert result["blockers"] == ["dirty_repo"]


def test_good_candidate_scores_70_to_84() -> None:
    result = score_shadow_candidate(
        {
            "components": {
                "complexity": 80,
                "measurability": 80,
                "reproducibility": 70,
                "aios_relevance": 70,
                "learning_value": 70,
                "safety": 80,
                "benchmark_coverage_need": 80,
            }
        }
    )

    assert 70 <= result["score"] < 85
    assert result["recommendation"] == "good_shadow_candidate"
    assert result["reasons"]


def test_excellent_candidate_scores_85_to_100() -> None:
    result = score_shadow_candidate(
        {
            "components": {
                "complexity": 95,
                "measurability": 90,
                "reproducibility": 90,
                "aios_relevance": 90,
                "learning_value": 85,
                "safety": 90,
                "benchmark_coverage_need": 90,
            }
        }
    )

    assert 85 <= result["score"] <= 100
    assert result["recommendation"] == "excellent_shadow_candidate"


def test_recommendation_tiers() -> None:
    assert (
        score_shadow_candidate({"components": {"complexity": 0}})["recommendation"] == "trace_only"
    )
    assert (
        score_shadow_candidate({"components": {"complexity": 100, "measurability": 100}})[
            "recommendation"
        ]
        == "possible_shadow_candidate"
    )


def test_reasons_and_blockers_lists_are_populated() -> None:
    result = score_shadow_candidate(
        {
            "components": {"complexity": 75, "measurability": 80},
            "blockers": ["informational_note"],
        }
    )

    assert result["reasons"] == ["complexity:75", "measurability:80"]
    assert result["blockers"] == []
