#!/usr/bin/env python3
"""
AIOS: vault-lint.py
Checks the Obsidian vault for structural quality issues.

Checks:
  1. Project notes with blank/placeholder Current Focus section
  2. Batch notes with empty synthesis sections (Recurring Themes, Blind Spots, etc.)
  3. Pattern candidates >30 days old without a promotion decision
  4. Orphan handoff notes for inactive/unknown projects

Output: ~/AIOS/logs/vault-lint-latest.json
        Also prints a summary to stdout.
"""

import json
import os
import re
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

VAULT = os.path.expanduser("~/Vaults/Command-Center")
DB = os.path.expanduser("~/AIOS/data/aios.db")
OUTPUT = os.path.expanduser("~/AIOS/logs/vault-lint-latest.json")

PROJECTS_DIR = os.path.join(VAULT, "03 Projects")
HANDOFFS_DIR = os.path.join(VAULT, "02 AI OS", "02 Session Handoffs")
ARCHIVE_DIR = os.path.join(VAULT, "09 Archive", "AI History")

SYNTHESIS_SECTIONS = ["Recurring Themes", "Repeated Blind Spots", "Prompt Patterns", "Concepts Deserving a Page"]
STALE_DAYS = 30


# ---------------------------------------------------------------------------
# Check 1: Project notes with blank Current Focus
# ---------------------------------------------------------------------------

def check_blank_current_focus() -> list[dict]:
    issues = []
    if not os.path.exists(PROJECTS_DIR):
        return issues
    for fname in os.listdir(PROJECTS_DIR):
        if not fname.endswith(".md"):
            continue
        path = os.path.join(PROJECTS_DIR, fname)
        try:
            text = Path(path).read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        m = re.search(r"## Current Focus\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
        if not m:
            continue
        section_text = m.group(1).strip()
        # Blank, comment placeholder, or very short
        is_blank = (
            not section_text
            or section_text.startswith("<!--")
            or len(section_text) <= 20
        )
        if is_blank:
            issues.append({
                "check": "blank_current_focus",
                "path": path,
                "note": fname.replace(".md", ""),
                "detail": f"Current Focus section is empty or placeholder ({len(section_text)} chars)",
            })
    return issues


# ---------------------------------------------------------------------------
# Check 2: Batch notes with empty synthesis sections
# ---------------------------------------------------------------------------

def check_empty_batch_synthesis() -> list[dict]:
    issues = []
    if not os.path.exists(ARCHIVE_DIR):
        return issues
    for fname in os.listdir(ARCHIVE_DIR):
        if not fname.startswith("_Batch-") or not fname.endswith(".md"):
            continue
        path = os.path.join(ARCHIVE_DIR, fname)
        try:
            text = Path(path).read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for section in SYNTHESIS_SECTIONS:
            m = re.search(rf"## {re.escape(section)}\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
            if not m:
                continue
            section_text = m.group(1).strip()
            is_empty = (
                not section_text
                or section_text.startswith("<!--")
                or len(section_text) <= 30
            )
            if is_empty:
                issues.append({
                    "check": "empty_batch_synthesis",
                    "path": path,
                    "note": fname.replace(".md", ""),
                    "detail": f"Section '{section}' is empty or placeholder",
                })
    return issues


# ---------------------------------------------------------------------------
# Check 3: Stale pattern candidates
# ---------------------------------------------------------------------------

def check_stale_patterns() -> list[dict]:
    issues = []
    try:
        conn = sqlite3.connect(DB)
        cutoff = (datetime.now(UTC) - timedelta(days=STALE_DAYS)).isoformat()
        cur = conn.execute(
            """
            SELECT id, class, title, created_at
            FROM patterns
            WHERE status = 'candidate' AND created_at < ?
            ORDER BY created_at
            """,
            (cutoff,),
        )
        rows = cur.fetchall()
        conn.close()
        for pid, class_, title, created_at in rows:
            issues.append({
                "check": "stale_pattern_candidate",
                "id": pid,
                "class": class_,
                "title": title,
                "created_at": created_at,
                "detail": f"Pattern candidate untouched for >{STALE_DAYS} days — promote or discard",
            })
    except Exception as e:
        issues.append({"check": "stale_pattern_candidate", "error": str(e)})
    return issues


# ---------------------------------------------------------------------------
# Check 4: Orphan handoff notes
# ---------------------------------------------------------------------------

def check_orphan_handoffs() -> list[dict]:
    """Handoff notes whose project_id has no active project in the DB."""
    issues = []
    if not os.path.exists(HANDOFFS_DIR):
        return issues

    # Get active project names from DB
    active_names: set[str] = set()
    try:
        conn = sqlite3.connect(DB)
        cur = conn.execute("SELECT name FROM projects WHERE status = 'active'")
        active_names = {row[0].lower() for row in cur.fetchall()}
        conn.close()
    except Exception:
        pass

    # Handoff filename format: YYYY-MM-DD-ProjectName-hash.md
    fname_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}-(.+)-[0-9a-f]{8}\.md$")

    for fname in os.listdir(HANDOFFS_DIR):
        if not fname.endswith(".md"):
            continue
        m = fname_pattern.match(fname)
        if not m:
            continue
        project_slug = m.group(1).lower()
        if active_names and project_slug not in active_names:
            path = os.path.join(HANDOFFS_DIR, fname)
            issues.append({
                "check": "orphan_handoff",
                "path": path,
                "note": fname.replace(".md", ""),
                "detail": f"Project slug '{project_slug}' not found in active projects (may need project registration)",
            })
    return issues


# ---------------------------------------------------------------------------
# Check 5: Large deferred import backlog
# ---------------------------------------------------------------------------

DEFERRED_THRESHOLD = 100  # warn when > N items remain deferred


def check_deferred_imports() -> list[dict]:
    """Warn when a large number of AI history imports remain deferred."""
    issues = []
    try:
        conn = sqlite3.connect(DB)
        cur = conn.execute(
            "SELECT source, COUNT(*) FROM ai_history_imports WHERE quality = 'deferred' GROUP BY source"
        )
        rows = cur.fetchall()
        conn.close()
        for source, count in rows:
            if count >= DEFERRED_THRESHOLD:
                issues.append({
                    "check": "deferred_import_backlog",
                    "source": source,
                    "count": count,
                    "detail": f"{count} deferred '{source}' imports — run review-imports.sh to process",
                })
    except Exception as e:
        issues.append({"check": "deferred_import_backlog", "error": str(e)})
    return issues


# ---------------------------------------------------------------------------
# Check 6: Rules without body text
# ---------------------------------------------------------------------------

def check_rules_missing_body() -> list[dict]:
    """Active rules (state='rule') that have no body text cannot inject useful context."""
    issues = []
    try:
        conn = sqlite3.connect(DB)
        cur = conn.execute(
            "SELECT id, title FROM patterns WHERE state = 'rule' AND (body IS NULL OR body = '')"
        )
        rows = cur.fetchall()
        conn.close()
        for pid, title in rows:
            issues.append({
                "check": "rule_missing_body",
                "id": pid,
                "title": title,
                "detail": "Rule has no body — cannot inject meaningful context; add body text via approve-pattern.py",
            })
    except Exception as e:
        issues.append({"check": "rule_missing_body", "error": str(e)})
    return issues


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    all_issues = []
    all_issues.extend(check_blank_current_focus())
    all_issues.extend(check_empty_batch_synthesis())
    all_issues.extend(check_stale_patterns())
    all_issues.extend(check_orphan_handoffs())
    all_issues.extend(check_deferred_imports())
    all_issues.extend(check_rules_missing_body())

    # Group by check type for summary
    by_check: dict[str, list] = {}
    for issue in all_issues:
        key = issue["check"]
        by_check.setdefault(key, []).append(issue)

    result = {
        "run_at": datetime.now(UTC).isoformat(),
        "total_issues": len(all_issues),
        "summary": {k: len(v) for k, v in by_check.items()},
        "issues": all_issues,
    }

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w") as f:
        json.dump(result, f, indent=2)

    print(f"vault-lint: {len(all_issues)} issues found")
    for check_name, count in result["summary"].items():
        print(f"  {check_name}: {count}")
    print(f"Full report: {OUTPUT}")


if __name__ == "__main__":
    main()
