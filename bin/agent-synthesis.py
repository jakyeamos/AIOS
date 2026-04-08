#!/usr/bin/env python3
"""
AIOS: agent-synthesis.py
Scan promoted AI history notes for recurring themes and create pattern candidates.

Reads vault notes in 09 Archive/AI History/{source}/{year}/ and extracts:
- Recurring topic tags (cross-source)
- Conversation title n-grams above threshold

Usage:
  python3 agent-synthesis.py [--dry-run] [--min-count N]
"""

import argparse
import os
import re
import sqlite3
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

DB = Path.home() / "AIOS" / "data" / "aios.db"
ARCHIVE = Path.home() / "Vaults/Command-Center/09 Archive/AI History"
MIN_COUNT_DEFAULT = 3


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def extract_title_bigrams(titles: list[str]) -> Counter:
    stopwords = {
        "the", "and", "for", "with", "from", "this", "that", "have",
        "what", "when", "where", "which", "will", "your", "about",
    }
    bigrams: Counter = Counter()
    for title in titles:
        words = [w for w in re.findall(r"[a-z]{3,}", title.lower()) if w not in stopwords]
        for i in range(len(words) - 1):
            bigrams[(words[i], words[i + 1])] += 1
    return bigrams


def collect_promoted_titles() -> list[str]:
    """Read all promoted ai_history_imports titles from DB."""
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT title FROM ai_history_imports WHERE status = 'promoted' AND title IS NOT NULL AND title != ''"
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


def collect_topic_tags() -> Counter:
    """Read topic_tags JSON arrays from promoted imports and count occurrences."""
    import json
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT topic_tags FROM ai_history_imports WHERE status = 'promoted'"
    ).fetchall()
    conn.close()
    tags: Counter = Counter()
    for (tag_json,) in rows:
        try:
            for tag in json.loads(tag_json or "[]"):
                if tag:
                    tags[tag] += 1
        except Exception:
            pass
    return tags


def upsert_pattern(conn: sqlite3.Connection, title: str, domain: str, count: int, dry_run: bool) -> bool:
    existing = conn.execute("SELECT id FROM patterns WHERE title = ?", (title,)).fetchone()
    if existing:
        return False
    if dry_run:
        print(f"  WOULD ADD  [{count}x] {title}")
        return True
    conn.execute(
        """
        INSERT INTO patterns
          (id, class, title, domain, state, confidence, source_type, first_observed_at, created_at)
        VALUES (?, 'architecture', ?, ?, 'observation', ?, 'agent-synthesis', ?, ?)
        """,
        (
            str(uuid.uuid4()),
            title,
            domain,
            round(min(0.85, 0.5 + count * 0.03), 2),
            now(),
            now(),
        ),
    )
    print(f"  ADDED      [{count}x] {title}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Synthesize patterns from AI history corpus")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--min-count", type=int, default=MIN_COUNT_DEFAULT,
                        help=f"Min occurrences to promote (default: {MIN_COUNT_DEFAULT})")
    args = parser.parse_args()

    print("=== AI History Synthesis ===")

    titles = collect_promoted_titles()
    print(f"Analyzing {len(titles)} promoted conversation titles...")

    bigrams = extract_title_bigrams(titles)
    candidates = [(bg, cnt) for bg, cnt in bigrams.most_common(30) if cnt >= args.min_count]

    tags = collect_topic_tags()
    tag_candidates = [(tag, cnt) for tag, cnt in tags.most_common(20) if cnt >= args.min_count]

    conn = sqlite3.connect(DB)
    added = 0

    if candidates:
        print(f"\nTitle bigrams (min {args.min_count}x):")
        for (w1, w2), count in candidates:
            title = f"Recurring AI theme: '{w1} {w2}'"
            if upsert_pattern(conn, title, "workflow", count, args.dry_run):
                added += 1

    if tag_candidates:
        print(f"\nTopic tags (min {args.min_count}x):")
        for tag, count in tag_candidates:
            title = f"Topic cluster: {tag}"
            if upsert_pattern(conn, title, "workflow", count, args.dry_run):
                added += 1

    if not args.dry_run:
        conn.commit()
    conn.close()

    print(f"\nDone: {added} new pattern candidates")


if __name__ == "__main__":
    main()
