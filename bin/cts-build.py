#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.cts import full_build  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Build full CTS index for a repo.")
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="Repo root path")
    args = parser.parse_args()
    result = full_build(args.repo)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
