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
from services.cts.incremental import WatchEvent, watch_repo  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Watch repo and run CTS incremental updates.")
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="Repo root path")
    parser.add_argument("--base", default="HEAD~1", help="Fallback git base for manual update mode")
    parser.add_argument("--debounce-ms", type=int, default=300, help="Debounce window in milliseconds")
    args = parser.parse_args()

    def on_change(event: WatchEvent) -> None:
        rel = []
        for path in event.changed_files:
            try:
                rel.append(str(path.resolve().relative_to(args.repo.resolve())))
            except Exception:
                continue
        if not rel:
            return
        result = incremental_update(args.repo, changed_files=rel, base=args.base)
        payload = {"event_reason": event.reason, "changed_files": rel, "result": result}
        print(json.dumps(payload, sort_keys=True), flush=True)

    watch_repo(args.repo.resolve(), callback=on_change, debounce_ms=args.debounce_ms)


if __name__ == "__main__":
    main()

