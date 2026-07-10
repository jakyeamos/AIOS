from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from services.business.paths import WIKI_CANDIDATES_ROOT


def append_compile_log(
    *,
    run_id: str,
    sources_processed: int,
    pages_created: int,
    pages_updated: int,
) -> Path:
    log_path = WIKI_CANDIDATES_ROOT / "log.md"
    if not log_path.exists():
        log_path.write_text("# Business Memory Compile Log\n\n", encoding="utf-8")
    timestamp = datetime.now(UTC).replace(microsecond=0).isoformat()
    entry = (
        f"- {timestamp} run `{run_id}` processed {sources_processed} sources; "
        f"created {pages_created} pages; updated {pages_updated} pages.\n"
    )
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(entry)
    return log_path


def rebuild_index(candidate_root: Path | None = None) -> Path:
    root = candidate_root or WIKI_CANDIDATES_ROOT
    rows: list[tuple[str, str, str, str]] = []
    for subdir in (
        "summaries",
        "concepts",
        "courses",
        "questions",
        "decisions",
        "contradictions",
    ):
        folder = root / subdir
        if not folder.exists():
            continue
        for path in sorted(folder.glob("*.md")):
            page_type = f"business-{subdir[:-1] if subdir.endswith('s') else subdir}"
            title = _title_from_file(path)
            rel = f"{subdir}/{path.name}"
            review = _review_status(path)
            rows.append((page_type, title, rel, review))

    lines = [
        "---",
        "type: business-index",
        "status: draft",
        "quality: agent-generated",
        "trust: working",
        "area: business",
        "---",
        "",
        "# Business Wiki Candidate Index",
        "",
        "| Type | Title | Path | Review |",
        "| --- | --- | --- | --- |",
    ]
    for page_type, title, rel, review in rows:
        lines.append(f"| {page_type} | {title} | `{rel}` | {review} |")
    if not rows:
        lines.append("| — | — | — | — |")
    lines.append("")

    index_path = root / "_INDEX.md"
    index_path.write_text("\n".join(lines), encoding="utf-8")
    return index_path


def _title_from_file(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem


def _review_status(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("review-status:"):
            return line.split(":", 1)[1].strip().strip('"')
    return "pending"
