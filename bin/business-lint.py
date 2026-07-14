#!/usr/bin/env python3
"""AIOS: business-lint.py — lint business wiki candidates and ingest state."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.business.lint import (  # noqa: E402
    LINT_REPORT,
    OUTPUT_JSON,
    lint_summary_text,
    run_business_lint,
    write_lint_outputs,
)
from services.business.paths import DB_PATH  # noqa: E402
from services.business.schema import ensure_business_memory_schema  # noqa: E402
from services.storage import connect as connect_storage  # noqa: E402


def main() -> int:
    conn = connect_storage(Path(os.environ.get("AIOS_DB", str(DB_PATH))))
    ensure_business_memory_schema(conn)
    report = run_business_lint(conn)
    conn.close()
    write_lint_outputs(report)
    print(lint_summary_text(report))
    print(f"json: {OUTPUT_JSON}")
    print(f"report: {LINT_REPORT}")
    if not report.ok:
        print(json.dumps({"critical": [f.__dict__ for f in report.critical]}, indent=2))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
