from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from services.business.schema import ensure_business_memory_schema
from services.business.wiki.io import page_title_from_markdown, strip_frontmatter


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def ensure_knowledge_graph(conn: sqlite3.Connection) -> None:
    ensure_business_memory_schema(conn)


def upsert_topic(
    conn: sqlite3.Connection,
    *,
    slug: str,
    title: str,
    kind: str,
    summary: str,
    canonical_href: str,
    tags: list[str],
    source_ids: list[str],
) -> str:
    ensure_knowledge_graph(conn)
    topic_id = f"topic-{slug}"
    now = _now_iso()
    metadata = {"source_ids": source_ids}
    existing = conn.execute(
        "SELECT id FROM knowledge_topics WHERE slug = ?",
        (slug,),
    ).fetchone()
    if existing:
        conn.execute(
            """
            UPDATE knowledge_topics
            SET title = ?, kind = ?, summary = ?, canonical_href = ?,
                tags_json = ?, metadata_json = ?, updated_at = ?, confidence = ?
            WHERE slug = ?
            """,
            (
                title,
                kind,
                summary,
                canonical_href,
                json.dumps(tags),
                json.dumps(metadata),
                now,
                min(0.95, 0.55 + 0.1 * len(source_ids)),
                slug,
            ),
        )
        return str(existing[0])

    conn.execute(
        """
        INSERT INTO knowledge_topics (
            id, slug, title, kind, summary, confidence, freshness,
            project_id, canonical_href, tags_json, metadata_json, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?)
        """,
        (
            topic_id,
            slug,
            title,
            kind,
            summary,
            min(0.95, 0.55 + 0.1 * len(source_ids)),
            "Recent",
            canonical_href,
            json.dumps(tags),
            json.dumps(metadata),
            now,
            now,
        ),
    )
    return topic_id


def upsert_reference(
    conn: sqlite3.Connection,
    *,
    topic_id: str,
    source_id: str,
    label: str,
    excerpt: str,
) -> None:
    ref_id = f"ref-{uuid.uuid4()}"
    now = _now_iso()
    conn.execute(
        """
        INSERT INTO knowledge_references (
            id, topic_id, source_kind, source_id, project_id, label, href,
            excerpt, freshness, confidence, metadata_json, created_at
        )
        VALUES (?, ?, 'business_raw', ?, NULL, ?, ?, ?, 'Recent', 0.7, '{}', ?)
        """,
        (
            ref_id,
            topic_id,
            source_id,
            label,
            f"raw://{source_id}",
            excerpt[:500],
            now,
        ),
    )


def index_wiki_page_fts(
    conn: sqlite3.Connection,
    *,
    vault_path: str,
    content: str,
) -> None:
    title = page_title_from_markdown(content, Path(vault_path).stem)
    body = strip_frontmatter(content)
    tags = " ".join(_extract_tags(content))
    conn.execute("DELETE FROM business_wiki_fts WHERE vault_path = ?", (vault_path,))
    conn.execute(
        """
        INSERT INTO business_wiki_fts (vault_path, title, body, tags)
        VALUES (?, ?, ?, ?)
        """,
        (vault_path, title, body, tags),
    )


def _extract_tags(content: str) -> list[str]:
    if not content.startswith("---"):
        return []
    end = content.find("\n---", 3)
    if end == -1:
        return []
    block = content[3:end]
    tags: list[str] = []
    in_tags = False
    for line in block.splitlines():
        if line.strip() == "tags:":
            in_tags = True
            continue
        if in_tags:
            if line.startswith("  - "):
                tags.append(line[4:].strip())
                continue
            break
    return tags


def relative_href(page_type_dir: str, filename: str) -> str:
    return f"staging/business-wiki-candidates/{page_type_dir}/{filename}"
