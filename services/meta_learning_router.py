from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass
from typing import Any, Literal

from services.meta_learning_scoring import ScoredMetaLearningSignal

TargetLayer = Literal[
    "global",
    "project",
    "skill",
    "command",
    "agent",
    "second_brain",
    "eval",
    "observe_only",
]


@dataclass(frozen=True)
class MetaLearningRoute:
    signal_id: str
    target_layer: TargetLayer
    target_scope: str
    target_hint: str
    justification: str
    requires_manual_review: bool
    score: int
    band: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def route_scored_signal(scored: ScoredMetaLearningSignal) -> MetaLearningRoute:
    if not scored.accepted:
        return _route(
            scored,
            "observe_only",
            "none",
            "rejected by quality filter",
            "Signal is observe-only because the quality filter rejected it.",
        )

    signal = scored.signal
    text = _signal_text(scored)
    recommended = signal.recommended_target_layer
    project_specific = _project_specific(scored)
    multi_project = _multi_project_evidence(scored)

    if signal.type == "contradiction":
        return _route(
            scored,
            "observe_only",
            "manual-review",
            "conflict ledger",
            "Contradictory signals are not routed into rule files automatically.",
        )
    if "second brain" in text or "second-brain" in text:
        return _route(
            scored,
            "second_brain",
            "personal",
            "second-brain note",
            "Signal cites second-brain context.",
        )
    if recommended == "command_suggestion" or signal.type == "command_repetition":
        return _route(
            scored,
            "command",
            "project" if project_specific else "global",
            "command policy",
            "Signal concerns repeated command behavior.",
        )
    if signal.type == "candidate_skill":
        return _route(
            scored,
            "skill",
            "project" if project_specific else "global",
            "skill instruction",
            "Signal identifies a candidate reusable skill.",
        )
    if recommended == "skill_or_agent_suggestion":
        if "skill" in text:
            return _route(
                scored,
                "skill",
                "project" if project_specific else "global",
                "skill instruction",
                "Signal explicitly concerns skill behavior.",
            )
        return _route(
            scored,
            "agent",
            "project" if project_specific else "global",
            "agent/sub-agent suggestion",
            "Signal concerns agent routing or behavior.",
        )
    if recommended == "model_routing_policy" or signal.type == "model_mismatch":
        return _route(
            scored,
            "agent",
            "project" if project_specific else "global",
            "model-routing policy",
            "Signal concerns model selection or sub-agent routing.",
        )
    if signal.type in {"context_miss", "tool_friction"} and scored.score >= 5:
        return _route(
            scored,
            "eval",
            "project" if project_specific else "global",
            "eval/test case",
            "Repeated operational miss should become regression evidence before policy.",
        )
    if recommended == "project_rule" or project_specific:
        return _route(
            scored,
            "project",
            "project",
            "project rule or project note",
            "Project-specific evidence routes away from global rules.",
        )
    if multi_project and scored.score >= 5:
        return _route(
            scored,
            "global",
            "global",
            "global rule proposal",
            "Multi-project evidence justifies global review.",
        )
    return _route(
        scored,
        "observe_only",
        "none",
        "observation log",
        "Signal lacks a safer specific target layer.",
    )


def route_scored_signals(signals: Iterable[ScoredMetaLearningSignal]) -> list[MetaLearningRoute]:
    return [route_scored_signal(signal) for signal in signals]


def routes_to_dicts(routes: Iterable[MetaLearningRoute]) -> list[dict[str, Any]]:
    return [route.to_dict() for route in routes]


def _route(
    scored: ScoredMetaLearningSignal,
    target_layer: TargetLayer,
    target_scope: str,
    target_hint: str,
    justification: str,
) -> MetaLearningRoute:
    return MetaLearningRoute(
        signal_id=scored.signal.signal_id,
        target_layer=target_layer,
        target_scope=target_scope,
        target_hint=target_hint,
        justification=justification,
        requires_manual_review=scored.requires_manual_review
        or target_layer in {"global", "skill", "agent"},
        score=scored.score,
        band=scored.band,
    )


def _project_specific(scored: ScoredMetaLearningSignal) -> bool:
    text = _signal_text(scored)
    return (
        scored.signal.recommended_target_layer == "project_rule"
        or "in this repo" in text
        or any(key in text for key in ("project:", "project_id", "repo:"))
    )


def _multi_project_evidence(scored: ScoredMetaLearningSignal) -> bool:
    projects = {
        value
        for evidence in scored.signal.evidence
        for key in ("project", "project_id", "repo", "workspace")
        if (value := evidence.get(key))
    }
    return len(projects) >= 2


def _signal_text(scored: ScoredMetaLearningSignal) -> str:
    signal = scored.signal
    evidence_text = " ".join(item.get("summary", "") for item in signal.evidence)
    confidence_text = " ".join(signal.confidence_points)
    return f"{signal.summary} {evidence_text} {confidence_text} {signal.recommended_target_layer}".lower()
