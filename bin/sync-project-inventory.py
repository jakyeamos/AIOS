#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.project_inventory import sync_git_projects  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync Git repositories into the AIOS/Taski projects table.")
    parser.add_argument("--db", default=str(ROOT / "data" / "aios.db"))
    parser.add_argument("--root", default=str(Path.home() / "projects"))
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    try:
        results = sync_git_projects(conn, Path(args.root))
        conn.commit()
    finally:
        conn.close()

    inserted = [project for project in results if project["inserted"]]
    for project in results:
        marker = "inserted" if project["inserted"] else "tracked"
        print(f"{marker}\t{project['id']}\t{project['name']}\t{project['repo_path']}")
    print(f"inserted={len(inserted)} tracked={len(results)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
