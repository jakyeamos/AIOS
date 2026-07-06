#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.aios_cli import DEFAULT_DB_PATH  # noqa: E402
from services.quality_pipeline import (  # noqa: E402
    DEFAULT_CONFIG_PATH,
    get_project_quality_pipeline,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify local CI replacement proof for a linked repo."
    )
    parser.add_argument("--project", required=True)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    return parser.parse_args()


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def main() -> int:
    args = _parse_args()
    with sqlite3.connect(str(args.db)) as conn:
        summary = get_project_quality_pipeline(conn, args.project, config_path=args.config)
    failing = [
        {
            "gate": gate["key"],
            "status": gate["status"],
            "latest_run_id": gate["latest_run_id"],
        }
        for gate in summary["gates"]
        if gate["required"] and gate["key"] != "ci" and gate["status"] != "pass"
    ]
    _print_json(
        {
            "project_id": args.project,
            "status": "pass" if not failing else "fail",
            "checked_gate_count": len(
                [gate for gate in summary["gates"] if gate["required"] and gate["key"] != "ci"]
            ),
            "failing_gates": failing,
        }
    )
    return 0 if not failing else 1


if __name__ == "__main__":
    raise SystemExit(main())
