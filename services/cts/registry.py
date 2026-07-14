from __future__ import annotations

import hashlib
import os
import sqlite3
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

from services.storage import connect as connect_storage

from .graph_store import GraphStore

AIOS_DB_DEFAULT = Path(
    os.environ.get("AIOS_DB", str(Path.home() / "AIOS" / "data" / "aios.db"))
).expanduser()
CTS_DATA_ROOT_DEFAULT = Path(os.path.expanduser("~/AIOS/data/cts"))


@dataclass(slots=True)
class CTSRepo:
    repo_id: str
    repo_path: Path
    name: str
    status: str


class CTSRegistry:
    def __init__(
        self,
        aios_db_path: Path = AIOS_DB_DEFAULT,
        cts_data_root: Path = CTS_DATA_ROOT_DEFAULT,
        pool_size: int = 10,
    ) -> None:
        self.aios_db_path = aios_db_path
        self.cts_data_root = cts_data_root
        self.pool_size = pool_size
        self._pool: OrderedDict[str, GraphStore] = OrderedDict()
        self.cts_data_root.mkdir(parents=True, exist_ok=True)

    def _connect_aios(self) -> sqlite3.Connection:
        return connect_storage(self.aios_db_path, read_only=True, timeout=30)

    def list_repos(self, active_only: bool = True) -> list[CTSRepo]:
        conn = self._connect_aios()
        try:
            if active_only:
                rows = conn.execute(
                    "SELECT id, name, repo_path, status FROM projects WHERE status='active'"
                ).fetchall()
            else:
                rows = conn.execute("SELECT id, name, repo_path, status FROM projects").fetchall()
        finally:
            conn.close()
        repos: list[CTSRepo] = []
        for row in rows:
            repo_path = Path(str(row["repo_path"])).expanduser().resolve()
            repos.append(
                CTSRepo(
                    repo_id=str(row["id"]),
                    repo_path=repo_path,
                    name=str(row["name"]),
                    status=str(row["status"]),
                )
            )
        return repos

    def get_repo_by_path(self, repo_path: Path) -> CTSRepo | None:
        normalized = str(repo_path.expanduser().resolve())
        conn = self._connect_aios()
        try:
            row = conn.execute(
                "SELECT id, name, repo_path, status FROM projects WHERE repo_path=? LIMIT 1",
                (normalized,),
            ).fetchone()
            if row is not None:
                return CTSRepo(
                    repo_id=str(row["id"]),
                    repo_path=Path(str(row["repo_path"])).expanduser().resolve(),
                    name=str(row["name"]),
                    status=str(row["status"]),
                )
            # Gracefully handle logically equivalent path representations.
            rows = conn.execute("SELECT id, name, repo_path, status FROM projects").fetchall()
        finally:
            conn.close()
        for candidate in rows:
            candidate_path = Path(str(candidate["repo_path"])).expanduser().resolve()
            if str(candidate_path) == normalized:
                return CTSRepo(
                    repo_id=str(candidate["id"]),
                    repo_path=candidate_path,
                    name=str(candidate["name"]),
                    status=str(candidate["status"]),
                )
        return None

    def require_repo_by_path(self, repo_path: Path) -> CTSRepo:
        repo = self.get_repo_by_path(repo_path)
        if repo is not None:
            return repo
        raise ValueError(
            f"Repo path is not registered in projects table: {repo_path}. "
            "Register/open a session for this repo first."
        )

    def graph_db_path(self, repo_id: str) -> Path:
        bucket = hashlib.sha256(repo_id.encode("utf-8")).hexdigest()[:16]
        folder = self.cts_data_root / bucket
        folder.mkdir(parents=True, exist_ok=True)
        return folder / "graph.db"

    def open_store(self, repo: CTSRepo) -> GraphStore:
        if repo.repo_id in self._pool:
            store = self._pool.pop(repo.repo_id)
            self._pool[repo.repo_id] = store
            return store
        if len(self._pool) >= self.pool_size:
            _, evicted = self._pool.popitem(last=False)
            evicted.close()
        store = GraphStore(self.graph_db_path(repo.repo_id))
        store.ensure_repo(repo.repo_id, str(repo.repo_path), repo.name)
        self._pool[repo.repo_id] = store
        return store

    def close(self) -> None:
        for store in self._pool.values():
            store.close()
        self._pool.clear()
