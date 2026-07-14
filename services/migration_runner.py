from __future__ import annotations

import sqlite3
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from services.storage import (
    BackupMetadata,
    DatabaseHealth,
    backup_database,
    connect,
    database_health,
    ensure_migration_schema,
    record_migration,
    restore_database,
)

MigrationTransformer = Callable[[sqlite3.Connection], Sequence[int]]


@dataclass(frozen=True)
class MigrationReport:
    migration_id: str
    version: int
    source_path: Path
    working_path: Path
    pre_backup: BackupMetadata
    post_backup: BackupMetadata
    before_health: DatabaseHealth
    after_health: DatabaseHealth
    before_counts: dict[str, int]
    after_counts: dict[str, int]
    quarantine_ids: tuple[int, ...]


class MigrationValidationError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        working_path: Path,
        health: DatabaseHealth,
    ) -> None:
        super().__init__(message)
        self.working_path = working_path
        self.health = health


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def table_counts(
    conn: sqlite3.Connection,
    tables: Sequence[str] = (),
) -> dict[str, int]:
    names = tuple(tables)
    if not names:
        names = tuple(
            str(row[0])
            for row in conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            ).fetchall()
        )
    return {
        name: int(conn.execute(f"SELECT COUNT(*) FROM {_quote_identifier(name)}").fetchone()[0])
        for name in names
    }


def run_copied_migration(
    source_path: Path | str,
    working_path: Path | str,
    pre_backup_path: Path | str,
    post_backup_path: Path | str,
    *,
    version: int,
    migration_id: str,
    checksum: str,
    transform: MigrationTransformer,
    count_tables: Sequence[str] = (),
) -> MigrationReport:
    source = Path(source_path).expanduser().resolve()
    working = Path(working_path).expanduser().resolve()
    pre_backup_path = Path(pre_backup_path).expanduser().resolve()
    post_backup_path = Path(post_backup_path).expanduser().resolve()
    pre_backup = backup_database(source, pre_backup_path)
    restore_database(pre_backup.path, working)

    with connect(working) as conn:
        before_health = database_health(conn)
        before_counts = table_counts(conn, count_tables)
        ensure_migration_schema(conn)
        quarantine_ids = tuple(int(row_id) for row_id in transform(conn))
        candidate_health = database_health(conn)
        if candidate_health.quick_check != "ok":
            raise MigrationValidationError(
                "copied migration failed SQLite quick_check",
                working_path=working,
                health=candidate_health,
            )
        if candidate_health.integrity_check != "ok":
            raise MigrationValidationError(
                "copied migration failed SQLite integrity_check",
                working_path=working,
                health=candidate_health,
            )
        if candidate_health.foreign_key_violations:
            raise MigrationValidationError(
                "copied migration left foreign-key violations",
                working_path=working,
                health=candidate_health,
            )
        record_migration(
            conn,
            version=version,
            migration_id=migration_id,
            checksum=checksum,
            pre_backup_ref=str(pre_backup.path),
            post_backup_ref=str(post_backup_path),
        )
        after_health = database_health(conn)
        after_counts = table_counts(conn, count_tables)

    post_backup = backup_database(working, post_backup_path)
    return MigrationReport(
        migration_id=migration_id,
        version=version,
        source_path=source,
        working_path=working,
        pre_backup=pre_backup,
        post_backup=post_backup,
        before_health=before_health,
        after_health=after_health,
        before_counts=before_counts,
        after_counts=after_counts,
        quarantine_ids=quarantine_ids,
    )
