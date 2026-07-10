#!/usr/bin/env python3
"""
AIOS: business-ingest.py
Business memory ingest CLI — init, sync, status.

Usage:
  python3 ~/AIOS/bin/business-ingest.py init
  python3 ~/AIOS/bin/business-ingest.py sync --source manual
  python3 ~/AIOS/bin/business-ingest.py sync --all
  python3 ~/AIOS/bin/business-ingest.py status
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bin"))

from services.business.config import write_default_config_files  # noqa: E402
from services.business.paths import AIOS_ROOT, DB_PATH, ensure_staging_dirs  # noqa: E402
from services.business.pipeline import sync_all, sync_source  # noqa: E402
from services.business.schema import ensure_business_memory_schema  # noqa: E402
from services.business.store import status_snapshot  # noqa: E402


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def cmd_init(_: argparse.Namespace) -> int:
    ensure_staging_dirs()
    config_files = write_default_config_files()
    conn = _connect()
    ensure_business_memory_schema(conn)
    conn.commit()
    conn.close()
    print(
        json.dumps(
            {
                "ok": True,
                "aios_root": str(AIOS_ROOT),
                "db_path": str(DB_PATH),
                "config_files_written": [str(path) for path in config_files],
            },
            indent=2,
        )
    )
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    since = datetime.fromisoformat(args.since) if args.since else None
    conn = _connect()
    ensure_business_memory_schema(conn)
    if args.all:
        summaries = sync_all(conn, since=since)
    else:
        summaries = [
            sync_source(conn, args.source, since=since, move_manual_inbox=not args.keep_inbox)
        ]
    conn.close()
    print(
        json.dumps(
            {
                "ok": True,
                "summaries": [summary.__dict__ for summary in summaries],
            },
            indent=2,
        )
    )
    return 0


def cmd_status(_: argparse.Namespace) -> int:
    conn = _connect()
    ensure_business_memory_schema(conn)
    snapshot = status_snapshot(conn)
    conn.close()
    print(json.dumps({"ok": True, **snapshot}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Create staging dirs, config defaults, and schema")

    sync_parser = sub.add_parser("sync", help="Sync one or all business sources")
    sync_parser.add_argument("--source", choices=["manual", "gmail", "discord", "x"])
    sync_parser.add_argument("--all", action="store_true")
    sync_parser.add_argument("--since", help="ISO8601 lower bound for source timestamps")
    sync_parser.add_argument(
        "--keep-inbox",
        action="store_true",
        help="Do not move processed manual inbox files",
    )

    sub.add_parser("status", help="Show business ingest status")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "sync" and not args.all and not args.source:
        parser.error("sync requires --source NAME or --all")
    if args.command == "init":
        return cmd_init(args)
    if args.command == "sync":
        return cmd_sync(args)
    if args.command == "status":
        return cmd_status(args)
    parser.error(f"Unknown command: {args.command}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
