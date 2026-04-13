#!/usr/bin/env python3
"""
AIOS: run-experiment.py
Manage workflow improvement experiments. One surface at a time.

Usage:
  python3 run-experiment.py start <name> <surface> <hypothesis> [--challenger <config.json>]
  python3 run-experiment.py end <experiment_id> --verdict keep|discard|inconclusive [--notes "..."]
  python3 run-experiment.py list
  python3 run-experiment.py status <experiment_id>

Surfaces: retrieval_policy, session_packet, prompt_template, hook_behavior

Example:
  python3 run-experiment.py start "larger-packet" session_packet \\
    "Increasing max_chars to 2400 will reduce follow_up_turns" \\
    --challenger ~/AIOS/config/retrieval-policy-challenger.json
"""

import json
import os
import shutil
import sqlite3
import sys
import uuid
from datetime import UTC, datetime

DB = os.path.expanduser("~/AIOS/data/aios.db")
POLICY_PATH = os.path.expanduser("~/AIOS/config/retrieval-policy.json")
POLICY_BACKUP = os.path.expanduser("~/AIOS/config/retrieval-policy.baseline.json")


def get_conn() -> sqlite3.Connection:
    return sqlite3.connect(DB)


def cmd_start(args: list[str]) -> None:
    if len(args) < 3:
        print("Usage: run-experiment.py start <name> <surface> <hypothesis> [--challenger <file>]")
        sys.exit(1)

    name, surface, hypothesis = args[0], args[1], args[2]
    challenger_path = None
    if "--challenger" in args:
        idx = args.index("--challenger")
        challenger_path = args[idx + 1] if idx + 1 < len(args) else None

    exp_id = str(uuid.uuid4())[:8]
    conn = get_conn()
    now = datetime.now(UTC).isoformat()
    conn.execute(
        "INSERT INTO experiments (id, name, surface, hypothesis, started_at) VALUES (?, ?, ?, ?, ?)",
        (exp_id, name, surface, hypothesis, now),
    )
    conn.commit()
    conn.close()

    # Swap in challenger config if provided
    if challenger_path and surface in ("retrieval_policy", "session_packet"):
        if os.path.exists(POLICY_PATH):
            shutil.copy(POLICY_PATH, POLICY_BACKUP)
            print(f"Baseline config backed up to {POLICY_BACKUP}")
        if os.path.exists(challenger_path):
            shutil.copy(challenger_path, POLICY_PATH)
            print(f"Challenger config activated from {challenger_path}")

    print(f"Experiment started: {exp_id}")
    print(f"  Name:      {name}")
    print(f"  Surface:   {surface}")
    print(f"  Hypothesis: {hypothesis}")
    print(f"\nRun at least 3 sessions, then: python3 run-experiment.py end {exp_id} --verdict keep|discard")


def cmd_end(args: list[str]) -> None:
    if not args:
        print("Usage: run-experiment.py end <experiment_id> --verdict keep|discard|inconclusive [--notes '...']")
        sys.exit(1)

    exp_id = args[0]
    verdict = None
    notes = None

    if "--verdict" in args:
        idx = args.index("--verdict")
        verdict = args[idx + 1] if idx + 1 < len(args) else None
    if "--notes" in args:
        idx = args.index("--notes")
        notes = args[idx + 1] if idx + 1 < len(args) else None

    if verdict not in ("keep", "discard", "inconclusive"):
        print("ERROR: --verdict must be keep, discard, or inconclusive")
        sys.exit(1)

    conn = get_conn()
    now = datetime.now(UTC).isoformat()
    conn.execute(
        "UPDATE experiments SET verdict=?, ended_at=?, notes=? WHERE id=?",
        (verdict, now, notes, exp_id),
    )
    conn.commit()

    # If discarding, restore baseline config
    if verdict == "discard" and os.path.exists(POLICY_BACKUP):
        shutil.copy(POLICY_BACKUP, POLICY_PATH)
        print("Baseline config restored.")

    row = conn.execute("SELECT name, surface, hypothesis FROM experiments WHERE id=?", (exp_id,)).fetchone()
    conn.close()

    if row:
        name, surface, hypothesis = row
        print(f"Experiment {exp_id} closed: {verdict.upper()}")
        print(f"  Name:      {name}")
        print(f"  Surface:   {surface}")
        if notes:
            print(f"  Notes:     {notes}")


def cmd_list() -> None:
    conn = get_conn()
    cur = conn.execute(
        "SELECT id, name, surface, verdict, started_at, ended_at FROM experiments ORDER BY started_at DESC LIMIT 20"
    )
    rows = cur.fetchall()
    conn.close()

    if not rows:
        print("No experiments recorded yet.")
        return

    for exp_id, name, surface, verdict, started, ended in rows:
        status = verdict.upper() if verdict else "ACTIVE"
        print(f"  {exp_id}  [{status}]  {name}  ({surface})  started={started[:10]}")


def cmd_status(args: list[str]) -> None:
    if not args:
        print("Usage: run-experiment.py status <experiment_id>")
        sys.exit(1)
    exp_id = args[0]
    conn = get_conn()
    row = conn.execute(
        "SELECT id, name, surface, hypothesis, verdict, baseline_value, challenger_value, started_at, ended_at, notes FROM experiments WHERE id=?",
        (exp_id,),
    ).fetchone()
    conn.close()
    if not row:
        print(f"Experiment {exp_id} not found")
        sys.exit(1)
    print(json.dumps(dict(zip(
        ["id","name","surface","hypothesis","verdict","baseline_value","challenger_value","started_at","ended_at","notes"],
        row
    )), indent=2))


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)

    cmd = args[0]
    rest = args[1:]

    if cmd == "start":
        cmd_start(rest)
    elif cmd == "end":
        cmd_end(rest)
    elif cmd == "list":
        cmd_list()
    elif cmd == "status":
        cmd_status(rest)
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
