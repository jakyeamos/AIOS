#!/usr/bin/env python3
"""
AIOS: cron-ingest-codex.py
Auto-ingest new Codex session rollout files into aios.db.

Scans ~/.codex/sessions/**/*.jsonl for rollout files not yet imported.
Uses the same parser as import-ai-history.py (codex source type).
Marks files in processed_files so each rollout is imported exactly once.

Run via cron: 0 * * * * python3 ~/AIOS/bin/cron-ingest-codex.py >> ~/AIOS/logs/cron.log 2>&1
Or hourly:    0 * * * * ...
"""
import json
import sqlite3
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import import_ai_history as ih  # noqa: E402

DB          = Path.home() / "AIOS/data/aios.db"
CODEX_SESSIONS = Path.home() / ".codex/sessions"
LOG         = Path.home() / "AIOS/logs/cron.log"
STAGING_DIR = Path.home() / "AIOS/staging/ai-history/codex"

# Minimum quality bar — skip very short/empty sessions
MIN_WORDS = 50


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _log(msg: str) -> None:
    ts = _now()
    line = f"{ts} [codex-ingest] {msg}\n"
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a") as f:
            f.write(line)
    except Exception:
        pass
    print(line, end="")


def _get_processed(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT path FROM processed_files").fetchall()
    return {r[0] for r in rows}


def _mark_processed(conn: sqlite3.Connection, path: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO processed_files (path, processed_at) VALUES (?, ?)",
        (path, _now()),
    )


def _find_rollouts() -> list[Path]:
    if not CODEX_SESSIONS.exists():
        return []
    return sorted(CODEX_SESSIONS.glob("**/*.jsonl"))


def _total_words(conversation: dict) -> int:
    return sum(
        len((m.get("content") or "").split())
        for m in conversation.get("messages", [])
    )


def _ingest_rollout(
    conn: sqlite3.Connection,
    rollout_path: Path,
    title_index: dict[str, str],
) -> bool:
    """
    Parse one rollout file, insert into ai_history_imports, extract patterns.
    Returns True if imported, False if skipped.
    """
    rollout = ih.load_codex_rollout(rollout_path, title_index)
    if not rollout:
        return False

    batch_id = f"codex-cron-{rollout_path.stem[:20]}"
    conversation = ih.parse_codex_conversation(rollout, batch_id)
    if not conversation:
        return False

    if _total_words(conversation) < MIN_WORDS:
        return False

    conv_id = conversation.get("id") or str(uuid.uuid4())

    # Check for duplicate by id
    existing = conn.execute(
        "SELECT id FROM ai_history_imports WHERE id=?", (conv_id,)
    ).fetchone()
    if existing:
        return False

    # Render markdown and save to staging (for vault import if desired)
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    md = ih.render_markdown(conversation)
    slug = ih.title_to_slug(conversation.get("title") or "codex-session")
    suffix = ih.make_file_suffix(conversation)
    out_path = STAGING_DIR / f"{slug}-{suffix}.md"
    out_path.write_text(md)

    # Insert into ai_history_imports
    conn.execute(
        """
        INSERT OR IGNORE INTO ai_history_imports
          (id, source, title, started_at, ended_at, exchange_count, word_count,
           quality_score, tags_json, file_path, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            conv_id,
            "codex",
            conversation.get("title", "")[:200],
            conversation.get("started_at"),
            conversation.get("ended_at"),
            conversation.get("exchange_count", 0),
            _total_words(conversation),
            conversation.get("quality_score", 0.0),
            json.dumps(conversation.get("tags", [])),
            str(out_path),
            _now(),
        ),
    )

    # Extract tool-error patterns from Codex session (commands that errored)
    _extract_codex_patterns(conn, conversation)

    return True


def _extract_codex_patterns(conn: sqlite3.Connection, conversation: dict) -> None:
    """
    Mine Codex conversation for recurring error/workflow signals and surface
    them as observation-class patterns for later human review.
    """
    import re
    ERROR_RE = re.compile(
        r"(Error:|error:|Traceback|TypeError|ValueError|SyntaxError|"
        r"FAILED|command not found|No such file|npm ERR!)",
        re.IGNORECASE,
    )

    for msg in conversation.get("messages", []):
        role = msg.get("role", "")
        content = msg.get("content", "") or ""

        # Look for errors in assistant or tool-output turns
        if role in ("assistant", "tool") and ERROR_RE.search(content):
            for line in content.splitlines():
                if ERROR_RE.search(line) and len(line.strip()) > 20:
                    title = line.strip()[:200]
                    # Skip if already in DB
                    exists = conn.execute(
                        "SELECT 1 FROM patterns WHERE title=? LIMIT 1", (title,)
                    ).fetchone()
                    if not exists:
                        conn.execute(
                            """
                            INSERT INTO patterns
                              (id, class, domain, title, body, confidence, state,
                               status, source_type, first_observed_at, created_at)
                            VALUES (?, 'error', 'tooling', ?, ?, 0.2, 'observation',
                                    'candidate', 'tool-error', ?, ?)
                            """,
                            (str(uuid.uuid4()), title, title, _now(), _now()),
                        )
                    break  # one pattern per message


def main() -> None:
    _log("starting Codex ingestion scan")

    rollouts = _find_rollouts()
    if not rollouts:
        _log("no rollout files found at ~/.codex/sessions/")
        return

    _log(f"found {len(rollouts)} rollout file(s)")

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    processed = _get_processed(conn)
    title_index = ih.load_codex_title_index(CODEX_SESSIONS)

    new_count = skip_count = error_count = 0

    for rollout_path in rollouts:
        path_str = str(rollout_path)
        if path_str in processed:
            skip_count += 1
            continue

        try:
            imported = _ingest_rollout(conn, rollout_path, title_index)
            if imported:
                _mark_processed(conn, path_str)
                new_count += 1
                _log(f"  imported: {rollout_path.name}")
            else:
                # Still mark as processed so we don't recheck it
                _mark_processed(conn, path_str)
                skip_count += 1
        except Exception as exc:
            _log(f"  error on {rollout_path.name}: {exc}")
            error_count += 1

    conn.commit()
    conn.close()

    _log(f"done: {new_count} imported, {skip_count} skipped, {error_count} errors")


if __name__ == "__main__":
    main()
