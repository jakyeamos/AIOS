from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime


@dataclass
class DbSource:
    source_id: str
    source_type: str
    body_text: str
    subject_or_title: str | None
    author_name: str | None
    channel_or_thread: str | None
    occurred_at: str
    privacy_level: str
    raw_path: str | None
    tags: list[str]

    @property
    def combined_text(self) -> str:
        parts = [self.subject_or_title or "", self.body_text, " ".join(self.tags)]
        return "\n".join(part for part in parts if part)


def _parse_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except json.JSONDecodeError:
        pass
    return []


def _row_to_source(row: sqlite3.Row) -> DbSource:
    return DbSource(
        source_id=str(row["id"]),
        source_type=str(row["source_type"]),
        body_text=str(row["body_text"] or row["original_content"] or ""),
        subject_or_title=row["subject_or_title"],
        author_name=row["author_name"],
        channel_or_thread=row["channel_or_thread"],
        occurred_at=str(row["occurred_at"] or row["created_at"]),
        privacy_level=str(row["privacy_level"] or "internal"),
        raw_path=row["raw_path"],
        tags=_parse_tags(row["tags_json"]),
    )


def fetch_uncompiled_sources(
    conn: sqlite3.Connection,
    *,
    since_iso: str | None = None,
) -> list[DbSource]:
    params: list[object] = []
    where = [
        "source_type IN ('manual', 'gmail', 'discord', 'x')",
        "compiled_at IS NULL",
    ]
    if since_iso:
        where.append("COALESCE(occurred_at, created_at) >= ?")
        params.append(since_iso)
    query = f"""
        SELECT *
        FROM memory_raw_sources
        WHERE {' AND '.join(where)}
        ORDER BY COALESCE(occurred_at, created_at) ASC
    """
    rows = conn.execute(query, params).fetchall()
    return [_row_to_source(row) for row in rows]


def last_compile_started_at(conn: sqlite3.Connection) -> str | None:
    row = conn.execute(
        """
        SELECT started_at FROM business_compile_runs
        WHERE status IN ('success', 'partial')
        ORDER BY started_at DESC
        LIMIT 1
        """
    ).fetchone()
    return str(row[0]) if row else None


def mark_sources_compiled(conn: sqlite3.Connection, source_ids: list[str], compiled_at: str) -> None:
    if not source_ids:
        return
    placeholders = ",".join("?" for _ in source_ids)
    conn.execute(
        f"""
        UPDATE memory_raw_sources
        SET compiled_at = ?, updated_at = ?
        WHERE id IN ({placeholders})
        """,
        [compiled_at, compiled_at, *source_ids],
    )


def resolve_since_cursor(conn: sqlite3.Connection, since: str) -> str | None:
    if since == "beginning":
        return None
    if since == "last-run":
        return last_compile_started_at(conn)
    datetime.fromisoformat(since.replace("Z", "+00:00"))
    return since
