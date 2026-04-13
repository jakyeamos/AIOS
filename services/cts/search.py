from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from .models import CTSNode, NodeKind


def kind_boost(query: str, node: CTSNode) -> float:
    q = query.strip()
    if "." in q and node.kind == NodeKind.FUNCTION:
        return 1.10
    if "_" in q and node.kind == NodeKind.FUNCTION:
        return 1.08
    if q and q[0].isupper() and node.kind == NodeKind.CLASS:
        return 1.12
    return 1.0


def reciprocal_rank_fusion(
    ranked_lists: list[list[dict[str, Any]]],
    k: int = 60,
) -> list[dict[str, Any]]:
    scores: dict[str, float] = defaultdict(float)
    payload: dict[str, dict[str, Any]] = {}
    for results in ranked_lists:
        for rank, item in enumerate(results, start=1):
            node: CTSNode = item["node"]
            node_key = node.qualified_name
            scores[node_key] += 1.0 / (k + rank)
            payload[node_key] = item
    fused = []
    for key, score in scores.items():
        entry = dict(payload[key])
        entry["rrf_score"] = score
        fused.append(entry)
    fused.sort(key=lambda r: r["rrf_score"], reverse=True)
    return fused


@dataclass(slots=True)
class SearchResult:
    items: list[dict[str, Any]]
    has_embeddings: bool


class HybridSearcher:
    def __init__(self, store) -> None:
        self.store = store

    def semantic_search_nodes(
        self,
        repo_id: str,
        query: str,
        kind: NodeKind | None = None,
        limit: int = 20,
    ) -> SearchResult:
        phrase_query = f"\"{query}\"" if " " in query.strip() else query
        fts_hits = self.store.search_fts(repo_id=repo_id, query=phrase_query, kind=kind, limit=limit * 2)
        like_hits = self.store.search_like(repo_id=repo_id, query=query, kind=kind, limit=limit * 2)
        fused = reciprocal_rank_fusion([fts_hits, like_hits])
        boosted: list[dict[str, Any]] = []
        for row in fused:
            node = row["node"]
            score = row["rrf_score"] * float(node.confidence) * kind_boost(query, node)
            row["score"] = score
            boosted.append(row)
        boosted.sort(key=lambda r: r["score"], reverse=True)
        return SearchResult(items=boosted[:limit], has_embeddings=False)

