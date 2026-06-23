from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass
from typing import Any, Literal

from services.meta_learning_signals import MetaLearningSignal

ConfidenceBand = Literal[
    "observe_only",
    "suggest_project_note_or_low_risk_command",
    "propose_project_rule_skill_or_command",
    "strong_review_gated_proposal",
]

GENERIC_PATTERNS = (
    "best practice",
    "clean code",
    "write better code",
    "be better",
    "improve quality",
)
VAGUE_PATTERNS = (
    "stuff",
    "things",
    "something",
    "better",
    "nice",
)
HIGH_BLAST_RADIUS_PATTERNS = (
    "all repos",
    "all projects",
    "every repo",
    "every project",
    "global",
    "always-loaded",
    "agent rule",
    "agents.md",
    "config/agent-rules.md",
)
SECURITY_PATTERNS = (
    "secret",
    "credential",
    "token",
    "password",
    "auth",
    "production",
    "deploy",
)
PERMISSION_PATTERNS = (
    "auto-allow",
    "auto allow",
    "without approval",
    "without asking",
    "always approve",
    "accept all permissions",
)


@dataclass(frozen=True)
class QualityFilterResult:
    accepted: bool
    rejected_reasons: list[str]
    questions: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScoredMetaLearningSignal:
    signal: MetaLearningSignal
    score: int
    band: ConfidenceBand
    score_reasons: list[str]
    quality_filter: QualityFilterResult
    requires_manual_review: bool
    risk_flags: list[str]

    @property
    def accepted(self) -> bool:
        return self.quality_filter.accepted

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal": self.signal.to_dict(),
            "score": self.score,
            "band": self.band,
            "score_reasons": self.score_reasons,
            "quality_filter": self.quality_filter.to_dict(),
            "requires_manual_review": self.requires_manual_review,
            "risk_flags": self.risk_flags,
            "accepted": self.accepted,
        }


def score_meta_learning_signal(signal: MetaLearningSignal) -> ScoredMetaLearningSignal:
    score, score_reasons = _base_score(signal)
    risk_flags = _risk_flags(signal)
    modifier_score, modifier_reasons = _modifier_score(signal, risk_flags)
    score += modifier_score
    score_reasons.extend(modifier_reasons)
    quality_filter = quality_filter_signal(signal, risk_flags)
    requires_manual_review = bool(risk_flags) or signal.type == "contradiction" or score >= 8
    return ScoredMetaLearningSignal(
        signal=signal,
        score=max(0, score),
        band=confidence_band(score),
        score_reasons=score_reasons,
        quality_filter=quality_filter,
        requires_manual_review=requires_manual_review,
        risk_flags=risk_flags,
    )


def score_meta_learning_signals(
    signals: Iterable[MetaLearningSignal],
) -> list[ScoredMetaLearningSignal]:
    return [score_meta_learning_signal(signal) for signal in signals]


def scored_signals_to_dicts(signals: Iterable[ScoredMetaLearningSignal]) -> list[dict[str, Any]]:
    return [signal.to_dict() for signal in signals]


def confidence_band(score: int) -> ConfidenceBand:
    if score <= 2:
        return "observe_only"
    if score <= 4:
        return "suggest_project_note_or_low_risk_command"
    if score <= 7:
        return "propose_project_rule_skill_or_command"
    return "strong_review_gated_proposal"


def quality_filter_signal(
    signal: MetaLearningSignal,
    risk_flags: list[str] | None = None,
) -> QualityFilterResult:
    risks = risk_flags if risk_flags is not None else _risk_flags(signal)
    text = _signal_text(signal)
    questions = {
        "specific_actionable_learning": _is_specific(signal, text),
        "future_value": _has_future_value(signal, text),
        "supported_and_non_contradictory": _is_supported_and_non_contradictory(signal),
        "safe_to_route": "permission_risk" not in risks,
    }
    rejected_reasons = [name for name, passed in questions.items() if not passed]
    if _matches_any(text, GENERIC_PATTERNS):
        rejected_reasons.append("generic_best_practice")
    if signal.type == "contradiction" and signal.frequency < 3:
        rejected_reasons.append("contradictory_without_enough_evidence")
    if "permission_risk" in risks:
        rejected_reasons.append("unsafe_permission_change")
    return QualityFilterResult(
        accepted=not rejected_reasons,
        rejected_reasons=sorted(set(rejected_reasons)),
        questions=questions,
    )


def _base_score(signal: MetaLearningSignal) -> tuple[int, list[str]]:
    text = _signal_text(signal)
    if signal.type == "explicit_correction":
        if _matches_any(text, ("always", "never", "from now on")):
            return 5, ["explicit always/never/from-now-on correction +5"]
        return 2, ["single correction +2"]
    if signal.type == "repeated_pattern":
        if len(signal.source_sessions) >= 2:
            return 4, ["repeated correction across sessions +4"]
        if signal.frequency >= 2:
            return 3, ["repeated correction within one session +3"]
        return 2, ["single repeated-pattern evidence +2"]
    if signal.type == "approval":
        if signal.frequency >= 2 or len(signal.source_sessions) >= 2:
            return 2, ["repeated approval +2"]
        return 1, ["single approval +1"]
    if signal.type == "command_repetition":
        return 3, ["repeated manual command +3"]
    if signal.type == "tool_friction":
        return 3, ["repeated tool loop/failure +3"]
    if signal.type == "model_mismatch":
        return 3, ["model mismatch +3"]
    if signal.type == "context_miss":
        return 4, ["context miss +4"]
    if signal.type == "contradiction":
        return 0, ["contradiction: no auto-promotion"]
    return 0, ["unknown signal type"]


def _modifier_score(signal: MetaLearningSignal, risk_flags: list[str]) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    text = _signal_text(signal)
    if signal.recency:
        score += 1
        reasons.append("recent signal +1")
    if "remember" in text or "from now on" in text:
        score += 2
        reasons.append("explicit remember/from-now-on request +2")
    if _multi_project_evidence(signal):
        score += 2
        reasons.append("multi-project evidence +2")
    if "contradiction" in risk_flags:
        reasons.append("contradiction: conflict, no auto-promotion")
    if "high_blast_radius" in risk_flags:
        reasons.append("high blast radius: manual review required")
    if "security_sensitive" in risk_flags:
        reasons.append("security sensitive: manual review required")
    if "permission_risk" in risk_flags:
        reasons.append("permission risk: manual review required")
    return score, reasons


def _risk_flags(signal: MetaLearningSignal) -> list[str]:
    text = _signal_text(signal)
    flags: list[str] = []
    if signal.type == "contradiction":
        flags.append("contradiction")
    if signal.risk_level == "high" or _matches_any(text, HIGH_BLAST_RADIUS_PATTERNS):
        flags.append("high_blast_radius")
    if _matches_any(text, SECURITY_PATTERNS):
        flags.append("security_sensitive")
    if _matches_any(text, PERMISSION_PATTERNS):
        flags.append("permission_risk")
    return sorted(set(flags))


def _is_specific(signal: MetaLearningSignal, text: str) -> bool:
    if _matches_any(text, GENERIC_PATTERNS):
        return False
    if len(signal.summary.split()) < 4:
        return False
    return not (_matches_any(text, VAGUE_PATTERNS) and signal.frequency <= 1)


def _has_future_value(signal: MetaLearningSignal, text: str) -> bool:
    if signal.frequency > 1 or len(signal.source_sessions) > 1:
        return True
    if signal.type in {"explicit_correction", "command_repetition", "context_miss", "model_mismatch"}:
        return _matches_any(
            text,
            (
                "always",
                "never",
                "from now on",
                "in this repo",
                "remember",
                "command",
                "model",
                "context",
            ),
        )
    return False


def _is_supported_and_non_contradictory(signal: MetaLearningSignal) -> bool:
    if signal.type != "contradiction":
        return bool(signal.evidence)
    return signal.frequency >= 3 and len(signal.source_sessions) >= 2


def _multi_project_evidence(signal: MetaLearningSignal) -> bool:
    projects = {
        value
        for evidence in signal.evidence
        for key in ("project", "project_id", "repo", "workspace")
        if (value := evidence.get(key))
    }
    return len(projects) >= 2


def _signal_text(signal: MetaLearningSignal) -> str:
    evidence_text = " ".join(item.get("summary", "") for item in signal.evidence)
    confidence_text = " ".join(signal.confidence_points)
    return f"{signal.summary} {evidence_text} {confidence_text} {signal.recommended_target_layer}".lower()


def _matches_any(text: str, patterns: Iterable[str]) -> bool:
    return any(pattern in text for pattern in patterns)
