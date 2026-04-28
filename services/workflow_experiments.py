from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEST_REPOS = ROOT / "config" / "experiments" / "test-repos.json"
DEFAULT_PAPER_FIXTURES = ROOT / "fixtures" / "papers" / "generated"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def ensure_workflow_experiment_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS github_skill_candidates (
          id TEXT PRIMARY KEY,
          workflow_key TEXT NOT NULL,
          skill_key TEXT NOT NULL,
          name TEXT NOT NULL,
          github_url TEXT NOT NULL,
          repo TEXT NOT NULL,
          path TEXT,
          summary TEXT NOT NULL,
          tags_json TEXT NOT NULL DEFAULT '[]',
          detail_json TEXT NOT NULL DEFAULT '{}',
          status TEXT NOT NULL DEFAULT 'candidate',
          created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
          updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS workflow_skill_experiments (
          id TEXT PRIMARY KEY,
          workflow_key TEXT NOT NULL,
          skill_key TEXT NOT NULL,
          candidate_id TEXT,
          test_repo_id TEXT NOT NULL,
          test_repo_path TEXT NOT NULL,
          branch_name TEXT NOT NULL,
          experiment_kind TEXT NOT NULL,
          baseline_score REAL,
          candidate_score REAL,
          outcome TEXT,
          status TEXT NOT NULL DEFAULT 'queued',
          details_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
          updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
          UNIQUE(workflow_key, skill_key, test_repo_id, experiment_kind)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS workflow_paper_fixtures (
          id TEXT PRIMARY KEY,
          title TEXT NOT NULL,
          fixture_path TEXT NOT NULL UNIQUE,
          purpose TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'active',
          created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """
    )


def load_test_repos(path: Path = DEFAULT_TEST_REPOS) -> list[dict[str, str]]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    repos = loaded.get("test_repos", [])
    if not isinstance(repos, list):
        return []
    normalized = []
    for repo in repos:
        if not isinstance(repo, dict):
            continue
        repo_id = str(repo.get("id", "")).strip()
        repo_path = str(repo.get("repo_path", "")).strip()
        if repo_id and repo_path:
            normalized.append(
                {
                    "id": repo_id,
                    "name": str(repo.get("name", repo_id)),
                    "repo_path": repo_path,
                    "profile": str(repo.get("profile", repo_id)),
                }
            )
    return normalized


def queue_test_repo_experiments(
    conn: sqlite3.Connection,
    *,
    workflow_key: str,
    skill_key: str,
    candidate_id: str | None = None,
    test_repos_path: Path = DEFAULT_TEST_REPOS,
) -> list[dict[str, str]]:
    ensure_workflow_experiment_schema(conn)
    queued: list[dict[str, str]] = []
    for repo in load_test_repos(test_repos_path):
        branch_name = f"aios/experiment/{workflow_key}/{skill_key}/{repo['id']}"
        experiment_id = f"workflow-skill-exp-{uuid.uuid4()}"
        now = _now_iso()
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO workflow_skill_experiments (
              id, workflow_key, skill_key, candidate_id, test_repo_id, test_repo_path,
              branch_name, experiment_kind, status, details_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'test_repo_branch', 'queued', ?, ?, ?)
            """,
            (
                experiment_id,
                workflow_key,
                skill_key,
                candidate_id,
                repo["id"],
                repo["repo_path"],
                branch_name,
                _json({"repo_profile": repo["profile"], "repo_name": repo["name"]}),
                now,
                now,
            ),
        )
        if cursor.rowcount > 0:
            queued.append(
                {
                    "workflow_key": workflow_key,
                    "skill_key": skill_key,
                    "test_repo_id": repo["id"],
                    "branch_name": branch_name,
                }
            )
    return queued


def seed_paper_fixtures(
    conn: sqlite3.Connection,
    *,
    fixtures_dir: Path = DEFAULT_PAPER_FIXTURES,
) -> list[dict[str, str]]:
    ensure_workflow_experiment_schema(conn)
    seeded: list[dict[str, str]] = []
    if not fixtures_dir.exists():
        return seeded
    for path in sorted(fixtures_dir.glob("*.md")):
        title = path.stem.replace("-", " ").title()
        fixture_id = f"paper-fixture-{path.stem}"
        conn.execute(
            """
            INSERT OR IGNORE INTO workflow_paper_fixtures (id, title, fixture_path, purpose)
            VALUES (?, ?, ?, ?)
            """,
            (
                fixture_id,
                title,
                _display_path(path),
                "Humanizer workflow experiment fixture generated for controlled rewrite evaluation.",
            ),
        )
        seeded.append({"id": fixture_id, "path": _display_path(path)})
    return seeded
