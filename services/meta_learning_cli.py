from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from services.meta_learning_proposals import DEFAULT_PROPOSAL_ROOT, read_proposals_jsonl
from services.meta_learning_shadow_eval import generate_shadow_eval_plan
from services.meta_learning_signals import extract_meta_learning_signals, signals_to_dicts


def create_meta_learning_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Meta-learning proposal fallback CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("audit", help="Show meta-learning fallback CLI capabilities")

    analyze_session = subparsers.add_parser("analyze-session", help="Analyze one JSON session")
    analyze_session.add_argument("path")

    analyze_sessions = subparsers.add_parser(
        "analyze-sessions", help="Analyze JSON sessions in a directory"
    )
    analyze_sessions.add_argument("directory")

    proposals = subparsers.add_parser("proposals", help="List stored proposal records")
    proposals.add_argument("--file", default=str(DEFAULT_PROPOSAL_ROOT / "proposals.jsonl"))

    apply = subparsers.add_parser("apply", help="Block until governed apply path exists")
    apply.add_argument("proposal_id")

    reject = subparsers.add_parser("reject", help="Return a review rejection record")
    reject.add_argument("proposal_id")
    reject.add_argument("--reason", default="")

    eval_plan = subparsers.add_parser("eval", help="Generate a shadow eval plan for a proposal")
    eval_plan.add_argument("proposal_id")
    eval_plan.add_argument("--file", default=str(DEFAULT_PROPOSAL_ROOT / "proposals.jsonl"))
    eval_plan.add_argument("--exemption", default=None)
    return parser


def meta_learning_cli_payload(argv: list[str]) -> dict[str, Any]:
    parser = create_meta_learning_parser()
    args = parser.parse_args(argv)
    if args.command == "audit":
        return {
            "commands": [
                "audit",
                "analyze-session",
                "analyze-sessions",
                "proposals",
                "apply",
                "reject",
                "eval",
            ],
            "fallback_reason": "central aios_cli integration is deferred when the file is already dirty",
        }
    if args.command == "analyze-session":
        return _analyze_session(Path(args.path))
    if args.command == "analyze-sessions":
        return _analyze_sessions(Path(args.directory))
    if args.command == "proposals":
        proposals = read_proposals_jsonl(Path(args.file))
        return {
            "proposal_count": len(proposals),
            "proposals": [proposal.to_dict() for proposal in proposals],
        }
    if args.command == "apply":
        return {
            "proposal_id": args.proposal_id,
            "status": "blocked_requires_governed_apply_path",
            "requires_manual_approval": True,
        }
    if args.command == "reject":
        return {"proposal_id": args.proposal_id, "status": "rejected", "reason": args.reason}
    if args.command == "eval":
        proposal = _find_proposal(Path(args.file), args.proposal_id)
        plan = generate_shadow_eval_plan(proposal, exemption_reason=args.exemption)
        return {"proposal_id": args.proposal_id, "eval_plan": plan.to_dict()}
    raise ValueError(f"Unsupported meta-learning command: {args.command}")


def _analyze_session(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    signals = signals_to_dicts(extract_meta_learning_signals(raw))
    return {"input_path": str(path), "signal_count": len(signals), "signals": signals}


def _analyze_sessions(directory: Path) -> dict[str, Any]:
    results = [_analyze_session(path) for path in sorted(directory.glob("*.json"))]
    return {
        "directory": str(directory),
        "session_count": len(results),
        "signal_count": sum(int(result["signal_count"]) for result in results),
        "sessions": results,
    }


def _find_proposal(path: Path, proposal_id: str):
    for proposal in read_proposals_jsonl(path):
        if proposal.proposal_id == proposal_id:
            return proposal
    raise ValueError(f"Proposal not found: {proposal_id}")
