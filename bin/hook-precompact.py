#!/usr/bin/env python3
"""
AIOS hook: PreCompact (fires on /clear)
If /close was already run this session, just runs cleanup.
If not, writes a basic fallback note from available data and notifies the user.
"""

import json
import os
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime

DB = os.path.expanduser("~/AIOS/data/aios.db")
LOG = os.path.expanduser("~/AIOS/logs/hooks.log")
CLOSED_DIR = os.path.expanduser("~/AIOS/logs/closed")
SUMMARIES_DIR = os.path.expanduser("~/AIOS/logs/summaries")
VAULT = os.path.expanduser("~/Vaults/Command-Center")
HANDOFFS = os.path.expanduser("~/AIOS/staging/session-handoffs")


def log(msg: str) -> None:
    ts = datetime.now(UTC).isoformat()
    try:
        with open(LOG, "a") as f:
            f.write(f"{ts} [precompact] {msg}\n")
    except Exception:
        pass


def notify(title: str, msg: str) -> None:
    subprocess.run(
        ["osascript", "-e", f'display notification "{msg}" with title "{title}"'],
        capture_output=True,
    )


def close_was_run(session_id: str) -> bool:
    marker = os.path.join(CLOSED_DIR, session_id)
    return os.path.exists(marker)


def get_git_commits(cwd: str, since: str) -> list[str]:
    if not cwd:
        return []
    path = cwd
    for _ in range(4):
        if os.path.isdir(os.path.join(path, ".git")):
            break
        path = os.path.dirname(path)
    else:
        return []
    try:
        since_dt = datetime.fromisoformat(since)
        result = subprocess.run(
            ["git", "log", "--oneline", f"--since={since_dt.strftime('%Y-%m-%d %H:%M:%S')}"],
            cwd=path, capture_output=True, text=True, timeout=5,
        )
        return [l.strip() for l in result.stdout.strip().splitlines() if l.strip()]
    except Exception:
        return []


def write_fallback_note(session_id, project_name, started_at, ended_at, cwd, prompts, artifacts, commits):
    os.makedirs(HANDOFFS, exist_ok=True)
    try:
        file_date = datetime.fromisoformat(started_at).strftime("%Y-%m-%d")
    except Exception:
        file_date = "unknown-date"

    safe_project = (project_name or "unknown").replace(" ", "-").replace("/", "-")
    short_id = session_id[:8]
    note_path = os.path.join(HANDOFFS, f"{file_date}-{safe_project}-{short_id}.md")

    artifact_lines = "\n".join(
        f"- {a[1]}" for a in artifacts if a[1]
    ) or "- (none)"
    commit_lines = "\n".join(f"- {c}" for c in commits) or "- (none)"
    classifications = ", ".join({p[0] for p in prompts if p[0]}) or "(none)"
    reusable = [p[2] for p in prompts if p[1]] or []
    reusable_lines = "\n".join(f"- {r}" for r in reusable[:5]) if reusable else "- none flagged"

    content = f"""---
type: session
project: {project_name or "unknown"}
tool: claude-code
started: {started_at}
ended: {ended_at}
status: closed
session_id: {session_id}
tags:
  - ai/session
---

## Objective

<!-- Run /close for synthesized objective -->

## Outcome

<!-- Run /close for synthesized outcome -->

## Key Changes

{commit_lines}

## Artifacts

{artifact_lines}

## Prompt Types

{classifications}

## Reusable Prompts

{reusable_lines}

## Next Actions

- [ ]
"""
    with open(note_path, "w") as f:
        f.write(content)
    return note_path


def main() -> None:
    try:
        data = json.loads(sys.stdin.read())
    except Exception as e:
        log(f"failed to parse stdin: {e}")
        sys.exit(0)

    session_id = data.get("session_id", "")
    # Prefer the pointer file — more reliable than hook payload after /clear re-fires
    pointer = os.path.expanduser("~/AIOS/logs/current_session")
    if os.path.exists(pointer):
        with open(pointer) as f:
            session_id = f.read().strip() or session_id
    if not session_id:
        sys.exit(0)

    # If /close already ran, just run the stop hooks
    if close_was_run(session_id):
        log(f"session {session_id} already closed via /close, skipping fallback")
        print("AIOS · /close already run — context compacting")
        sys.exit(0)

    try:
        conn = sqlite3.connect(DB)
        cur = conn.execute(
            "SELECT s.id, s.started_at, s.cwd, s.status, p.name, p.repo_path "
            "FROM sessions s LEFT JOIN projects p ON s.project_id = p.id WHERE s.id = ?",
            (session_id,),
        )
        row = cur.fetchone()

        if not row or row[3] == "closed":
            conn.close()
            sys.exit(0)

        _, started_at, cwd, _, project_name, repo_path = row
        now = datetime.now(UTC).isoformat()

        prompts = conn.execute(
            "SELECT classification, reusable_candidate, prompt_text FROM prompts_used WHERE session_id = ?",
            (session_id,),
        ).fetchall()

        artifacts = conn.execute(
            "SELECT DISTINCT artifact_type, path FROM artifacts WHERE session_id = ? AND path IS NOT NULL",
            (session_id,),
        ).fetchall()

        conn.execute(
            "UPDATE sessions SET status='closed', ended_at=? WHERE id=?",
            (now, session_id),
        )
        conn.commit()
        conn.close()

        commits = get_git_commits(cwd or repo_path or "", started_at or "")
        note_path = write_fallback_note(
            session_id, project_name, started_at or "", now,
            cwd or "", prompts, artifacts, commits
        )

        log(f"fallback note written: {os.path.basename(note_path)}")
        print(f"AIOS · basic note saved ({len(commits)} commits, {len(artifacts)} artifacts) — use /close before /clear for full synthesis")
        notify(
            "AIOS · Use /close next time",
            f"{len(commits)} commits captured. Run /close before /clear for complete session notes."
        )

        # Also run focus update
        subprocess.run(
            ["python3", os.path.expanduser("~/AIOS/bin/hook-update-focus.py")],
            input=json.dumps({"session_id": session_id}),
            text=True, capture_output=True, timeout=10,
        )

    except Exception as e:
        log(f"error: {e}")
        print(f"AIOS · precompact error: {e}")


if __name__ == "__main__":
    main()
