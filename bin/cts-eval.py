#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.cts.eval.runner import run_suite  # noqa: E402
from services.cts.mcp_server import CTSService  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run CTS benchmark suite.")
    parser.add_argument(
        "--cases-dir",
        type=Path,
        default=ROOT / "services" / "cts" / "eval" / "cases",
        help="Directory containing benchmark case JSON files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("~/AIOS/data/cts/eval_results.json").expanduser(),
        help="Path to write benchmark result JSON",
    )
    args = parser.parse_args()
    service = CTSService()
    report = run_suite(service, args.cases_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.output), "summary": report.get("summary", {})}))


if __name__ == "__main__":
    main()

