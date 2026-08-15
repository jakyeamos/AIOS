#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.storage import connect as connect_storage  # noqa: E402
from services.workflow_experiments import (  # noqa: E402
    run_queued_workflow_skill_experiments,
    run_workflow_skill_experiment,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run queued workflow-skill experiments without an LLM agent."
    )
    parser.add_argument("--db", default=os.environ.get("AIOS_DB", str(ROOT / "data" / "aios.db")))
    parser.add_argument("--id", help="Run one workflow_skill_experiments row by id.")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conn = connect_storage(Path(args.db).expanduser())
    try:
        if args.id:
            results = [run_workflow_skill_experiment(conn, args.id, dry_run=args.dry_run)]
        else:
            results = run_queued_workflow_skill_experiments(
                conn,
                limit=args.limit,
                dry_run=args.dry_run,
            )
    finally:
        conn.close()

    print(json.dumps({"count": len(results), "results": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
