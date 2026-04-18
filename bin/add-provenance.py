#!/usr/bin/env python3
"""
AIOS: add-provenance.py
Add provenance + review-status frontmatter to vault files that lack them.

Rules:
  06 Knowledge/Wiki/        quality:human-curated  → provenance:human, review-status:current
  06 Knowledge/Wiki/        otherwise              → provenance:agent-promoted, review-status:pending
  09 Archive/AI History/    all                    → provenance:agent-compiled, review-status:archived
  02 AI OS/02 Session Handoffs/  all               → provenance:agent-generated, ttl:<30d from now>

Idempotent — skips files that already have a provenance field.

Usage:
  python3 add-provenance.py [--dry-run]
"""

import argparse
import re
from datetime import date, timedelta
from pathlib import Path

from aios_paths import get_vault_root

VAULT = get_vault_root()

TARGETS = [
    {
        "glob": "06 Knowledge/Wiki/*.md",
        "mode": "wiki",
    },
    {
        "glob": "09 Archive/AI History/**/*.md",
        "mode": "ai_history",
    },
    {
        "glob": "02 AI OS/02 Session Handoffs/*.md",
        "mode": "handoff",
    },
]

TTL = (date.today() + timedelta(days=30)).isoformat()


def has_field(text: str, field: str) -> bool:
    return bool(re.search(rf"^{field}:", text, re.MULTILINE))


def inject_fields(text: str, fields: dict[str, str]) -> str:
    """Insert fields into existing YAML frontmatter block."""
    if not text.startswith("---"):
        # No frontmatter — wrap it
        fm = "\n".join(f"{k}: {v}" for k, v in fields.items())
        return f"---\n{fm}\n---\n\n{text}"

    # Find end of frontmatter
    end = text.find("\n---", 3)
    if end == -1:
        return text  # malformed, skip

    fm_block = text[3:end]
    insertion = "\n".join(f"{k}: {v}" for k, v in fields.items())
    new_fm = fm_block.rstrip() + "\n" + insertion
    return "---" + new_fm + text[end:]


def get_quality(text: str) -> str:
    m = re.search(r"^quality:\s*(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else ""


def process_file(path: Path, mode: str, dry_run: bool) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"  SKIP (read error): {path.name} — {e}")
        return False

    if has_field(text, "provenance"):
        return False  # already tagged

    if mode == "wiki":
        quality = get_quality(text)
        if quality == "human-curated":
            fields = {"provenance": "human", "review-status": "current"}
        else:
            fields = {"provenance": "agent-promoted", "review-status": "pending"}

    elif mode == "ai_history":
        fields = {"provenance": "agent-compiled", "review-status": "archived"}

    elif mode == "handoff":
        fields = {"provenance": "agent-generated", "ttl": TTL}

    else:
        return False

    new_text = inject_fields(text, fields)
    if dry_run:
        print(f"  [dry-run] {path.name}  +{list(fields.keys())}")
    else:
        path.write_text(new_text, encoding="utf-8")
        print(f"  tagged {path.name}  +{list(fields.keys())}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    total = 0
    for target in TARGETS:
        mode = target["mode"]
        pattern = target["glob"]
        files = sorted((VAULT).glob(pattern))
        updated = 0
        print(f"\n=== {pattern} ({len(files)} files) ===")
        for f in files:
            if process_file(f, mode, args.dry_run):
                updated += 1
        print(f"  → {updated} updated")
        total += updated

    print(f"\nTotal updated: {total}")


if __name__ == "__main__":
    main()
