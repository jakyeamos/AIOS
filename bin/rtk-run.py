#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.rtk_integration import rtk_metrics_log, rtk_run  # noqa: E402


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a command through the AIOS RTK compression layer.")
    parser.add_argument("command", nargs="*", help="Command to run. Use -- before commands with flags.")
    parser.add_argument("--mode", choices=["compressed", "raw", "adaptive"], default="compressed")
    parser.add_argument("--cwd", default=None)
    parser.add_argument("--timeout", type=int, default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--db", default=str(Path.home() / "AIOS" / "data" / "aios.db"))
    parser.add_argument("--session", default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--workflow", default=None)
    parser.add_argument("--metrics", action="store_true", help="Print RTK metrics instead of running a command.")
    return parser


def main() -> None:
    args = create_parser().parse_args()
    conn = None
    db_path = Path(args.db).expanduser()
    if db_path.exists():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

    if args.metrics:
        if conn is None:
            print("ERROR: metrics require an existing AIOS DB", file=sys.stderr)
            raise SystemExit(1)
        payload = rtk_metrics_log(conn, session_id=args.session)
        print(json.dumps(payload, indent=2, sort_keys=True) if args.json else payload)
        conn.close()
        raise SystemExit(0)

    command = shlex.join(args.command).strip()
    if not command:
        print("ERROR: command is required unless --metrics is set", file=sys.stderr)
        raise SystemExit(2)

    result = rtk_run(
        command,
        args.mode,
        cwd=args.cwd,
        timeout=args.timeout,
        session_id=args.session,
        run_id=args.run_id,
        workflow_key=args.workflow,
        conn=conn,
        source_kind="rtk-run-cli",
    )
    if conn is not None:
        conn.commit()
        conn.close()

    if args.json:
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    else:
        print(result.output)
    raise SystemExit(result.exit_code)


if __name__ == "__main__":
    main()
