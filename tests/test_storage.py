from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.storage import (  # noqa: E402
    backup_database,
    connect,
    database_health,
    list_quarantine,
    migration_records,
    quarantine_row,
    record_migration,
    resolve_db_path,
    restore_database,
)


def test_connection_contract_uses_one_resolved_path_and_pragmas(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "nested" / "aios.db"
    monkeypatch.setenv("AIOS_DB", str(db_path))

    with connect() as conn:
        assert resolve_db_path() == db_path.resolve()
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == 10_000
        assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        assert conn.execute("PRAGMA query_only").fetchone()[0] == 0

    with connect(db_path, read_only=True) as conn:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert conn.execute("PRAGMA query_only").fetchone()[0] == 1
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("CREATE TABLE forbidden (id INTEGER PRIMARY KEY)")


def test_migration_ledger_is_idempotent_and_rejects_checksum_drift(tmp_path: Path) -> None:
    db_path = tmp_path / "ledger.db"
    with connect(db_path) as conn:
        assert record_migration(
            conn,
            version=1,
            migration_id="m001-storage-contract",
            checksum="checksum-a",
            pre_backup_ref="backup-before",
        ) is True
        assert record_migration(
            conn,
            version=1,
            migration_id="m001-storage-contract",
            checksum="checksum-a",
            pre_backup_ref="backup-before",
        ) is False
        assert [record.version for record in migration_records(conn)] == [1]
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 1
        with pytest.raises(ValueError, match="different record"):
            record_migration(
                conn,
                version=1,
                migration_id="m001-storage-contract",
                checksum="checksum-drift",
                pre_backup_ref="backup-before",
            )


def test_quarantine_preserves_orphan_payload_before_fixture_repair(tmp_path: Path) -> None:
    db_path = tmp_path / "quarantine.db"
    with connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE projects (id TEXT PRIMARY KEY);
            CREATE TABLE sessions (
              id TEXT PRIMARY KEY,
              project_id TEXT NOT NULL REFERENCES projects(id)
            );
            """
        )
        conn.commit()
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute(
            "INSERT INTO sessions (id, project_id) VALUES (?, ?)",
            ("session-orphan", "missing-project"),
        )
        conn.commit()
        conn.execute("PRAGMA foreign_keys = ON")

        health_before = database_health(conn)
        assert len(health_before.foreign_key_violations) == 1
        quarantine_id = quarantine_row(
            conn,
            migration_id="m001-storage-contract",
            source_table="sessions",
            source_primary_key="session-orphan",
            original_payload={"id": "session-orphan", "project_id": "missing-project"},
            reason="missing project parent",
            proposed_disposition="review-or-archive",
        )
        conn.execute("DELETE FROM sessions WHERE id = ?", ("session-orphan",))
        conn.commit()

        assert database_health(conn).foreign_key_violations == ()
        records = list_quarantine(conn, migration_id="m001-storage-contract")
        assert len(records) == 1
        assert records[0].id == quarantine_id
        assert json.loads(records[0].original_payload_json)["project_id"] == "missing-project"


def test_backup_restore_preserves_rows_and_integrity(tmp_path: Path) -> None:
    source_path = tmp_path / "source.db"
    backup_path = tmp_path / "backups" / "source.db"
    restored_path = tmp_path / "restored" / "source.db"
    with connect(source_path) as conn:
        conn.execute("CREATE TABLE values_table (id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
        conn.execute("INSERT INTO values_table (value) VALUES (?)", ("preserved",))
        conn.commit()

    metadata = backup_database(source_path, backup_path)
    assert metadata.path == backup_path.resolve()
    assert metadata.size_bytes == os.path.getsize(backup_path)
    assert oct(backup_path.stat().st_mode & 0o777) == "0o600"

    assert restore_database(backup_path, restored_path) == restored_path.resolve()
    with connect(restored_path, read_only=True) as conn:
        health = database_health(conn)
        assert health.quick_check == "ok"
        assert health.integrity_check == "ok"
        assert health.foreign_key_violations == ()
        assert conn.execute("SELECT value FROM values_table").fetchone()[0] == "preserved"
