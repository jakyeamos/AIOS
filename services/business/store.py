from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime

from services.business.dedupe import filter_new_records
from services.business.models import IngestRunSummary, SourceRecord
from services.business.normalize import write_immutable_raw
from services.business.paths import raw_source_dir
from services.business.schema import ensure_business_memory_schema


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _new_run_id() -> str:
    return f"ingest-{uuid.uuid4()}"


def index_source_fts(conn: sqlite3.Connection, record: SourceRecord) -> None:
    conn.execute("DELETE FROM business_sources_fts WHERE source_id = ?", (record.source_id,))
    conn.execute(
        """
        INSERT INTO business_sources_fts (
            source_id, body_text, subject_or_title, author_name, channel_or_thread
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            record.source_id,
            record.body_text,
            record.subject_or_title or "",
            record.author_name or "",
            record.channel_or_thread or "",
        ),
    )


def insert_source_record(
    conn: sqlite3.Connection,
    record: SourceRecord,
    *,
    raw_path: str,
    ingest_run_id: str,
) -> None:
    now = _now_iso()
    conn.execute(
        """
        INSERT INTO memory_raw_sources (
            id, source_type, source_path, project_id, author, confidence,
            original_content, extraction_status, created_at, updated_at,
            external_id, author_name, author_handle, occurred_at,
            channel_or_thread, subject_or_title, body_text, url,
            attachments_json, tags_json, content_hash, privacy_level,
            raw_path, normalized_json_path, ingest_run_id, compiled_at
        )
        VALUES (
            ?, ?, ?, NULL, ?, NULL,
            ?, 'pending', ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, NULL
        )
        """,
        (
            record.source_id,
            record.source_type,
            raw_path,
            record.author_name,
            record.body_text,
            now,
            now,
            record.external_id,
            record.author_name,
            record.author_handle,
            record.timestamp,
            record.channel_or_thread,
            record.subject_or_title,
            record.body_text,
            record.url,
            json.dumps(record.attachments),
            json.dumps(record.tags),
            record.hash,
            record.privacy_level,
            raw_path,
            raw_path,
            ingest_run_id,
        ),
    )
    index_source_fts(conn, record)


def persist_records(
    conn: sqlite3.Connection,
    records: list[SourceRecord],
    *,
    source_type: str,
    config_snapshot: dict | None = None,
) -> IngestRunSummary:
    ensure_business_memory_schema(conn)
    run_id = _new_run_id()
    started_at = _now_iso()
    errors: list[str] = []
    new_records, duplicates = filter_new_records(conn, records)

    conn.execute(
        """
        INSERT INTO business_ingest_runs (
            id, source_type, started_at, status, records_fetched,
            records_new, records_duplicate, config_snapshot_json
        )
        VALUES (?, ?, ?, 'running', ?, 0, ?, ?)
        """,
        (
            run_id,
            source_type,
            started_at,
            len(records),
            len(duplicates),
            json.dumps(config_snapshot or {}),
        ),
    )

    inserted = 0
    for record in new_records:
        try:
            raw_dir = raw_source_dir(record.source_type, record.timestamp)
            raw_path = write_immutable_raw(record, raw_dir)
            insert_source_record(conn, record, raw_path=str(raw_path), ingest_run_id=run_id)
            inserted += 1
        except Exception as exc:  # noqa: BLE001 — collect per-record failures
            errors.append(f"{record.source_id}: {exc}")

    status = "success"
    if errors and inserted:
        status = "partial"
    elif errors and not inserted:
        status = "failed"

    finished_at = _now_iso()
    conn.execute(
        """
        UPDATE business_ingest_runs
        SET finished_at = ?, status = ?, records_new = ?, error_summary = ?
        WHERE id = ?
        """,
        (
            finished_at,
            status,
            inserted,
            "\n".join(errors) if errors else None,
            run_id,
        ),
    )
    conn.commit()

    return IngestRunSummary(
        run_id=run_id,
        source_type=source_type,
        status=status,
        records_fetched=len(records),
        records_new=inserted,
        records_duplicate=len(duplicates),
        errors=errors,
    )


def status_snapshot(conn: sqlite3.Connection) -> dict:
    ensure_business_memory_schema(conn)
    by_type = conn.execute(
        """
        SELECT source_type, COUNT(*) AS count
        FROM memory_raw_sources
        WHERE source_type IN ('manual', 'gmail', 'discord', 'x')
        GROUP BY source_type
        ORDER BY source_type
        """
    ).fetchall()
    uncompiled = conn.execute(
        """
        SELECT COUNT(*) FROM memory_raw_sources
        WHERE source_type IN ('manual', 'gmail', 'discord', 'x')
          AND compiled_at IS NULL
        """
    ).fetchone()
    last_runs = conn.execute(
        """
        SELECT id, source_type, status, started_at, records_new, records_duplicate
        FROM business_ingest_runs
        ORDER BY started_at DESC
        LIMIT 5
        """
    ).fetchall()
    compile_runs = conn.execute(
        """
        SELECT id, status, started_at, sources_processed, pages_created, pages_updated
        FROM business_compile_runs
        ORDER BY started_at DESC
        LIMIT 3
        """
    ).fetchall()
    candidate_pages = conn.execute(
        "SELECT COUNT(*) FROM business_wiki_fts"
    ).fetchone()
    return {
        "sources_by_type": {row[0]: row[1] for row in by_type},
        "uncompiled_sources": int(uncompiled[0]) if uncompiled else 0,
        "wiki_candidate_pages_indexed": int(candidate_pages[0]) if candidate_pages else 0,
        "recent_ingest_runs": [
            {
                "id": row[0],
                "source_type": row[1],
                "status": row[2],
                "started_at": row[3],
                "records_new": row[4],
                "records_duplicate": row[5],
            }
            for row in last_runs
        ],
        "recent_compile_runs": [
            {
                "id": row[0],
                "status": row[1],
                "started_at": row[2],
                "sources_processed": row[3],
                "pages_created": row[4],
                "pages_updated": row[5],
            }
            for row in compile_runs
        ],
    }
