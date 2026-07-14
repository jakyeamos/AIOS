#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.storage import connect as connect_storage  # noqa: E402

DEFAULT_DB = Path(os.environ.get("AIOS_DB", str(ROOT / "data" / "aios.db"))).expanduser()
VALID_STATES = {"draft", "candidate", "approved", "active", "deprecated"}
STATUS_MAPPING = {"promoted": "candidate", "rejected": "deprecated", "pending": "candidate"}
ASSET_KINDS = {"prompt", "skill", "workflow"}


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def _json_dict(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def migrate_lifecycle_statuses(
    conn: sqlite3.Connection,
    *,
    dry_run: bool,
    include_legacy_kinds: bool = False,
) -> dict[str, Any]:
    if not _table_exists(conn, "promotion_lifecycle_items"):
        return {
            "scanned": 0,
            "remapped": {},
            "unmapped": {},
            "dry_run": dry_run,
            "mapping_used": STATUS_MAPPING,
        }

    rows = conn.execute(
        """
        SELECT id, item_kind, status, metadata_json
        FROM promotion_lifecycle_items
        WHERE status NOT IN ('draft', 'candidate', 'approved', 'active', 'deprecated')
        """
    ).fetchall()
    remapped: dict[str, int] = {}
    unmapped: dict[str, int] = {}
    scanned = 0
    for row in rows:
        row_id = str(row[0])
        item_kind = str(row[1])
        status = str(row[2])
        if not include_legacy_kinds and item_kind not in ASSET_KINDS:
            continue
        scanned += 1
        new_status = STATUS_MAPPING.get(status)
        if new_status is None or new_status not in VALID_STATES:
            unmapped[status] = unmapped.get(status, 0) + 1
            continue
        remapped[status] = remapped.get(status, 0) + 1
        if dry_run:
            continue
        metadata = _json_dict(row[3])
        metadata["migrated_from"] = status
        conn.execute(
            """
            UPDATE promotion_lifecycle_items
            SET status = ?,
                updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now'),
                metadata_json = ?
            WHERE id = ?
            """,
            (new_status, json.dumps(metadata, sort_keys=True), row_id),
        )
    return {
        "scanned": scanned,
        "remapped": remapped,
        "unmapped": unmapped,
        "dry_run": dry_run,
        "mapping_used": STATUS_MAPPING,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize asset lifecycle status values.")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="SQLite database path.")
    parser.add_argument(
        "--dry-run", action="store_true", help="Report changes without mutating rows."
    )
    parser.add_argument(
        "--include-legacy-kinds",
        action="store_true",
        help="Also migrate rows whose item_kind is not prompt, skill, or workflow.",
    )
    args = parser.parse_args()

    db_path = args.db
    conn = (
        sqlite3.connect(":memory:")
        if db_path == ":memory:"
        else connect_storage(Path(db_path).expanduser())
    )
    with conn:
        summary = migrate_lifecycle_statuses(
            conn,
            dry_run=bool(args.dry_run),
            include_legacy_kinds=bool(args.include_legacy_kinds),
        )
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
