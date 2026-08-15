from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from services.business import lint
from services.business.schema import ensure_business_memory_schema


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_business_lint_reports_page_index_source_and_freshness_failures(
    tmp_path: Path, monkeypatch
) -> None:
    wiki = tmp_path / "wiki"
    monkeypatch.setattr(lint, "WIKI_CANDIDATES_ROOT", wiki)
    _write(wiki / "_INDEX.md", "- `courses/indexed.md`\n- `missing.md`\n")
    _write(
        wiki / "courses" / "indexed.md",
        "---\n"
        "type: summary\n"
        "title: Indexed\n"
        "trust: reviewed\n"
        "sensitivity: private\n"
        "source_ids:\n"
        "  - missing-source\n"
        "review-status: reviewed\n"
        "last_reviewed: 2020-01-01\n"
        "---\n"
        "## Evidence\nNo citation.\n"
        "## Links\n[[missing-concept]]\n",
    )
    _write(wiki / "concepts" / "partial.md", "---\ntype: concept\n---\n")
    _write(wiki / "notes" / "plain.md", "No frontmatter.\n")
    _write(
        wiki / "contradictions" / "open-contradiction.md",
        "---\n"
        "type: contradiction\n"
        "title: Open\n"
        "trust: provisional\n"
        "sensitivity: private\n"
        "source_ids:\n"
        "review-status: pending\n"
        "---\n",
    )
    _write(wiki / "a" / "concepts" / "duplicate.md", "No frontmatter.\n")
    _write(wiki / "b" / "concepts" / "duplicate.md", "No frontmatter.\n")

    conn = sqlite3.connect(":memory:")
    ensure_business_memory_schema(conn)
    old = (datetime.now(UTC) - timedelta(days=8)).isoformat()
    conn.execute(
        """
        INSERT INTO memory_raw_sources (
          id, source_type, created_at, updated_at, occurred_at, compiled_at
        ) VALUES (?, ?, ?, ?, ?, NULL)
        """,
        ("stale-source", "manual", old, old, old),
    )

    report = lint.run_business_lint(conn)
    checks = {finding.check for finding in report.critical}
    warning_checks = {finding.check for finding in report.warnings}

    assert {
        "broken_wikilink",
        "duplicate_concept_slug",
        "index_missing_file",
        "invalid_source_id",
        "missing_citations",
        "missing_frontmatter",
        "uncompiled_source",
    } <= checks
    assert {"missing_index_entry", "open_contradiction", "stale_page"} <= warning_checks
    assert report.ok is False
