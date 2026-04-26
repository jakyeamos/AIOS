from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.project_inventory import sync_git_projects  # noqa: E402


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
