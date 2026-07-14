from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.migration_runner import (  # noqa: E402
    MigrationValidationError,
    run_copied_migration,
    run_live_migration,
)
from services.storage import (  # noqa: E402
    connect,
    database_health,
    list_quarantine,
    migration_records,
    quarantine_row,
)


def _seed_clean_store(path: Path) -> None:
    with connect(path) as conn:
        conn.executescript(
            """
            CREATE TABLE projects (id TEXT PRIMARY KEY);
            CREATE TABLE sessions (
              id TEXT PRIMARY KEY,
              project_id TEXT NOT NULL REFERENCES projects(id)
            );
            INSERT INTO projects (id) VALUES ('project-1');
            INSERT INTO sessions (id, project_id) VALUES ('session-1', 'project-1');
            """
        )


def _seed_orphan_store(path: Path) -> None:
    with connect(path) as conn:
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


def test_copied_migration_records_ledger_and_post_backup(tmp_path: Path) -> None:
    source = tmp_path / "source.db"
    working = tmp_path / "working.db"
    pre_backup = tmp_path / "backups" / "pre.db"
    post_backup = tmp_path / "backups" / "post.db"
    _seed_clean_store(source)

    report = run_copied_migration(
        source,
        working,
        pre_backup,
        post_backup,
        version=1,
        migration_id="m001-copied-proof",
        checksum="fixture-checksum",
        transform=lambda _conn: (),
        count_tables=("projects", "sessions"),
    )

    assert report.before_counts == {"projects": 1, "sessions": 1}
    assert report.after_counts == {"projects": 1, "sessions": 1}
    assert report.before_health.foreign_key_violations == ()
    assert report.after_health.foreign_key_violations == ()
    assert report.quarantine_ids == ()
    with connect(working, read_only=True) as conn:
        assert [record.version for record in migration_records(conn)] == [1]
    with connect(source, read_only=True) as conn:
        assert migration_records(conn) == ()
        assert database_health(conn).foreign_key_violations == ()


def test_copied_migration_quarantines_orphan_without_mutating_source(tmp_path: Path) -> None:
    source = tmp_path / "source.db"
    working = tmp_path / "working.db"
    pre_backup = tmp_path / "backups" / "pre.db"
    post_backup = tmp_path / "backups" / "post.db"
    _seed_orphan_store(source)

    def quarantine_orphan(conn: sqlite3.Connection) -> tuple[int, ...]:
        row = conn.execute(
            "SELECT id, project_id FROM sessions WHERE project_id = ?",
            ("missing-project",),
        ).fetchone()
        assert row is not None
        quarantine_id = quarantine_row(
            conn,
            migration_id="m001-copied-proof",
            source_table="sessions",
            source_primary_key=str(row["id"]),
            original_payload={"id": row["id"], "project_id": row["project_id"]},
            reason="missing project parent",
            proposed_disposition="review-or-archive",
        )
        conn.execute("DELETE FROM sessions WHERE id = ?", (row["id"],))
        return (quarantine_id,)

    report = run_copied_migration(
        source,
        working,
        pre_backup,
        post_backup,
        version=1,
        migration_id="m001-copied-proof",
        checksum="fixture-checksum",
        transform=quarantine_orphan,
        count_tables=("projects", "sessions"),
    )

    assert report.before_health.foreign_key_violations
    assert report.after_health.foreign_key_violations == ()
    with connect(working, read_only=True) as conn:
        assert len(list_quarantine(conn, migration_id="m001-copied-proof")) == 1
    with connect(source, read_only=True) as conn:
        assert len(database_health(conn).foreign_key_violations) == 1
        assert (
            conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'migration_quarantine'"
            ).fetchone()
            is None
        )


def test_failed_copied_migration_keeps_source_unchanged(tmp_path: Path) -> None:
    source = tmp_path / "source.db"
    working = tmp_path / "working.db"
    pre_backup = tmp_path / "backups" / "pre.db"
    post_backup = tmp_path / "backups" / "post.db"
    _seed_orphan_store(source)

    with pytest.raises(MigrationValidationError, match="foreign-key violations"):
        run_copied_migration(
            source,
            working,
            pre_backup,
            post_backup,
            version=1,
            migration_id="m001-copied-proof",
            checksum="fixture-checksum",
            transform=lambda _conn: (),
            count_tables=("projects", "sessions"),
        )

    with connect(source, read_only=True) as conn:
        assert len(database_health(conn).foreign_key_violations) == 1
        assert migration_records(conn) == ()


def test_live_migration_records_backup_and_updates_source(tmp_path: Path) -> None:
    source = tmp_path / "source.db"
    pre_backup = tmp_path / "backups" / "pre.db"
    post_backup = tmp_path / "backups" / "post.db"
    _seed_orphan_store(source)

    def quarantine_orphan(conn: sqlite3.Connection) -> tuple[int, ...]:
        row = conn.execute(
            "SELECT id, project_id FROM sessions WHERE project_id = ?",
            ("missing-project",),
        ).fetchone()
        assert row is not None
        quarantine_id = quarantine_row(
            conn,
            migration_id="m001-live-proof",
            source_table="sessions",
            source_primary_key=str(row["id"]),
            original_payload={"id": row["id"], "project_id": row["project_id"]},
            reason="missing project parent",
            proposed_disposition="review-or-archive",
        )
        conn.execute("DELETE FROM sessions WHERE id = ?", (row["id"],))
        return (quarantine_id,)

    report = run_live_migration(
        source,
        pre_backup,
        post_backup,
        version=1,
        migration_id="m001-live-proof",
        checksum="fixture-checksum",
        transform=quarantine_orphan,
        count_tables=("projects", "sessions"),
    )

    assert report.before_health.foreign_key_violations
    assert report.after_health.foreign_key_violations == ()
    assert report.before_counts == {"projects": 0, "sessions": 1}
    assert report.after_counts == {"projects": 0, "sessions": 0}
    assert pre_backup.exists()
    assert post_backup.exists()
    with connect(source, read_only=True) as conn:
        assert database_health(conn).foreign_key_violations == ()
        assert [record.version for record in migration_records(conn)] == [1]
        assert len(list_quarantine(conn, migration_id="m001-live-proof")) == 1


def test_failed_live_migration_rolls_back_source(tmp_path: Path) -> None:
    source = tmp_path / "source.db"
    pre_backup = tmp_path / "backups" / "pre.db"
    post_backup = tmp_path / "backups" / "post.db"
    _seed_orphan_store(source)

    with pytest.raises(MigrationValidationError, match="foreign-key violations"):
        run_live_migration(
            source,
            pre_backup,
            post_backup,
            version=1,
            migration_id="m001-live-proof",
            checksum="fixture-checksum",
            transform=lambda _conn: (),
        )

    with connect(source, read_only=True) as conn:
        assert len(database_health(conn).foreign_key_violations) == 1
        assert migration_records(conn) == ()
