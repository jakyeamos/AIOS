#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.cts.registry import CTSRegistry  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Show CTS index status for a repo.")
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="Repo root path")
    args = parser.parse_args()
    registry = CTSRegistry()
    repo = registry.require_repo_by_path(args.repo.resolve())
    store = registry.open_store(repo)
    report = store.get_status_report(repo.repo_id)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

