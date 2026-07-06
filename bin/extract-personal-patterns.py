#!/usr/bin/env python3
"""
AIOS: extract-personal-patterns.py
Mine sessions, prompts_used, and ai_history_imports for personal behavioral patterns.

Pattern sub-classes (stored in domain field):
  preference  — how the user likes things done
  learning    — concepts the user asked to understand or be reminded of
  blindspot   — mistakes Claude made that the user corrected
  habit       — repeated actions/approaches the user takes

Extracted patterns land in the patterns table with:
  class='personal', state='notice', status='candidate', source_type='personal-extract'

They require human review before promotion to Obsidian.

Usage:
  python3 ~/AIOS/bin/extract-personal-patterns.py [--dry-run] [--days N]
"""

import argparse
import re
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

DB = Path.home() / "AIOS/data/aios.db"

DEFAULT_DAYS = 30

# Minimum number of distinct sessions a signal must appear in before it is
# persisted as a pattern candidate. Prevents single-session noise from
# flooding the candidate queue.
# Exception: 'blindspot' class uses MIN_SESSIONS_BLINDSPOT (1) because
# explicit user corrections are high-signal regardless of frequency.
MIN_SESSIONS = 2
MIN_SESSIONS_BLINDSPOT = 1

# ── Signal patterns ────────────────────────────────────────────────────────────

PREFERENCE_RE = re.compile(
    r"(?:i (?:always|usually|prefer|want|like)\b|"
    r"\b(?:please |always |make sure (?:to )?)?(?:use|keep|avoid)\b|"
    r"\bmy (?:preference|style|rule)\b|"
    r"\bi (?:hate|love|never) (?:when|having)\b)",
    re.IGNORECASE,
)

LEARNING_RE = re.compile(
    r"(?:\bexplain\b|\bcan you explain\b|\bwhy does\b|\bhow does\b|"
    r"\bwhat (?:is|are|does)\b|\bi (?:don'?t understand|didn'?t know|wasn'?t aware)\b|"
    r"\bremind me\b|\btl;?dr\b|\beli5\b)",
    re.IGNORECASE,
)

BLINDSPOT_RE = re.compile(
    r"(?:\bno[,.]? (?:don'?t|stop|that'?s not)\b|"
    r"\bi (?:didn'?t ask|said|told you)\b|"
    r"\bwhy did you\b|\bthat'?s wrong\b|\brevert\b|"
    r"\bthat'?s not what i\b|"
    r"\b(?:you )?(?:added|changed|removed) (?:something|that|it) without\b)",
    re.IGNORECASE,
)

HABIT_RE = re.compile(
    r"(?:\bas usual\b|\blike (?:i always|before)\b|\bsame as\b|\blike last time\b|"
    r"\bsame (?:pattern|approach|thing) as\b|"
    r"\b(?:again|still) (?:do|use|run|check)\b)",
    re.IGNORECASE,
)

SIGNAL_MAP = [
    ("preference", PREFERENCE_RE),
    ("learning", LEARNING_RE),
    ("blindspot", BLINDSPOT_RE),
    ("habit", HABIT_RE),
]


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _extract_lines(text: str, pattern: re.Pattern, max_len: int = 200) -> list[str]:
    seen: set[str] = set()
    results = []
    for line in text.splitlines():
        line = line.strip()
        if len(line) < 20 or line.startswith("#"):
            continue
        if pattern.search(line):
            key = line[:max_len].lower()
            if key not in seen:
                seen.add(key)
                results.append(line[:max_len])
    return results


def _already_exists(conn: sqlite3.Connection, title: str) -> bool:
    return bool(
        conn.execute(
            "SELECT 1 FROM patterns WHERE class='personal' AND title=? LIMIT 1",
            (title,),
        ).fetchone()
    )


def _insert_pattern(
    conn: sqlite3.Connection,
    sub_class: str,
    title: str,
    body: str,
    dry_run: bool,
) -> bool:
    if _already_exists(conn, title):
        return False
    if not dry_run:
        conn.execute(
            """
            INSERT INTO patterns
              (id, class, domain, title, body, confidence, state, status,
               source_type, first_observed_at, created_at)
            VALUES (?, 'personal', ?, ?, ?, 0.3, 'notice', 'candidate',
                    'personal-extract', ?, ?)
            """,
            (str(uuid.uuid4()), sub_class, title, body, _now(), _now()),
        )
    return True


def _scan_prompts(conn: sqlite3.Connection, cutoff: str, dry_run: bool) -> dict[str, int]:
    """Scan prompts_used table. Two-pass: collect with session context, then
    gate by MIN_SESSIONS before inserting. Prevents single-session noise from
    entering the candidate queue. prompts_used has no created_at so all rows
    are scanned; deduplication is by title."""

    counts = {k: 0 for k, _ in SIGNAL_MAP}
    # Include session_id so we can count distinct sessions per signal
    rows = conn.execute(
        "SELECT prompt_text, session_id FROM prompts_used WHERE length(prompt_text) > 30"
    ).fetchall()

    # Pass 1: collect matches grouped by title, tracking distinct sessions
    # structure: title -> {"sub_class": str, "body": str, "sessions": set}
    matches: dict[str, dict] = {}
    for text, session_id in rows:
        if not text:
            continue
        for sub_class, pattern in SIGNAL_MAP:
            for line in _extract_lines(text, pattern):
                title = line[:200]
                if title not in matches:
                    matches[title] = {"sub_class": sub_class, "body": line, "sessions": set()}
                matches[title]["sessions"].add(session_id)

    # Pass 2: insert only signals that meet the session threshold
    for title, info in matches.items():
        threshold = MIN_SESSIONS_BLINDSPOT if info["sub_class"] == "blindspot" else MIN_SESSIONS
        if len(info["sessions"]) >= threshold and _insert_pattern(
            conn, info["sub_class"], title, info["body"], dry_run
        ):
            counts[info["sub_class"]] += 1

    return counts


def _scan_ai_history(conn: sqlite3.Connection, cutoff: str, dry_run: bool) -> dict[str, int]:
    """Scan ai_history_imports markdown files (vault_path column).
    Two-pass: each distinct file counts as one 'session'. Only insert
    signals that appear in MIN_SESSIONS+ distinct files."""

    counts = {k: 0 for k, _ in SIGNAL_MAP}
    rows = conn.execute(
        """
        SELECT title, vault_path FROM ai_history_imports
        WHERE created_at >= ?
          AND source IN ('claude-code', 'codex')
          AND vault_path IS NOT NULL
        """,
        (cutoff,),
    ).fetchall()

    # Pass 1: collect matches grouped by line text, tracking distinct files
    matches: dict[str, dict] = {}
    for title, vault_path in rows:
        fpath = Path(vault_path)
        if not fpath.exists():
            continue
        try:
            text = fpath.read_text(errors="replace")
        except Exception:
            continue
        for sub_class, pattern in SIGNAL_MAP:
            for line in _extract_lines(text, pattern, max_len=180):
                # Label includes source title for context
                label = f"[{(title or '')[:60]}] {line}".strip()[:200]
                if label not in matches:
                    matches[label] = {"sub_class": sub_class, "body": line, "files": set()}
                matches[label]["files"].add(vault_path)

    # Pass 2: gate by MIN_SESSIONS (distinct files)
    for label, info in matches.items():
        threshold = MIN_SESSIONS_BLINDSPOT if info["sub_class"] == "blindspot" else MIN_SESSIONS
        if len(info["files"]) >= threshold and _insert_pattern(
            conn, info["sub_class"], label, info["body"], dry_run
        ):
            counts[info["sub_class"]] += 1

    return counts


def _scan_bug_log(conn: sqlite3.Connection, cutoff: str, dry_run: bool) -> dict[str, int]:
    """Mine bug_log for blindspot signals — repeated errors are blindspots."""
    counts = {k: 0 for k, _ in SIGNAL_MAP}
    rows = conn.execute(
        "SELECT symptom, root_cause FROM bug_log WHERE created_at >= ?",
        (cutoff,),
    ).fetchall()
    for desc, root_cause in rows:
        for text in [desc, root_cause]:
            if not text or len(text) < 20:
                continue
            for line in _extract_lines(text, BLINDSPOT_RE):
                if _insert_pattern(conn, "blindspot", line, line, dry_run):
                    counts["blindspot"] += 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS)
    args = parser.parse_args()

    cutoff = (datetime.now(UTC) - timedelta(days=args.days)).isoformat()

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    total: dict[str, int] = {k: 0 for k, _ in SIGNAL_MAP}

    for source_name, scanner in [
        ("prompts_used", _scan_prompts),
        ("ai_history", _scan_ai_history),
        ("bug_log", _scan_bug_log),
    ]:
        try:
            counts = scanner(conn, cutoff, args.dry_run)
            for k, v in counts.items():
                total[k] += v
        except Exception as exc:
            print(f"  [warn] {source_name} scan failed: {exc}")

    if not args.dry_run:
        conn.commit()
    conn.close()

    grand = sum(total.values())
    prefix = "[DRY] " if args.dry_run else ""
    print(f"{prefix}personal patterns extracted: {grand} new")
    for sub_class, count in total.items():
        if count:
            print(f"  {sub_class:<16} {count}")


if __name__ == "__main__":
    main()
