#!/usr/bin/env python3
"""
AIOS: index-pdfs.py
Walk ~/Downloads/ (and optionally other paths), extract PDF metadata,
write to pdf_index table in aios.db.

Usage:
  python3 index-pdfs.py [--path <dir>] [--reset] [--dry-run]

Options:
  --path    Directory to walk (default: ~/Downloads)
  --reset   Drop and recreate pdf_index table before indexing
  --dry-run Print what would be indexed without writing to DB
"""

import argparse
import contextlib
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

DB = Path.home() / "AIOS" / "data" / "aios.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS pdf_index (
  id          TEXT PRIMARY KEY,
  path        TEXT NOT NULL UNIQUE,
  filename    TEXT NOT NULL,
  size_bytes  INTEGER,
  page_count  INTEGER,
  title       TEXT,
  author      TEXT,
  subject     TEXT,
  created     TEXT,
  modified    TEXT,
  indexed_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_pdf_filename ON pdf_index(filename);
CREATE INDEX IF NOT EXISTS idx_pdf_size ON pdf_index(size_bytes);
"""


def make_id(path: str) -> str:
    import hashlib
    return hashlib.sha256(path.encode()).hexdigest()[:16]


def get_pdf_metadata(path: Path) -> dict:
    """Extract metadata using pdfinfo if available, else basic file stats."""
    meta = {
        "page_count": None,
        "title": None,
        "author": None,
        "subject": None,
        "created": None,
        "modified": None,
    }
    try:
        result = subprocess.run(
            ["pdfinfo", str(path)],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if ":" not in line:
                    continue
                key, _, val = line.partition(":")
                val = val.strip()
                key = key.strip().lower()
                if key == "pages":
                    with contextlib.suppress(ValueError):
                        meta["page_count"] = int(val)
                elif key == "title":
                    meta["title"] = val or None
                elif key == "author":
                    meta["author"] = val or None
                elif key == "subject":
                    meta["subject"] = val or None
                elif key == "creationdate":
                    meta["created"] = val or None
                elif key == "moddate":
                    meta["modified"] = val or None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass  # pdfinfo not available
    return meta


def main() -> None:
    parser = argparse.ArgumentParser(description="Index PDFs into aios.db")
    parser.add_argument("--path", default="~/Downloads", help="Directory to walk")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate table")
    parser.add_argument("--dry-run", action="store_true", help="Print without writing")
    args = parser.parse_args()

    root = Path(args.path).expanduser()
    if not root.exists():
        print(f"Error: path not found: {root}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(DB)

    if args.reset:
        conn.execute("DROP TABLE IF EXISTS pdf_index")
        print("Dropped pdf_index table")

    conn.executescript(SCHEMA)
    conn.commit()

    pdfs = sorted(root.rglob("*.pdf"))
    print(f"Found {len(pdfs)} PDF files in {root}")

    inserted = 0
    skipped = 0
    now = datetime.now(UTC).isoformat()

    for pdf_path in pdfs:
        path_str = str(pdf_path)
        file_id = make_id(path_str)

        # Skip if already indexed
        row = conn.execute("SELECT id FROM pdf_index WHERE path = ?", (path_str,)).fetchone()
        if row:
            skipped += 1
            continue

        size = pdf_path.stat().st_size
        meta = get_pdf_metadata(pdf_path)

        if args.dry_run:
            print(f"  WOULD INDEX  {pdf_path.name} ({size // 1024}KB, {meta['page_count']} pages)")
            inserted += 1
            continue

        conn.execute(
            """
            INSERT OR IGNORE INTO pdf_index
              (id, path, filename, size_bytes, page_count, title, author, subject, created, modified, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                file_id, path_str, pdf_path.name, size,
                meta["page_count"], meta["title"], meta["author"],
                meta["subject"], meta["created"], meta["modified"],
                now,
            ),
        )
        inserted += 1

    if not args.dry_run:
        conn.commit()

    print(f"\nDone: {inserted} indexed, {skipped} already in DB")
    conn.close()


if __name__ == "__main__":
    main()
