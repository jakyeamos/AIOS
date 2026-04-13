from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .migrations import apply_migrations
from .models import (
    CTSEdge,
    CTSNode,
    EdgeKind,
    ExtractionMethod,
    IndexStatus,
    NodeKind,
    ResolutionMethod,
)


def utcnow_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _in_placeholders(items: Sequence[Any]) -> str:
    return ",".join("?" for _ in items)


def _row_to_node(row: sqlite3.Row) -> CTSNode:
    try:
        extraction_method = ExtractionMethod(str(row["extraction_method"]))
    except ValueError:
        extraction_method = ExtractionMethod.INFERRED
    return CTSNode(
        id=row["id"],
        repo_id=row["repo_id"],
        kind=NodeKind(row["kind"]),
        name=row["name"],
        qualified_name=row["qualified_name"],
        file_path=row["file_path"],
        line_start=int(row["line_start"]),
        line_end=int(row["line_end"]),
        language=row["language"],
        parent_qualified=row["parent_qualified"],
        params=row["params"],
        return_type=row["return_type"],
        modifiers=json.loads(row["modifiers"] or "[]"),
        is_test=bool(row["is_test"]),
        file_hash=row["file_hash"],
        confidence=float(row["confidence"]),
        extraction_method=extraction_method,
        last_verified_at=row["last_verified_at"],
        is_stale=bool(row["is_stale"]),
        unresolved_call_count=int(row["unresolved_call_count"]),
        extra=json.loads(row["extra"] or "{}"),
        updated_at=row["updated_at"],
    )


def _row_to_edge(row: sqlite3.Row) -> CTSEdge:
    try:
        resolution_method = ResolutionMethod(str(row["resolution_method"]))
    except ValueError:
        resolution_method = ResolutionMethod.INFERRED
    try:
        extraction_method = ExtractionMethod(str(row["extraction_method"]))
    except ValueError:
        extraction_method = ExtractionMethod.INFERRED
    return CTSEdge(
        id=row["id"],
        repo_id=row["repo_id"],
        kind=EdgeKind(row["kind"]),
        source_qualified=row["source_qualified"],
        target_qualified=row["target_qualified"],
        file_path=row["file_path"],
        line=int(row["line"]),
        confidence=float(row["confidence"]),
        resolution_method=resolution_method,
        extraction_method=extraction_method,
        last_verified_at=row["last_verified_at"],
        is_stale=bool(row["is_stale"]),
        extra=json.loads(row["extra"] or "{}"),
        updated_at=row["updated_at"],
    )


class GraphStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, timeout=30)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA busy_timeout=10000")
        apply_migrations(self.conn)

    def close(self) -> None:
        self.conn.close()

    def ensure_repo(self, repo_id: str, repo_path: str, name: str) -> None:
        now = utcnow_iso()
        self.conn.execute(
            """
            INSERT INTO repos (repo_id, repo_path, name, index_status, index_updated_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(repo_id) DO UPDATE SET
                repo_path=excluded.repo_path,
                name=excluded.name,
                updated_at=excluded.updated_at
            """,
            (repo_id, repo_path, name, IndexStatus.EMPTY.value, now, now),
        )
        self.conn.commit()

    def set_repo_status(self, repo_id: str, status: IndexStatus) -> None:
        now = utcnow_iso()
        self.conn.execute(
            "UPDATE repos SET index_status=?, updated_at=? WHERE repo_id=?",
            (status.value, now, repo_id),
        )
        self.conn.commit()

    def get_repo_meta(self, repo_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM repos WHERE repo_id=?", (repo_id,)).fetchone()
        if row is None:
            return None
        return dict(row)

    def replace_repo_graph(
        self,
        repo_id: str,
        repo_path: str,
        repo_name: str,
        current_commit: str | None,
        nodes: list[CTSNode],
        edges: list[CTSEdge],
        coverage_pct: float,
        language_breakdown: dict[str, float],
    ) -> None:
        now = utcnow_iso()
        self.conn.execute("BEGIN")
        self.conn.execute("DELETE FROM edges WHERE repo_id=?", (repo_id,))
        self.conn.execute("DELETE FROM nodes WHERE repo_id=?", (repo_id,))
        self.conn.execute("DELETE FROM nodes_fts WHERE repo_id=?", (repo_id,))
        self._insert_nodes(nodes)
        self._insert_edges(edges)
        self._rebuild_fts(repo_id)
        self.conn.execute(
            """
            INSERT INTO repos (
                repo_id, repo_path, name, current_commit, last_full_build_at,
                index_status, coverage_pct, node_count, edge_count, language_breakdown,
                index_updated_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(repo_id) DO UPDATE SET
                repo_path=excluded.repo_path,
                name=excluded.name,
                current_commit=excluded.current_commit,
                last_full_build_at=excluded.last_full_build_at,
                index_status=excluded.index_status,
                coverage_pct=excluded.coverage_pct,
                node_count=excluded.node_count,
                edge_count=excluded.edge_count,
                language_breakdown=excluded.language_breakdown,
                index_updated_at=excluded.index_updated_at,
                updated_at=excluded.updated_at
            """,
            (
                repo_id,
                repo_path,
                repo_name,
                current_commit,
                now,
                IndexStatus.CURRENT.value,
                coverage_pct,
                len(nodes),
                len(edges),
                json.dumps(language_breakdown, sort_keys=True),
                now,
                now,
            ),
        )
        self.conn.commit()

    def upsert_files(
        self,
        repo_id: str,
        changed_files: list[str],
        nodes: list[CTSNode],
        edges: list[CTSEdge],
        current_commit: str | None,
        coverage_pct: float | None = None,
        language_breakdown: dict[str, float] | None = None,
    ) -> None:
        if not changed_files:
            return
        placeholders = _in_placeholders(changed_files)
        now = utcnow_iso()
        self.conn.execute("BEGIN")
        self.conn.execute(
            f"DELETE FROM edges WHERE repo_id=? AND file_path IN ({placeholders})",
            [repo_id, *changed_files],
        )
        self.conn.execute(
            f"DELETE FROM nodes WHERE repo_id=? AND file_path IN ({placeholders})",
            [repo_id, *changed_files],
        )
        self.conn.execute(
            f"DELETE FROM nodes_fts WHERE repo_id=? AND file_path IN ({placeholders})",
            [repo_id, *changed_files],
        )
        self._insert_nodes(nodes)
        self._insert_edges(edges)
        self._rebuild_fts(repo_id)
        counts = self.conn.execute(
            "SELECT COUNT(*) AS node_count FROM nodes WHERE repo_id=?",
            (repo_id,),
        ).fetchone()
        edge_counts = self.conn.execute(
            "SELECT COUNT(*) AS edge_count FROM edges WHERE repo_id=?",
            (repo_id,),
        ).fetchone()
        self.conn.execute(
            """
            UPDATE repos
            SET current_commit=?,
                last_incremental_at=?,
                index_status=?,
                coverage_pct=COALESCE(?, coverage_pct),
                node_count=?,
                edge_count=?,
                language_breakdown=COALESCE(?, language_breakdown),
                index_updated_at=?,
                updated_at=?
            WHERE repo_id=?
            """,
            (
                current_commit,
                now,
                IndexStatus.CURRENT.value,
                coverage_pct,
                int(counts["node_count"]) if counts else 0,
                int(edge_counts["edge_count"]) if edge_counts else 0,
                json.dumps(language_breakdown, sort_keys=True) if language_breakdown else None,
                now,
                now,
                repo_id,
            ),
        )
        self.conn.commit()

    def mark_files_stale(self, repo_id: str, file_paths: list[str]) -> None:
        if not file_paths:
            return
        placeholders = _in_placeholders(file_paths)
        now = utcnow_iso()
        self.conn.execute(
            f"UPDATE nodes SET is_stale=1, updated_at=? WHERE repo_id=? AND file_path IN ({placeholders})",
            [now, repo_id, *file_paths],
        )
        self.conn.execute(
            f"UPDATE edges SET is_stale=1, updated_at=? WHERE repo_id=? AND file_path IN ({placeholders})",
            [now, repo_id, *file_paths],
        )
        self.conn.execute(
            "UPDATE repos SET index_status=?, updated_at=? WHERE repo_id=?",
            (IndexStatus.NEEDS_UPDATE.value, now, repo_id),
        )
        self.conn.commit()

    def mark_nodes_stale(self, repo_id: str, qualified_names: list[str]) -> None:
        if not qualified_names:
            return
        placeholders = _in_placeholders(qualified_names)
        now = utcnow_iso()
        self.conn.execute(
            f"UPDATE nodes SET is_stale=1, updated_at=? WHERE repo_id=? AND qualified_name IN ({placeholders})",
            [now, repo_id, *qualified_names],
        )
        self.conn.execute(
            f"""
            UPDATE edges
            SET is_stale=1, updated_at=?
            WHERE repo_id=? AND (
                source_qualified IN ({placeholders}) OR target_qualified IN ({placeholders})
            )
            """,
            [now, repo_id, *qualified_names, *qualified_names],
        )
        self.conn.commit()

    def _insert_nodes(self, nodes: list[CTSNode]) -> None:
        if not nodes:
            return
        rows = [
            (
                n.id,
                n.repo_id,
                n.kind.value if isinstance(n.kind, NodeKind) else n.kind,
                n.name,
                n.qualified_name,
                n.file_path,
                n.line_start,
                n.line_end,
                n.language,
                n.parent_qualified,
                n.params,
                n.return_type,
                json.dumps(n.modifiers),
                1 if n.is_test else 0,
                n.file_hash,
                n.confidence,
                n.extraction_method,
                n.last_verified_at,
                1 if n.is_stale else 0,
                n.unresolved_call_count,
                json.dumps(n.extra or {}, sort_keys=True),
                n.updated_at or utcnow_iso(),
            )
            for n in nodes
        ]
        self.conn.executemany(
            """
            INSERT INTO nodes (
                id, repo_id, kind, name, qualified_name, file_path, line_start, line_end,
                language, parent_qualified, params, return_type, modifiers, is_test,
                file_hash, confidence, extraction_method, last_verified_at, is_stale,
                unresolved_call_count, extra, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

    def _insert_edges(self, edges: list[CTSEdge]) -> None:
        if not edges:
            return
        rows = [
            (
                e.id,
                e.repo_id,
                e.kind.value if isinstance(e.kind, EdgeKind) else e.kind,
                e.source_qualified,
                e.target_qualified,
                e.file_path,
                e.line,
                e.confidence,
                e.resolution_method,
                e.extraction_method,
                e.last_verified_at,
                1 if e.is_stale else 0,
                json.dumps(e.extra or {}, sort_keys=True),
                e.updated_at or utcnow_iso(),
            )
            for e in edges
        ]
        self.conn.executemany(
            """
            INSERT INTO edges (
                id, repo_id, kind, source_qualified, target_qualified, file_path, line,
                confidence, resolution_method, extraction_method, last_verified_at,
                is_stale, extra, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

    def _rebuild_fts(self, repo_id: str) -> None:
        self.conn.execute("DELETE FROM nodes_fts WHERE repo_id=?", (repo_id,))
        rows = self.conn.execute(
            """
            SELECT repo_id, qualified_name, name, kind, file_path,
                   COALESCE(name, '') || ' ' || COALESCE(qualified_name, '') || ' ' || COALESCE(file_path, '') AS content
            FROM nodes WHERE repo_id=?
            """,
            (repo_id,),
        ).fetchall()
        self.conn.executemany(
            """
            INSERT INTO nodes_fts (repo_id, qualified_name, name, kind, file_path, content)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

    def get_nodes_for_files(self, repo_id: str, file_paths: list[str]) -> list[CTSNode]:
        if not file_paths:
            return []
        placeholders = _in_placeholders(file_paths)
        rows = self.conn.execute(
            f"SELECT * FROM nodes WHERE repo_id=? AND file_path IN ({placeholders})",
            [repo_id, *file_paths],
        ).fetchall()
        return [_row_to_node(r) for r in rows]

    def get_node(self, repo_id: str, qualified_name: str) -> CTSNode | None:
        row = self.conn.execute(
            "SELECT * FROM nodes WHERE repo_id=? AND qualified_name=? LIMIT 1",
            (repo_id, qualified_name),
        ).fetchone()
        if row is None:
            return None
        return _row_to_node(row)

    def query_nodes(
        self,
        repo_id: str,
        kind: NodeKind | None = None,
        limit: int = 50,
    ) -> list[CTSNode]:
        if kind:
            rows = self.conn.execute(
                """
                SELECT * FROM nodes
                WHERE repo_id=? AND kind=?
                ORDER BY confidence DESC, unresolved_call_count ASC
                LIMIT ?
                """,
                (repo_id, kind.value, limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                """
                SELECT * FROM nodes
                WHERE repo_id=?
                ORDER BY confidence DESC, unresolved_call_count ASC
                LIMIT ?
                """,
                (repo_id, limit),
            ).fetchall()
        return [_row_to_node(r) for r in rows]

    def search_fts(
        self,
        repo_id: str,
        query: str,
        kind: NodeKind | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT n.*, bm25(nodes_fts) AS rank
            FROM nodes_fts
            JOIN nodes n
              ON n.repo_id = nodes_fts.repo_id
             AND n.qualified_name = nodes_fts.qualified_name
            WHERE nodes_fts.repo_id = ?
              AND nodes_fts MATCH ?
        """
        params: list[Any] = [repo_id, query]
        if kind:
            sql += " AND n.kind = ?"
            params.append(kind.value)
        sql += " ORDER BY rank LIMIT ?"
        params.append(limit)
        rows = self.conn.execute(sql, params).fetchall()
        results: list[dict[str, Any]] = []
        for row in rows:
            score = 1.0 / (1.0 + abs(float(row["rank"])))
            results.append({"node": _row_to_node(row), "score": score, "source": "fts"})
        return results

    def search_like(
        self,
        repo_id: str,
        query: str,
        kind: NodeKind | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        needle = f"%{query.lower()}%"
        if kind:
            rows = self.conn.execute(
                """
                SELECT * FROM nodes
                WHERE repo_id=? AND kind=? AND (
                    LOWER(name) LIKE ? OR LOWER(qualified_name) LIKE ? OR LOWER(file_path) LIKE ?
                )
                ORDER BY confidence DESC
                LIMIT ?
                """,
                (repo_id, kind.value, needle, needle, needle, limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                """
                SELECT * FROM nodes
                WHERE repo_id=? AND (
                    LOWER(name) LIKE ? OR LOWER(qualified_name) LIKE ? OR LOWER(file_path) LIKE ?
                )
                ORDER BY confidence DESC
                LIMIT ?
                """,
                (repo_id, needle, needle, needle, limit),
            ).fetchall()
        results: list[dict[str, Any]] = []
        for row in rows:
            results.append({"node": _row_to_node(row), "score": 0.35, "source": "like"})
        return results

    def get_dependent_files(
        self,
        repo_id: str,
        changed_files: list[str],
        max_depth: int = 2,
        cap: int = 500,
    ) -> list[str]:
        seed_nodes = self.get_nodes_for_files(repo_id, changed_files)
        frontier = {n.qualified_name for n in seed_nodes}
        visited = set(frontier)
        dependent_files = set(changed_files)
        depth = 0
        while frontier and depth < max_depth and len(dependent_files) < cap:
            placeholders = _in_placeholders(list(frontier))
            rows = self.conn.execute(
                f"""
                SELECT source_qualified, target_qualified
                FROM edges
                WHERE repo_id=?
                  AND (source_qualified IN ({placeholders}) OR target_qualified IN ({placeholders}))
                """,
                [repo_id, *frontier, *frontier],
            ).fetchall()
            next_frontier: set[str] = set()
            for row in rows:
                source = row["source_qualified"]
                target = row["target_qualified"]
                if source in frontier and target not in visited:
                    next_frontier.add(target)
                if target in frontier and source not in visited:
                    next_frontier.add(source)
            if not next_frontier:
                break
            visited |= next_frontier
            placeholders = _in_placeholders(list(next_frontier))
            file_rows = self.conn.execute(
                f"""
                SELECT DISTINCT file_path
                FROM nodes
                WHERE repo_id=? AND qualified_name IN ({placeholders})
                LIMIT ?
                """,
                [repo_id, *next_frontier, cap],
            ).fetchall()
            dependent_files |= {r["file_path"] for r in file_rows}
            frontier = next_frontier
            depth += 1
        return sorted(dependent_files)[:cap]

    def get_impact_radius(
        self,
        repo_id: str,
        changed_files: list[str],
        max_depth: int = 3,
        cap: int = 2000,
    ) -> dict[str, Any]:
        changed_nodes = self.get_nodes_for_files(repo_id, changed_files)
        changed_qnames = {n.qualified_name for n in changed_nodes}
        visited = set(changed_qnames)
        frontier = set(changed_qnames)
        depth = 0
        truncated = False
        while frontier and depth < max_depth:
            placeholders = _in_placeholders(list(frontier))
            rows = self.conn.execute(
                f"""
                SELECT source_qualified, target_qualified
                FROM edges
                WHERE repo_id=?
                  AND (source_qualified IN ({placeholders}) OR target_qualified IN ({placeholders}))
                """,
                [repo_id, *frontier, *frontier],
            ).fetchall()
            next_frontier: set[str] = set()
            for row in rows:
                a = row["source_qualified"]
                b = row["target_qualified"]
                if a in frontier and b not in visited:
                    next_frontier.add(b)
                if b in frontier and a not in visited:
                    next_frontier.add(a)
            if not next_frontier:
                break
            visited |= next_frontier
            if len(visited) > cap:
                truncated = True
                break
            frontier = next_frontier
            depth += 1
        if not visited:
            return {
                "changed_nodes": [],
                "impacted_nodes": [],
                "impacted_files": [],
                "edges": [],
                "truncated": False,
                "total_impacted": 0,
            }
        placeholders = _in_placeholders(list(visited))
        node_rows = self.conn.execute(
            f"""
            SELECT * FROM nodes
            WHERE repo_id=? AND qualified_name IN ({placeholders})
            """,
            [repo_id, *visited],
        ).fetchall()
        impacted_nodes = [_row_to_node(r) for r in node_rows]
        impacted_files = sorted({n.file_path for n in impacted_nodes})
        edge_rows = self.conn.execute(
            f"""
            SELECT * FROM edges
            WHERE repo_id=?
              AND source_qualified IN ({placeholders})
              AND target_qualified IN ({placeholders})
            """,
            [repo_id, *visited, *visited],
        ).fetchall()
        edges = [_row_to_edge(r) for r in edge_rows]
        return {
            "changed_nodes": changed_nodes,
            "impacted_nodes": impacted_nodes,
            "impacted_files": impacted_files,
            "edges": edges,
            "truncated": truncated,
            "total_impacted": len(impacted_nodes),
        }

    def get_indexed_files(self, repo_id: str) -> set[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT file_path FROM nodes WHERE repo_id=?",
            (repo_id,),
        ).fetchall()
        return {r["file_path"] for r in rows}

    def get_unindexed_files(self, repo_id: str, file_paths: Iterable[str]) -> list[str]:
        indexed = self.get_indexed_files(repo_id)
        return [f for f in file_paths if f not in indexed]

    def query_graph(
        self,
        repo_id: str,
        pattern: str,
        target: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        pattern_norm = pattern.strip().lower()
        if pattern_norm in {"callers", "called_by"}:
            rows = self.conn.execute(
                """
                SELECT * FROM edges
                WHERE repo_id=? AND kind='CALLS' AND target_qualified=?
                LIMIT ?
                """,
                (repo_id, target, limit),
            ).fetchall()
            return [{"edge": _row_to_edge(r)} for r in rows]
        if pattern_norm in {"callees", "calls"}:
            rows = self.conn.execute(
                """
                SELECT * FROM edges
                WHERE repo_id=? AND kind='CALLS' AND source_qualified=?
                LIMIT ?
                """,
                (repo_id, target, limit),
            ).fetchall()
            return [{"edge": _row_to_edge(r)} for r in rows]
        if pattern_norm in {"imports", "imports_from"}:
            rows = self.conn.execute(
                """
                SELECT * FROM edges
                WHERE repo_id=? AND kind='IMPORTS_FROM' AND source_qualified=?
                LIMIT ?
                """,
                (repo_id, target, limit),
            ).fetchall()
            return [{"edge": _row_to_edge(r)} for r in rows]
        node = self.get_node(repo_id, target)
        return [{"node": node}] if node else []

    def get_architecture_overview(self, repo_id: str, limit: int = 8) -> dict[str, Any]:
        file_rows = self.conn.execute(
            """
            SELECT file_path, COUNT(*) AS node_count
            FROM nodes
            WHERE repo_id=?
            GROUP BY file_path
            ORDER BY node_count DESC
            LIMIT ?
            """,
            (repo_id, limit),
        ).fetchall()
        language_rows = self.conn.execute(
            """
            SELECT language, COUNT(*) AS count
            FROM nodes
            WHERE repo_id=?
            GROUP BY language
            ORDER BY count DESC
            """,
            (repo_id,),
        ).fetchall()
        coupling_rows = self.conn.execute(
            """
            SELECT source_qualified, COUNT(*) AS out_degree
            FROM edges
            WHERE repo_id=? AND kind='CALLS'
            GROUP BY source_qualified
            ORDER BY out_degree DESC
            LIMIT ?
            """,
            (repo_id, limit),
        ).fetchall()
        return {
            "top_files": [dict(r) for r in file_rows],
            "language_breakdown": {r["language"]: r["count"] for r in language_rows},
            "hot_callers": [dict(r) for r in coupling_rows],
        }

    def index_age_seconds(self, repo_id: str) -> int:
        row = self.conn.execute(
            "SELECT index_updated_at FROM repos WHERE repo_id=?",
            (repo_id,),
        ).fetchone()
        if not row or not row["index_updated_at"]:
            return 0
        ts = datetime.fromisoformat(str(row["index_updated_at"]).replace("Z", "+00:00"))
        return max(0, int((datetime.now(UTC) - ts).total_seconds()))

    def list_file_hashes(self, repo_id: str) -> dict[str, str]:
        rows = self.conn.execute(
            """
            SELECT file_path, file_hash
            FROM nodes
            WHERE repo_id=? AND kind='File'
            """,
            (repo_id,),
        ).fetchall()
        return {r["file_path"]: r["file_hash"] for r in rows}

    def get_status_report(self, repo_id: str) -> dict[str, Any]:
        repo = self.get_repo_meta(repo_id)
        if repo is None:
            return {"repo_id": repo_id, "exists": False}
        stale_nodes = self.conn.execute(
            "SELECT COUNT(*) AS c FROM nodes WHERE repo_id=? AND is_stale=1",
            (repo_id,),
        ).fetchone()
        low_conf_nodes = self.conn.execute(
            "SELECT COUNT(*) AS c FROM nodes WHERE repo_id=? AND confidence < 0.6",
            (repo_id,),
        ).fetchone()
        return {
            "repo_id": repo_id,
            "exists": True,
            "repo_path": repo["repo_path"],
            "name": repo["name"],
            "current_commit": repo["current_commit"],
            "last_full_build_at": repo["last_full_build_at"],
            "last_incremental_at": repo["last_incremental_at"],
            "index_status": repo["index_status"],
            "coverage_pct": repo["coverage_pct"],
            "node_count": repo["node_count"],
            "edge_count": repo["edge_count"],
            "language_breakdown": json.loads(repo["language_breakdown"] or "{}"),
            "index_age_seconds": self.index_age_seconds(repo_id),
            "stale_nodes": int(stale_nodes["c"]) if stale_nodes else 0,
            "low_confidence_nodes": int(low_conf_nodes["c"]) if low_conf_nodes else 0,
            "db_path": str(self.db_path),
            "db_size_bytes": self.db_path.stat().st_size if self.db_path.exists() else 0,
        }

    def get_unresolved_call_count_for_files(self, repo_id: str, file_paths: list[str]) -> int:
        if not file_paths:
            return 0
        placeholders = _in_placeholders(file_paths)
        row = self.conn.execute(
            f"""
            SELECT COALESCE(SUM(unresolved_call_count), 0) AS c
            FROM nodes
            WHERE repo_id=? AND kind='File' AND file_path IN ({placeholders})
            """,
            [repo_id, *file_paths],
        ).fetchone()
        return int(row["c"]) if row else 0

    def get_files_summary(self, repo_id: str) -> dict[str, dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT file_path, MAX(unresolved_call_count) AS unresolved,
                   MAX(is_stale) AS is_stale, COUNT(*) AS node_count
            FROM nodes
            WHERE repo_id=?
            GROUP BY file_path
            """,
            (repo_id,),
        ).fetchall()
        summary: dict[str, dict[str, Any]] = defaultdict(dict)
        for row in rows:
            summary[row["file_path"]] = {
                "unresolved_call_count": int(row["unresolved"]),
                "is_stale": bool(row["is_stale"]),
                "node_count": int(row["node_count"]),
            }
        return summary
