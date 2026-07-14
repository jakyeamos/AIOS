#!/usr/bin/env python3
"""
AIOS: business-compile.py
Business wiki compiler — raw sources to wiki candidates.

Usage:
  python3 ~/AIOS/bin/business-compile.py --since beginning
  python3 ~/AIOS/bin/business-compile.py --since beginning --llm
  python3 ~/AIOS/bin/business-compile.py --since beginning --llm --provider agent
  python3 ~/AIOS/bin/business-compile.py --llm-apply --run-id agent-20260707T120000Z
  python3 ~/AIOS/bin/business-compile.py --llm-status
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bin"))

from services.business.compiler import compile_business_sources  # noqa: E402
from services.business.llm.apply import apply_agent_run  # noqa: E402
from services.business.llm.client import provider_status  # noqa: E402
from services.business.paths import DB_PATH, ensure_staging_dirs  # noqa: E402
from services.business.schema import ensure_business_memory_schema  # noqa: E402
from services.business.sources_db import (  # noqa: E402
    fetch_uncompiled_sources,
    resolve_since_cursor,
)
from services.storage import connect as connect_storage  # noqa: E402


def _connect() -> sqlite3.Connection:
    return connect_storage(Path(os.environ.get("AIOS_DB", str(DB_PATH))))


def cmd_compile(args: argparse.Namespace) -> int:
    ensure_staging_dirs()
    conn = _connect()
    ensure_business_memory_schema(conn)
    if args.dry_run:
        since_cursor = resolve_since_cursor(conn, args.since)
        pending = fetch_uncompiled_sources(conn, since_iso=since_cursor)
        conn.close()
        print(
            json.dumps(
                {
                    "ok": True,
                    "dry_run": True,
                    "since": args.since,
                    "since_cursor": since_cursor,
                    "pending_sources": len(pending),
                    "source_ids": [source.source_id for source in pending],
                    "llm": bool(args.llm),
                    "provider": args.provider,
                    "llm_status": provider_status(args.provider) if args.llm else None,
                },
                indent=2,
            )
        )
        return 0

    summary = compile_business_sources(
        conn,
        since=args.since,
        llm=bool(args.llm),
        provider_name=args.provider,
    )
    conn.close()
    print(
        json.dumps(
            {
                "ok": summary.status in {"success", "partial"},
                "summary": {
                    "run_id": summary.run_id,
                    "status": summary.status,
                    "sources_processed": summary.sources_processed,
                    "pages_created": summary.pages_created,
                    "pages_updated": summary.pages_updated,
                    "since_cursor": summary.since_cursor,
                    "llm_enabled": summary.llm_enabled,
                    "llm_provider": summary.llm_provider,
                    "llm_analyzed": summary.llm_analyzed,
                    "llm_jobs_queued": summary.llm_jobs_queued,
                    "agent_manifest": summary.agent_manifest,
                    "errors": summary.errors,
                },
            },
            indent=2,
        )
    )
    return 0 if summary.status in {"success", "partial"} else 1


def cmd_llm_apply(args: argparse.Namespace) -> int:
    if not args.run_id:
        print(json.dumps({"ok": False, "error": "--run-id is required for --llm-apply"}))
        return 1
    conn = _connect()
    ensure_business_memory_schema(conn)
    result = apply_agent_run(conn, args.run_id)
    conn.close()
    print(json.dumps({"ok": True, **result}, indent=2))
    return 0


def cmd_llm_status(args: argparse.Namespace) -> int:
    print(json.dumps({"ok": True, **provider_status(args.provider)}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--since",
        default="beginning",
        help="beginning | last-run | ISO8601 timestamp",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show pending sources only")
    parser.add_argument("--llm", action="store_true", help="Enable LLM-enhanced summary compile")
    parser.add_argument(
        "--provider",
        choices=["auto", "api", "cli", "agent"],
        default=None,
        help="LLM provider (default: BUSINESS_LLM_PROVIDER or auto-detect)",
    )
    parser.add_argument(
        "--llm-apply",
        action="store_true",
        help="Apply agent JSON responses from staging/business-llm-responses/",
    )
    parser.add_argument("--run-id", help="Agent LLM run id for --llm-apply")
    parser.add_argument("--llm-status", action="store_true", help="Show LLM provider availability")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.llm_status:
        return cmd_llm_status(args)
    if args.llm_apply:
        return cmd_llm_apply(args)
    return cmd_compile(args)


if __name__ == "__main__":
    raise SystemExit(main())
