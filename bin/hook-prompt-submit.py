#!/usr/bin/env python3
"""
AIOS hook: UserPromptSubmit
Logs prompt metadata and flags reusable candidates.
"""

import hashlib
import json
import os
import sqlite3
import sys
import uuid
from datetime import datetime, timezone

DB = os.path.expanduser("~/AIOS/data/aios.db")
LOG = os.path.expanduser("~/AIOS/logs/hooks.log")

# Keywords that hint a prompt might be worth saving
REUSABLE_SIGNALS = [
    "how do i", "how to", "explain", "refactor", "review", "write a",
    "create a", "generate", "plan", "debug", "fix", "help me",
]

CLASSIFICATIONS = {
    "debug": ["debug", "fix", "error", "bug", "broken", "failing", "crash"],
    "plan": ["plan", "roadmap", "design", "architect", "how should"],
    "refactor": ["refactor", "clean up", "simplify", "improve", "optimize"],
    "review": ["review", "check", "audit", "analyze", "evaluate"],
    "explain": ["explain", "what is", "how does", "what does", "why does"],
}


def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    try:
        with open(LOG, "a") as f:
            f.write(f"{ts} [prompt-submit] {msg}\n")
    except Exception:
        pass


def classify(text: str) -> str:
    lower = text.lower()
    for label, keywords in CLASSIFICATIONS.items():
        if any(k in lower for k in keywords):
            return label
    return "other"


def is_reusable_candidate(text: str) -> int:
    lower = text.lower()
    return 1 if any(s in lower for s in REUSABLE_SIGNALS) else 0


def main() -> None:
    try:
        data = json.loads(sys.stdin.read())
    except Exception as e:
        log(f"failed to parse stdin: {e}")
        sys.exit(0)

    session_id = data.get("session_id", "")
    prompt = data.get("prompt", "")

    if not session_id or not prompt:
        sys.exit(0)

    try:
        conn = sqlite3.connect(DB)
        # Ensure session exists (may have been missed if hook was added mid-session)
        cur = conn.execute("SELECT id FROM sessions WHERE id = ?", (session_id,))
        if not cur.fetchone():
            log(f"unknown session {session_id}, skipping")
            conn.close()
            sys.exit(0)

        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:32]
        classification = classify(prompt)
        reusable = is_reusable_candidate(prompt)

        conn.execute(
            """
            INSERT INTO prompts_used
              (id, session_id, prompt_hash, prompt_text, classification, reusable_candidate)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), session_id, prompt_hash, prompt, classification, reusable),
        )
        conn.execute(
            """
            INSERT INTO tool_events (id, session_id, source_tool, event_type, event_time, payload_json)
            VALUES (?, ?, 'claude-code', 'UserPromptSubmit', ?, ?)
            """,
            (
                str(uuid.uuid4()),
                session_id,
                datetime.now(timezone.utc).isoformat(),
                json.dumps({"session_id": session_id, "classification": classification,
                            "reusable": reusable, "prompt_hash": prompt_hash}),
            ),
        )
        conn.commit()
        conn.close()
        log(f"prompt logged ({classification}, reusable={reusable}) session={session_id}")
    except Exception as e:
        log(f"db error: {e}")


if __name__ == "__main__":
    main()
