#!/usr/bin/env python3
"""
AIOS: extract-handoff-learnings.py
Parse session handoff files for Learned: blocks and seed them as notice-state patterns.

- Splits semicolon-delimited paragraphs into individual items
- Idempotent: skips files already in processed_files table
- Derives project from handoff frontmatter
- Sets source_type='handoff-learned', impact_score=0.6 (explicitly flagged learning)

Run: python3 ~/AIOS/bin/extract-handoff-learnings.py [--dry-run]
"""
import argparse
import json
import os
import re
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from aios_paths import get_vault_subpath

DB = os.path.expanduser("~/AIOS/data/aios.db")
HANDOFFS_DIR = get_vault_subpath("02 AI OS", "02 Session Handoffs")

# Minimum character length for a learning item to be worth recording
MIN_ITEM_LEN = 40

# Cap items per handoff to avoid flooding from one long session
MAX_ITEMS_PER_HANDOFF = 12


def now() -> str:
    return datetime.now(UTC).isoformat()


def extract_frontmatter(text: str) -> dict:
    """Pull simple key: value pairs from YAML frontmatter block."""
    meta = {}
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return meta
    for line in match.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    return meta


def extract_learned_blocks(text: str) -> list[str]:
    """Return all text blocks that follow a **Learned:** marker."""
    # Match **Learned:** or Learned: followed by content up to next **X:** or end
    pattern = re.compile(
        r"\*\*Learned:\*\*\s*\n?(.*?)(?=\n\*\*[A-Z]|\Z)",
        re.DOTALL | re.IGNORECASE,
    )
    blocks = []
    for m in pattern.finditer(text):
        block = m.group(1).strip()
        if block:
            blocks.append(block)
    return blocks


def split_into_items(block: str) -> list[str]:
    """Split a learned block into individual actionable items."""
    # Try semicolons first (most common in these handoffs)
    if ";" in block:
        items = [s.strip() for s in block.split(";")]
    else:
        # Fall back to newlines or treat as single item
        items = [s.strip() for s in block.splitlines() if s.strip()]
        if not items:
            items = [block.strip()]

    # Filter: long enough, not just a fragment
    cleaned = []
    for item in items:
        item = re.sub(r"^[-*•]\s+", "", item).strip()
        if len(item) >= MIN_ITEM_LEN:
            cleaned.append(item)
    return cleaned[:MAX_ITEMS_PER_HANDOFF]


def get_project_id(conn: sqlite3.Connection, project_name: str) -> str | None:
    if not project_name:
        return None
    row = conn.execute(
        "SELECT id FROM projects WHERE name=? LIMIT 1", (project_name,)
    ).fetchone()
    return row[0] if row else None


def already_exists(conn: sqlite3.Connection, title: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM patterns WHERE title=? LIMIT 1", (title,)
    ).fetchone()
    return row is not None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    handoff_files = sorted(HANDOFFS_DIR.glob("*.md"))
    total_inserted = 0
    total_skipped_dup = 0
    total_files_processed = 0
    total_files_skipped = 0

    for fpath in handoff_files:
        path_str = str(fpath)

        # Skip already processed
        already = conn.execute(
            "SELECT 1 FROM processed_files WHERE path=? LIMIT 1", (path_str,)
        ).fetchone()
        if already:
            total_files_skipped += 1
            continue

        text = fpath.read_text(encoding="utf-8", errors="ignore")
        meta = extract_frontmatter(text)
        project_name = meta.get("project", "")
        session_id = meta.get("session_id", "")
        project_id = get_project_id(conn, project_name) if project_name else None

        blocks = extract_learned_blocks(text)
        if not blocks:
            if not args.dry_run:
                conn.execute(
                    "INSERT OR IGNORE INTO processed_files (path, processed_at) VALUES (?, ?)",
                    (path_str, now()),
                )
            total_files_processed += 1
            continue

        file_inserted = 0
        for block in blocks:
            items = split_into_items(block)
            for item in items:
                title = item[:200]
                if already_exists(conn, title):
                    total_skipped_dup += 1
                    continue

                if args.dry_run:
                    print(f"  [DRY] {title[:100]!r}")
                    file_inserted += 1
                    continue

                # Determine domain from project context (rough heuristic)
                domain = "unclassified"
                if project_name:
                    project_lower = project_name.lower()
                    if any(k in project_lower for k in ("bball", "fantasy", "sports")):
                        domain = "workflow"
                    elif any(k in project_lower for k in ("soundscape", "amos", "remodel", "dispatches")):
                        domain = "architecture"

                conn.execute(
                    """
                    INSERT INTO patterns
                        (id, class, domain, title, body, evidence,
                         confidence, state, status, source_type,
                         impact_score, frequency_count, source_sessions,
                         first_observed_at, last_seen_at, created_at, project_id)
                    VALUES (?, 'observation', ?, ?, ?, ?,
                            0.4, 'notice', 'candidate', 'handoff-learned',
                            0.6, 1, 1,
                            ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        domain,
                        title,
                        item,  # full text as body
                        json.dumps([{"handoff": fpath.name, "session_id": session_id}]),
                        now(),
                        now(),
                        now(),
                        project_id,
                    ),
                )
                file_inserted += 1
                total_inserted += 1

        if not args.dry_run:
            conn.execute(
                "INSERT OR IGNORE INTO processed_files (path, processed_at) VALUES (?, ?)",
                (path_str, now()),
            )
        total_files_processed += 1
        if file_inserted:
            print(f"  {fpath.name}: {file_inserted} items")

    if not args.dry_run:
        conn.commit()

    conn.close()
    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Done:")
    print(f"  files processed: {total_files_processed}")
    print(f"  files skipped (already done): {total_files_skipped}")
    print(f"  patterns inserted: {total_inserted}")
    print(f"  duplicates skipped: {total_skipped_dup}")


if __name__ == "__main__":
    main()
