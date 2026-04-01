#!/usr/bin/env python3
"""
AIOS hook: PreCompact
Runs on every /clear. Two jobs:
  1. Update Current Focus in Obsidian (via hook-update-focus.py)
  2. Output customSummaryPrompt to instruct Claude to write claude-mem
     observations before compacting context.
"""

import json
import os
import subprocess
import sys

FOCUS_HOOK = os.path.expanduser("~/AIOS/bin/hook-update-focus.py")

CUSTOM_PROMPT = """Before compacting this conversation, save observations to claude-mem using the MCP tools (mcp__plugin_claude-mem_mcp-search__ namespace).

Capture what happened since the last compaction:
- Completed work: what was built, changed, or fixed (be specific — file paths, function names, decisions)
- Technical decisions: what was decided and why (the "why" is the part that won't survive compaction)
- Bugs found or fixed: root cause, not just "fixed X"
- Current state of any in-progress work: where exactly things stand
- Open questions or blockers that need to carry forward

Write as many observations as the work warrants — one per distinct topic is better than one large blob. Each observation must be self-contained and understandable without this conversation as context. Use the session ID from the conversation if available for the session tag.

After saving observations, proceed with normal compaction."""


def main() -> None:
    try:
        payload = sys.stdin.read()
    except Exception:
        payload = "{}"

    # Run focus update — captures its own output, we don't relay it
    # (it also fires osascript notification, so user gets feedback)
    try:
        subprocess.run(
            ["python3", FOCUS_HOOK],
            input=payload,
            text=True,
            capture_output=True,
            timeout=10,
        )
    except Exception:
        pass

    # Output customSummaryPrompt for Claude to receive during compaction
    print(json.dumps({"customSummaryPrompt": CUSTOM_PROMPT}))


if __name__ == "__main__":
    main()
