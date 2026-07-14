from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_DB_PATH = Path.home() / "AIOS" / "data" / "aios.db"
BUSY_TIMEOUT_MS = 10_000
CONNECTION_TIMEOUT_SECONDS = 10.0
MIGRATION_TOOL_VERSION = "aios-migration-v0.1"


@dataclass(frozen=True)
class ForeignKeyViolation:
    table: str
    row_id: int | None
    parent_table: str
    foreign_key_index: int


@dataclass(frozen=True)
class DatabaseHealth:
    quick_check: str
    integrity_check: str
    foreign_key_violations: tuple[ForeignKeyViolation, ...]
    schema_checksum: str
    user_version: int


@dataclass(frozen=True)
class BackupMetadata:
    path: Path
    sha256: str
    size_bytes: int
    created_at: str


@dataclass(frozen=True)
class MigrationRecord:
    version: int
    migration_id: str
    checksum: str
    applied_at: str
    tool_version: str
    pre_backup_ref: str | None
    post_backup_ref: str | None


@dataclass(frozen=True)
class QuarantineRecord:
    id: int
    migration_id: str
    source_table: str
    source_primary_key: str
    original_payload_json: str
    reason: str
    detected_at: str
    proposed_disposition: str
    reviewer_decision: str | None


def resolve_db_path(db_path: Path | str | None = None) -> Path:
    raw_path = db_path if db_path is not None else os.environ.get("AIOS_DB")
    return Path(raw_path or DEFAULT_DB_PATH).expanduser().resolve()


def connect(
    db_path: Path | str | None = None,
    *,
    read_only: bool = False,
    timeout: float = CONNECTION_TIMEOUT_SECONDS,
) -> sqlite3.Connection:
    path = resolve_db_path(db_path)
    if read_only:
        if not path.exists():
            raise FileNotFoundError(path)
        conn = sqlite3.connect(
            f"file:{path}?mode=ro",
            uri=True,
            timeout=timeout,
        )
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path, timeout=timeout)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
    if read_only:
        conn.execute("PRAGMA query_only = ON")
    else:
        conn.execute("PRAGMA journal_mode = WAL")
    return conn


def ensure_migration_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
          version INTEGER PRIMARY KEY,
          migration_id TEXT NOT NULL UNIQUE,
          checksum TEXT NOT NULL,
          applied_at TEXT NOT NULL,
          tool_version TEXT NOT NULL,
          pre_backup_ref TEXT,
          post_backup_ref TEXT
        );
        CREATE TABLE IF NOT EXISTS migration_quarantine (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          migration_id TEXT NOT NULL,
          source_table TEXT NOT NULL,
          source_primary_key TEXT NOT NULL,
          original_payload_json TEXT NOT NULL,
          reason TEXT NOT NULL,
          detected_at TEXT NOT NULL,
          proposed_disposition TEXT NOT NULL,
          reviewer_decision TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_migration_quarantine_migration
          ON migration_quarantine(migration_id, detected_at);
        CREATE INDEX IF NOT EXISTS idx_migration_quarantine_source
          ON migration_quarantine(source_table, source_primary_key);
        """
    )


def migration_records(conn: sqlite3.Connection) -> tuple[MigrationRecord, ...]:
    ensure_migration_schema(conn)
    rows = conn.execute(
        """
        SELECT version, migration_id, checksum, applied_at, tool_version,
               pre_backup_ref, post_backup_ref
        FROM schema_migrations
        ORDER BY version
        """
    ).fetchall()
    return tuple(
        MigrationRecord(
            version=int(row["version"]),
            migration_id=str(row["migration_id"]),
            checksum=str(row["checksum"]),
            applied_at=str(row["applied_at"]),
            tool_version=str(row["tool_version"]),
            pre_backup_ref=row["pre_backup_ref"],
            post_backup_ref=row["post_backup_ref"],
        )
        for row in rows
    )


def record_migration(
    conn: sqlite3.Connection,
    *,
    version: int,
    migration_id: str,
    checksum: str,
    pre_backup_ref: str | None = None,
    post_backup_ref: str | None = None,
    applied_at: str | None = None,
    tool_version: str = MIGRATION_TOOL_VERSION,
) -> bool:
    if version < 1:
        raise ValueError("migration version must be positive")
    if not migration_id.strip() or not checksum.strip():
        raise ValueError("migration_id and checksum are required")
    ensure_migration_schema(conn)
    existing = conn.execute(
        "SELECT * FROM schema_migrations WHERE version = ?",
        (version,),
    ).fetchone()
    if existing is not None:
        expected = {
            "migration_id": migration_id,
            "checksum": checksum,
            "tool_version": tool_version,
            "pre_backup_ref": pre_backup_ref,
            "post_backup_ref": post_backup_ref,
        }
        if any(existing[key] != value for key, value in expected.items()):
            raise ValueError(f"migration version {version} already has a different record")
        return False
    if conn.execute(
        "SELECT 1 FROM schema_migrations WHERE migration_id = ?",
        (migration_id,),
    ).fetchone():
        raise ValueError(f"migration id {migration_id!r} already has a different version")
    timestamp = applied_at or datetime.now(UTC).isoformat()
    with conn:
        conn.execute(
            """
            INSERT INTO schema_migrations (
              version, migration_id, checksum, applied_at, tool_version,
              pre_backup_ref, post_backup_ref
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                version,
                migration_id,
                checksum,
                timestamp,
                tool_version,
                pre_backup_ref,
                post_backup_ref,
            ),
        )
        conn.execute(f"PRAGMA user_version = {version}")
    return True


def schema_checksum(conn: sqlite3.Connection) -> str:
    rows = conn.execute(
        """
        SELECT type, name, tbl_name, COALESCE(sql, '') AS sql
        FROM sqlite_master
        WHERE name NOT LIKE 'sqlite_%'
        ORDER BY type, name, tbl_name
        """
    ).fetchall()
    canonical = "\n".join(
        "\x1f".join(str(row[key]) for key in ("type", "name", "tbl_name", "sql"))
        for row in rows
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def database_health(conn: sqlite3.Connection) -> DatabaseHealth:
    quick_check = str(conn.execute("PRAGMA quick_check").fetchone()[0])
    integrity_check = str(conn.execute("PRAGMA integrity_check").fetchone()[0])
    violations = tuple(
        ForeignKeyViolation(
            table=str(row[0]),
            row_id=int(row[1]) if row[1] is not None else None,
            parent_table=str(row[2]),
            foreign_key_index=int(row[3]),
        )
        for row in conn.execute("PRAGMA foreign_key_check").fetchall()
    )
    user_version = int(conn.execute("PRAGMA user_version").fetchone()[0])
    return DatabaseHealth(
        quick_check=quick_check,
        integrity_check=integrity_check,
        foreign_key_violations=violations,
        schema_checksum=schema_checksum(conn),
        user_version=user_version,
    )


def backup_database(source_path: Path | str, backup_path: Path | str) -> BackupMetadata:
    source = resolve_db_path(source_path)
    target = Path(backup_path).expanduser().resolve()
    if target.exists():
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    with connect(source, read_only=True) as source_conn, sqlite3.connect(target) as backup_conn:
        source_conn.backup(backup_conn)
    target.chmod(0o600)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    return BackupMetadata(
        path=target,
        sha256=digest,
        size_bytes=target.stat().st_size,
        created_at=datetime.now(UTC).isoformat(),
    )


def restore_database(backup_path: Path | str, target_path: Path | str) -> Path:
    source = Path(backup_path).expanduser().resolve()
    target = Path(target_path).expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(source)
    if target.exists():
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source) as source_conn, sqlite3.connect(target) as target_conn:
        source_conn.backup(target_conn)
    target.chmod(0o600)
    return target


def quarantine_row(
    conn: sqlite3.Connection,
    *,
    migration_id: str,
    source_table: str,
    source_primary_key: str,
    original_payload: Mapping[str, object],
    reason: str,
    proposed_disposition: str,
    detected_at: str | None = None,
) -> int:
    if not all(value.strip() for value in (migration_id, source_table, reason, proposed_disposition)):
        raise ValueError("migration_id, source_table, reason, and proposed_disposition are required")
    ensure_migration_schema(conn)
    with conn:
        cursor = conn.execute(
            """
            INSERT INTO migration_quarantine (
              migration_id, source_table, source_primary_key,
              original_payload_json, reason, detected_at, proposed_disposition
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                migration_id,
                source_table,
                source_primary_key,
                json.dumps(dict(original_payload), sort_keys=True),
                reason,
                detected_at or datetime.now(UTC).isoformat(),
                proposed_disposition,
            ),
        )
    row_id = cursor.lastrowid
    if row_id is None:
        raise RuntimeError("quarantine insert did not return an id")
    return int(row_id)


def list_quarantine(
    conn: sqlite3.Connection,
    *,
    migration_id: str | None = None,
) -> tuple[QuarantineRecord, ...]:
    ensure_migration_schema(conn)
    if migration_id is None:
        rows = conn.execute(
            "SELECT * FROM migration_quarantine ORDER BY id"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM migration_quarantine WHERE migration_id = ? ORDER BY id",
            (migration_id,),
        ).fetchall()
    return tuple(
        QuarantineRecord(
            id=int(row["id"]),
            migration_id=str(row["migration_id"]),
            source_table=str(row["source_table"]),
            source_primary_key=str(row["source_primary_key"]),
            original_payload_json=str(row["original_payload_json"]),
            reason=str(row["reason"]),
            detected_at=str(row["detected_at"]),
            proposed_disposition=str(row["proposed_disposition"]),
            reviewer_decision=row["reviewer_decision"],
        )
        for row in rows
    )
