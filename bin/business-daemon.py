#!/usr/bin/env python3
"""
AIOS: business-daemon.py
Scheduled business memory loop: sync -> compile -> lint -> log.

Usage:
  python3 ~/AIOS/bin/business-daemon.py --once
  python3 ~/AIOS/bin/business-daemon.py --interval-hours 3
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "bin"
sys.path.insert(0, str(ROOT))

from services.business.compiler import compile_business_sources  # noqa: E402
from services.business.lint import run_business_lint, write_lint_outputs  # noqa: E402
from services.business.paths import DB_PATH, ensure_staging_dirs  # noqa: E402
from services.business.pipeline import sync_all  # noqa: E402
from services.business.schema import ensure_business_memory_schema  # noqa: E402
from services.storage import connect as connect_storage  # noqa: E402

LOG = ROOT / "logs" / "business-daemon.log"


def _log(message: str) -> None:
    line = f"{datetime.now(UTC).replace(microsecond=0).isoformat()} {message}\n"
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(line)
    print(line, end="")


def _connect() -> sqlite3.Connection:
    conn = connect_storage(Path(os.environ.get("AIOS_DB", str(DB_PATH))))
    ensure_business_memory_schema(conn)
    return conn


def run_cycle(*, llm: bool = False, provider: str | None = None) -> dict:
    ensure_staging_dirs()
    conn = _connect()
    ingest = [summary.__dict__ for summary in sync_all(conn)]
    compile_summary = compile_business_sources(
        conn, since="last-run", llm=llm, provider_name=provider
    )
    lint_report = run_business_lint(conn)
    write_lint_outputs(lint_report)
    conn.close()
    return {
        "ingest": ingest,
        "compile": {
            "run_id": compile_summary.run_id,
            "status": compile_summary.status,
            "sources_processed": compile_summary.sources_processed,
            "pages_created": compile_summary.pages_created,
        },
        "lint_ok": lint_report.ok,
        "critical": len(lint_report.critical),
        "warnings": len(lint_report.warnings),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    parser.add_argument("--interval-hours", type=float, default=3.0)
    parser.add_argument("--llm", action="store_true")
    parser.add_argument("--provider", choices=["auto", "api", "cli", "agent"], default=None)
    args = parser.parse_args(argv)

    if args.once:
        result = run_cycle(llm=args.llm, provider=args.provider)
        _log(f"cycle complete {json.dumps(result)}")
        return 0 if result["lint_ok"] else 1

    interval_s = max(args.interval_hours, 0.25) * 3600
    _log(f"daemon starting interval_hours={args.interval_hours}")
    while True:
        try:
            result = run_cycle(llm=args.llm, provider=args.provider)
            _log(f"cycle complete {json.dumps(result)}")
        except Exception as exc:  # noqa: BLE001
            _log(f"cycle failed: {exc}")
        time.sleep(interval_s)


if __name__ == "__main__":
    raise SystemExit(main())
