from __future__ import annotations

import sqlite3

from services.business.models import SourceRecord


def is_duplicate(conn: sqlite3.Connection, content_hash: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM memory_raw_sources WHERE content_hash = ? LIMIT 1",
        (content_hash,),
    ).fetchone()
    return row is not None


def filter_new_records(
    conn: sqlite3.Connection,
    records: list[SourceRecord],
) -> tuple[list[SourceRecord], list[SourceRecord]]:
    new_records: list[SourceRecord] = []
    duplicates: list[SourceRecord] = []
    for record in records:
        if is_duplicate(conn, record.hash):
            duplicates.append(record)
        else:
            new_records.append(record)
    return new_records, duplicates
