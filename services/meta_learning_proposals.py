from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from services.meta_learning_router import MetaLearningRoute
from services.meta_learning_scoring import ScoredMetaLearningSignal

DEFAULT_PROPOSAL_ROOT = Path("data/meta-learning/proposals")
ProposalStatus = Literal["pending_review", "rejected", "approved", "observed"]
ConflictAction = Literal["replace", "narrow", "split_by_context", "ask_user"]


@dataclass(frozen=True)
class MetaLearningConflictRecord:
    older_rule: str
    newer_signal: str
    recommended_action: ConflictAction
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MetaLearningProposal:
    proposal_id: str
    title: str
    summary: str
    target_layer: str
    target_file: str
    confidence_score: int
    risk_level: str
    evidence: list[dict[str, str]]
    why_this_layer: str
    proposed_patch: str
    rollback: str
    requires_manual_approval: bool
    source_signal_id: str
    status: ProposalStatus = "pending_review"
    conflict: MetaLearningConflictRecord | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.conflict is None:
            data["conflict"] = None
        return data


def generate_meta_learning_proposal(
    scored: ScoredMetaLearningSignal,
    route: MetaLearningRoute,
    *,
    existing_rules: Sequence[str] = (),
) -> MetaLearningProposal:
    signal = scored.signal
    conflict = detect_conflict(scored, existing_rules)
    target_file = _target_file(route)
    proposal_id = stable_proposal_id(signal.signal_id, route.target_layer, target_file)
    return MetaLearningProposal(
        proposal_id=proposal_id,
        title=_proposal_title(scored, route),
        summary=signal.summary,
        target_layer=route.target_layer,
        target_file=target_file,
        confidence_score=scored.score,
        risk_level=_proposal_risk(scored),
        evidence=signal.evidence,
        why_this_layer=route.justification,
        proposed_patch=_proposed_patch(scored, route, conflict),
        rollback=_rollback(route),
        requires_manual_approval=True,
        source_signal_id=signal.signal_id,
        conflict=conflict,
    )


def generate_meta_learning_proposals(
    scored_signals: Iterable[ScoredMetaLearningSignal],
    routes: Iterable[MetaLearningRoute],
    *,
    existing_rules: Sequence[str] = (),
) -> list[MetaLearningProposal]:
    scored_by_id = {scored.signal.signal_id: scored for scored in scored_signals}
    proposals: list[MetaLearningProposal] = []
    for route in routes:
        scored = scored_by_id.get(route.signal_id)
        if scored is None:
            continue
        if route.target_layer == "observe_only" and scored.signal.type != "contradiction":
            continue
        proposals.append(
            generate_meta_learning_proposal(scored, route, existing_rules=existing_rules)
        )
    return proposals


def proposals_to_dicts(proposals: Iterable[MetaLearningProposal]) -> list[dict[str, Any]]:
    return [proposal.to_dict() for proposal in proposals]


def write_proposals_jsonl(
    proposals: Iterable[MetaLearningProposal],
    *,
    root: Path = DEFAULT_PROPOSAL_ROOT,
    filename: str = "proposals.jsonl",
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    output_path = root / filename
    with output_path.open("a", encoding="utf-8") as handle:
        for proposal in proposals:
            handle.write(json.dumps(proposal.to_dict(), sort_keys=True))
            handle.write("\n")
    return output_path


def read_proposals_jsonl(path: Path) -> list[MetaLearningProposal]:
    proposals: list[MetaLearningProposal] = []
    if not path.exists():
        return proposals
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            proposals.append(_proposal_from_dict(json.loads(stripped)))
    return proposals


def stable_proposal_id(signal_id: str, target_layer: str, target_file: str) -> str:
    raw = json.dumps(
        {"signal_id": signal_id, "target_layer": target_layer, "target_file": target_file},
        sort_keys=True,
    )
    return f"meta-proposal-{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def detect_conflict(
    scored: ScoredMetaLearningSignal,
    existing_rules: Sequence[str],
) -> MetaLearningConflictRecord | None:
    signal_text = scored.signal.summary.lower()
    if scored.signal.type == "contradiction":
        return MetaLearningConflictRecord(
            older_rule="conflicting directives in session evidence",
            newer_signal=scored.signal.summary,
            recommended_action="ask_user",
            rationale="Contradictory signal evidence requires an explicit user decision.",
        )
    for rule in existing_rules:
        lowered = rule.lower()
        if _opposes(signal_text, lowered):
            return MetaLearningConflictRecord(
                older_rule=rule,
                newer_signal=scored.signal.summary,
                recommended_action=_recommended_conflict_action(scored),
                rationale="The new signal appears to oppose an existing rule or preference.",
            )
    return None


def _proposal_title(scored: ScoredMetaLearningSignal, route: MetaLearningRoute) -> str:
    return f"Route {scored.signal.type.replace('_', ' ')} to {route.target_layer}"


def _proposal_risk(scored: ScoredMetaLearningSignal) -> str:
    if scored.risk_flags:
        return "high" if "permission_risk" in scored.risk_flags else "medium"
    return scored.signal.risk_level


def _target_file(route: MetaLearningRoute) -> str:
    if route.target_layer == "global":
        return "config/agent-rules.md or an intent-specific pointer after review"
    if route.target_layer == "project":
        return "AGENTS.md or project context packet after review"
    if route.target_layer == "skill":
        return "relevant SKILL.md after review"
    if route.target_layer == "command":
        return "command metadata or command docs after review"
    if route.target_layer == "agent":
        return "agent/sub-agent routing policy after review"
    if route.target_layer == "second_brain":
        return "second-brain note proposal after review"
    if route.target_layer == "eval":
        return "eval fixture or regression test after review"
    return "observation log"


def _proposed_patch(
    scored: ScoredMetaLearningSignal,
    route: MetaLearningRoute,
    conflict: MetaLearningConflictRecord | None,
) -> str:
    signal = scored.signal
    lines = [
        f"Target layer: {route.target_layer}",
        f"Target hint: {route.target_hint}",
        f"Learning: {signal.summary}",
        f"Confidence score: {scored.score} ({scored.band})",
        f"Evidence sessions: {', '.join(signal.source_sessions) or 'unknown'}",
        "Review action: decide whether to add this as a narrow, intent-specific rule.",
    ]
    if route.target_layer == "global":
        lines.append(
            "Global rule guard: promote only if this is broadly applicable; otherwise create an intent-specific pointer."
        )
    if conflict is not None:
        lines.extend(
            [
                "",
                "Conflict:",
                f"- Older rule: {conflict.older_rule}",
                f"- Newer signal: {conflict.newer_signal}",
                f"- Recommended action: {conflict.recommended_action}",
            ]
        )
    return "\n".join(lines)


def _rollback(route: MetaLearningRoute) -> str:
    return (
        "Do not apply automatically. If approved content is later wrong, revert the reviewed "
        f"change in {route.target_layer} storage and mark this proposal rejected or superseded."
    )


def _opposes(signal_text: str, rule_text: str) -> bool:
    return (
        ("always" in signal_text and "never" in rule_text)
        or ("never" in signal_text and "always" in rule_text)
        or ("pnpm" in signal_text and "npm" in rule_text and "never" not in signal_text)
        or ("npm" in signal_text and "pnpm" in rule_text and "never" not in signal_text)
    )


def _recommended_conflict_action(scored: ScoredMetaLearningSignal) -> ConflictAction:
    if "high_blast_radius" in scored.risk_flags or scored.signal.risk_level == "high":
        return "ask_user"
    if len(scored.signal.source_sessions) >= 2:
        return "narrow"
    return "split_by_context"


def _proposal_from_dict(raw: dict[str, Any]) -> MetaLearningProposal:
    conflict = raw.get("conflict")
    return MetaLearningProposal(
        proposal_id=str(raw["proposal_id"]),
        title=str(raw["title"]),
        summary=str(raw["summary"]),
        target_layer=str(raw["target_layer"]),
        target_file=str(raw["target_file"]),
        confidence_score=int(raw["confidence_score"]),
        risk_level=str(raw["risk_level"]),
        evidence=[
            {str(key): str(value) for key, value in item.items()}
            for item in raw.get("evidence", [])
            if isinstance(item, dict)
        ],
        why_this_layer=str(raw["why_this_layer"]),
        proposed_patch=str(raw["proposed_patch"]),
        rollback=str(raw["rollback"]),
        requires_manual_approval=bool(raw["requires_manual_approval"]),
        source_signal_id=str(raw["source_signal_id"]),
        status=str(raw.get("status", "pending_review")),  # type: ignore[arg-type]
        conflict=MetaLearningConflictRecord(
            older_rule=str(conflict["older_rule"]),
            newer_signal=str(conflict["newer_signal"]),
            recommended_action=str(conflict["recommended_action"]),  # type: ignore[arg-type]
            rationale=str(conflict["rationale"]),
        )
        if isinstance(conflict, dict)
        else None,
    )
