#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.peer_trace import end_peer_session, record_peer_trace  # noqa: E402
from services.storage import connect as connect_storage  # noqa: E402

DEFAULT_POLICY_PATH = REPO_ROOT / "config" / "peer-eval" / "peer-trace-policy.json"


def _trace_mode_enabled(policy_path: Path = DEFAULT_POLICY_PATH) -> bool:
    if not policy_path.exists():
        return False
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    return policy.get("peerMode") == "trace"


def close_peer_trace_session(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    task_category: str = "session_stop",
    final_status: str = "completed",
) -> None:
    if not _trace_mode_enabled():
        return
    end_peer_session(conn, session_id)
    record_peer_trace(
        conn,
        session_id=session_id,
        task_category=task_category,
        prompt_length=0,
        turn_count=0,
        tool_call_count=0,
        failed_command_count=0,
        duration_ms=0,
        files_changed_count=0,
        tests_run=0,
        final_status=final_status,
        notes="peer trace session closed by hook-session-stop",
    )
    conn.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description="Additive peer trace stop hook")
    parser.add_argument("--db", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--final-status", default="completed")
    args = parser.parse_args()
    conn = connect_storage(args.db)
    close_peer_trace_session(conn, session_id=args.session_id, final_status=args.final_status)
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
