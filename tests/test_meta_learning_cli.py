from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.meta_learning_cli import (  # noqa: E402
    create_meta_learning_parser,
    meta_learning_cli_payload,
)
from services.meta_learning_proposals import (  # noqa: E402
    MetaLearningProposal,
    write_proposals_jsonl,
)


def _proposal() -> MetaLearningProposal:
    return MetaLearningProposal(
        proposal_id="meta-proposal-cli",
        title="Route explicit correction to project",
        summary="User correction: Always use pnpm in this repo.",
        target_layer="project",
        target_file="AGENTS.md or project context packet after review",
        confidence_score=6,
        risk_level="medium",
        evidence=[{"session_id": "s1", "kind": "message:user", "summary": "Always use pnpm"}],
        why_this_layer="Project-specific evidence routes away from global rules.",
        proposed_patch="Review action: decide whether to add this narrowly.",
        rollback="Do not apply automatically.",
        requires_manual_approval=True,
        source_signal_id="meta-signal-cli",
    )


def test_parser_accepts_required_meta_commands() -> None:
    parser = create_meta_learning_parser()

    assert parser.parse_args(["analyze-session", "session.json"]).command == "analyze-session"
    assert parser.parse_args(["proposals", "--file", "proposals.jsonl"]).command == "proposals"
    assert parser.parse_args(["eval", "meta-proposal-cli"]).command == "eval"


def test_analyze_session_payload_extracts_signals(tmp_path: Path) -> None:
    session = tmp_path / "session.json"
    session.write_text(
        json.dumps({"session_id": "s1", "messages": [{"role": "user", "text": "Never use npm."}]}),
        encoding="utf-8",
    )

    payload = meta_learning_cli_payload(["analyze-session", str(session)])

    assert payload["signal_count"] == 1
    assert payload["signals"][0]["type"] == "explicit_correction"


def test_proposals_payload_lists_jsonl_records(tmp_path: Path) -> None:
    path = write_proposals_jsonl([_proposal()], root=tmp_path)

    payload = meta_learning_cli_payload(["proposals", "--file", str(path)])

    assert payload["proposal_count"] == 1
    assert payload["proposals"][0]["proposal_id"] == "meta-proposal-cli"


def test_eval_payload_generates_shadow_eval_plan(tmp_path: Path) -> None:
    path = write_proposals_jsonl([_proposal()], root=tmp_path)

    payload = meta_learning_cli_payload(["eval", "meta-proposal-cli", "--file", str(path)])

    assert payload["eval_plan"]["proposal_id"] == "meta-proposal-cli"
    assert payload["eval_plan"]["required_for_durable_global_promotion"] is True
