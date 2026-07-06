#!/usr/bin/env python3
"""
AIOS: extract-patterns.py
Deterministic pattern extraction from ops data → patterns table.

Sources:
  - prompts_used (classification) → class: prompt
  - bug_log (symptom stems)       → class: bug_fix
  - session traces                → class: workflow

Run weekly (or manually). Idempotent — skips titles already in DB.
Output: JSON summary of what was inserted.
"""

import json
import os
import re
import sqlite3
import uuid
from collections import Counter
from datetime import UTC, datetime

DB = os.path.expanduser("~/AIOS/data/aios.db")
MIN_FREQUENCY = 2  # min occurrences before a pattern is worth recording
MIN_PROMPT_LENGTH = 20  # ignore very short prompts as noise
TOP_N = 10  # max patterns extracted per class per run


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def load_existing_titles(conn: sqlite3.Connection) -> set[str]:
    cur = conn.execute("SELECT title FROM patterns")
    return {row[0] for row in cur.fetchall()}


def _table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {str(row[0]) for row in rows}


CLASS_TO_DOMAIN = {
    "bug_fix": "debugging",
    "failure": "debugging",
    "prompt": "prompting",
    "architecture": "architecture",
    "refactor": "architecture",
    "workflow": "workflow",
    "assumption": "workflow",
}


def insert_pattern(
    conn: sqlite3.Connection, class_: str, title: str, evidence: list, confidence: float
) -> None:
    domain = CLASS_TO_DOMAIN.get(class_, "unclassified")
    now = datetime.now(UTC).isoformat()
    conn.execute(
        """
        INSERT INTO patterns
            (id, class, title, evidence, confidence, status,
             domain, state, source_type, human_approved, first_observed_at, created_at)
        VALUES (?, ?, ?, ?, ?, 'candidate',
                ?, 'observation', 'bigram', 0, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            class_,
            title,
            json.dumps(evidence),
            confidence,
            domain,
            now,
            now,
        ),
    )


# ---------------------------------------------------------------------------
# Source 1: prompts_used — class: prompt
# ---------------------------------------------------------------------------

STOP_WORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "in",
    "on",
    "at",
    "to",
    "for",
    "of",
    "with",
    "by",
    "from",
    "up",
    "about",
    "into",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "will",
    "would",
    "could",
    "should",
    "may",
    "might",
    "can",
    "this",
    "that",
    "these",
    "those",
    "it",
    "its",
    "you",
    "your",
    "our",
    "their",
    "them",
    "they",
    "his",
    "her",
    "not",
    "no",
    "also",
    "just",
    "some",
    "than",
    "then",
    "when",
    "where",
    "which",
    "what",
    "here",
    "there",
    "each",
}

# Path and identity tokens — never meaningful as pattern bigrams
PATH_TOKENS = {
    "jakyeamos",
    "vaults",
    "command",
    "center",
    "downloads",
    "desktop",
    "users",
    "python3",
    "sqlite3",
    "obsidian",
    "claude",
    "codex",
    "localhost",
    "github",
    "https",
    "http",
    "file",
    "home",
}


def tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-z]{4,}", text.lower())
    return [w for w in words if w not in STOP_WORDS and w not in PATH_TOKENS]


def extract_prompt_patterns(conn: sqlite3.Connection, existing: set[str]) -> list[dict]:
    cur = conn.execute(
        """
        SELECT classification, prompt_text
        FROM prompts_used
        WHERE prompt_text IS NOT NULL AND length(prompt_text) >= ?
        ORDER BY rowid
        """,
        (MIN_PROMPT_LENGTH,),
    )
    rows = cur.fetchall()

    # Count bigrams per classification
    class_bigrams: dict[str, Counter] = {}
    class_prompt_ids: dict[str, dict[str, list]] = {}  # bigram → [session_ids]

    for classification, text in rows:
        tokens = tokenize(text)
        bigrams = [f"{tokens[i]} {tokens[i + 1]}" for i in range(len(tokens) - 1)]
        if classification not in class_bigrams:
            class_bigrams[classification] = Counter()
            class_prompt_ids[classification] = {}
        class_bigrams[classification].update(bigrams)
        for bg in bigrams:
            class_prompt_ids[classification].setdefault(bg, [])

    inserted = []
    for classification, counter in class_bigrams.items():
        for bigram, count in counter.most_common(TOP_N):
            if count < MIN_FREQUENCY:
                continue
            title = f"Recurring prompt pattern [{classification}]: '{bigram}'"
            if title in existing:
                continue
            confidence = min(0.3 + (count / 10) * 0.4, 0.7)
            evidence = [f"frequency:{count}", f"classification:{classification}"]
            inserted.append({"class": "prompt", "title": title, "count": count})
            existing.add(title)
            insert_pattern(conn, "prompt", title, evidence, confidence)

    return inserted


# ---------------------------------------------------------------------------
# Source 2: bug_log — class: bug_fix
# ---------------------------------------------------------------------------


def extract_bug_patterns(conn: sqlite3.Connection, existing: set[str]) -> list[dict]:
    try:
        cur = conn.execute("SELECT id, symptom FROM bug_log WHERE symptom IS NOT NULL")
    except Exception:
        return []

    rows = cur.fetchall()
    if not rows:
        return []

    # Count symptom stem overlap using simple word frequency
    symptom_tokens: list[tuple[str, list[str]]] = []
    for bug_id, symptom in rows:
        tokens = tokenize(symptom)
        if tokens:
            symptom_tokens.append((bug_id, tokens))

    if len(symptom_tokens) < MIN_FREQUENCY:
        return []

    # Find bigrams that appear in multiple bug symptoms
    global_bigrams: Counter = Counter()
    bigram_to_bug_ids: dict[str, list[str]] = {}
    for bug_id, tokens in symptom_tokens:
        bigrams = {f"{tokens[i]} {tokens[i + 1]}" for i in range(len(tokens) - 1)}
        global_bigrams.update(bigrams)
        for bg in bigrams:
            bigram_to_bug_ids.setdefault(bg, []).append(bug_id)

    inserted = []
    for bigram, count in global_bigrams.most_common(TOP_N):
        if count < MIN_FREQUENCY:
            continue
        title = f"Recurring bug symptom: '{bigram}'"
        if title in existing:
            continue
        confidence = min(0.4 + (count / 5) * 0.3, 0.85)
        evidence = bigram_to_bug_ids.get(bigram, [])[:10]
        inserted.append({"class": "bug_fix", "title": title, "count": count})
        existing.add(title)
        insert_pattern(conn, "bug_fix", title, evidence, confidence)

    return inserted


# ---------------------------------------------------------------------------
# Source 3: session traces — class: workflow
# ---------------------------------------------------------------------------

WORKFLOW_CLASSIFICATION_TITLES = {
    "debug": "Captured workflow: debug fix failing behavior",
    "implement": "Captured workflow: implement build feature",
    "plan": "Captured workflow: plan design architecture decision",
    "review": "Captured workflow: review pull request audit",
    "refactor": "Captured workflow: refactor cleanup improve code",
}

WORKFLOW_CLASSIFICATION_PURPOSES = {
    "debug": "Use when repeated sessions start from a failure, inspect evidence, change code, and verify the fix.",
    "implement": "Use when repeated sessions add or change product behavior from an implementation request.",
    "plan": "Use when repeated sessions turn ambiguous work into a technical plan, decision, or architecture direction.",
    "review": "Use when repeated sessions inspect existing work, identify risks, and produce review findings or follow-up fixes.",
    "refactor": "Use when repeated sessions improve structure or clarity while preserving behavior.",
}

WORKFLOW_MIN_SESSIONS = 3
WORKFLOW_MIN_TOOL_EVENTS = 3


def _prompt_classification_counts(conn: sqlite3.Connection) -> dict[str, Counter]:
    rows = conn.execute(
        """
        SELECT session_id, classification
        FROM prompts_used
        WHERE classification IS NOT NULL
        """
    ).fetchall()
    counts: dict[str, Counter] = {}
    for session_id, classification in rows:
        normalized = str(classification or "other").strip().lower()
        counts.setdefault(str(session_id), Counter())[normalized] += 1
    return counts


def _tool_event_counts(conn: sqlite3.Connection) -> dict[str, int]:
    rows = conn.execute(
        """
        SELECT session_id, COUNT(*)
        FROM tool_events
        WHERE event_type = 'PostToolUse'
        GROUP BY session_id
        """
    ).fetchall()
    return {str(session_id): int(count) for session_id, count in rows}


def _primary_workflow_classification(counts: Counter) -> str | None:
    ranked = [
        (classification, count)
        for classification, count in counts.items()
        if classification in WORKFLOW_CLASSIFICATION_TITLES
    ]
    if not ranked:
        return None
    ranked.sort(key=lambda item: (-item[1], item[0]))
    return ranked[0][0]


def _workflow_body(classification: str, session_count: int, tool_event_count: int) -> str:
    purpose = WORKFLOW_CLASSIFICATION_PURPOSES[classification]
    return (
        f"{purpose}\n\n"
        f"Evidence: observed across {session_count} sessions with "
        f"{tool_event_count} post-tool events."
    )


def _insert_workflow_pattern(
    conn: sqlite3.Connection,
    title: str,
    evidence: list[str],
    confidence: float,
    body: str,
    source_sessions: int,
    frequency_count: int,
    first_seen: str | None,
    last_seen: str | None,
) -> None:
    now = datetime.now(UTC).isoformat()
    conn.execute(
        """
        INSERT INTO patterns
            (id, class, title, evidence, confidence, status, domain, state,
             body, source_type, human_approved, first_observed_at, created_at,
             frequency_count, source_sessions, last_seen_at)
        VALUES (?, 'workflow', ?, ?, ?, 'candidate', 'workflow', 'observation',
                ?, 'session-workflow', 0, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            title,
            json.dumps(evidence),
            confidence,
            body,
            first_seen or now,
            now,
            frequency_count,
            source_sessions,
            last_seen,
        ),
    )


def extract_workflow_patterns(conn: sqlite3.Connection, existing: set[str]) -> list[dict]:
    if "sessions" not in _table_names(conn):
        return []

    classification_counts = _prompt_classification_counts(conn)
    tool_counts = _tool_event_counts(conn) if "tool_events" in _table_names(conn) else {}

    rows = conn.execute(
        """
        SELECT id, started_at, ended_at, status, objective
        FROM sessions
        ORDER BY started_at
        """
    ).fetchall()

    grouped: dict[str, dict] = {}
    for session_id, started_at, ended_at, status, objective in rows:
        session_key = str(session_id)
        counts = classification_counts.get(session_key, Counter())
        primary = _primary_workflow_classification(counts)
        if primary is None:
            continue

        post_tool_events = tool_counts.get(session_key, 0)
        if post_tool_events < WORKFLOW_MIN_TOOL_EVENTS and sum(counts.values()) < 2:
            continue

        title = WORKFLOW_CLASSIFICATION_TITLES[primary]
        group = grouped.setdefault(
            title,
            {
                "classification": primary,
                "sessions": [],
                "tool_events": 0,
                "first_seen": started_at,
                "last_seen": ended_at or started_at,
            },
        )
        group["sessions"].append(
            {
                "id": session_key,
                "started_at": started_at,
                "status": status,
                "objective": objective,
                "classifications": dict(counts),
                "post_tool_events": post_tool_events,
            }
        )
        group["tool_events"] += post_tool_events
        if started_at and (group["first_seen"] is None or started_at < group["first_seen"]):
            group["first_seen"] = started_at
        seen_at = ended_at or started_at
        if seen_at and (group["last_seen"] is None or seen_at > group["last_seen"]):
            group["last_seen"] = seen_at

    inserted = []
    for title, group in sorted(
        grouped.items(), key=lambda item: len(item[1]["sessions"]), reverse=True
    )[:TOP_N]:
        session_count = len(group["sessions"])
        if session_count < WORKFLOW_MIN_SESSIONS:
            continue
        if title in existing:
            continue
        tool_event_count = int(group["tool_events"])
        confidence = min(0.75 + (session_count / 20) * 0.12 + (tool_event_count / 500) * 0.05, 0.92)
        evidence = [
            (
                f"session:{session['id']} classifications:{json.dumps(session['classifications'], sort_keys=True)} "
                f"post_tool_events:{session['post_tool_events']} status:{session['status'] or 'unknown'}"
            )
            for session in group["sessions"][:12]
        ]
        body = _workflow_body(group["classification"], session_count, tool_event_count)
        inserted.append(
            {
                "class": "workflow",
                "title": title,
                "count": session_count,
                "tool_events": tool_event_count,
            }
        )
        existing.add(title)
        _insert_workflow_pattern(
            conn,
            title,
            evidence,
            confidence,
            body,
            session_count,
            session_count,
            group["first_seen"],
            group["last_seen"],
        )

    return inserted


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # Bigram extraction disabled — produces frequency noise, not actionable rules.
    # Errors are now captured directly by hook-post-tool-use.py with full symptom text.
    prompt_inserted: list = []
    bug_inserted: list = []
    workflow_inserted: list = []

    conn = sqlite3.connect(DB)
    existing = load_existing_titles(conn)
    workflow_inserted = extract_workflow_patterns(conn, existing)
    if args.dry_run:
        conn.rollback()
    else:
        conn.commit()

    conn.close()

    summary = {
        "run_at": datetime.now(UTC).isoformat(),
        "inserted": {
            "prompt": len(prompt_inserted),
            "bug_fix": len(bug_inserted),
            "workflow": len(workflow_inserted),
        },
        "total": len(prompt_inserted) + len(bug_inserted) + len(workflow_inserted),
        "details": {
            "prompt": prompt_inserted,
            "bug_fix": bug_inserted,
            "workflow": workflow_inserted,
        },
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
