from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from typing import TypedDict


class RegisteredProject(TypedDict):
    id: str
    name: str
    repo_path: str
    inserted: bool


def ensure_projects_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS projects (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          repo_path TEXT NOT NULL,
          obsidian_path TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'active',
          created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
          updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """
    )


def _canonical_repo_path(path: Path) -> str:
    return str(path.expanduser().resolve()).rstrip("/ ")


def discover_git_repos(root: Path) -> list[Path]:
    root = root.expanduser()
    if not root.exists():
        return []
    return sorted(path.parent for path in root.glob("*/.git") if path.is_dir())


def _stable_project_id(repo_path: str) -> str:
    return hashlib.sha1(repo_path.encode("utf-8")).hexdigest()[:16]


def _unique_project_id(conn: sqlite3.Connection, base_id: str) -> str:
    candidate = base_id
    suffix = 1
    while conn.execute("SELECT 1 FROM projects WHERE id = ? LIMIT 1", (candidate,)).fetchone():
        suffix += 1
        candidate = f"{base_id[:14]}{suffix:02d}"
    return candidate


def sync_git_projects(conn: sqlite3.Connection, root: Path) -> list[RegisteredProject]:
    ensure_projects_schema(conn)
    existing_paths = {
        _canonical_repo_path(Path(row[0])): str(row[1])
        for row in conn.execute("SELECT repo_path, id FROM projects")
        if row[0]
    }
    results: list[RegisteredProject] = []
    for repo in discover_git_repos(root):
        repo_path = _canonical_repo_path(repo)
        if repo_path in existing_paths:
            results.append(
                {
                    "id": existing_paths[repo_path],
                    "name": repo.name,
                    "repo_path": repo_path,
                    "inserted": False,
                }
            )
            continue
        project_id = _unique_project_id(conn, _stable_project_id(repo_path))
        conn.execute(
            """
            INSERT INTO projects (id, name, repo_path, obsidian_path, status)
            VALUES (?, ?, ?, ?, 'active')
            """,
            (project_id, repo.name, repo_path, f"03 Projects/{repo.name}"),
        )
        results.append(
            {
                "id": project_id,
                "name": repo.name,
                "repo_path": repo_path,
                "inserted": True,
            }
        )
    return results
