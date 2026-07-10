"""Tiered FTS retrieval for business memory queries."""

from __future__ import annotations

import sqlite3

from services.business.paths import WIKI_CANDIDATES_ROOT
from services.business.search.fts_search import SearchHit, search_sources, search_wiki


def retrieve_context(
    conn: sqlite3.Connection,
    question: str,
    *,
    wiki_limit: int = 5,
    source_limit: int = 5,
) -> list[SearchHit]:
    wiki_hits = search_wiki(conn, question, limit=wiki_limit)
    source_hits = search_sources(conn, question, limit=source_limit)

    if _is_course_question(question):
        course_path = WIKI_CANDIDATES_ROOT / "courses" / "agent-wiki-course.md"
        if course_path.exists():
            text = course_path.read_text(encoding="utf-8")
            title = "Agent Wiki Course"
            for line in text.splitlines():
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
            wiki_hits = [
                SearchHit(
                    tier="wiki",
                    rank=-1.0,
                    path="courses/agent-wiki-course.md",
                    title=title,
                    excerpt=_excerpt(text, 400),
                ),
                *[hit for hit in wiki_hits if hit.path != "courses/agent-wiki-course.md"],
            ]

    return wiki_hits + source_hits


def _is_course_question(question: str) -> bool:
    lower = question.lower()
    keywords = (
        "course",
        "cohort",
        "module",
        "section",
        "talking point",
        "curriculum",
        "lesson",
    )
    return any(keyword in lower for keyword in keywords)


def _excerpt(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "…"
