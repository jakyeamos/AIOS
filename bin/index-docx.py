#!/usr/bin/env python3
"""
AIOS: index-docx.py
Walk ~/Downloads/ (and optionally other paths), extract DOCX metadata,
write to docx_index table in aios.db.

Requires: python-docx (pip install python-docx)

Usage:
  python3 index-docx.py [--path <dir>] [--reset] [--dry-run]
"""

import argparse
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

DB = Path.home() / "AIOS" / "data" / "aios.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS docx_index (
  id          TEXT PRIMARY KEY,
  path        TEXT NOT NULL UNIQUE,
  filename    TEXT NOT NULL,
  size_bytes  INTEGER,
  word_count  INTEGER,
  paragraph_count INTEGER,
  title       TEXT,
  author      TEXT,
  subject     TEXT,
  created     TEXT,
  modified    TEXT,
  indexed_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_docx_filename ON docx_index(filename);
CREATE INDEX IF NOT EXISTS idx_docx_size ON docx_index(size_bytes);
"""


def make_id(path: str) -> str:
    import hashlib

    return hashlib.sha256(path.encode()).hexdigest()[:16]


def get_docx_metadata(path: Path) -> dict:
    meta: dict[str, int | str | None] = {
        "word_count": None,
        "paragraph_count": None,
        "title": None,
        "author": None,
        "subject": None,
        "created": None,
        "modified": None,
    }
    try:
        import docx  # pyright: ignore[reportMissingImports]

        doc = docx.Document(str(path))
        props = doc.core_properties
        meta["title"] = props.title or None
        meta["author"] = props.author or None
        meta["subject"] = props.subject or None
        if props.created:
            meta["created"] = props.created.isoformat()
        if props.modified:
            meta["modified"] = props.modified.isoformat()
        paras = [p for p in doc.paragraphs if p.text.strip()]
        meta["paragraph_count"] = len(paras)
        words = sum(len(p.text.split()) for p in paras)
        meta["word_count"] = words
    except Exception:
        pass
    return meta


def main() -> None:
    parser = argparse.ArgumentParser(description="Index DOCX files into aios.db")
    parser.add_argument("--path", default="~/Downloads", help="Directory to walk")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate table")
    parser.add_argument("--dry-run", action="store_true", help="Print without writing")
    args = parser.parse_args()

    root = Path(args.path).expanduser()
    if not root.exists():
        print(f"Error: path not found: {root}", file=sys.stderr)
        sys.exit(1)

    try:
        import docx  # noqa: F401  # pyright: ignore[reportMissingImports]
    except ImportError:
        print("Error: python-docx not installed. Run: pip install python-docx", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(DB)

    if args.reset:
        conn.execute("DROP TABLE IF EXISTS docx_index")
        print("Dropped docx_index table")

    conn.executescript(SCHEMA)
    conn.commit()

    docx_files = sorted(root.rglob("*.docx"))
    print(f"Found {len(docx_files)} DOCX files in {root}")

    inserted = 0
    skipped = 0
    now = datetime.now(UTC).isoformat()

    for docx_path in docx_files:
        path_str = str(docx_path)
        file_id = make_id(path_str)

        row = conn.execute("SELECT id FROM docx_index WHERE path = ?", (path_str,)).fetchone()
        if row:
            skipped += 1
            continue

        size = docx_path.stat().st_size
        meta = get_docx_metadata(docx_path)

        if args.dry_run:
            print(f"  WOULD INDEX  {docx_path.name} ({size // 1024}KB, {meta['word_count']} words)")
            inserted += 1
            continue

        conn.execute(
            """
            INSERT OR IGNORE INTO docx_index
              (id, path, filename, size_bytes, word_count, paragraph_count,
               title, author, subject, created, modified, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                file_id,
                path_str,
                docx_path.name,
                size,
                meta["word_count"],
                meta["paragraph_count"],
                meta["title"],
                meta["author"],
                meta["subject"],
                meta["created"],
                meta["modified"],
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
