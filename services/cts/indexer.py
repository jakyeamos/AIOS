from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .incremental import detect_changed_files, git_head
from .models import IndexStatus
from .parser import SUPPORTED_EXTENSIONS, RepoParser
from .registry import CTSRegistry, CTSRepo


@dataclass(slots=True)
class BuildResult:
    repo_id: str
    repo_name: str
    repo_path: str
    node_count: int
    edge_count: int
    parsed_files: int
    total_files: int
    coverage_pct: float
    language_breakdown: dict[str, float]
    failed_files: list[str]
    current_commit: str | None


class CTSIndexer:
    def __init__(self, registry: CTSRegistry | None = None) -> None:
        self.registry = registry or CTSRegistry()

    def full_build(self, repo_path: Path) -> BuildResult:
        repo = self.registry.require_repo_by_path(repo_path)
        store = self.registry.open_store(repo)
        parser = RepoParser(repo.repo_path)
        store.set_repo_status(repo.repo_id, IndexStatus.BUILDING)
        parsed = parser.parse(repo.repo_id)
        parsed.nodes = self._dedupe_nodes(parsed.nodes)
        parsed.edges = self._dedupe_edges(parsed.edges)
        commit = git_head(repo.repo_path)
        store.replace_repo_graph(
            repo_id=repo.repo_id,
            repo_path=str(repo.repo_path),
            repo_name=repo.name,
            current_commit=commit,
            nodes=parsed.nodes,
            edges=parsed.edges,
            coverage_pct=parsed.coverage_pct,
            language_breakdown=parsed.language_breakdown,
        )
        return BuildResult(
            repo_id=repo.repo_id,
            repo_name=repo.name,
            repo_path=str(repo.repo_path),
            node_count=len(parsed.nodes),
            edge_count=len(parsed.edges),
            parsed_files=parsed.parsed_files,
            total_files=parsed.total_files,
            coverage_pct=parsed.coverage_pct,
            language_breakdown=parsed.language_breakdown,
            failed_files=parsed.failed_files,
            current_commit=commit,
        )

    def incremental_update(
        self,
        repo_path: Path,
        changed_files: list[Path] | None = None,
        base: str = "HEAD~1",
    ) -> BuildResult:
        repo = self.registry.require_repo_by_path(repo_path)
        store = self.registry.open_store(repo)
        parser = RepoParser(repo.repo_path)
        if changed_files is None:
            changed_files = detect_changed_files(repo.repo_path, base=base)
        changed_rel = [str(p.resolve().relative_to(repo.repo_path)) for p in changed_files if p.exists()]
        if not changed_rel:
            status = store.get_status_report(repo.repo_id)
            return BuildResult(
                repo_id=repo.repo_id,
                repo_name=repo.name,
                repo_path=str(repo.repo_path),
                node_count=int(status.get("node_count", 0)),
                edge_count=int(status.get("edge_count", 0)),
                parsed_files=0,
                total_files=0,
                coverage_pct=float(status.get("coverage_pct", 0.0)),
                language_breakdown=dict(status.get("language_breakdown", {})),
                failed_files=[],
                current_commit=git_head(repo.repo_path),
            )
        dependent_rel = store.get_dependent_files(repo.repo_id, changed_rel, max_depth=2, cap=500)
        parse_rel = sorted(set(dependent_rel))
        parse_paths = []
        for rel in parse_rel:
            full = (repo.repo_path / rel).resolve()
            if full.exists() and full.suffix in SUPPORTED_EXTENSIONS:
                parse_paths.append(full)
        store.mark_files_stale(repo.repo_id, changed_rel)
        store.set_repo_status(repo.repo_id, IndexStatus.BUILDING)
        parsed = parser.parse(repo.repo_id, files=parse_paths)
        parsed.nodes = self._dedupe_nodes(parsed.nodes)
        parsed.edges = self._dedupe_edges(parsed.edges)
        commit = git_head(repo.repo_path)
        coverage = self._coverage_pct(repo, store, parsed.parsed_files)
        language_breakdown = self._language_breakdown_from_store(store, repo.repo_id)
        store.upsert_files(
            repo_id=repo.repo_id,
            changed_files=parse_rel,
            nodes=parsed.nodes,
            edges=parsed.edges,
            current_commit=commit,
            coverage_pct=coverage,
            language_breakdown=language_breakdown,
        )
        status = store.get_status_report(repo.repo_id)
        return BuildResult(
            repo_id=repo.repo_id,
            repo_name=repo.name,
            repo_path=str(repo.repo_path),
            node_count=int(status.get("node_count", 0)),
            edge_count=int(status.get("edge_count", 0)),
            parsed_files=parsed.parsed_files,
            total_files=len(parse_paths),
            coverage_pct=float(status.get("coverage_pct", 0.0)),
            language_breakdown=dict(status.get("language_breakdown", {})),
            failed_files=parsed.failed_files,
            current_commit=commit,
        )

    @staticmethod
    def _coverage_pct(repo: CTSRepo, store, parsed_files: int) -> float:
        all_supported = len(RepoParser(repo.repo_path).collect_files())
        if all_supported == 0:
            return 0.0
        indexed_files = len(store.get_indexed_files(repo.repo_id))
        if parsed_files == 0 and indexed_files == 0:
            return 0.0
        return indexed_files / all_supported

    @staticmethod
    def _language_breakdown_from_store(store, repo_id: str) -> dict[str, float]:
        rows = store.conn.execute(
            """
            SELECT language, COUNT(*) AS c
            FROM nodes
            WHERE repo_id=? AND kind IN ('File', 'Test')
            GROUP BY language
            """,
            (repo_id,),
        ).fetchall()
        total = sum(int(r["c"]) for r in rows)
        if total == 0:
            return {}
        return {str(r["language"]): int(r["c"]) / total for r in rows}

    @staticmethod
    def _dedupe_nodes(nodes):
        deduped = {}
        for node in nodes:
            deduped[node.qualified_name] = node
        return list(deduped.values())

    @staticmethod
    def _dedupe_edges(edges):
        seen = set()
        deduped = []
        for edge in edges:
            key = (
                edge.kind,
                edge.source_qualified,
                edge.target_qualified,
                edge.file_path,
                edge.line,
                edge.resolution_method,
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(edge)
        return deduped
