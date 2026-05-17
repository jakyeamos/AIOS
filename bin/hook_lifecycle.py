from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def load_hook_payload(
    *,
    log,
    hook_name: str,
    logs_dir: str | None = None,
    allow_current_session_fallback: bool = False,
) -> dict[str, Any]:
    raw = sys.stdin.read()
    if raw.strip():
        try:
            data = json.loads(raw)
        except Exception as exc:
            log(f"failed to parse stdin: {exc}")
            return {}
        return data if isinstance(data, dict) else {}

    if not allow_current_session_fallback:
        return {}

    session_id = current_session_id(logs_dir)
    if not session_id:
        return {}
    log(f"empty stdin; using current_session pointer for {hook_name}")
    return {"session_id": session_id, "recovered_from": "current_session_pointer"}


def current_session_id(logs_dir: str | None = None) -> str | None:
    root = logs_dir or os.path.expanduser("~/AIOS/logs")
    pointer = Path(root).expanduser() / "current_session"
    try:
        session_id = pointer.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None
    return session_id or None


def get_or_create_project(conn: sqlite3.Connection, cwd: str) -> str:
    row = conn.execute("SELECT id FROM projects WHERE repo_path = ?", (cwd,)).fetchone()
    if row:
        return str(row[0])

    project_id = hashlib.sha256(cwd.encode()).hexdigest()[:16]
    name = os.path.basename(cwd.rstrip("/")) or cwd
    conn.execute(
        """
        INSERT OR IGNORE INTO projects (id, name, repo_path, obsidian_path, status)
        VALUES (?, ?, ?, ?, 'active')
        """,
        (project_id, name, cwd, ""),
    )
    return project_id


def ensure_session(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    cwd: str | None,
    objective: str | None = None,
    source_event: str,
    log,
    tool: str = "claude-code",
) -> tuple[str, bool]:
    row = conn.execute(
        "SELECT id, project_id FROM sessions WHERE id = ? LIMIT 1",
        (session_id,),
    ).fetchone()
    if row:
        return str(row[1]), False

    resolved_cwd = cwd or os.getcwd()
    project_id = get_or_create_project(conn, resolved_cwd)
    conn.execute(
        """
        INSERT INTO sessions
          (id, project_id, tool, started_at, objective, status, cwd)
        VALUES (?, ?, ?, ?, ?, 'open', ?)
        """,
        (session_id, project_id, tool, now_iso(), objective or None, resolved_cwd),
    )
    log(f"recovered missing session {session_id} from {source_event} (cwd: {resolved_cwd})")
    return project_id, True
