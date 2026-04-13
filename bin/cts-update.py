#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.cts import incremental_update  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run incremental CTS update.")
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="Repo root path")
    parser.add_argument("--base", default="HEAD~1", help="Git base reference for changed-file detection")
    parser.add_argument(
        "--changed-file",
        action="append",
        default=[],
        help="Explicit changed file path (relative to repo); can be repeated",
    )
    args = parser.parse_args()
    changed_files = args.changed_file if args.changed_file else None
    result = incremental_update(args.repo, changed_files=changed_files, base=args.base)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

