#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bin"))

from aios_paths import get_vault_root  # noqa: E402

from services.workflow_synthesis import (  # noqa: E402
    approve_workflow_proposal,
    synthesize_workflow_proposals,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Synthesize reusable workflow proposals from recurring AIOS patterns."
    )
    parser.add_argument("--db", default=str(ROOT / "data" / "aios.db"))
    parser.add_argument("--min-confidence", type=float, default=0.75)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview synthesized proposals without persisting them.",
    )
    parser.add_argument("--vault-root", default=str(get_vault_root()))
    parser.add_argument(
        "--no-vault", action="store_true", help="Disable Obsidian vault backfill candidates."
    )
    parser.add_argument(
        "--approve", help="Approve a proposal id and append it to workflow/skill registries."
    )
    parser.add_argument("--actor", default="operator")
    parser.add_argument("--note")
    parser.add_argument("--registry", default=str(ROOT / "config" / "workflows" / "registry.json"))
    parser.add_argument("--skills", default=str(ROOT / "config" / "workflows" / "skills.json"))
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    try:
        if args.approve:
            proposal = approve_workflow_proposal(
                conn,
                proposal_id=args.approve,
                actor=args.actor,
                registry_path=Path(args.registry),
                skills_path=Path(args.skills),
                note=args.note,
            )
            conn.commit()
            print(f"approved\t{proposal['id']}\t{proposal['proposal_key']}")
            return 0

        proposals = synthesize_workflow_proposals(
            conn,
            min_confidence=args.min_confidence,
            limit=args.limit,
            vault_root=None if args.no_vault else Path(args.vault_root).expanduser(),
        )
        if args.dry_run:
            conn.rollback()
        else:
            conn.commit()
    finally:
        conn.close()

    for proposal in proposals:
        marker = "would_create" if args.dry_run else "pending_approval"
        print(f"{marker}\t{proposal['id']}\t{proposal['proposal_key']}\t{proposal['title']}")
    prefix = "would_create" if args.dry_run else "created"
    print(f"{prefix}={len(proposals)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
