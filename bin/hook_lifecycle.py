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


def _normalize_path(path: str | None) -> str | None:
    if not path:
        return None
    try:
        return str(Path(path).expanduser().resolve())
    except OSError:
        return str(Path(path).expanduser())


def _is_agent_config_cwd(path: str | None) -> bool:
    if not path:
        return False
    return Path(path).expanduser().name in {".claude", ".codex"}


def _project_id_for_cwd(conn: sqlite3.Connection, cwd: str | None) -> str | None:
    normalized = _normalize_path(cwd)
    if not normalized:
        return None
    row = conn.execute(
        "SELECT id FROM projects WHERE repo_path = ? LIMIT 1", (normalized,)
    ).fetchone()
    if row:
        return str(row[0])
    return None


def resolve_session_cwd(conn: sqlite3.Connection, payload_cwd: str | None) -> str:
    """
    Prefer the real hook process workspace over agent configuration dirs.

    Claude can pass `/Users/.../.claude` as payload cwd for global config
    interactions. When the hook itself is running from a registered project,
    treating `.claude` as the project poisons downstream attribution.
    """
    resolved_payload = _normalize_path(payload_cwd)
    process_cwd = _normalize_path(os.getcwd())
    if (
        resolved_payload
        and _is_agent_config_cwd(resolved_payload)
        and process_cwd
        and process_cwd != resolved_payload
        and not _is_agent_config_cwd(process_cwd)
        and _project_id_for_cwd(conn, process_cwd)
    ):
        return process_cwd
    return resolved_payload or process_cwd or os.getcwd()


def _session_row(
    conn: sqlite3.Connection, session_id: str | None
) -> sqlite3.Row | tuple[Any, ...] | None:
    if not session_id:
        return None
    return conn.execute(
        """
        SELECT id, status, started_at, cwd
        FROM sessions
        WHERE id = ?
        LIMIT 1
        """,
        (session_id,),
    ).fetchone()


def _row_value(row: sqlite3.Row | tuple[Any, ...] | None, key: str, index: int) -> Any:
    if row is None:
        return None
    if isinstance(row, sqlite3.Row):
        return row[key]
    return row[index]


def _is_newer(
    candidate: sqlite3.Row | tuple[Any, ...], current: sqlite3.Row | tuple[Any, ...] | None
) -> bool:
    if current is None:
        return True
    candidate_started = str(_row_value(candidate, "started_at", 2) or "")
    current_started = str(_row_value(current, "started_at", 2) or "")
    return candidate_started > current_started


def resolve_hook_session_id(
    conn: sqlite3.Connection,
    *,
    payload_session_id: str | None,
    payload_cwd: str | None = None,
    logs_dir: str | None = None,
    hook_name: str,
    log,
) -> str | None:
    """
    Resolve hook events away from stale payload ids when SessionStart has already
    opened a newer local session and updated the current_session pointer.
    """
    pointer_session_id = current_session_id(logs_dir)
    if not payload_session_id:
        if pointer_session_id:
            log(f"missing payload session; using current_session pointer for {hook_name}")
        return pointer_session_id

    if not pointer_session_id or pointer_session_id == payload_session_id:
        return payload_session_id

    payload_row = _session_row(conn, payload_session_id)
    pointer_row = _session_row(conn, pointer_session_id)
    if pointer_row is None:
        return payload_session_id

    pointer_status = str(_row_value(pointer_row, "status", 1) or "")
    if pointer_status != "open":
        return payload_session_id

    effective_cwd = _normalize_path(payload_cwd or os.getcwd())
    payload_cwd_value = _normalize_path(str(_row_value(payload_row, "cwd", 3) or ""))
    pointer_cwd_value = _normalize_path(str(_row_value(pointer_row, "cwd", 3) or ""))

    pointer_matches_cwd = bool(effective_cwd and pointer_cwd_value == effective_cwd)
    payload_mismatches_cwd = bool(
        effective_cwd and payload_cwd_value and payload_cwd_value != effective_cwd
    )
    payload_missing = payload_row is None
    payload_closed = str(_row_value(payload_row, "status", 1) or "") == "closed"

    should_reassign = pointer_matches_cwd and (payload_closed or payload_mismatches_cwd)
    if payload_missing and pointer_matches_cwd and _is_newer(pointer_row, payload_row):
        should_reassign = True

    if should_reassign:
        log(
            "reassigned stale "
            f"{hook_name} payload session {payload_session_id} to current session {pointer_session_id}"
        )
        return pointer_session_id

    return payload_session_id


def get_or_create_project(conn: sqlite3.Connection, cwd: str) -> str:
    resolved_cwd = resolve_session_cwd(conn, cwd)
    row = conn.execute("SELECT id FROM projects WHERE repo_path = ?", (resolved_cwd,)).fetchone()
    if row:
        return str(row[0])

    project_id = hashlib.sha256(resolved_cwd.encode()).hexdigest()[:16]
    name = os.path.basename(resolved_cwd.rstrip("/")) or resolved_cwd
    conn.execute(
        """
        INSERT OR IGNORE INTO projects (id, name, repo_path, obsidian_path, status)
        VALUES (?, ?, ?, ?, 'active')
        """,
        (project_id, name, resolved_cwd, ""),
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

    resolved_cwd = resolve_session_cwd(conn, cwd)
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
