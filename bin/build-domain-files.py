#!/usr/bin/env python3
"""
AIOS: build-domain-files.py
Generate Domains/<domain>/rules.md, hypotheses.md, knowledge.md from SQLite.

Run weekly (or on-demand after approving/confirming patterns).
Regenerates everything above <!-- END AUTO-GENERATED --> and preserves
any human annotations below that marker.

Usage:
  python3 build-domain-files.py [--domain <name>] [--dry-run]
"""

import argparse
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

DB = os.path.expanduser("~/AIOS/data/aios.db")
DOMAINS_DIR = os.path.expanduser("~/Vaults/Command-Center/06 Knowledge/Domains")

DOMAINS = ["debugging", "prompting", "architecture", "workflow", "system"]

END_MARKER = "<!-- END AUTO-GENERATED -->"
BEGIN_MARKER = "<!-- AUTO-GENERATED: do not edit above this line -->"


def load_human_annotations(existing_path: Path) -> str:
    """Return everything after END_MARKER in an existing file, or empty string."""
    if not existing_path.exists():
        return ""
    text = existing_path.read_text(encoding="utf-8")
    if END_MARKER in text:
        after = text.split(END_MARKER, 1)[1]
        # Strip leading newlines but preserve intentional content
        return after.rstrip()
    return ""


def format_pattern_block(row: dict) -> str:
    body = row["body"] or "_No description yet. Fill in via review-observations.py._"
    confirmed = row["confirmation_count"] or 0
    conf = row["confidence"] or 0.5
    last = row["last_confirmed_at"] or "never"
    source = row["source_type"] or "bigram"
    return (
        f"## {row['title']}\n\n"
        f"{body}\n\n"
        f"**Confidence:** {conf:.2f} | **Confirmed:** {confirmed}× | "
        f"**Last:** {last} | **Source:** {source}\n\n"
        "---\n"
    )


def build_rules_md(domain: str, rows: list[dict]) -> str:
    now = datetime.now(UTC).isoformat()
    count = len(rows)
    lines = [
        BEGIN_MARKER,
        "",
        "---",
        f"domain: {domain}",
        f"generated: {now}",
        f"rule_count: {count}",
        "---",
        "",
        f"# {domain.capitalize()} Rules",
        "",
        "_Auto-generated from aios.db. Edit via approve-pattern.py / contradict-pattern.py._",
        "",
    ]
    if not rows:
        lines.append("_No approved rules yet for this domain._\n")
    else:
        for row in rows:
            lines.append(format_pattern_block(row))
    lines.append(END_MARKER)
    return "\n".join(lines)


def build_hypotheses_md(domain: str, rows: list[dict]) -> str:
    now = datetime.now(UTC).isoformat()
    count = len(rows)

    # Compute class thresholds for confirmations_needed display
    class_thresholds = {
        "bug_fix": 2, "failure": 2,
        "architecture": 3, "workflow": 3, "assumption": 3,
        "prompt": 4,
    }

    lines = [
        BEGIN_MARKER,
        "",
        "---",
        f"domain: {domain}",
        f"generated: {now}",
        f"hypothesis_count: {count}",
        "---",
        "",
        f"# {domain.capitalize()} Hypotheses",
        "",
        "_Patterns under testing. Confirm with confirm-pattern.py, contradict with contradict-pattern.py._",
        "",
    ]
    if not rows:
        lines.append("_No active hypotheses for this domain._\n")
    else:
        for row in rows:
            confirmed = row["confirmation_count"] or 0
            threshold = class_thresholds.get(row["class"] or "", 3)
            needed = max(0, threshold - confirmed)
            body = row["body"] or "_No description yet._"
            lines.append(
                f"## {row['title']}\n\n"
                f"{body}\n\n"
                f"**Progress:** {confirmed}/{threshold} confirmations ({needed} needed) | "
                f"**Confidence:** {(row['confidence'] or 0.5):.2f}\n\n"
                "---\n"
            )
    lines.append(END_MARKER)
    return "\n".join(lines)


def build_knowledge_md(domain: str, rows: list[dict]) -> str:
    now = datetime.now(UTC).isoformat()
    count = len(rows)
    lines = [
        BEGIN_MARKER,
        "",
        "---",
        f"domain: {domain}",
        f"generated: {now}",
        f"knowledge_count: {count}",
        "---",
        "",
        f"# {domain.capitalize()} Knowledge",
        "",
        "_Confirmed facts not yet promoted to rules. Review with review-observations.py._",
        "",
    ]
    if not rows:
        lines.append("_No knowledge entries for this domain._\n")
    else:
        for row in rows:
            lines.append(format_pattern_block(row))
    lines.append(END_MARKER)
    return "\n".join(lines)


def build_index_md(stats: list[dict]) -> str:
    now = datetime.now(UTC).isoformat()
    lines = [
        BEGIN_MARKER,
        "",
        "---",
        f"generated: {now}",
        "---",
        "",
        "# Knowledge Domains Index",
        "",
        "_Auto-generated. Do not edit above END_MARKER._",
        "",
        "| Domain | Rules | Hypotheses | Knowledge | Observations |",
        "|--------|-------|------------|-----------|--------------|",
    ]
    for s in stats:
        domain = s["domain"]
        lines.append(
            f"| [{domain}]({domain}/rules.md) "
            f"| {s['rule_count']} "
            f"| {s['hypothesis_count']} "
            f"| {s['knowledge_count']} "
            f"| {s['observation_count']} |"
        )
    lines.append("")
    lines.append(END_MARKER)
    return "\n".join(lines)


def write_file(path: Path, new_header: str, dry_run: bool) -> None:
    annotations = load_human_annotations(path)
    if annotations:
        content = new_header + "\n\n" + annotations + "\n"
    else:
        content = new_header + "\n"
    if dry_run:
        print(f"  [dry-run] would write {path}")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"  wrote {path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", help="Only rebuild a single domain")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    domains = [args.domain] if args.domain else DOMAINS

    for domain in domains:
        print(f"\n=== {domain} ===")
        domain_dir = Path(DOMAINS_DIR) / domain

        rules = conn.execute(
            "SELECT * FROM patterns WHERE domain=? AND state='rule' AND human_approved=1 ORDER BY confidence DESC",
            (domain,),
        ).fetchall()
        hypotheses = conn.execute(
            "SELECT * FROM patterns WHERE domain=? AND state='hypothesis' ORDER BY confidence DESC",
            (domain,),
        ).fetchall()
        knowledge = conn.execute(
            "SELECT * FROM patterns WHERE domain=? AND state='knowledge' ORDER BY confidence DESC",
            (domain,),
        ).fetchall()

        write_file(domain_dir / "rules.md",      build_rules_md(domain, [dict(r) for r in rules]),           args.dry_run)
        write_file(domain_dir / "hypotheses.md", build_hypotheses_md(domain, [dict(r) for r in hypotheses]), args.dry_run)
        write_file(domain_dir / "knowledge.md",  build_knowledge_md(domain, [dict(r) for r in knowledge]),   args.dry_run)

    # Build INDEX.md
    stats = conn.execute("SELECT * FROM domain_stats ORDER BY domain").fetchall()
    # Pad with zeros for domains with no rows in domain_stats
    stats_by_domain = {row["domain"]: dict(row) for row in stats}
    full_stats = []
    for d in DOMAINS:
        full_stats.append(stats_by_domain.get(d, {
            "domain": d, "rule_count": 0, "hypothesis_count": 0,
            "knowledge_count": 0, "observation_count": 0, "last_activity": None,
        }))

    index_path = Path(DOMAINS_DIR) / "INDEX.md"
    write_file(index_path, build_index_md(full_stats), args.dry_run)

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
