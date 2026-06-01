from __future__ import annotations

import sys
from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.learning_taxonomy import (  # noqa: E402
    IS_ACTIONABLE_SIGNAL,
    LEARNING_SIGNAL_KINDS,
    SIGNAL_TO_IMPACT_SCOPE,
    ConservatismPolicy,
    impact_scope_for_signal,
)


def test_learning_signal_kind_literal_members() -> None:
    assert LEARNING_SIGNAL_KINDS == (
        "repeated_failure",
        "ignored_rule",
        "bloated_packet",
        "weak_prompt",
        "weak_workflow",
        "route_misroute",
        "standards_regression",
        "writeback_adopted",
        "writeback_rejected",
        "compounding_gain",
    )


def test_signal_to_impact_scope_covers_every_kind() -> None:
    assert set(SIGNAL_TO_IMPACT_SCOPE) == set(LEARNING_SIGNAL_KINDS)
    assert SIGNAL_TO_IMPACT_SCOPE["repeated_failure"] == "workflow-default"
    assert SIGNAL_TO_IMPACT_SCOPE["ignored_rule"] == "standards-default"
    assert SIGNAL_TO_IMPACT_SCOPE["bloated_packet"] == "packet-default"
    assert SIGNAL_TO_IMPACT_SCOPE["weak_prompt"] == "prompt-default"
    assert SIGNAL_TO_IMPACT_SCOPE["weak_workflow"] == "workflow-default"
    assert SIGNAL_TO_IMPACT_SCOPE["route_misroute"] == "route-default"
    assert SIGNAL_TO_IMPACT_SCOPE["standards_regression"] == "standards-default"
    assert SIGNAL_TO_IMPACT_SCOPE["writeback_adopted"] == "scoped"
    assert SIGNAL_TO_IMPACT_SCOPE["writeback_rejected"] == "scoped"
    assert SIGNAL_TO_IMPACT_SCOPE["compounding_gain"] == "scoped"


def test_is_actionable_signal_excludes_informational() -> None:
    assert isinstance(IS_ACTIONABLE_SIGNAL, frozenset)
    assert "repeated_failure" in IS_ACTIONABLE_SIGNAL
    assert "ignored_rule" in IS_ACTIONABLE_SIGNAL
    assert "bloated_packet" in IS_ACTIONABLE_SIGNAL
    assert "weak_prompt" in IS_ACTIONABLE_SIGNAL
    assert "weak_workflow" in IS_ACTIONABLE_SIGNAL
    assert "route_misroute" in IS_ACTIONABLE_SIGNAL
    assert "standards_regression" in IS_ACTIONABLE_SIGNAL
    assert "writeback_adopted" not in IS_ACTIONABLE_SIGNAL
    assert "writeback_rejected" not in IS_ACTIONABLE_SIGNAL
    assert "compounding_gain" not in IS_ACTIONABLE_SIGNAL


def test_impact_scope_for_signal_helper() -> None:
    assert impact_scope_for_signal("repeated_failure") == "workflow-default"
    assert impact_scope_for_signal("route_misroute") == "route-default"
    with pytest.raises(KeyError):
        impact_scope_for_signal("unknown")  # type: ignore[arg-type]


def test_conservatism_policy_dataclass_is_frozen() -> None:
    policy = ConservatismPolicy(
        min_sample_size=5,
        min_recurrence_count=3,
        min_confidence=0.6,
        cooling_period_days=14,
        min_sample_size_for_trend=10,
        per_signal_overrides={},
    )

    assert is_dataclass(policy)
    with pytest.raises(FrozenInstanceError):
        policy.min_sample_size = 10  # type: ignore[misc]


def test_conservatism_policy_per_signal_overrides_typed() -> None:
    policy = ConservatismPolicy(
        min_sample_size=5,
        min_recurrence_count=3,
        min_confidence=0.6,
        cooling_period_days=14,
        min_sample_size_for_trend=10,
        per_signal_overrides={"weak_prompt": {"min_sample_size": 12}},
    )

    assert isinstance(policy.per_signal_overrides, dict)
    weak_prompt = policy.per_signal_overrides.get("weak_prompt", {})
    weak_workflow = policy.per_signal_overrides.get("weak_workflow", {})
    assert weak_prompt.get("min_sample_size", policy.min_sample_size) == 12
    assert weak_workflow.get("min_sample_size", policy.min_sample_size) == 5
