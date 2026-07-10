from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from services.business.paths import AIOS_ROOT, DB_PATH, WIKI_CANDIDATES_ROOT
from services.business.schema import ensure_business_memory_schema

REQUIRED_FRONTMATTER = {
    "type",
    "title",
    "trust",
    "sensitivity",
    "source_ids",
    "review-status",
}
WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")
SRC_CITE_RE = re.compile(r"\[src:[^\]]+\]")
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
OUTPUT_JSON = AIOS_ROOT / "logs" / "business-lint-latest.json"
LINT_REPORT = WIKI_CANDIDATES_ROOT / "lint-report.md"


@dataclass
class LintFinding:
    severity: str
    check: str
    path: str
    detail: str


@dataclass
class LintReport:
    critical: list[LintFinding] = field(default_factory=list)
    warnings: list[LintFinding] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.critical


def _parse_frontmatter(text: str) -> dict[str, str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip().strip('"')
    return fields


def _parse_source_ids(text: str) -> list[str]:
    if not text.startswith("---"):
        return []
    end = text.find("\n---", 3)
    if end == -1:
        return []
    block = text[3:end]
    ids: list[str] = []
    in_ids = False
    for line in block.splitlines():
        if line.strip() == "source_ids:":
            in_ids = True
            continue
        if in_ids:
            if line.startswith("  - "):
                ids.append(line[4:].strip())
                continue
            break
    return ids


def run_business_lint(conn: sqlite3.Connection) -> LintReport:
    ensure_business_memory_schema(conn)
    report = LintReport()
    if not WIKI_CANDIDATES_ROOT.exists():
        return report

    pages = list(WIKI_CANDIDATES_ROOT.rglob("*.md"))
    pages = [p for p in pages if p.name not in {"_INDEX.md", "log.md", "lint-report.md"}]

    index_text = ""
    index_path = WIKI_CANDIDATES_ROOT / "_INDEX.md"
    if index_path.exists():
        index_text = index_path.read_text(encoding="utf-8")

    concept_slugs: dict[str, str] = {}
    indexed_paths: set[str] = set()
    for line in index_text.splitlines():
        m = re.search(r"`([^`]+\.md)`", line)
        if m:
            indexed_paths.add(m.group(1))

    for path in pages:
        rel = path.relative_to(WIKI_CANDIDATES_ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        fm = _parse_frontmatter(text)

        if path.parent.name == "concepts":
            slug = path.stem
            if slug in concept_slugs:
                report.critical.append(
                    LintFinding("critical", "duplicate_concept_slug", rel, f"duplicate of {concept_slugs[slug]}")
                )
            concept_slugs[slug] = rel

        missing = REQUIRED_FRONTMATTER - set(fm)
        if missing and fm:
            report.critical.append(
                LintFinding("critical", "missing_frontmatter", rel, f"missing: {', '.join(sorted(missing))}")
            )
        elif not fm:
            report.critical.append(LintFinding("critical", "missing_frontmatter", rel, "no YAML frontmatter"))

        if "## Evidence" in text:
            evidence_block = text.split("## Evidence", 1)[1].split("\n##", 1)[0]
            if "summary" in rel or "concept" in rel or "course" in rel:
                if not SRC_CITE_RE.search(evidence_block):
                    report.critical.append(
                        LintFinding("critical", "missing_citations", rel, "Evidence section lacks [src:...]")
                    )

        for source_id in _parse_source_ids(text):
            row = conn.execute("SELECT 1 FROM memory_raw_sources WHERE id = ?", (source_id,)).fetchone()
            if not row:
                report.critical.append(
                    LintFinding("critical", "invalid_source_id", rel, f"unknown source_id {source_id}")
                )

        for link in WIKILINK_RE.findall(text):
            target = link.strip()
            if target.startswith("http"):
                continue
            if "/" not in target:
                candidates = list(WIKI_CANDIDATES_ROOT.rglob(f"{target}.md"))
                if not candidates:
                    report.critical.append(LintFinding("critical", "broken_wikilink", rel, f"unresolved [[{target}]]"))

        if rel not in indexed_paths and path.parent.name != "questions":
            report.warnings.append(LintFinding("warning", "missing_index_entry", rel, "not listed in _INDEX.md"))

        reviewed = fm.get("last_reviewed")
        if reviewed and reviewed not in {"null", ""}:
            try:
                reviewed_date = datetime.fromisoformat(reviewed).date()
                if reviewed_date < (datetime.now(UTC).date() - timedelta(days=90)):
                    report.warnings.append(LintFinding("warning", "stale_page", rel, f"last_reviewed {reviewed}"))
            except ValueError:
                pass

        if fm.get("review-status") == "pending" and "contradiction" in rel:
            report.warnings.append(LintFinding("warning", "open_contradiction", rel, "contradiction still pending"))

    for indexed in indexed_paths:
        if not (WIKI_CANDIDATES_ROOT / indexed).exists():
            report.critical.append(
                LintFinding("critical", "index_missing_file", "_INDEX.md", f"missing file {indexed}")
            )

    cutoff = (datetime.now(UTC) - timedelta(days=7)).isoformat()
    stale = conn.execute(
        """
        SELECT id FROM memory_raw_sources
        WHERE source_type IN ('manual', 'gmail', 'discord', 'x')
          AND compiled_at IS NULL
          AND COALESCE(occurred_at, created_at) < ?
        """,
        (cutoff,),
    ).fetchall()
    for row in stale:
        report.critical.append(
            LintFinding("critical", "uncompiled_source", str(row[0]), "raw source uncompiled >7 days")
        )

    return report


def write_lint_outputs(report: LintReport) -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "ok": report.ok,
        "critical_count": len(report.critical),
        "warning_count": len(report.warnings),
        "critical": [finding.__dict__ for finding in report.critical],
        "warnings": [finding.__dict__ for finding in report.warnings],
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
    }
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Business Wiki Lint Report",
        "",
        f"Generated: {payload['generated_at']}",
        "",
        f"**Critical:** {len(report.critical)} | **Warnings:** {len(report.warnings)}",
        "",
    ]
    if report.critical:
        lines.append("## Critical")
        for finding in report.critical:
            lines.append(f"- `{finding.path}` — **{finding.check}**: {finding.detail}")
        lines.append("")
    if report.warnings:
        lines.append("## Warnings")
        for finding in report.warnings:
            lines.append(f"- `{finding.path}` — **{finding.check}**: {finding.detail}")
        lines.append("")
    if report.ok and not report.warnings:
        lines.append("No issues found.")
    LINT_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def lint_summary_text(report: LintReport) -> str:
    return f"critical={len(report.critical)} warnings={len(report.warnings)} ok={report.ok}"
