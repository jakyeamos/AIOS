#!/usr/bin/env python3
"""
AIOS hook: SessionStart
Creates a session row in SQLite on session open.
Claude Code passes JSON via stdin.
"""

import json
import sqlite3
import sys
import os
import hashlib
from datetime import datetime, timezone

DB = os.path.expanduser("~/AIOS/data/aios.db")
LOG = os.path.expanduser("~/AIOS/logs/hooks.log")


def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    try:
        with open(LOG, "a") as f:
            f.write(f"{ts} [session-start] {msg}\n")
    except Exception:
        pass


def get_or_create_project(conn: sqlite3.Connection, cwd: str) -> str:
    cur = conn.execute("SELECT id FROM projects WHERE repo_path = ?", (cwd,))
    row = cur.fetchone()
    if row:
        return row[0]
    project_id = hashlib.sha256(cwd.encode()).hexdigest()[:16]
    name = os.path.basename(cwd.rstrip("/")) or cwd
    conn.execute(
        "INSERT OR IGNORE INTO projects (id, name, repo_path, obsidian_path, status) VALUES (?, ?, ?, ?, ?)",
        (project_id, name, cwd, "", "active"),
    )
    conn.commit()
    return project_id


def main() -> None:
    try:
        data = json.loads(sys.stdin.read())
    except Exception as e:
        log(f"failed to parse stdin: {e}")
        sys.exit(0)

    session_id = data.get("session_id", "")
    cwd = data.get("cwd", os.getcwd())

    if not session_id:
        log("no session_id in payload")
        sys.exit(0)

    try:
        conn = sqlite3.connect(DB)
        project_id = get_or_create_project(conn, cwd)

        # Check if session already exists — /clear re-fires SessionStart with same ID
        existing = conn.execute("SELECT id, status FROM sessions WHERE id=?", (session_id,)).fetchone()
        if existing:
            # Session already exists — just update current_session file and exit
            conn.close()
            current_path = os.path.expanduser("~/AIOS/logs/current_session")
            with open(current_path, "w") as f:
                f.write(session_id)
            log(f"session {session_id} re-fired (clear event), skipping duplicate row")
            sys.exit(0)

        conn.execute(
            """
            INSERT OR IGNORE INTO sessions
              (id, project_id, tool, started_at, status, cwd)
            VALUES (?, ?, 'claude-code', ?, 'open', ?)
            """,
            (session_id, project_id, datetime.now(timezone.utc).isoformat(), cwd),
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO tool_events (id, session_id, source_tool, event_type, event_time, payload_json)
            VALUES (?, ?, 'claude-code', 'SessionStart', ?, ?)
            """,
            (
                f"{session_id}-start",
                session_id,
                datetime.now(timezone.utc).isoformat(),
                json.dumps(data),
            ),
        )
        conn.commit()
        conn.close()

        # Write current session pointer
        current_path = os.path.expanduser("~/AIOS/logs/current_session")
        with open(current_path, "w") as f:
            f.write(session_id)

        log(f"session {session_id} opened (project: {project_id}, cwd: {cwd})")
    except Exception as e:
        log(f"db error: {e}")


if __name__ == "__main__":
    main()
