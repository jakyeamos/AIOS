#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.meta_learning_cli import meta_learning_cli_payload  # noqa: E402


def main() -> int:
    payload = meta_learning_cli_payload(sys.argv[1:])
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
