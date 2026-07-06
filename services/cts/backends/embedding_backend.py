from __future__ import annotations

from .base import BackendResult


class EmbeddingBackend:
    name = "embedding"
    confidence_floor = 0.50

    def __init__(self, adapter) -> None:
        self.adapter = adapter

    def is_available(self, repo_id: str) -> bool:
        _ = repo_id
        return self.adapter.is_available()

    def search(self, repo_id: str, query: str, limit: int = 20) -> BackendResult:
        _ = repo_id
        _ = self.adapter.embed(query)
        return BackendResult(
            backend=self.name,
            confidence_floor=self.confidence_floor,
            items=[],
            warnings=["Embedding backend scaffold is present but semantic index is not built yet."],
        )
