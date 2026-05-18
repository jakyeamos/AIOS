#!/usr/bin/env python3
"""
AIOS: promote-patterns.py
Automated pattern promotion: candidates above threshold → wiki stubs.

Rules by class:
  bug_fix      → auto-promote all (recurring bugs are high signal)
  prompt       → promote if confidence >= 0.60 AND not a path/noise pattern
  workflow     → promote if confidence >= 0.70 (verbs need strong recurrence)
  architecture → promote all (design decisions are high signal)
  failure      → promote all
  assumption   → promote all

Noise patterns (skip regardless of class):
  Bigrams containing filesystem path tokens, pronouns, or stop paths.

Usage:
  python3 promote-patterns.py [--dry-run] [--threshold 0.60]

Output: prints promoted count and wiki paths. Writes to vault.
"""

import argparse
import json
import os
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from aios_paths import get_vault_subpath

DB = os.path.expanduser("~/AIOS/data/aios.db")
# Stubs land in staging, not directly in vault.
# Human must author the body, then manually promote to the resolved vault wiki.
WIKI_DIR = os.path.expanduser("~/AIOS/staging/knowledge-drafts")
LOG = os.path.expanduser("~/AIOS/logs/promote-patterns.log")

# Tokens that indicate a path/noise bigram — not worth a wiki page
NOISE_TOKENS = {
    "jakyeamos", "vaults", "command", "center", "downloads", "desktop",
    "users", "python3", "sqlite3", "aios", "claude", "codex", "obsidian",
}

# Class-specific minimum confidence
CLASS_THRESHOLDS = {
    "prompt": 0.60,
    "workflow": 0.70,
    "bug_fix": 0.0,       # all bug_fix candidates
    "architecture": 0.0,
    "failure": 0.0,
    "assumption": 0.0,
}


def log(msg: str) -> None:
    ts = datetime.now(UTC).isoformat()
    try:
        with open(LOG, "a") as f:
            f.write(f"{ts} {msg}\n")
    except Exception:
        pass


def is_noise(title: str) -> bool:
    words = set(re.findall(r"[a-z]+", title.lower()))
    return bool(words & NOISE_TOKENS)


def title_to_slug(title: str) -> str:
    # Extract meaningful part: strip prefix like "Recurring prompt pattern [debug]: "
    clean = re.sub(r"^Recurring \w+ pattern \[\w+\]:\s*'?(.+?)'?$", r"\1", title)
    clean = re.sub(r"^Recurring next-action verb:\s*'?(.+?)'?$", r"\1", clean)
    clean = re.sub(r"^Recurring bug symptom:\s*'?(.+?)'?$", r"\1", clean)
    slug = re.sub(r"[^a-z0-9]+", "-", clean.lower()).strip("-")
    return slug[:60] or re.sub(r"[^a-z0-9-]", "", title.lower()[:40])


def wiki_title(title: str, class_: str) -> str:
    if class_ == "prompt":
        m = re.search(r"'(.+?)'", title)
        phrase = m.group(1) if m else title
        cls_m = re.search(r"\[(\w+)\]", title)
        cls = cls_m.group(1).capitalize() if cls_m else ""
        return f"Prompt Pattern: {phrase.title()} ({cls})"
    if class_ == "workflow":
        m = re.search(r"'(.+?)'", title)
        verb = m.group(1) if m else title
        return f"Workflow Pattern: '{verb}' as recurring next action"
    if class_ == "bug_fix":
        m = re.search(r"'(.+?)'", title)
        phrase = m.group(1) if m else title
        return f"Bug Pattern: {phrase.title()}"
    return title


def generate_wiki_stub(pattern_id: str, class_: str, title: str,
                        evidence: list, confidence: float) -> tuple[str, str]:
    """Returns (wiki_content, slug)."""
    slug = title_to_slug(title)
    page_title = wiki_title(title, class_)
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    evidence_str = "\n".join(f"- {e}" for e in evidence[:8]) if evidence else "- (none recorded)"
    promote_path = get_vault_subpath("06 Knowledge", "Wiki", f"{slug}.md")

    content = f"""---
type: wiki-draft
topic: {slug}
class: {class_}
quality: staging-draft
created: {today}
source_pattern_id: {pattern_id}
confidence: {confidence:.2f}
promote_to: "{promote_path}"
tags:
  - wiki-draft
  - pattern/{class_}
---

# {page_title}

<!-- STAGING DRAFT — not yet in vault.
     Author the sections below, then move this file to:
     {promote_path}
     Change type: wiki, quality: human-curated before promoting. -->

## Pattern

_What repeats, where, and why it matters._

## When It Appears

_Context, trigger, which project or session type._

## What To Do

_The standard response, template, or checklist to apply next time._

## Evidence

{evidence_str}

## Notes

<!-- Add root cause analysis, failure modes, or related patterns. -->
"""
    return content, slug


def promote(dry_run: bool = False) -> None:
    """
    Promote observations → knowledge (noise-filter + threshold gate).
    Does NOT auto-promote to rule — that requires human_approved=1 via approve-pattern.py.
    """
    os.makedirs(WIKI_DIR, exist_ok=True)
    conn = sqlite3.connect(DB)

    # Candidates: observations that haven't been noise-filtered yet
    cur = conn.execute(
        """
        SELECT id, class, title, evidence, confidence
        FROM patterns
        WHERE state = 'observation' AND human_approved = 0
        ORDER BY confidence DESC, created_at ASC
        """
    )
    candidates = cur.fetchall()

    promoted = []        # observation → knowledge + wiki stub
    skipped_noise = []
    skipped_threshold = []

    for pid, class_, title, evidence_json, confidence in candidates:
        threshold = CLASS_THRESHOLDS.get(class_, 0.60)
        evidence = json.loads(evidence_json) if evidence_json else []

        if is_noise(title):
            skipped_noise.append(title)
            if not dry_run:
                # Discard: mark status discarded, keep state=observation so it's not re-processed
                conn.execute(
                    "UPDATE patterns SET status='discarded', state='observation' WHERE id=?",
                    (pid,),
                )
            continue

        if confidence < threshold:
            skipped_threshold.append((title, confidence, threshold))
            continue

        # Promote to knowledge + create wiki stub
        content, slug = generate_wiki_stub(pid, class_, title, evidence, confidence)
        wiki_path = os.path.join(WIKI_DIR, f"{slug}.md")

        if os.path.exists(wiki_path):
            if not dry_run:
                conn.execute(
                    "UPDATE patterns SET status='promoted', state='knowledge', promoted_at=?, vault_path=? WHERE id=?",
                    (datetime.now(UTC).isoformat(), wiki_path, pid),
                )
            promoted.append((title, wiki_path, "existing"))
            continue

        if not dry_run:
            Path(wiki_path).write_text(content, encoding="utf-8")
            conn.execute(
                "UPDATE patterns SET status='promoted', state='knowledge', promoted_at=?, vault_path=? WHERE id=?",
                (datetime.now(UTC).isoformat(), wiki_path, pid),
            )
        promoted.append((title, wiki_path, "new"))

    if not dry_run:
        conn.commit()
    conn.close()

    mode = "[DRY RUN] " if dry_run else ""
    print(f"{mode}Promoted to knowledge: {len(promoted)}")
    for _title, path, kind in promoted:
        print(f"  [{kind}] {os.path.basename(path)}")

    print(f"\n{mode}Discarded as noise: {len(skipped_noise)}")
    print(f"{mode}Below threshold (not yet promoted): {len(skipped_threshold)}")
    for title, conf, thresh in skipped_threshold:
        print(f"  conf={conf:.2f} < {thresh:.2f}  {title[:60]}")

    log(f"promoted={len(promoted)} noise_discarded={len(skipped_noise)} below_threshold={len(skipped_threshold)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without writing")
    args = parser.parse_args()
    promote(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
