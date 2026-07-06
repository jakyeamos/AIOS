from __future__ import annotations

from .base import BackendResult


class GraphBackend:
    name = "graph"
    confidence_floor = 0.40

    def __init__(self, store, searcher, impact_analyzer) -> None:
        self.store = store
        self.searcher = searcher
        self.impact_analyzer = impact_analyzer

    def is_available(self, repo_id: str) -> bool:
        meta = self.store.get_repo_meta(repo_id)
        return meta is not None

    def semantic_search_nodes(
        self,
        repo_id: str,
        query: str,
        kind=None,
        limit: int = 20,
    ) -> BackendResult:
        result = self.searcher.semantic_search_nodes(
            repo_id=repo_id, query=query, kind=kind, limit=limit
        )
        return BackendResult(
            backend=self.name,
            confidence_floor=self.confidence_floor,
            items=result.items,
            extra={"has_embeddings": result.has_embeddings},
        )

    def get_impact_radius(
        self, repo_id: str, changed_files: list[str], max_depth: int = 3
    ) -> BackendResult:
        impact = self.impact_analyzer.get_impact_radius(
            repo_id=repo_id,
            changed_files=changed_files,
            max_depth=max_depth,
        )
        return BackendResult(
            backend=self.name,
            confidence_floor=self.confidence_floor,
            items=[
                {
                    "changed_nodes": impact.changed_nodes,
                    "impacted_nodes": impact.impacted_nodes,
                    "impacted_files": impact.impacted_files,
                    "edges": impact.edges,
                    "truncated": impact.truncated,
                    "total_impacted": impact.total_impacted,
                    "risk_summary": impact.risk_summary,
                    "low_confidence_count": impact.low_confidence_count,
                    "stale_count": impact.stale_count,
                    "unindexed_changed_files": impact.unindexed_changed_files,
                }
            ],
        )
