#!/usr/bin/env python3
"""
AIOS: extract-bug-motifs.py
Scan bug_log for recurring symptom/cause patterns and promote candidates
to the patterns table as bug_fix class observations.

Also supports seeding known motifs via --seed-file.

Usage:
  python3 extract-bug-motifs.py [--dry-run] [--seed-file <path>]
  python3 extract-bug-motifs.py --list   # Show existing bug motif patterns
"""

import argparse
import json
import os
import re
import sqlite3
import sys
import uuid
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.storage import connect as connect_storage  # noqa: E402

DB = Path(os.environ.get("AIOS_DB", str(Path.home() / "AIOS" / "data" / "aios.db"))).expanduser()

KNOWN_MOTIFS = [
    {
        "title": "Prisma Decimal type — JS number coercion",
        "body": (
            "Prisma returns Decimal objects, not JS numbers. "
            "Arithmetic operations silently produce NaN or incorrect results when using + or * directly. "
            "Fix: call .toNumber() or use Decimal arithmetic methods. "
            "Appears in Soundscape (Jan 2026, 3x in Claude history)."
        ),
        "domain": "debugging",
    },
    {
        "title": "TypeScript null propagation — optional chain omitted at API boundary",
        "body": (
            "Nullable fields returned from Prisma or external APIs are typed as T | null but "
            "downstream code assumes T. Error surfaces as 'possibly undefined' or runtime crash at "
            "property access. Fix: add explicit null check or optional chain before use. "
            "High recurrence in monorepo packages that consume shared types."
        ),
        "domain": "debugging",
    },
    {
        "title": "Monorepo build order — declaration files not emitted before consuming package",
        "body": (
            "In TypeScript monorepos with composite projects, a consuming package fails to resolve "
            "types if the dependency package hasn't emitted .d.ts files yet. "
            "Symptom: 'Module not found' or missing exports despite correct package.json wiring. "
            "Fix: ensure correct build order (tsc --build on dependency first, or use project references). "
            "Recurs 3x in Codex session archive (atomic commits pattern, unresolved)."
        ),
        "domain": "debugging",
    },
]


def now() -> str:
    return datetime.now(UTC).isoformat()


def list_motifs(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        "SELECT id, title, confidence, state, human_approved FROM patterns WHERE class = 'bug_fix' ORDER BY confidence DESC"
    ).fetchall()
    if not rows:
        print("No bug_fix patterns in DB.")
        return
    print(f"\n{'ID':18} {'State':12} {'Appr':5} {'Conf':5} Title")
    print("-" * 80)
    for row_id, title, confidence, state, approved in rows:
        print(
            f"{row_id[:16]:18} {state:12} {'Y' if approved else 'N':5} {confidence:.2f}  {title[:60]}"
        )


def seed_motif(conn: sqlite3.Connection, motif: dict, dry_run: bool) -> None:
    title = motif["title"]
    existing = conn.execute(
        "SELECT id FROM patterns WHERE title = ? AND class = 'bug_fix'", (title,)
    ).fetchone()
    if existing:
        print(f"  EXISTS   {title[:70]}")
        return

    pat_id = str(uuid.uuid4())
    if dry_run:
        print(f"  WOULD ADD  {title[:70]}")
        return

    conn.execute(
        """
        INSERT INTO patterns
          (id, class, title, body, domain, state, confidence, source_type,
           human_approved, first_observed_at, created_at)
        VALUES (?, 'bug_fix', ?, ?, ?, 'observation', 0.80, 'manual', 1, ?, ?)
        """,
        (pat_id, title, motif["body"], motif["domain"], now(), now()),
    )
    print(f"  SEEDED   {title[:70]}")


def extract_from_bug_log(conn: sqlite3.Connection, dry_run: bool) -> None:
    rows = conn.execute(
        "SELECT symptom, root_cause FROM bug_log WHERE symptom IS NOT NULL"
    ).fetchall()
    if not rows:
        print("Bug log is empty — nothing to extract.")
        return

    # Tokenize and find common bigrams in symptoms
    bigrams: Counter = Counter()
    for symptom, _ in rows:
        words = re.findall(r"\b[a-z]{4,}\b", symptom.lower())
        for i in range(len(words) - 1):
            bigrams[(words[i], words[j := i + 1])] += 1  # noqa: F841

    # Promote frequent bigrams as candidate patterns
    threshold = max(2, len(rows) // 10)
    candidates = [(bg, cnt) for bg, cnt in bigrams.most_common(20) if cnt >= threshold]

    if not candidates:
        print(f"No bigrams exceed threshold ({threshold}) in {len(rows)} bugs.")
        return

    print(f"\nFrequent bug symptom bigrams (threshold={threshold}):")
    for (w1, w2), cnt in candidates[:10]:
        title = f"Bug motif: '{w1} {w2}'"
        existing = conn.execute("SELECT id FROM patterns WHERE title = ?", (title,)).fetchone()
        if existing:
            print(f"  EXISTS   [{cnt}x] {title}")
            continue
        if dry_run:
            print(f"  WOULD ADD [{cnt}x] {title}")
            continue
        pat_id = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO patterns
              (id, class, title, domain, state, confidence, source_type, first_observed_at, created_at)
            VALUES (?, 'bug_fix', ?, 'debugging', 'observation', ?, 'bigram', ?, ?)
            """,
            (pat_id, title, round(min(0.9, 0.5 + cnt * 0.05), 2), now(), now()),
        )
        print(f"  ADDED    [{cnt}x] {title}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract and seed bug motifs")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--list", action="store_true", help="List existing motifs")
    parser.add_argument("--seed-file", help="JSON file with motif dicts to seed")
    args = parser.parse_args()

    conn = connect_storage(DB)

    if args.list:
        list_motifs(conn)
        conn.close()
        return

    print("=== Seeding known motifs ===")
    motifs = KNOWN_MOTIFS[:]
    if args.seed_file:
        with open(args.seed_file) as f:
            motifs += json.load(f)

    for motif in motifs:
        seed_motif(conn, motif, args.dry_run)

    print("\n=== Extracting from bug_log ===")
    extract_from_bug_log(conn, args.dry_run)

    if not args.dry_run:
        conn.commit()

    conn.close()


if __name__ == "__main__":
    main()
