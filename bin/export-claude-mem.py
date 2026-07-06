#!/usr/bin/env python3
"""
export-claude-mem.py — Export claude-mem SQLite data to Obsidian vault.

Strategy:
  - Match sessions by content_session_id == vault note's session_id frontmatter
  - If vault note exists: append claude-mem sections if not already present (idempotent)
  - If no vault note exists: create one in 02 Session Handoffs/
  - Run any time; safe to re-run (deduplication by section header marker)
"""

import json
import sqlite3
from pathlib import Path

from aios_paths import get_vault_subpath

DB_PATH = Path.home() / ".claude-mem" / "claude-mem.db"
VAULT_SESSIONS = get_vault_subpath("02 AI OS", "02 Session Handoffs")
CM_MARKER = "<!-- claude-mem-exported -->"


def short_id(uuid_str):
    return uuid_str.split("-")[0] if uuid_str else "unknown"


def fmt_date(iso_str):
    """Return YYYY-MM-DD from ISO timestamp."""
    if not iso_str:
        return "unknown"
    return iso_str[:10]


def parse_frontmatter(text):
    """Extract YAML frontmatter dict from note text. Returns (dict, body_start_index)."""
    if not text.startswith("---"):
        return {}, 0
    end = text.find("\n---", 3)
    if end == -1:
        return {}, 0
    fm_text = text[3:end].strip()
    result = {}
    for line in fm_text.splitlines():
        if ": " in line:
            k, v = line.split(": ", 1)
            result[k.strip()] = v.strip()
    return result, end + 4  # skip closing ---\n


def build_cm_section(session, summaries, observations):
    """Build the claude-mem data block to append to a vault note."""
    lines = ["\n\n---\n", f"{CM_MARKER}\n", "## claude-mem Data\n"]

    # Session metadata
    lines.append(f"\n**Project:** {session['project']}  \n")
    lines.append(f"**Started:** {session['started_at']}  \n")
    if session.get("custom_title"):
        lines.append(f"**Title:** {session['custom_title']}  \n")

    # Session summaries
    if summaries:
        lines.append("\n### Session Summaries\n")
        for s in summaries:
            if s.get("request"):
                lines.append(f"\n**Request:** {s['request']}\n")
            if s.get("completed"):
                lines.append(f"\n**Completed:**\n{s['completed']}\n")
            if s.get("next_steps"):
                lines.append(f"\n**Next Steps:**\n{s['next_steps']}\n")
            if s.get("learned"):
                lines.append(f"\n**Learned:**\n{s['learned']}\n")

    # Observations grouped by type
    if observations:
        by_type = {}
        for obs in observations:
            t = obs.get("type", "other")
            by_type.setdefault(t, []).append(obs)

        type_labels = {
            "feature": "Features Built",
            "bugfix": "Bugs Fixed",
            "discovery": "Discoveries",
            "change": "Changes",
            "decision": "Decisions",
            "refactor": "Refactors",
        }

        lines.append("\n### Observations\n")
        for type_key, obs_list in sorted(by_type.items()):
            label = type_labels.get(type_key, type_key.title())
            lines.append(f"\n#### {label}\n")
            for obs in obs_list:
                title = obs.get("title", "Untitled")
                subtitle = obs.get("subtitle", "")
                narrative = obs.get("narrative", "")
                facts_raw = obs.get("facts", "")

                lines.append(f"\n**{title}**")
                if subtitle:
                    lines.append(f"  \n*{subtitle}*")
                if narrative:
                    lines.append(f"\n\n{narrative}")
                if facts_raw:
                    try:
                        facts = json.loads(facts_raw)
                        if facts:
                            lines.append("\n\nFacts:")
                            for fact in facts:
                                lines.append(f"\n- {fact}")
                    except (json.JSONDecodeError, TypeError):
                        pass
                lines.append("\n")

    return "".join(lines)


def find_vault_note(content_session_id):
    """Find existing vault note by searching session_id in frontmatter."""
    short = short_id(content_session_id)
    # Fast path: filename contains short id
    for f in VAULT_SESSIONS.glob(f"*{short}*.md"):
        return f
    # Slow path: search frontmatter
    for f in VAULT_SESSIONS.glob("*.md"):
        try:
            text = f.read_text()
            fm, _ = parse_frontmatter(text)
            if fm.get("session_id", "") == content_session_id:
                return f
        except Exception:
            pass
    return None


def create_vault_note(session, summaries, observations):
    """Create a new vault note for a session with no existing handoff."""
    date = fmt_date(session["started_at"])
    project = session["project"]
    sid = short_id(session["content_session_id"])
    filename = f"{date}-{project}-{sid}.md"
    filepath = VAULT_SESSIONS / filename

    # Build request from first summary
    request = ""
    if summaries:
        request = summaries[0].get("request", "") or ""

    frontmatter = f"""---
type: session
project: {project}
tool: claude-code
started: {session["started_at"]}
ended: {session.get("completed_at") or ""}
status: {session["status"]}
session_id: {session["content_session_id"]}
tags:
  - ai/session
---

## Objective
{request}

## Outcome
*(no handoff note — claude-mem export only)*
"""

    cm_block = build_cm_section(session, summaries, observations)
    filepath.write_text(frontmatter + cm_block)
    return filepath, "created"


def append_to_vault_note(filepath, session, summaries, observations):
    """Append claude-mem data to existing vault note if not already present."""
    text = filepath.read_text()
    if CM_MARKER in text:
        return filepath, "already-exported"

    cm_block = build_cm_section(session, summaries, observations)
    filepath.write_text(text + cm_block)
    return filepath, "appended"


def main():
    if not DB_PATH.exists():
        print(f"DB not found: {DB_PATH}")
        return

    VAULT_SESSIONS.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Load all sessions
    cur.execute("""
        SELECT content_session_id, memory_session_id, project, custom_title,
               started_at, completed_at, status
        FROM sdk_sessions
        ORDER BY started_at_epoch ASC
    """)
    sessions = [dict(r) for r in cur.fetchall()]

    stats = {"created": 0, "appended": 0, "already-exported": 0, "skipped": 0}

    for session in sessions:
        msid = session["memory_session_id"]
        csid = session["content_session_id"]

        if not msid:
            stats["skipped"] += 1
            continue

        # Load summaries
        cur.execute(
            """
            SELECT request, investigated, learned, completed, next_steps, notes
            FROM session_summaries
            WHERE memory_session_id = ?
            ORDER BY created_at_epoch ASC
        """,
            (msid,),
        )
        summaries = [dict(r) for r in cur.fetchall()]

        # Load observations
        cur.execute(
            """
            SELECT type, title, subtitle, narrative, facts, concepts
            FROM observations
            WHERE memory_session_id = ?
            ORDER BY created_at_epoch ASC
        """,
            (msid,),
        )
        observations = [dict(r) for r in cur.fetchall()]

        # Skip sessions with nothing to export
        if not summaries and not observations:
            stats["skipped"] += 1
            continue

        vault_note = find_vault_note(csid)

        if vault_note:
            _, action = append_to_vault_note(vault_note, session, summaries, observations)
        else:
            _, action = create_vault_note(session, summaries, observations)

        stats[action] += 1
        print(
            f"  {action.upper():16} {session['project']} / {csid[:8]} ({len(summaries)} summaries, {len(observations)} obs)"
        )

    conn.close()

    print("\n=== Summary ===")
    print(f"  Created:          {stats['created']}")
    print(f"  Appended:         {stats['appended']}")
    print(f"  Already exported: {stats['already-exported']}")
    print(f"  Skipped (empty):  {stats['skipped']}")


if __name__ == "__main__":
    main()
