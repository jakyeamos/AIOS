from __future__ import annotations

from .base import BackendResult


class FTSBackend:
    name = "fts"
    confidence_floor = 0.30

    def __init__(self, store) -> None:
        self.store = store

    def is_available(self, repo_id: str) -> bool:
        meta = self.store.get_repo_meta(repo_id)
        return meta is not None

    def search(self, repo_id: str, query: str, kind=None, limit: int = 20) -> BackendResult:
        hits = self.store.search_fts(repo_id=repo_id, query=query, kind=kind, limit=limit)
        if not hits:
            hits = self.store.search_like(repo_id=repo_id, query=query, kind=kind, limit=limit)
        return BackendResult(
            backend=self.name,
            confidence_floor=self.confidence_floor,
            items=hits,
            warnings=[] if hits else ["FTS backend returned no results."],
        )
