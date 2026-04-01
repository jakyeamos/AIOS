#!/usr/bin/env python3
"""
AIOS hook: update Current Focus in the project's Obsidian note.
Reads git log since session start, writes a concise summary to ## Current Focus.
Preserves or creates ## Notes section below it for manual additions.
"""

import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone

DB = os.path.expanduser("~/AIOS/data/aios.db")
LOG = os.path.expanduser("~/AIOS/logs/hooks.log")
VAULT = os.path.expanduser("~/Vaults/Command-Center")
PROJECTS_DIR = os.path.join(VAULT, "03 Projects")

PROJECT_NAME_MAP = {
    "Fantasy": "Fantasy",
    "Bball": "Bball",
    "soundscape-app": "Soundscape",
    "remodelvision": "RemodelVision",
    "jakyeamos": "jakyeamos",
}


def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    try:
        with open(LOG, "a") as f:
            f.write(f"{ts} [update-focus] {msg}\n")
    except Exception:
        pass


def get_git_commits(cwd: str, since: str) -> list[str]:
    if not cwd or not os.path.isdir(os.path.join(cwd, ".git")):
        # walk up to find git root
        path = cwd
        found = False
        for _ in range(4):
            if os.path.isdir(os.path.join(path, ".git")):
                cwd = path
                found = True
                break
            path = os.path.dirname(path)
        if not found:
            return []
    try:
        since_dt = datetime.fromisoformat(since)
        since_str = since_dt.strftime("%Y-%m-%d %H:%M:%S")
        result = subprocess.run(
            ["git", "log", "--oneline", f"--since={since_str}"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        )
        lines = [l.strip() for l in result.stdout.strip().splitlines() if l.strip()]
        return lines
    except Exception:
        return []


def find_project_note(repo_path: str, project_name: str) -> str | None:
    # Try mapped name first, then raw project_name
    candidates = []
    folder = os.path.basename(repo_path)
    mapped = PROJECT_NAME_MAP.get(folder) or PROJECT_NAME_MAP.get(project_name)
    if mapped:
        candidates.append(os.path.join(PROJECTS_DIR, f"{mapped}.md"))
    candidates.append(os.path.join(PROJECTS_DIR, f"{project_name}.md"))
    candidates.append(os.path.join(PROJECTS_DIR, f"{folder}.md"))
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def update_note(note_path: str, commits: list[str]) -> None:
    with open(note_path, "r") as f:
        content = f.read()

    # Build new Current Focus block
    if commits:
        commit_lines = "\n".join(f"- {c}" for c in commits[:10])
        new_focus = f"## Current Focus\n\n{commit_lines}\n\n<!-- Add context here -->"
    else:
        new_focus = "## Current Focus\n\n<!-- No commits this session -->\n\n<!-- Add context here -->"

    # Ensure ## Notes section exists after Current Focus
    notes_section = "## Notes\n\n<!-- Manual additions -->"

    # Replace existing ## Current Focus section (up to next ##)
    focus_pattern = re.compile(r"## Current Focus\n.*?(?=\n## |\Z)", re.DOTALL)
    if focus_pattern.search(content):
        content = focus_pattern.sub(new_focus + "\n\n", content)
    else:
        content = content.rstrip() + "\n\n" + new_focus + "\n"

    # Add ## Notes if missing
    if "## Notes" not in content:
        content = content.rstrip() + "\n\n" + notes_section + "\n"

    with open(note_path, "w") as f:
        f.write(content)


def main() -> None:
    try:
        data = json.loads(sys.stdin.read())
    except Exception as e:
        log(f"failed to parse stdin: {e}")
        sys.exit(0)

    session_id = data.get("session_id", "")
    if not session_id:
        sys.exit(0)

    try:
        conn = sqlite3.connect(DB)
        cur = conn.execute(
            "SELECT s.cwd, s.started_at, p.name, p.repo_path FROM sessions s "
            "LEFT JOIN projects p ON s.project_id = p.id WHERE s.id = ?",
            (session_id,),
        )
        row = cur.fetchone()
        conn.close()

        if not row:
            log(f"session {session_id} not found")
            sys.exit(0)

        cwd, started_at, project_name, repo_path = row
        work_dir = cwd or repo_path or ""

        if not work_dir:
            log("no cwd or repo_path, skipping focus update")
            print("AIOS · focus update skipped (no project path)")
            sys.exit(0)

        commits = get_git_commits(work_dir, started_at or "")
        note_path = find_project_note(repo_path or "", project_name or "")

        if not note_path:
            log(f"no project note found for {project_name}")
            print(f"AIOS · focus update skipped (no note for {project_name})")
            sys.exit(0)

        update_note(note_path, commits)
        note_name = os.path.basename(note_path).replace(".md", "")
        commit_word = "commit" if len(commits) == 1 else "commits"
        msg = f"Current Focus updated → {note_name} ({len(commits)} {commit_word})"
        log(f"updated Current Focus in {os.path.basename(note_path)} ({len(commits)} commits)")
        print(f"AIOS · {msg}")
        subprocess.run(
            ["osascript", "-e", f'display notification "{msg}" with title "AIOS"'],
            capture_output=True,
        )

    except Exception as e:
        log(f"error: {e}")
        print(f"AIOS · focus update failed: {e}")
        subprocess.run(
            ["osascript", "-e", f'display notification "Focus update failed: {e}" with title "AIOS · Error"'],
            capture_output=True,
        )


if __name__ == "__main__":
    main()
