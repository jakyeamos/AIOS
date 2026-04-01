#!/usr/bin/env python3
"""
AIOS hook: PostToolUse
Logs tool events and detects artifact candidates.
"""

import json
import os
import sqlite3
import sys
import uuid
from datetime import datetime, timezone

DB = os.path.expanduser("~/AIOS/data/aios.db")
LOG = os.path.expanduser("~/AIOS/logs/hooks.log")

# Tools whose outputs are worth tracking as artifacts
ARTIFACT_TOOLS = {"Write", "Edit", "MultiEdit", "Bash", "Task"}


def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    try:
        with open(LOG, "a") as f:
            f.write(f"{ts} [post-tool-use] {msg}\n")
    except Exception:
        pass


def extract_artifact(tool_name: str, tool_input: dict) -> dict | None:
    if tool_name in ("Write", "Edit", "MultiEdit"):
        path = tool_input.get("file_path", "")
        if path:
            return {"artifact_type": "patch", "path": path}
    if tool_name == "Bash":
        cmd = tool_input.get("command", "")[:200]
        return {"artifact_type": "patch", "path": None, "metadata_json": json.dumps({"command": cmd})}
    return None


def main() -> None:
    try:
        data = json.loads(sys.stdin.read())
    except Exception as e:
        log(f"failed to parse stdin: {e}")
        sys.exit(0)

    session_id = data.get("session_id", "")
    tool_name = data.get("tool_name", "")

    if not session_id:
        sys.exit(0)

    try:
        conn = sqlite3.connect(DB)
        cur = conn.execute("SELECT id FROM sessions WHERE id = ?", (session_id,))
        if not cur.fetchone():
            conn.close()
            sys.exit(0)

        now = datetime.now(timezone.utc).isoformat()

        # Log the event (strip large response bodies to keep DB small)
        payload = {
            "tool_name": tool_name,
            "tool_input_keys": list((data.get("tool_input") or {}).keys()),
        }
        conn.execute(
            """
            INSERT INTO tool_events (id, session_id, source_tool, event_type, event_time, payload_json)
            VALUES (?, ?, 'claude-code', 'PostToolUse', ?, ?)
            """,
            (str(uuid.uuid4()), session_id, now, json.dumps(payload)),
        )

        # Detect artifact candidate
        if tool_name in ARTIFACT_TOOLS:
            artifact = extract_artifact(tool_name, data.get("tool_input") or {})
            if artifact:
                conn.execute(
                    """
                    INSERT INTO artifacts (id, session_id, artifact_type, path, metadata_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        session_id,
                        artifact["artifact_type"],
                        artifact.get("path"),
                        artifact.get("metadata_json"),
                        now,
                    ),
                )

        conn.commit()
        conn.close()
    except Exception as e:
        log(f"db error: {e}")


if __name__ == "__main__":
    main()
