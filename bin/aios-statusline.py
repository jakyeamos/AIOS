#!/usr/bin/env python3
"""
Claude Code statusLine renderer for AIOS session activity.

Claude Code pipes status JSON to stdin and renders stdout in the bottom bar.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.session_effectiveness import (  # noqa: E402
    build_session_effectiveness_receipt,
    latest_effectiveness_receipt,
    load_activity_snapshot,
)

DB = os.environ.get("AIOS_DB", os.path.expanduser("~/AIOS/data/aios.db"))
CURRENT_SESSION = os.path.expanduser("~/AIOS/logs/current_session")


def _read_status_input() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _current_session_id(status_input: dict[str, Any]) -> str | None:
    value = status_input.get("session_id")
    if isinstance(value, str) and value:
        return value
    try:
        return Path(CURRENT_SESSION).read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def _short_model(status_input: dict[str, Any]) -> str:
    model = status_input.get("model")
    if isinstance(model, dict):
        name = model.get("display_name") or model.get("id")
        if isinstance(name, str) and name:
            return name.replace("Claude ", "")
    return "model?"


def _context_percent(status_input: dict[str, Any]) -> str:
    context_window = status_input.get("context_window")
    if not isinstance(context_window, dict):
        return "ctx:--"
    value = context_window.get("used_percentage")
    if isinstance(value, int | float):
        return f"ctx:{int(value)}%"
    return "ctx:--"


def _state_letter(state: str) -> str:
    return {"green": "G", "yellow": "Y", "red": "R"}.get(state, "?")


def _render_from_receipt(
    status_input: dict[str, Any],
    receipt: dict[str, Any],
    *,
    live: bool,
) -> str:
    lights = (
        receipt.get("activity_lights") if isinstance(receipt.get("activity_lights"), dict) else {}
    )
    measures = receipt.get("measures") if isinstance(receipt.get("measures"), dict) else {}
    session_id = str(receipt.get("session_id") or "")[:8] or "session?"
    score = int(float(receipt.get("score") or 0))
    rating = str(receipt.get("rating") or "unknown")
    marker = "live" if live else "closed"
    capture = _state_letter(str((lights.get("capture") or {}).get("state", "")))
    work = _state_letter(str((lights.get("work") or {}).get("state", "")))
    quality = _state_letter(str((lights.get("quality") or {}).get("state", "")))
    governance = _state_letter(str((lights.get("governance") or {}).get("state", "")))
    prompts = int(measures.get("prompt_count") or 0)
    artifacts = int(measures.get("artifact_count") or 0)
    bugs = int(measures.get("bug_count") or 0)
    saved = int(measures.get("rtk_tokens_saved") or 0)
    return (
        f"AIOS {session_id} {marker} {rating}:{score} "
        f"cap:{capture} work:{work} q:{quality} gov:{governance} "
        f"p:{prompts} a:{artifacts} b:{bugs} saved:{saved} "
        f"{_short_model(status_input)} {_context_percent(status_input)}"
    )


def _truncate(line: str, columns: int | None) -> str:
    if not columns or columns < 20 or len(line) <= columns:
        return line
    return line[: max(columns - 1, 1)]


def main() -> None:
    status_input = _read_status_input()
    session_id = _current_session_id(status_input)
    columns = status_input.get("columns")
    width = int(columns) if isinstance(columns, int | float) else None
    if not session_id:
        print(
            _truncate(
                f"AIOS no-session {_short_model(status_input)} {_context_percent(status_input)}",
                width,
            )
        )
        return

    try:
        conn = sqlite3.connect(DB)
        snapshot = load_activity_snapshot(conn, session_id)
        if snapshot:
            receipt = build_session_effectiveness_receipt(snapshot)
            conn.close()
            print(_truncate(_render_from_receipt(status_input, receipt, live=True), width))
            return
        receipt = latest_effectiveness_receipt(conn, session_id)
        conn.close()
        if receipt:
            print(_truncate(_render_from_receipt(status_input, receipt, live=False), width))
            return
    except Exception:
        pass

    print(
        _truncate(
            f"AIOS {session_id[:8]} pending {_short_model(status_input)} {_context_percent(status_input)}",
            width,
        )
    )


if __name__ == "__main__":
    main()
