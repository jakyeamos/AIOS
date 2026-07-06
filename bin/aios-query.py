#!/usr/bin/env python3
"""
AIOS: aios-query.py
Agent-first interface to the AIOS operational database.

Modeled after vault-search.py. Always outputs JSON. Results capped.
Explicit empty states. Suggested next actions included where useful.

Modes:
  --status                          System health snapshot
  --bugs [--project NAME]           Open bug log entries
  --patterns [--domain D]           Patterns, filterable by state/domain
    [--state rule|hypothesis|notice|observation|knowledge]
  --rules [--domain D]              Active rules only (state=rule, human_approved)
  --next [--project NAME]           Pending next-action candidates
  --sessions [--last N]             Recent session summaries

Options:
  --project NAME     Partial project name match (case-insensitive)
  --domain NAME      Pattern domain filter
  --state STATE      Pattern state filter
  --last N           Return N most recent (default varies by mode)
  --limit N          Max results cap (default: 10, max: 50)

Output: JSON — {ok, mode, data, count, truncated, suggested_next}
Exit codes: 0=ok, 1=usage error, 2=db error
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import UTC, datetime

DB = os.path.expanduser("~/AIOS/data/aios.db")
DEFAULT_LIMIT = 10
MAX_LIMIT = 50

VALID_PATTERN_STATES = {"rule", "hypothesis", "notice", "observation", "knowledge"}


def die(msg: str, code: int = 1) -> None:
    print(json.dumps({"ok": False, "error": msg}), flush=True)
    sys.exit(code)


def connect() -> sqlite3.Connection:
    try:
        conn = sqlite3.connect(DB)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        die(f"db connect failed: {e}", 2)


def _ago_hours(ts: str | None) -> float | None:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return round((datetime.now(UTC) - dt).total_seconds() / 3600, 1)
    except Exception:
        return None


def _clamp_limit(n: int) -> int:
    return max(1, min(n, MAX_LIMIT))


# ── Modes ─────────────────────────────────────────────────────────────────────


def mode_status(conn: sqlite3.Connection) -> dict:
    """Compact system health snapshot."""
    rows = conn.execute("SELECT state, COUNT(*) as cnt FROM patterns GROUP BY state").fetchall()
    pattern_counts = {r["state"]: r["cnt"] for r in rows}

    open_bugs = conn.execute("SELECT COUNT(*) FROM bug_log WHERE status='open'").fetchone()[0]

    sessions_7d = conn.execute(
        "SELECT COUNT(*) FROM sessions WHERE started_at > datetime('now', '-7 days')"
    ).fetchone()[0]

    next_pending = conn.execute(
        "SELECT COUNT(*) FROM next_action_candidates WHERE status='pending_review'"
    ).fetchone()[0]

    review_queue = conn.execute("SELECT COUNT(*) FROM patterns WHERE state='knowledge'").fetchone()[
        0
    ]

    active_rules_count = conn.execute("SELECT COUNT(*) FROM active_rules").fetchone()[0]

    last_session_row = conn.execute(
        """SELECT p.name, s.started_at, s.cwd, s.status
           FROM sessions s LEFT JOIN projects p ON s.project_id = p.id
           ORDER BY s.started_at DESC LIMIT 1"""
    ).fetchone()

    last_session = None
    if last_session_row:
        ago = _ago_hours(last_session_row["started_at"])
        last_session = {
            "project": last_session_row["name"],
            "started_at": last_session_row["started_at"],
            "ago_hours": ago,
            "status": last_session_row["status"],
        }

    data = {
        "sessions_7d": sessions_7d,
        "open_bugs": open_bugs,
        "pattern_counts": pattern_counts,
        "active_rules": active_rules_count,
        "review_queue": review_queue,
        "next_action_pending": next_pending,
        "last_session": last_session,
    }

    suggested = []
    if open_bugs > 0:
        suggested.append("aios-query --bugs")
    if review_queue > 0:
        suggested.append("approve-pattern --list")
    if next_pending > 0:
        suggested.append("aios-query --next")
    suggested.append("aios-query --rules")
    if active_rules_count == 0:
        suggested.append("aios-query --patterns --state hypothesis")

    return {
        "mode": "status",
        "data": data,
        "count": 1,
        "truncated": False,
        "suggested_next": suggested[:4],
    }


def mode_bugs(conn: sqlite3.Connection, project: str | None, limit: int) -> dict:
    """Open bugs, optionally filtered by project name."""
    where = "b.status = 'open'"
    params: list = []
    if project:
        where += " AND p.name LIKE ?"
        params.append(f"%{project}%")

    rows = conn.execute(
        f"""SELECT b.id, p.name as project, b.symptom, b.root_cause, b.fix,
                   b.status, b.created_at, b.resolved_at
            FROM bug_log b LEFT JOIN projects p ON b.project_id = p.id
            WHERE {where}
            ORDER BY b.created_at DESC
            LIMIT ?""",
        params + [limit + 1],
    ).fetchall()

    truncated = len(rows) > limit
    rows = rows[:limit]

    bugs = [
        {
            "id": r["id"],
            "project": r["project"],
            "symptom": r["symptom"],
            "root_cause": r["root_cause"],
            "fix": r["fix"],
            "status": r["status"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]

    suggested = []
    if not bugs:
        suggested.append("aios-query --status")
    else:
        suggested.append(
            "sqlite3 ~/AIOS/data/aios.db \"UPDATE bug_log SET status='resolved' WHERE id='<id>'\""
        )

    return {
        "mode": "bugs",
        "data": bugs,
        "count": len(bugs),
        "truncated": truncated,
        "suggested_next": suggested,
    }


def mode_patterns(
    conn: sqlite3.Connection, domain: str | None, state: str | None, limit: int
) -> dict:
    """Query patterns by state and/or domain."""
    where_parts = []
    params: list = []

    if domain:
        where_parts.append("domain = ?")
        params.append(domain)
    if state:
        if state not in VALID_PATTERN_STATES:
            die(f"invalid --state '{state}'. Valid: {', '.join(sorted(VALID_PATTERN_STATES))}")
        where_parts.append("state = ?")
        params.append(state)

    where = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    rows = conn.execute(
        f"""SELECT id, class, title, domain, state, confidence,
                   body, confirmation_count, source_type, created_at, last_confirmed_at
            FROM patterns
            {where}
            ORDER BY confidence DESC, confirmation_count DESC
            LIMIT ?""",
        params + [limit + 1],
    ).fetchall()

    truncated = len(rows) > limit
    rows = rows[:limit]

    patterns = [
        {
            "id": r["id"],
            "class": r["class"],
            "title": r["title"],
            "domain": r["domain"],
            "state": r["state"],
            "confidence": r["confidence"],
            "has_body": r["body"] is not None,
            "confirmation_count": r["confirmation_count"] or 0,
            "source_type": r["source_type"],
            "last_confirmed_at": r["last_confirmed_at"],
        }
        for r in rows
    ]

    suggested = []
    if not patterns:
        suggested.append("aios-query --status")
        if domain:
            suggested.append("aios-query --patterns  # drop --domain to see all")
    else:
        if state == "hypothesis":
            suggested.append("approve-pattern --list  # promote passing hypotheses")
        if not state:
            suggested.append("aios-query --patterns --state rule")

    return {
        "mode": "patterns",
        "data": patterns,
        "count": len(patterns),
        "truncated": truncated,
        "suggested_next": suggested,
    }


def mode_rules(conn: sqlite3.Connection, domain: str | None, limit: int) -> dict:
    """Active rules only (state=rule, human_approved=1)."""
    where_parts = ["human_approved = 1", "state = 'rule'"]
    params: list = []
    if domain:
        where_parts.append("domain = ?")
        params.append(domain)

    where = "WHERE " + " AND ".join(where_parts)
    rows = conn.execute(
        f"""SELECT id, class, title, domain, confidence, body,
                   confirmation_count, last_confirmed_at
            FROM patterns
            {where}
            ORDER BY confidence DESC
            LIMIT ?""",
        params + [limit + 1],
    ).fetchall()

    truncated = len(rows) > limit
    rows = rows[:limit]

    rules = [
        {
            "id": r["id"],
            "class": r["class"],
            "title": r["title"],
            "domain": r["domain"],
            "confidence": r["confidence"],
            "body": r["body"],
            "confirmation_count": r["confirmation_count"] or 0,
            "last_confirmed_at": r["last_confirmed_at"],
        }
        for r in rows
    ]

    suggested = []
    if not rules:
        suggested.append(
            "aios-query --patterns --state hypothesis  # no rules yet — check hypotheses"
        )
    else:
        suggested.append("confirm-pattern --id <id>  # confirm a rule seen in practice")

    return {
        "mode": "rules",
        "data": rules,
        "count": len(rules),
        "truncated": truncated,
        "suggested_next": suggested,
    }


def mode_next(conn: sqlite3.Connection, project: str | None, limit: int) -> dict:
    """Pending next-action candidates."""
    where_parts = ["n.status = 'pending_review'"]
    params: list = []

    if project:
        where_parts.append("p.name LIKE ?")
        params.append(f"%{project}%")

    where = "WHERE " + " AND ".join(where_parts)

    rows = conn.execute(
        f"""SELECT n.id, n.text, n.priority, n.status, n.created_at, p.name as project
            FROM next_action_candidates n
            LEFT JOIN sessions s ON n.session_id = s.id
            LEFT JOIN projects p ON s.project_id = p.id
            {where}
            ORDER BY
              CASE n.priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
              n.created_at DESC
            LIMIT ?""",
        params + [limit + 1],
    ).fetchall()

    truncated = len(rows) > limit
    rows = rows[:limit]

    actions = [
        {
            "id": r["id"],
            "text": r["text"],
            "priority": r["priority"],
            "project": r["project"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]

    if not actions:
        return {
            "mode": "next",
            "data": [],
            "count": 0,
            "truncated": False,
            "suggested_next": ["aios-query --status"],
        }

    return {
        "mode": "next",
        "data": actions,
        "count": len(actions),
        "truncated": truncated,
        "suggested_next": [],
    }


def mode_sessions(conn: sqlite3.Connection, last: int, limit: int) -> dict:
    """Recent session summaries."""
    rows = conn.execute(
        """SELECT s.id, p.name as project, s.tool, s.started_at, s.ended_at,
                  s.status, s.cwd,
                  (SELECT COUNT(*) FROM artifacts a WHERE a.session_id = s.id) as artifact_count,
                  (SELECT COUNT(*) FROM tool_events te WHERE te.session_id = s.id) as event_count
           FROM sessions s LEFT JOIN projects p ON s.project_id = p.id
           ORDER BY s.started_at DESC
           LIMIT ?""",
        (min(last, limit) + 1,),
    ).fetchall()

    actual_limit = min(last, limit)
    truncated = len(rows) > actual_limit
    rows = rows[:actual_limit]

    sessions = [
        {
            "id": r["id"],
            "project": r["project"],
            "tool": r["tool"],
            "started_at": r["started_at"],
            "ended_at": r["ended_at"],
            "status": r["status"],
            "ago_hours": _ago_hours(r["started_at"]),
            "artifacts": r["artifact_count"],
            "events": r["event_count"],
        }
        for r in rows
    ]

    return {
        "mode": "sessions",
        "data": sessions,
        "count": len(sessions),
        "truncated": truncated,
        "suggested_next": [],
    }


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Agent-first interface to the AIOS operational database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--status", action="store_true", help="System health snapshot")
    mode_group.add_argument("--bugs", action="store_true", help="Open bug log entries")
    mode_group.add_argument("--patterns", action="store_true", help="Pattern query")
    mode_group.add_argument("--rules", action="store_true", help="Active rules only")
    mode_group.add_argument("--next", action="store_true", help="Pending next actions")
    mode_group.add_argument("--sessions", action="store_true", help="Recent sessions")

    parser.add_argument("--project", help="Project name filter (partial match)")
    parser.add_argument("--domain", help="Pattern domain filter")
    parser.add_argument("--state", help="Pattern state filter")
    parser.add_argument("--last", type=int, default=5, help="Return N most recent (default: 5)")
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"Max results (default: {DEFAULT_LIMIT}, max: {MAX_LIMIT})",
    )

    args = parser.parse_args()
    limit = _clamp_limit(args.limit)

    try:
        conn = connect()
    except SystemExit:
        raise

    if args.status:
        result = mode_status(conn)
    elif args.bugs:
        result = mode_bugs(conn, args.project, limit)
    elif args.patterns:
        result = mode_patterns(conn, args.domain, args.state, limit)
    elif args.rules:
        result = mode_rules(conn, args.domain, limit)
    elif args.next:
        result = mode_next(conn, args.project, limit)
    elif args.sessions:
        result = mode_sessions(conn, args.last, limit)
    else:
        die("no mode specified")

    conn.close()
    result["ok"] = True
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
