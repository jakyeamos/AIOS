from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from .indexer import CTSIndexer
from .mcp_server import CTSService
from .registry import CTSRegistry

_registry = CTSRegistry()
_service = CTSService(registry=_registry)
_indexer = CTSIndexer(registry=_registry)


def full_build(repo_path: str | Path) -> dict[str, Any]:
    result = _indexer.full_build(Path(repo_path))
    return asdict(result)


def incremental_update(
    repo_path: str | Path,
    changed_files: list[str] | None = None,
    base: str = "HEAD~1",
) -> dict[str, Any]:
    paths = [Path(repo_path) / f for f in changed_files] if changed_files else None
    result = _indexer.incremental_update(Path(repo_path), changed_files=paths, base=base)
    return asdict(result)


def get_minimal_context(
    repo_path: str | Path,
    task: str,
    changed_files: list[str] | None = None,
    max_tokens: int = 300,
) -> dict[str, Any]:
    return _service.get_minimal_context(
        task=task,
        changed_files=changed_files,
        repo_root=str(Path(repo_path)),
        max_tokens=max_tokens,
    )


def get_impact_radius(
    repo_path: str | Path,
    changed_files: list[str],
    max_depth: int = 3,
) -> dict[str, Any]:
    return _service.get_impact_radius(
        changed_files=changed_files,
        max_depth=max_depth,
        repo_root=str(Path(repo_path)),
    )


def semantic_search_nodes(
    repo_path: str | Path,
    query: str,
    kind: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    return _service.semantic_search_nodes(
        query=query,
        kind=kind,
        limit=limit,
        repo_root=str(Path(repo_path)),
    )


def query_graph(
    repo_path: str | Path,
    pattern: str,
    target: str,
) -> dict[str, Any]:
    return _service.query_graph(pattern=pattern, target=target, repo_root=str(Path(repo_path)))


def get_architecture_overview(repo_path: str | Path) -> dict[str, Any]:
    return _service.get_architecture_overview(repo_root=str(Path(repo_path)))


def detect_changes(
    repo_path: str | Path,
    base: str = "HEAD~1",
    changed_files: list[str] | None = None,
) -> dict[str, Any]:
    return _service.detect_changes(
        base=base,
        changed_files=changed_files,
        repo_root=str(Path(repo_path)),
    )


__all__ = [
    "CTSIndexer",
    "CTSRegistry",
    "full_build",
    "incremental_update",
    "get_minimal_context",
    "get_impact_radius",
    "semantic_search_nodes",
    "query_graph",
    "get_architecture_overview",
    "detect_changes",
]
