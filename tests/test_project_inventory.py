from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.project_inventory import (  # noqa: E402
    list_registered_projects,
    rank_project_candidates,
    sync_git_projects,
)


def test_sync_git_projects_registers_missing_repos_once(tmp_path: Path) -> None:
    projects_root = tmp_path / "projects"
    repo = projects_root / "example"
    (repo / ".git").mkdir(parents=True)
    conn = sqlite3.connect(":memory:")

    first = sync_git_projects(conn, projects_root)
    second = sync_git_projects(conn, projects_root)

    assert len(first) == 1
    assert first[0]["inserted"] is True
    assert second[0]["inserted"] is False
    rows = conn.execute("SELECT name, repo_path, obsidian_path, status FROM projects").fetchall()
    assert rows == [("example", str(repo.resolve()), "03 Projects/example", "active")]


def test_rank_project_candidates_prefers_cwd_and_name_matches(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            repo_path TEXT NOT NULL,
            obsidian_path TEXT NOT NULL,
            status TEXT NOT NULL
        );
        """
    )
    conn.executemany(
        """
        INSERT INTO projects (id, name, repo_path, obsidian_path, status)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            ("p1", "AIOS", str((tmp_path / "AIOS").resolve()), "03 Projects/AIOS", "active"),
            (
                "p2",
                "Soundscape",
                str((tmp_path / "Soundscape").resolve()),
                "03 Projects/Soundscape",
                "active",
            ),
        ],
    )

    candidates = rank_project_candidates(
        conn,
        objective="Audit AIOS launch readiness and fix the last drift items",
        cwd=str((tmp_path / "AIOS" / "services").resolve()),
    )

    assert candidates[0].id == "p1"
    assert candidates[0].match_kind in {"cwd_match", "project_name_exact"}
    assert "AIOS" in candidates[0].rationale


def test_list_registered_projects_handles_sparse_schema() -> None:
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL
        );
        INSERT INTO projects (id, name) VALUES ('p1', 'AIOS');
        """
    )

    projects = list_registered_projects(conn)

    assert len(projects) == 1
    assert projects[0].repo_path == ""
    assert projects[0].status == "active"
