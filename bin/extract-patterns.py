#!/usr/bin/env python3
"""
AIOS: extract-patterns.py
Deterministic pattern extraction from ops data → patterns table.

Sources:
  - prompts_used (classification) → class: prompt
  - bug_log (symptom stems)       → class: bug_fix
  - session handoffs (Next Actions verbs) → class: workflow

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
from pathlib import Path

DB = os.path.expanduser("~/AIOS/data/aios.db")
HANDOFFS_DIR = os.path.expanduser("~/Vaults/Command-Center/02 AI OS/02 Session Handoffs")
MIN_FREQUENCY = 2          # min occurrences before a pattern is worth recording
MIN_PROMPT_LENGTH = 20     # ignore very short prompts as noise
TOP_N = 10                 # max patterns extracted per class per run


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def load_existing_titles(conn: sqlite3.Connection) -> set[str]:
    cur = conn.execute("SELECT title FROM patterns")
    return {row[0] for row in cur.fetchall()}


CLASS_TO_DOMAIN = {
    "bug_fix":      "debugging",
    "failure":      "debugging",
    "prompt":       "prompting",
    "architecture": "architecture",
    "refactor":     "architecture",
    "workflow":     "workflow",
    "assumption":   "workflow",
}


def insert_pattern(conn: sqlite3.Connection, class_: str, title: str, evidence: list, confidence: float) -> None:
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
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "up", "about", "into", "is", "are", "was",
    "were", "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "can", "this", "that",
    "these", "those", "it", "its", "you", "your", "our", "their", "them",
    "they", "his", "her", "not", "no", "also", "just", "some", "than",
    "then", "when", "where", "which", "what", "here", "there", "each",
}

# Path and identity tokens — never meaningful as pattern bigrams
PATH_TOKENS = {
    "jakyeamos", "vaults", "command", "center", "downloads", "desktop",
    "users", "python3", "sqlite3", "obsidian", "claude", "codex",
    "localhost", "github", "https", "http", "file", "home",
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
    all_session_ids: dict = {}

    cur2 = conn.execute("SELECT id, session_id, prompt_text FROM prompts_used WHERE prompt_text IS NOT NULL")
    id_map = {row[1] + row[2][:30]: row[0] for row in cur2.fetchall()}

    for classification, text in rows:
        tokens = tokenize(text)
        bigrams = [f"{tokens[i]} {tokens[i+1]}" for i in range(len(tokens) - 1)]
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
        bigrams = {f"{tokens[i]} {tokens[i+1]}" for i in range(len(tokens) - 1)}
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
# Source 3: handoff Next Actions — class: workflow
# ---------------------------------------------------------------------------

ACTION_VERBS = re.compile(
    r"^[-*]\s+(?:\[[ x]\]\s+)?([A-Z][a-z]+|[a-z]+)\b",
    re.MULTILINE,
)
NEXT_ACTIONS_SECTION = re.compile(
    r"## Next Actions\n(.*?)(?=\n## |\Z)",
    re.DOTALL,
)


def extract_workflow_patterns(conn: sqlite3.Connection, existing: set[str]) -> list[dict]:
    if not os.path.exists(HANDOFFS_DIR):
        return []

    verb_counter: Counter = Counter()
    verb_to_files: dict[str, list[str]] = {}

    for fname in os.listdir(HANDOFFS_DIR):
        if not fname.endswith(".md"):
            continue
        path = os.path.join(HANDOFFS_DIR, fname)
        try:
            text = Path(path).read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        sec_match = NEXT_ACTIONS_SECTION.search(text)
        if not sec_match:
            continue
        section_text = sec_match.group(1)

        verbs = ACTION_VERBS.findall(section_text)
        unique_verbs = set(v.lower() for v in verbs if len(v) >= 3)
        verb_counter.update(unique_verbs)
        for v in unique_verbs:
            verb_to_files.setdefault(v, []).append(fname)

    inserted = []
    for verb, count in verb_counter.most_common(TOP_N):
        if count < MIN_FREQUENCY:
            continue
        title = f"Recurring next-action verb: '{verb}'"
        if title in existing:
            continue
        confidence = min(0.25 + (count / 15) * 0.5, 0.75)
        evidence = verb_to_files.get(verb, [])[:10]
        inserted.append({"class": "workflow", "title": title, "count": count})
        existing.add(title)
        insert_pattern(conn, "workflow", title, evidence, confidence)

    return inserted


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # Bigram extraction disabled — produces frequency noise, not actionable rules.
    # Errors are now captured directly by hook-post-tool-use.py with full symptom text.
    prompt_inserted: list = []
    bug_inserted: list = []
    workflow_inserted: list = []

    conn = sqlite3.connect(DB)
    existing = load_existing_titles(conn)  # noqa: F841 (kept for future use)

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
