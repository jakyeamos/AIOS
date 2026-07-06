#!/usr/bin/env python3
"""
AIOS: eval-session.py
Evaluate a session's workflow metrics against rolling baseline.

Usage:
  python3 eval-session.py <session_id>
  python3 eval-session.py  # uses current session

Output: JSON with metric values and comparison to 5-session baseline.
"""

import json
import os
import sqlite3
import sys

DB = os.path.expanduser("~/AIOS/data/aios.db")


def get_current_session() -> str | None:
    pointer = os.path.expanduser("~/AIOS/logs/current_session")
    if os.path.exists(pointer):
        with open(pointer) as f:
            return f.read().strip() or None
    return None


def main() -> None:
    session_id = sys.argv[1] if len(sys.argv) > 1 else get_current_session()
    if not session_id:
        print(json.dumps({"error": "No session ID provided and no current session found"}))
        sys.exit(1)

    conn = sqlite3.connect(DB)

    # Get session info
    cur = conn.execute(
        "SELECT s.id, s.started_at, s.ended_at, p.name FROM sessions s LEFT JOIN projects p ON s.project_id = p.id WHERE s.id = ?",
        (session_id,),
    )
    row = cur.fetchone()
    if not row:
        print(json.dumps({"error": f"Session {session_id} not found"}))
        sys.exit(1)

    _, started_at, ended_at, project_name = row

    # Get metrics recorded for this session
    cur = conn.execute(
        "SELECT metric_name, metric_value, recorded_at FROM workflow_metrics WHERE session_id = ? ORDER BY recorded_at",
        (session_id,),
    )
    session_metrics = {name: value for name, value, _ in cur.fetchall()}

    # Get prompt stats
    cur = conn.execute(
        "SELECT COUNT(*), SUM(retrieval_fired), classification FROM prompts_used WHERE session_id = ? GROUP BY classification",
        (session_id,),
    )
    prompt_stats = {}
    total_prompts = 0
    total_retrievals = 0
    for count, retrievals, classification in cur.fetchall():
        prompt_stats[classification] = int(count)
        total_prompts += int(count)
        total_retrievals += int(retrievals or 0)

    # Get rolling baseline (last 5 sessions for this project, excluding current)
    baseline = {}
    if project_name:
        cur = conn.execute(
            """
            SELECT wm.metric_name, AVG(wm.metric_value)
            FROM workflow_metrics wm
            JOIN sessions s ON wm.session_id = s.id
            JOIN projects p ON s.project_id = p.id
            WHERE p.name = ? AND s.id != ?
            GROUP BY wm.metric_name
            ORDER BY s.started_at DESC
            LIMIT 5
            """,
            (project_name, session_id),
        )
        baseline = {name: round(avg, 3) for name, avg in cur.fetchall()}

    conn.close()

    # Build comparison
    comparison = {}
    for metric, value in session_metrics.items():
        entry = {"value": value}
        if metric in baseline:
            delta = value - baseline[metric]
            entry["baseline"] = baseline[metric]
            entry["delta"] = round(delta, 3)
            entry["trend"] = "up" if delta > 0 else ("down" if delta < 0 else "flat")
        comparison[metric] = entry

    result = {
        "session_id": session_id,
        "project": project_name,
        "started_at": started_at,
        "ended_at": ended_at,
        "prompt_count": total_prompts,
        "retrieval_count": total_retrievals,
        "prompt_breakdown": prompt_stats,
        "metrics": comparison,
        "baseline_note": f"Baseline from up to 5 prior {project_name} sessions"
        if baseline
        else "No baseline yet",
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
