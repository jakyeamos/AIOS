from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .backends import FileBackend, FTSBackend, GraphBackend
from .confidence import LOW_CONFIDENCE_THRESHOLD, confidence_note, summarize_nodes
from .impact import ImpactAnalyzer
from .incremental import detect_changed_files
from .models import (
    CTSNode,
    CTSQueryResult,
    FallbackType,
    IndexStatus,
    MinimalContextBundle,
    NodeKind,
)
from .registry import CTSRegistry
from .search import HybridSearcher


def _node_to_dict(node: CTSNode) -> dict[str, Any]:
    return {
        "id": node.id,
        "kind": node.kind.value if hasattr(node.kind, "value") else str(node.kind),
        "name": node.name,
        "qualified_name": node.qualified_name,
        "file_path": node.file_path,
        "line_start": node.line_start,
        "line_end": node.line_end,
        "language": node.language,
        "confidence": node.confidence,
        "extraction_method": (
            node.extraction_method.value
            if hasattr(node.extraction_method, "value")
            else str(node.extraction_method)
        ),
        "is_stale": node.is_stale,
        "unresolved_call_count": node.unresolved_call_count,
    }


def _edge_to_dict(edge) -> dict[str, Any]:
    return {
        "id": edge.id,
        "kind": edge.kind.value if hasattr(edge.kind, "value") else str(edge.kind),
        "source_qualified": edge.source_qualified,
        "target_qualified": edge.target_qualified,
        "file_path": edge.file_path,
        "line": edge.line,
        "confidence": edge.confidence,
        "resolution_method": (
            edge.resolution_method.value
            if hasattr(edge.resolution_method, "value")
            else str(edge.resolution_method)
        ),
        "is_stale": edge.is_stale,
    }


class CTSService:
    def __init__(self, registry: CTSRegistry | None = None) -> None:
        self.registry = registry or CTSRegistry()

    def _resolve_repo(self, repo_root: str | Path) -> tuple[Any, Any]:
        root = Path(repo_root).expanduser().resolve()
        repo = self.registry.require_repo_by_path(root)
        store = self.registry.open_store(repo)
        return repo, store

    def _build_envelope(
        self,
        query_type: str,
        repo_id: str,
        status: dict[str, Any],
        nodes: list[CTSNode],
        results: list[dict[str, Any]],
        fallback_used: FallbackType | None = None,
        warnings: list[str] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        summary = summarize_nodes(nodes)
        warning_list = list(warnings or [])
        if summary.stale_count > 0:
            warning_list.append("Stale nodes present; run incremental update before trusting results.")
        if summary.low_confidence_count > 0:
            warning_list.append("Low-confidence relations present; verify source before acting.")
        result = CTSQueryResult(
            query_type=query_type,
            repo_id=repo_id,
            index_age_seconds=int(status.get("index_age_seconds", 0)),
            index_status=IndexStatus(status.get("index_status", IndexStatus.EMPTY.value)),
            coverage_pct=float(status.get("coverage_pct", 0.0)),
            has_low_confidence_results=summary.low_confidence_count > 0,
            has_stale_results=summary.stale_count > 0,
            fallback_used=fallback_used,
            confidence_summary=summary,
            warnings=warning_list,
            results=results,
            extra=extra or {},
        )
        output = asdict(result)
        if result.fallback_used is not None:
            output["fallback_used"] = result.fallback_used.value
        output["index_status"] = result.index_status.value
        return output

    def get_minimal_context(
        self,
        task: str,
        changed_files: list[str] | None = None,
        repo_root: str | None = None,
        max_tokens: int = 300,
    ) -> dict[str, Any]:
        repo_root = repo_root or str(Path.cwd())
        repo, store = self._resolve_repo(repo_root)
        status = store.get_status_report(repo.repo_id)
        searcher = HybridSearcher(store)
        search_hits = searcher.semantic_search_nodes(repo.repo_id, task, limit=10)
        relevant_nodes = [row["node"] for row in search_hits.items]
        architecture = store.get_architecture_overview(repo.repo_id)
        changed_files = changed_files or []
        impact_files = changed_files
        if changed_files:
            impact_raw = store.get_impact_radius(repo.repo_id, changed_files, max_depth=2)
            impact_files = impact_raw["impacted_files"]
        unresolved = store.get_unresolved_call_count_for_files(repo.repo_id, changed_files)
        summary = summarize_nodes(relevant_nodes)
        note = confidence_note(summary, unresolved)
        lang = architecture.get("language_breakdown", {})
        total_lang = float(sum(float(v) for v in lang.values()))
        top_files = architecture.get("top_files", [])
        file_preview = ", ".join(row["file_path"] for row in top_files[:3]) if top_files else "none"
        if lang:
            if total_lang > 1.0:
                language_preview = ", ".join(
                    f"{k}:{round((float(v) / total_lang) * 100)}%" for k, v in lang.items()
                )
            else:
                language_preview = ", ".join(f"{k}:{round(float(v) * 100)}%" for k, v in lang.items())
        else:
            language_preview = "unknown"
        architecture_summary = (
            f"Primary languages: {language_preview}. Structural hotspots: {file_preview}."
        )
        bundle = MinimalContextBundle(
            repo_name=repo.name,
            index_status=IndexStatus(status.get("index_status", IndexStatus.EMPTY.value)),
            architecture_summary=architecture_summary,
            directly_relevant_nodes=[n.qualified_name for n in relevant_nodes[:10]],
            estimated_blast_radius=len(set(impact_files)),
            confidence_note=note,
            suggested_next_tools=[
                "get_impact_radius",
                "semantic_search_nodes",
                "query_graph",
            ],
        )
        payload = asdict(bundle)
        payload["index_status"] = bundle.index_status.value
        text_projection = json.dumps(payload, separators=(",", ":"))
        max_chars = max_tokens * 4
        if len(text_projection) > max_chars:
            payload["directly_relevant_nodes"] = payload["directly_relevant_nodes"][:6]
            payload["architecture_summary"] = payload["architecture_summary"][:200]
        return payload

    def get_impact_radius(
        self,
        changed_files: list[str],
        max_depth: int = 3,
        repo_root: str | None = None,
    ) -> dict[str, Any]:
        repo_root = repo_root or str(Path.cwd())
        repo, store = self._resolve_repo(repo_root)
        graph_backend = GraphBackend(store, HybridSearcher(store), ImpactAnalyzer(store))
        status = store.get_status_report(repo.repo_id)
        graph_result = graph_backend.get_impact_radius(
            repo_id=repo.repo_id,
            changed_files=changed_files,
            max_depth=max_depth,
        )
        impact = graph_result.items[0]
        impacted_nodes = impact["impacted_nodes"]
        results = [
            {
                "changed_nodes": [_node_to_dict(n) for n in impact["changed_nodes"]],
                "impacted_nodes": [_node_to_dict(n) for n in impacted_nodes],
                "impacted_files": impact["impacted_files"],
                "edges": [_edge_to_dict(e) for e in impact["edges"]],
                "truncated": impact["truncated"],
                "total_impacted": impact["total_impacted"],
                "risk_summary": impact["risk_summary"],
                "low_confidence_count": impact["low_confidence_count"],
                "stale_count": impact["stale_count"],
                "unindexed_changed_files": impact["unindexed_changed_files"],
            }
        ]
        fallback = None
        warnings: list[str] = []
        unindexed = impact["unindexed_changed_files"]
        if changed_files and (len(unindexed) / len(changed_files)) > 0.3:
            file_backend = FileBackend(Path(repo_root))
            file_hits = file_backend.search("|".join(Path(f).name for f in unindexed), limit=20)
            results.append({"fallback_file_hits": file_hits.items})
            fallback = FallbackType.FILE_EXPLORATION
            warnings.append("More than 30% of changed files are unindexed; fallback file scan attached.")
        return self._build_envelope(
            query_type="impact_radius",
            repo_id=repo.repo_id,
            status=status,
            nodes=impacted_nodes,
            results=results,
            fallback_used=fallback,
            warnings=warnings,
        )

    def semantic_search_nodes(
        self,
        query: str,
        kind: str | None = None,
        limit: int = 20,
        repo_root: str | None = None,
    ) -> dict[str, Any]:
        repo_root = repo_root or str(Path.cwd())
        repo, store = self._resolve_repo(repo_root)
        status = store.get_status_report(repo.repo_id)
        node_kind = NodeKind(kind) if kind else None
        graph_backend = GraphBackend(store, HybridSearcher(store), ImpactAnalyzer(store))
        graph_result = graph_backend.semantic_search_nodes(
            repo_id=repo.repo_id,
            query=query,
            kind=node_kind,
            limit=limit,
        )
        node_hits = [row["node"] for row in graph_result.items]
        low_conf_count = sum(1 for node in node_hits if node.confidence < LOW_CONFIDENCE_THRESHOLD)
        fallback = None
        warnings: list[str] = []
        result_items = [
            {
                **_node_to_dict(row["node"]),
                "score": row["score"],
                "source": row.get("source", "graph"),
            }
            for row in graph_result.items
        ]
        if (not result_items) or (low_conf_count > 0 and len(node_hits) > 0):
            fts_backend = FTSBackend(store)
            fts_result = fts_backend.search(repo.repo_id, query, kind=node_kind, limit=limit)
            if fts_result.items:
                fallback = FallbackType.FTS
                warnings.append("Graph confidence is low; FTS fallback included.")
                for row in fts_result.items:
                    item = _node_to_dict(row["node"])
                    item["score"] = row.get("score", 0.3)
                    item["source"] = row.get("source", "fts")
                    result_items.append(item)
        result_items = result_items[:limit]
        dedup: dict[str, dict[str, Any]] = {}
        for item in result_items:
            dedup[item["qualified_name"]] = item
        merged = list(dedup.values())
        merged.sort(key=lambda i: i.get("score", 0.0), reverse=True)
        merged = merged[:limit]
        merged_nodes = [store.get_node(repo.repo_id, item["qualified_name"]) for item in merged]
        typed_nodes = [n for n in merged_nodes if n is not None]
        return self._build_envelope(
            query_type="semantic_search",
            repo_id=repo.repo_id,
            status=status,
            nodes=typed_nodes,
            results=merged,
            fallback_used=fallback,
            warnings=warnings,
            extra={"has_embeddings": bool(graph_result.extra.get("has_embeddings", False))},
        )

    def query_graph(
        self,
        pattern: str,
        target: str,
        repo_root: str | None = None,
    ) -> dict[str, Any]:
        repo_root = repo_root or str(Path.cwd())
        repo, store = self._resolve_repo(repo_root)
        status = store.get_status_report(repo.repo_id)
        rows = store.query_graph(repo.repo_id, pattern=pattern, target=target, limit=100)
        result_rows: list[dict[str, Any]] = []
        nodes: list[CTSNode] = []
        for row in rows:
            if "node" in row and row["node"] is not None:
                node = row["node"]
                nodes.append(node)
                result_rows.append({"node": _node_to_dict(node)})
            elif "edge" in row:
                edge = row["edge"]
                src = store.get_node(repo.repo_id, edge.source_qualified)
                if src is not None:
                    nodes.append(src)
                result_rows.append({"edge": _edge_to_dict(edge)})
        return self._build_envelope(
            query_type="query_graph",
            repo_id=repo.repo_id,
            status=status,
            nodes=nodes,
            results=result_rows,
        )

    def get_architecture_overview(self, repo_root: str | None = None) -> dict[str, Any]:
        repo_root = repo_root or str(Path.cwd())
        repo, store = self._resolve_repo(repo_root)
        status = store.get_status_report(repo.repo_id)
        overview = store.get_architecture_overview(repo.repo_id, limit=10)
        nodes = store.query_nodes(repo.repo_id, limit=100)
        return self._build_envelope(
            query_type="architecture_overview",
            repo_id=repo.repo_id,
            status=status,
            nodes=nodes,
            results=[overview],
        )

    def detect_changes(
        self,
        base: str = "HEAD~1",
        changed_files: list[str] | None = None,
        repo_root: str | None = None,
    ) -> dict[str, Any]:
        repo_root = repo_root or str(Path.cwd())
        repo, store = self._resolve_repo(repo_root)
        status = store.get_status_report(repo.repo_id)
        if changed_files is None:
            changed_paths = detect_changed_files(Path(repo_root), base=base)
            changed_files = [str(p.resolve().relative_to(Path(repo_root).resolve())) for p in changed_paths]
        analyzer = ImpactAnalyzer(store)
        detection = analyzer.detect_changes(repo_id=repo.repo_id, changed_files=changed_files, base=base)
        impacted_nodes = store.get_impact_radius(repo.repo_id, changed_files, max_depth=2)["impacted_nodes"]
        warnings: list[str] = []
        if detection["low_confidence_estimate"]:
            warnings.append("Risk score includes low-confidence graph segments.")
        if detection["index_coverage_pct"] < 1.0:
            warnings.append("Some changed files are not indexed.")
        return self._build_envelope(
            query_type="detect_changes",
            repo_id=repo.repo_id,
            status=status,
            nodes=impacted_nodes,
            results=[detection],
            warnings=warnings,
        )


def run_stdio_mcp(service: CTSService | None = None) -> None:
    srv = service or CTSService()
    try:
        from fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("FastMCP is required to run CTS MCP server.") from exc

    mcp = FastMCP("aios-cts")

    @mcp.tool()
    def get_minimal_context(
        task: str,
        changed_files: list[str] | None = None,
        repo_root: str | None = None,
        max_tokens: int = 300,
    ) -> dict[str, Any]:
        return srv.get_minimal_context(
            task=task,
            changed_files=changed_files,
            repo_root=repo_root,
            max_tokens=max_tokens,
        )

    @mcp.tool()
    def get_impact_radius(
        changed_files: list[str],
        max_depth: int = 3,
        repo_root: str | None = None,
    ) -> dict[str, Any]:
        return srv.get_impact_radius(changed_files=changed_files, max_depth=max_depth, repo_root=repo_root)

    @mcp.tool()
    def semantic_search_nodes(
        query: str,
        kind: str | None = None,
        limit: int = 20,
        repo_root: str | None = None,
    ) -> dict[str, Any]:
        return srv.semantic_search_nodes(query=query, kind=kind, limit=limit, repo_root=repo_root)

    @mcp.tool()
    def query_graph(pattern: str, target: str, repo_root: str | None = None) -> dict[str, Any]:
        return srv.query_graph(pattern=pattern, target=target, repo_root=repo_root)

    @mcp.tool()
    def get_architecture_overview(repo_root: str | None = None) -> dict[str, Any]:
        return srv.get_architecture_overview(repo_root=repo_root)

    @mcp.tool()
    def detect_changes(
        base: str = "HEAD~1",
        changed_files: list[str] | None = None,
        repo_root: str | None = None,
    ) -> dict[str, Any]:
        return srv.detect_changes(base=base, changed_files=changed_files, repo_root=repo_root)

    mcp.run(transport="stdio")
