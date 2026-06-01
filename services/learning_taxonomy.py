from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

LearningSignalKind = Literal[
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
]

LEARNING_SIGNAL_KINDS: tuple[LearningSignalKind, ...] = (
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

SIGNAL_TO_IMPACT_SCOPE: dict[LearningSignalKind, str] = {
    "repeated_failure": "workflow-default",
    "ignored_rule": "standards-default",
    "bloated_packet": "packet-default",
    "weak_prompt": "prompt-default",
    "weak_workflow": "workflow-default",
    "route_misroute": "route-default",
    "standards_regression": "standards-default",
    "writeback_adopted": "scoped",
    "writeback_rejected": "scoped",
    "compounding_gain": "scoped",
}

IS_ACTIONABLE_SIGNAL: frozenset[LearningSignalKind] = frozenset(
    (
        "repeated_failure",
        "ignored_rule",
        "bloated_packet",
        "weak_prompt",
        "weak_workflow",
        "route_misroute",
        "standards_regression",
    )
)


def impact_scope_for_signal(kind: LearningSignalKind) -> str:
    return SIGNAL_TO_IMPACT_SCOPE[kind]


@dataclass(frozen=True)
class ConservatismPolicy:
    min_sample_size: int
    min_recurrence_count: int
    min_confidence: float
    cooling_period_days: int
    min_sample_size_for_trend: int
    per_signal_overrides: dict[str, dict[str, float | int]] = field(default_factory=dict)
