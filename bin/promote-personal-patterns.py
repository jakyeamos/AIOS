#!/usr/bin/env python3
"""
AIOS: promote-personal-patterns.py
Write human-approved personal patterns to the Obsidian mental map.

For each personal pattern with human_approved=1 and no vault_path set:
  - Writes a note to ~/projects/Vaults/Command-Center/04 Personal/Mental-Map/<slug>.md
  - Creates/updates the MOC at Mental-Map/_index.md
  - Updates vault_path in aios.db

Note format:
  # <title>
  **Sub-class:** <domain>  (preference / learning / blindspot / habit)
  **Confidence:** <confidence>
  **First seen:** <first_observed_at>

  <body>

  ---
  *Source: AIOS personal-extract — auto-promoted {{date}}*

Usage:
  python3 ~/AIOS/bin/promote-personal-patterns.py [--dry-run]
"""

import argparse
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from aios_paths import get_vault_subpath

DB = Path.home() / "AIOS/data/aios.db"
MENTAL_MAP = get_vault_subpath("04 Personal", "Mental-Map")
MOC_PATH = MENTAL_MAP / "_index.md"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _slug(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower())
    return slug.strip("-")[:60]


def _write_note(p: dict, dry_run: bool) -> Path:
    """Write pattern to vault as a markdown note. Returns the path."""
    MENTAL_MAP.mkdir(parents=True, exist_ok=True)
    slug = _slug(p["title"])
    note_path = MENTAL_MAP / f"{slug}.md"
    date_str = datetime.now().strftime("%Y-%m-%d")

    body = (p["body"] or "").strip() or p["title"]
    first_seen = (p["first_observed_at"] or "unknown")[:10]
    sub_class = p["domain"] or "unclassified"
    confidence = f"{p['confidence']:.0%}" if p["confidence"] else "—"

    content = (
        f"# {p['title']}\n\n"
        f"**Sub-class:** {sub_class}\n"
        f"**Confidence:** {confidence}\n"
        f"**First seen:** {first_seen}\n\n"
        f"{body}\n\n"
        f"---\n"
        f"*Source: AIOS personal-extract — promoted {date_str}*\n"
    )

    if not dry_run:
        note_path.write_text(content)
    return note_path


def _update_moc(entries: list[tuple[str, Path]], dry_run: bool) -> None:
    """Append new entries to the MOC file (creates if missing)."""
    if not entries:
        return
    MENTAL_MAP.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")

    if MOC_PATH.exists():
        existing = MOC_PATH.read_text()
    else:
        existing = "# Mental Map — Personal Patterns\n\nAuto-generated index of personal behavioral patterns.\n\n"

    new_lines = [f"\n## Added {date_str}\n"]
    for title, note_path in entries:
        rel = note_path.stem
        new_lines.append(f"- [[{rel}]] — {title}")

    if not dry_run:
        MOC_PATH.write_text(existing + "\n".join(new_lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    patterns = conn.execute(
        """
        SELECT id, title, body, domain, confidence, first_observed_at
        FROM patterns
        WHERE class='personal'
          AND human_approved=1
          AND (vault_path IS NULL OR vault_path='')
          AND status != 'discarded'
        """
    ).fetchall()

    if not patterns:
        print("no personal patterns pending promotion")
        conn.close()
        return

    promoted = []
    skipped = 0

    for row in patterns:
        p = dict(row)
        try:
            note_path = _write_note(p, args.dry_run)
            if not args.dry_run:
                conn.execute(
                    "UPDATE patterns SET vault_path=?, promoted_at=? WHERE id=?",
                    (str(note_path), _now(), p["id"]),
                )
            promoted.append((p["title"], note_path))
            tag = "[DRY] " if args.dry_run else ""
            print(f"  {tag}→ {note_path.name}  ({p['domain'] or 'unclassified'})")
        except Exception as exc:
            print(f"  SKIP {p['id'][:8]}: {exc}")
            skipped += 1

    _update_moc(promoted, args.dry_run)

    if not args.dry_run:
        conn.commit()
    conn.close()

    prefix = "[DRY] " if args.dry_run else ""
    print(f"{prefix}promoted {len(promoted)} personal patterns to Mental Map")
    if skipped:
        print(f"  {skipped} skipped (errors)")


if __name__ == "__main__":
    main()
