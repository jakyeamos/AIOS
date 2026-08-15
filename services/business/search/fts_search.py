from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass


@dataclass
class SearchHit:
    tier: str
    rank: float
    path: str
    title: str
    excerpt: str
    source_id: str | None = None


def _fts_query(text: str) -> str:
    tokens = re.findall(r"[A-Za-z0-9_]+", text.lower())
    tokens = [token for token in tokens if len(token) > 2][:12]
    if not tokens:
        return '""'
    return " OR ".join(tokens)


def _clean_excerpt(text: str) -> str:
    return text.replace(">>", "").replace("<<", "").strip()


def search_sources(conn: sqlite3.Connection, query: str, *, limit: int = 5) -> list[SearchHit]:
    fts_q = _fts_query(query)
    rows = conn.execute(
        """
        SELECT
            source_id,
            subject_or_title,
            snippet(business_sources_fts, 2, '>>', '<<', '…', 24) AS excerpt,
            bm25(business_sources_fts) AS rank
        FROM business_sources_fts
        WHERE business_sources_fts MATCH ?
        ORDER BY rank
        LIMIT ?
        """,
        (fts_q, limit),
    ).fetchall()
    hits: list[SearchHit] = []
    for row in rows:
        hits.append(
            SearchHit(
                tier="source",
                rank=float(row[3]),
                path=f"raw://{row[0]}",
                title=str(row[1] or row[0]),
                excerpt=_clean_excerpt(str(row[2] or "")),
                source_id=str(row[0]),
            )
        )
    return hits


def search_wiki(conn: sqlite3.Connection, query: str, *, limit: int = 5) -> list[SearchHit]:
    fts_q = _fts_query(query)
    rows = conn.execute(
        """
        SELECT
            vault_path,
            title,
            snippet(business_wiki_fts, 2, '>>', '<<', '…', 32) AS excerpt,
            bm25(business_wiki_fts) AS rank
        FROM business_wiki_fts
        WHERE business_wiki_fts MATCH ?
        ORDER BY rank
        LIMIT ?
        """,
        (fts_q, limit),
    ).fetchall()
    hits: list[SearchHit] = []
    for row in rows:
        path = str(row[0])
        rel = (
            path.split("business-wiki-candidates/")[-1]
            if "business-wiki-candidates/" in path
            else path
        )
        hits.append(
            SearchHit(
                tier="wiki",
                rank=float(row[3]),
                path=rel,
                title=str(row[1] or rel),
                excerpt=_clean_excerpt(str(row[2] or "")),
            )
        )
    return hits
