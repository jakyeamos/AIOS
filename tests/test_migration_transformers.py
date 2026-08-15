from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.migration_transformers import (  # noqa: E402
    quarantine_known_fk_violations,
)
from services.storage import (  # noqa: E402
    connect,
    database_health,
    list_quarantine,
)


def _seed_production_shaped_fixture(path: Path) -> None:
    with connect(path) as conn:
        conn.executescript(
            """
            CREATE TABLE projects (
              id TEXT PRIMARY KEY,
              repo_path TEXT NOT NULL
            );
            CREATE TABLE sessions (id TEXT PRIMARY KEY);
            CREATE TABLE eval_tasks (id TEXT PRIMARY KEY);
            CREATE TABLE quality_pipeline_runs (
              id TEXT PRIMARY KEY,
              project_id TEXT NOT NULL REFERENCES projects(id),
              metadata_json TEXT NOT NULL DEFAULT '{}'
            );
            CREATE TABLE orchestration_runs (
              id TEXT PRIMARY KEY,
              session_id TEXT REFERENCES sessions(id)
            );
            CREATE TABLE orchestration_invocations (
              id TEXT PRIMARY KEY,
              session_id TEXT REFERENCES sessions(id)
            );
            CREATE TABLE orchestration_run_events (
              id TEXT PRIMARY KEY,
              session_id TEXT REFERENCES sessions(id)
            );
            CREATE TABLE shadow_branch_runs (
              id TEXT PRIMARY KEY,
              task_id TEXT REFERENCES eval_tasks(id)
            );
            """
        )
        conn.commit()
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.executescript(
            """
            INSERT INTO projects (id, repo_path) VALUES ('project-1', '/tmp/project-one');
            INSERT INTO quality_pipeline_runs (id, project_id, metadata_json)
              VALUES ('quality-mappable', 'project-one', '{"working_directory":"/tmp/project-one"}');
            INSERT INTO quality_pipeline_runs (id, project_id, metadata_json)
              VALUES ('quality-unresolved', 'missing-project', '{}');
            INSERT INTO orchestration_runs (id, session_id) VALUES ('run-1', '');
            INSERT INTO orchestration_invocations (id, session_id) VALUES ('invocation-1', '');
            INSERT INTO orchestration_run_events (id, session_id) VALUES ('event-1', '');
            INSERT INTO shadow_branch_runs (id, task_id) VALUES ('shadow-1', 'missing-task');
            """
        )
        conn.commit()
        conn.execute("PRAGMA foreign_keys = ON")


def test_known_fk_transformers_map_or_archive_without_synthetic_parents(tmp_path: Path) -> None:
    db_path = tmp_path / "fixture.db"
    _seed_production_shaped_fixture(db_path)

    with connect(db_path) as conn:
        before = database_health(conn)
        assert len(before.foreign_key_violations) == 6
        quarantine_ids = quarantine_known_fk_violations(
            conn,
            migration_id="m001-known-fk-classes",
        )
        after = database_health(conn)
        assert len(quarantine_ids) == 6
        assert after.foreign_key_violations == ()
        assert (
            conn.execute(
                "SELECT project_id FROM quality_pipeline_runs WHERE id = 'quality-mappable'"
            ).fetchone()[0]
            == "project-1"
        )
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM quality_pipeline_runs WHERE id = 'quality-unresolved'"
            ).fetchone()[0]
            == 0
        )
        assert conn.execute("SELECT session_id FROM orchestration_runs").fetchone()[0] is None
        assert conn.execute("SELECT task_id FROM shadow_branch_runs").fetchone()[0] is None
        records = list_quarantine(conn, migration_id="m001-known-fk-classes")
        assert len(records) == 6
        assert {record.proposed_disposition for record in records} == {
            "mapped-by-unique-working-directory",
            "archive-unresolved-project",
            "retain-with-null-session-or-review",
            "retain-with-null-task-or-archive",
        }

        second_pass = quarantine_known_fk_violations(
            conn,
            migration_id="m001-known-fk-classes",
        )
        assert second_pass == ()


def test_quality_mapping_requires_unique_path(tmp_path: Path) -> None:
    db_path = tmp_path / "ambiguous.db"
    _seed_production_shaped_fixture(db_path)
    with connect(db_path) as conn:
        conn.execute(
            "INSERT INTO projects (id, repo_path) VALUES (?, ?)",
            ("project-duplicate", "/tmp/project-one"),
        )
        conn.commit()
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute(
            "INSERT INTO quality_pipeline_runs (id, project_id, metadata_json) VALUES (?, ?, ?)",
            ("quality-ambiguous", "project-one", '{"working_directory":"/tmp/project-one"}'),
        )
        conn.commit()
        conn.execute("PRAGMA foreign_keys = ON")
        quarantine_known_fk_violations(conn, migration_id="m001-ambiguous")
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM quality_pipeline_runs WHERE id = 'quality-ambiguous'"
            ).fetchone()[0]
            == 0
        )
        records = list_quarantine(conn, migration_id="m001-ambiguous")
        records = tuple(
            record for record in records if record.source_table == "quality_pipeline_runs"
        )
        assert len(records) == 3
        assert all(
            record.proposed_disposition == "archive-unresolved-project" for record in records
        )
