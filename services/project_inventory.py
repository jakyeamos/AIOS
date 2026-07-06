from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TypedDict


class RegisteredProject(TypedDict):
    id: str
    name: str
    repo_path: str
    inserted: bool


@dataclass(frozen=True)
class ProjectRecord:
    id: str
    name: str
    repo_path: str
    obsidian_path: str
    status: str

    def to_json(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class ProjectCandidate:
    id: str
    name: str
    repo_path: str
    obsidian_path: str
    status: str
    score: int
    match_kind: str
    rationale: str

    def to_json(self) -> dict[str, object]:
        return asdict(self)


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


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ? LIMIT 1",
        (name,),
    ).fetchone()
    return row is not None


def _table_columns(conn: sqlite3.Connection, name: str) -> set[str]:
    if not _table_exists(conn, name):
        return set()
    return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({name})").fetchall()}


def _tokenize(text: str | None) -> set[str]:
    if not text:
        return set()
    return set(re.findall(r"[a-z0-9]{3,}", text.lower()))


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


def list_registered_projects(conn: sqlite3.Connection) -> list[ProjectRecord]:
    if not _table_exists(conn, "projects"):
        return []

    columns = _table_columns(conn, "projects")
    select_parts = [
        "id",
        "name",
        "repo_path" if "repo_path" in columns else "'' AS repo_path",
        "obsidian_path" if "obsidian_path" in columns else "'' AS obsidian_path",
        "status" if "status" in columns else "'active' AS status",
    ]
    rows = conn.execute(f"SELECT {', '.join(select_parts)} FROM projects").fetchall()
    return [
        ProjectRecord(
            id=str(row[0]),
            name=str(row[1]),
            repo_path=str(row[2] or ""),
            obsidian_path=str(row[3] or ""),
            status=str(row[4] or "active"),
        )
        for row in rows
        if row[0] and row[1]
    ]


def rank_project_candidates(
    conn: sqlite3.Connection,
    *,
    objective: str,
    cwd: str | None = None,
    explicit_project_id: str | None = None,
    limit: int = 5,
) -> list[ProjectCandidate]:
    projects = list_registered_projects(conn)
    if not projects:
        return []

    objective_lower = objective.lower()
    objective_tokens = _tokenize(objective)
    canonical_cwd = _canonical_repo_path(Path(cwd)) if cwd else None
    candidates: list[ProjectCandidate] = []

    for project in projects:
        score = 0
        match_kind = "weak_match"
        reasons: list[str] = []
        repo_path = project.repo_path
        repo_name = Path(repo_path).name.lower() if repo_path else project.name.lower()
        name_lower = project.name.lower()
        name_tokens = _tokenize(project.name)

        if explicit_project_id:
            if project.id != explicit_project_id:
                continue
            score = 100
            match_kind = "explicit_project_id"
            reasons.append(f"Explicit project override selected {project.id}.")
        else:
            if canonical_cwd and repo_path:
                repo_root = _canonical_repo_path(Path(repo_path))
                if canonical_cwd == repo_root or canonical_cwd.startswith(repo_root + "/"):
                    score += 70
                    match_kind = "cwd_match"
                    reasons.append(f"Current working directory is inside {project.name}.")
            if name_lower and name_lower in objective_lower:
                score += 50
                match_kind = "project_name_exact"
                reasons.append(f"Objective explicitly names project {project.name}.")
            name_overlap = len(name_tokens & objective_tokens)
            if name_overlap:
                score += name_overlap * 12
                reasons.append(
                    f"Objective overlaps project-name tokens {sorted(name_tokens & objective_tokens)}."
                )
            if repo_name and repo_name in objective_lower:
                score += 35
                if match_kind == "weak_match":
                    match_kind = "repo_name_exact"
                reasons.append(f"Objective references repo name {repo_name}.")
            repo_tokens = _tokenize(repo_name)
            repo_overlap = len(repo_tokens & objective_tokens)
            if repo_overlap:
                score += repo_overlap * 8
                reasons.append(
                    f"Objective overlaps repo-name tokens {sorted(repo_tokens & objective_tokens)}."
                )

        if score <= 0:
            continue

        candidates.append(
            ProjectCandidate(
                id=project.id,
                name=project.name,
                repo_path=project.repo_path,
                obsidian_path=project.obsidian_path,
                status=project.status,
                score=score,
                match_kind=match_kind,
                rationale=" ".join(reasons),
            )
        )

    candidates.sort(key=lambda candidate: (-candidate.score, candidate.name.lower(), candidate.id))
    return candidates[:limit]
