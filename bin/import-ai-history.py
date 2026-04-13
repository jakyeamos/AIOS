#!/usr/bin/env python3
"""
AIOS: import-ai-history — CLI entry point.
"""

import argparse
import json
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from import_ai_history import (
    load_claude_code_export,
    load_codex_export,
    make_file_suffix,
    parse_chatgpt_conversation,
    parse_claude_code_conversation,
    parse_claude_conversation,
    parse_codex_conversation,
    render_markdown,
)

DB = Path.home() / "AIOS" / "data" / "aios.db"
READY_DIR = Path.home() / "AIOS" / "staging" / "ai-history" / "ready"


def make_batch_id(source: str) -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    return f"{timestamp}--{source}"


def resolve_export_path(path: str, source: str) -> Path:
    export_path = Path(path).expanduser()
    if not export_path.exists():
        raise FileNotFoundError(f"file not found: {export_path}")
    if source in {"chatgpt", "claude"} and export_path.is_dir():
        export_path = export_path / "conversations.json"
    if not export_path.exists():
        raise FileNotFoundError(f"file not found: {export_path}")
    return export_path


def resolve_claude_code_path(path: str) -> Path:
    """Accept a project dir, the full projects/ dir, or default to ~/.claude/projects/."""
    if path:
        p = Path(path).expanduser()
        if not p.exists():
            raise FileNotFoundError(f"file not found: {p}")
        return p
    default = Path.home() / ".claude" / "projects"
    if not default.exists():
        raise FileNotFoundError(f"Claude Code projects dir not found: {default}")
    return default


def load_json_array(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array at top level, got {type(data).__name__}")
    return data


def load_export(path: Path, source: str) -> list[dict]:
    if source == "codex":
        return load_codex_export(str(path))
    if source == "claude-code":
        return load_claude_code_export(str(path))
    return load_json_array(path)


def get_existing_ids(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT id FROM ai_history_imports").fetchall()
    return {row[0] for row in rows}


def source_dir_name(source: str) -> str:
    names = {"chatgpt": "ChatGPT", "claude": "Claude", "codex": "Codex", "claude-code": "Claude Code"}
    return names[source]


def stage_conversation(conv: dict) -> Path:
    source_cap = source_dir_name(conv["source"])
    year = conv["date"][:4]
    dest_dir = READY_DIR / source_cap / year
    dest_dir.mkdir(parents=True, exist_ok=True)
    file_suffix = make_file_suffix(conv.get("source_id", ""), conv["id"])
    filename = f"{conv['date']}-{conv['slug']}--{file_suffix}.md"
    dest = dest_dir / filename
    dest.write_text(render_markdown(conv), encoding="utf-8")
    return dest


def write_to_db(conn: sqlite3.Connection, conv: dict) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO ai_history_imports
          (id, batch_id, source, source_id, model, conversation_date, title, slug, topic_tags, quality, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'staged')
        """,
        (
            conv["id"],
            conv["batch_id"],
            conv["source"],
            conv.get("source_id", ""),
            conv.get("model", "unknown"),
            conv["date"],
            conv["title"],
            conv["slug"],
            json.dumps(conv.get("topic_tags", [])),
            conv["quality"],
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Import AI conversation history")
    parser.add_argument("--source", required=True, choices=["chatgpt", "claude", "codex", "claude-code"])
    parser.add_argument("--file", default="", help="Path to export file or dir (claude-code defaults to ~/.claude/projects/)")
    parser.add_argument("--batch", default=None, help="Batch ID (default: auto YYYYMMDDHHMMSS--source)")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be imported without writing files or DB")
    args = parser.parse_args()

    try:
        if args.source == "claude-code":
            export_path = resolve_claude_code_path(args.file)
        else:
            if not args.file:
                print("ERROR: --file is required for this source", file=sys.stderr)
                sys.exit(1)
            export_path = resolve_export_path(args.file, args.source)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    batch_id = args.batch or make_batch_id(args.source)
    parse_fn_map = {
        "chatgpt": parse_chatgpt_conversation,
        "claude": parse_claude_conversation,
        "codex": parse_codex_conversation,
        "claude-code": parse_claude_code_conversation,
    }
    parse_fn = parse_fn_map[args.source]

    try:
        raw_conversations = load_export(export_path, args.source)
    except Exception as exc:
        print(f"ERROR: failed to read export: {exc}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(str(DB))
    existing_ids = get_existing_ids(conn)

    total = 0
    keep_count = 0
    deferred_count = 0
    duplicate_count = 0
    errors = 0

    for raw in raw_conversations:
        try:
            conv = parse_fn(raw, batch_id)
        except Exception as exc:
            errors += 1
            if args.dry_run:
                print(f"  PARSE ERROR: {exc}")
            continue

        if conv["id"] in existing_ids:
            duplicate_count += 1
            continue

        existing_ids.add(conv["id"])
        total += 1
        if conv["quality"] == "keep":
            keep_count += 1
        else:
            deferred_count += 1

        if args.dry_run:
            flag = "" if conv["quality"] == "keep" else "  [deferred]"
            print(f"  {conv['date']}  {conv['title'][:60]:<60}  {conv['exchange_count']} exchanges{flag}")
        else:
            stage_conversation(conv)
            write_to_db(conn, conv)

    if not args.dry_run:
        conn.commit()
    conn.close()

    banner = "DRY RUN - " if args.dry_run else ""
    print(f"\n{banner}Batch {batch_id}")
    print(f"  Source:     {args.source}")
    print(f"  Total:      {total}")
    print(f"  Keep:       {keep_count}")
    print(f"  Deferred:   {deferred_count}")
    print(f"  Duplicates: {duplicate_count}")
    print(f"  Errors:     {errors}")
    if not args.dry_run:
        print(f"  Staged to:  {READY_DIR}")
        print(f"\nNext: review-imports.sh --batch {batch_id}")


if __name__ == "__main__":
    main()
