#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.workflow_experiments import (  # noqa: E402
    queue_test_repo_experiments,
    seed_paper_fixtures,
)


def _pending_workflow_skills(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    rows = conn.execute(
        """
        SELECT proposal_key, skill_specs_json
        FROM workflow_synthesis_proposals
        WHERE status = 'pending_approval'
        ORDER BY proposal_key
        """
    ).fetchall()
    pairs: list[tuple[str, str]] = []
    for workflow_key, raw_skills in rows:
        try:
            skills = json.loads(raw_skills)
        except json.JSONDecodeError:
            continue
        if not isinstance(skills, list):
            continue
        for skill in skills:
            if isinstance(skill, dict) and isinstance(skill.get("key"), str):
                pairs.append((str(workflow_key), str(skill["key"])))
    return pairs


def main() -> int:
    parser = argparse.ArgumentParser(description="Queue workflow skill experiments across AIOS test repos.")
    parser.add_argument("--db", default=str(ROOT / "data" / "aios.db"))
    parser.add_argument("--workflow-key")
    parser.add_argument("--skill-key")
    parser.add_argument("--all-pending", action="store_true")
    parser.add_argument("--seed-paper-fixtures", action="store_true")
    args = parser.parse_args()

    conn = sqlite3.connect(Path(args.db).expanduser())
    queued = []
    seeded = []
    try:
        if args.seed_paper_fixtures:
            seeded = seed_paper_fixtures(conn)

        pairs: list[tuple[str, str]]
        if args.all_pending:
            pairs = _pending_workflow_skills(conn)
        elif args.workflow_key and args.skill_key:
            pairs = [(args.workflow_key, args.skill_key)]
        else:
            parser.error("Use --all-pending or provide --workflow-key and --skill-key.")

        for workflow_key, skill_key in pairs:
            queued.extend(
                queue_test_repo_experiments(
                    conn,
                    workflow_key=workflow_key,
                    skill_key=skill_key,
                )
            )
        conn.commit()
    finally:
        conn.close()

    print(json.dumps({"queued": queued, "seeded_paper_fixtures": seeded}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
