#!/usr/bin/env python3
"""
AIOS: record-metric.py
Record a workflow metric for the current or specified session.

Usage:
  python3 record-metric.py <metric_name>=<value> [<metric_name>=<value> ...]
  python3 record-metric.py --session <id> <metric_name>=<value> ...

Metrics:
  first_pass_success   1 or 0  — did session complete without a correction turn?
  follow_up_turns      N       — turns needed after first response before task accepted
  accepted_diffs       0.0–1.0 — fraction of proposed changes accepted without modification
  bug_reopen_rate      0.0–1.0 — fraction of bugs that were reopened (rolling, use 0/1 per bug)
  retrieval_hit_rate   0.0–1.0 — fraction of retrieval events that changed the outcome

Examples:
  python3 ~/AIOS/bin/record-metric.py first_pass_success=1
  python3 ~/AIOS/bin/record-metric.py follow_up_turns=3 accepted_diffs=0.8
"""

import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.storage import connect as connect_storage  # noqa: E402

DB = Path(os.environ.get("AIOS_DB", str(Path.home() / "AIOS" / "data" / "aios.db"))).expanduser()
LOG = os.path.expanduser("~/AIOS/logs/hooks.log")

KNOWN_METRICS = {
    "first_pass_success",
    "follow_up_turns",
    "accepted_diffs",
    "bug_reopen_rate",
    "retrieval_hit_rate",
}


def log(msg: str) -> None:
    ts = datetime.now(UTC).isoformat()
    try:
        with open(LOG, "a") as f:
            f.write(f"{ts} [record-metric] {msg}\n")
    except Exception:
        pass


def get_current_session() -> str | None:
    pointer = os.path.expanduser("~/AIOS/logs/current_session")
    if os.path.exists(pointer):
        with open(pointer) as f:
            return f.read().strip() or None
    return None


def main() -> None:
    args = sys.argv[1:]
    session_id = None

    # Parse --session flag
    if "--session" in args:
        idx = args.index("--session")
        if idx + 1 < len(args):
            session_id = args[idx + 1]
            args = args[:idx] + args[idx + 2 :]

    if not session_id:
        session_id = get_current_session()

    if not session_id:
        print(
            "ERROR: No session ID found. Pass --session <id> or ensure current_session pointer exists."
        )
        sys.exit(1)

    if not args:
        print(__doc__)
        sys.exit(1)

    # Parse metric=value pairs
    metrics = {}
    for arg in args:
        if "=" not in arg:
            print(f"ERROR: Invalid format '{arg}'. Use metric_name=value.")
            sys.exit(1)
        name, _, raw_val = arg.partition("=")
        name = name.strip()
        try:
            value = float(raw_val.strip())
        except ValueError:
            print(f"ERROR: Value '{raw_val}' is not a number.")
            sys.exit(1)
        if name not in KNOWN_METRICS:
            print(
                f"WARNING: '{name}' is not a known metric. Known: {', '.join(sorted(KNOWN_METRICS))}"
            )
        metrics[name] = value

    try:
        conn = connect_storage(DB)
        now = datetime.now(UTC).isoformat()
        for name, value in metrics.items():
            row_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO workflow_metrics (id, session_id, metric_name, metric_value, recorded_at) VALUES (?, ?, ?, ?, ?)",
                (row_id, session_id, name, value, now),
            )
            log(f"recorded {name}={value} for session {session_id}")
            print(f"  {name} = {value}  →  recorded for session {session_id[:8]}")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"ERROR: {e}")
        log(f"db error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
