from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from services.meta_learning_proposals import (
    DEFAULT_PROPOSAL_ROOT,
    MetaLearningProposal,
    generate_meta_learning_proposals,
    write_proposals_jsonl,
)
from services.meta_learning_router import route_scored_signals
from services.meta_learning_scoring import score_meta_learning_signals
from services.meta_learning_signals import extract_meta_learning_signals


@dataclass(frozen=True)
class SessionMetaLearningIngestResult:
    signal_count: int
    accepted_signal_count: int
    proposal_count: int
    proposal_path: str | None
    proposals: list[MetaLearningProposal]

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_count": self.signal_count,
            "accepted_signal_count": self.accepted_signal_count,
            "proposal_count": self.proposal_count,
            "proposal_path": self.proposal_path,
            "proposals": [proposal.to_dict() for proposal in self.proposals],
        }


def propose_session_meta_learning(
    session: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    proposal_root: Path = DEFAULT_PROPOSAL_ROOT,
    filename: str = "codex-session-proposals.jsonl",
    existing_rules: Sequence[str] = (),
    write: bool = True,
) -> SessionMetaLearningIngestResult:
    signals = extract_meta_learning_signals(session)
    scored = score_meta_learning_signals(signals)
    routes = route_scored_signals(scored)
    proposals = generate_meta_learning_proposals(scored, routes, existing_rules=existing_rules)
    proposal_path = None
    if write and proposals:
        proposal_path = str(write_proposals_jsonl(proposals, root=proposal_root, filename=filename))
    return SessionMetaLearningIngestResult(
        signal_count=len(signals),
        accepted_signal_count=sum(1 for item in scored if item.accepted),
        proposal_count=len(proposals),
        proposal_path=proposal_path,
        proposals=proposals,
    )
