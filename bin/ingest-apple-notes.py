#!/usr/bin/env python3
"""
AIOS: ingest-apple-notes — Apple Notes → AIOS knowledge system.

Uses AppleScript via subprocess to read Notes (avoids protobuf/DB decoding).
Upserts into aios.db::apple_notes and writes per-note markdown files to
the Personal-Corpus vault at Personal-Corpus/Notes/{folder}/{title}.md.
"""

import argparse
import hashlib
import html
import re
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# HTML → plain text
# ---------------------------------------------------------------------------

_TAG_RE = re.compile(r"<[^>]+>")
_MULTI_BLANK_RE = re.compile(r"\n{3,}")
_HEADING_RE = re.compile(r"<h[1-6][^>]*>(.*?)</h[1-6]>", re.IGNORECASE | re.DOTALL)
_BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
_DIV_RE = re.compile(r"</div>", re.IGNORECASE)
_LI_RE = re.compile(r"<li[^>]*>", re.IGNORECASE)


def html_to_text(raw: str) -> str:
    """Convert Notes HTML to readable plain text."""
    text = raw
    text = _HEADING_RE.sub(lambda m: "\n## " + m.group(1).strip() + "\n", text)
    text = _BR_RE.sub("\n", text)
    text = _DIV_RE.sub("\n", text)
    text = _LI_RE.sub("\n- ", text)
    text = _TAG_RE.sub("", text)
    text = html.unescape(text)
    text = _MULTI_BLANK_RE.sub("\n\n", text)
    return text.strip()


def note_id(title: str, folder: str, created_iso: str) -> str:
    """Stable ID from title + folder + creation date."""
    key = f"{folder}|{title}|{created_iso}"
    return hashlib.sha256(key.encode()).hexdigest()[:20]


# ---------------------------------------------------------------------------
# AppleScript extraction
# ---------------------------------------------------------------------------

# Outputs one record per note as pipe-delimited fields, with body last.
# Delimiter: ␞ (ASCII 30, record separator) between fields, ␟ (31) between notes.
_FIELD_SEP = "\x1e"
_REC_SEP = "\x1f"

_APPLESCRIPT = r"""
tell application "Notes"
    set output to ""
    set sep to (ASCII character 31)
    set fsep to (ASCII character 30)
    repeat with n in every note
        try
            set nTitle to name of n
            set nBody to body of n
            set nFolder to ""
            try
                set nFolder to name of container of n
            end try
            set nMod to modification date of n as string
            set nCre to creation date of n as string
            set noteRow to nTitle & fsep & nFolder & fsep & nMod & fsep & nCre & fsep & nBody
            set output to output & noteRow & sep
        end try
    end repeat
    return output
end tell
"""


def fetch_notes_applescript() -> list[dict]:
    """Run AppleScript and parse the output into note dicts."""
    result = subprocess.run(
        ["osascript", "-e", _APPLESCRIPT],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"AppleScript failed: {result.stderr.strip()}")

    raw = result.stdout.strip()
    if not raw:
        return []

    notes = []
    for rec in raw.split(_REC_SEP):
        rec = rec.strip()
        if not rec:
            continue
        parts = rec.split(_FIELD_SEP, 4)
        if len(parts) < 5:
            continue
        title, folder, mod_str, cre_str, body_html = parts
        title = title.strip()
        folder = folder.strip() or "Notes"
        if not title:
            continue
        notes.append(
            {
                "title": title,
                "folder": folder,
                "mod_str": mod_str.strip(),
                "cre_str": cre_str.strip(),
                "body_html": body_html,
                "body_text": html_to_text(body_html),
            }
        )
    return notes


# ---------------------------------------------------------------------------
# AIOS DB
# ---------------------------------------------------------------------------


def ensure_apple_notes_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS apple_notes (
            id              TEXT PRIMARY KEY,
            title           TEXT NOT NULL,
            folder          TEXT NOT NULL DEFAULT '',
            body_preview    TEXT NOT NULL DEFAULT '',
            word_count      INTEGER NOT NULL DEFAULT 0,
            created_str     TEXT NOT NULL DEFAULT '',
            modified_str    TEXT NOT NULL DEFAULT '',
            vault_path      TEXT,
            updated_at      TEXT NOT NULL
        )
        """
    )
    conn.commit()


def upsert_note(
    conn: sqlite3.Connection, note: dict, note_id_val: str, vault_path: str | None, now_iso: str
) -> None:
    preview = note["body_text"][:300].replace("\n", " ").strip()
    word_count = len(note["body_text"].split())
    conn.execute(
        """
        INSERT INTO apple_notes
            (id, title, folder, body_preview, word_count, created_str,
             modified_str, vault_path, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            title        = excluded.title,
            folder       = excluded.folder,
            body_preview = excluded.body_preview,
            word_count   = excluded.word_count,
            modified_str = excluded.modified_str,
            vault_path   = excluded.vault_path,
            updated_at   = excluded.updated_at
        """,
        (
            note_id_val,
            note["title"],
            note["folder"],
            preview,
            word_count,
            note["cre_str"],
            note["mod_str"],
            vault_path,
            now_iso,
        ),
    )


# ---------------------------------------------------------------------------
# Vault markdown
# ---------------------------------------------------------------------------

_SAFE_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def safe_filename(name: str, max_len: int = 80) -> str:
    clean = _SAFE_RE.sub("_", name).strip(". ")
    return (clean or "untitled")[:max_len]


def build_markdown(note: dict, note_id_val: str, now_iso: str) -> str:
    folder = note["folder"]
    title = note["title"]
    body = note["body_text"]
    word_count = len(body.split())

    lines = [
        "---",
        "type: apple_note",
        f"title: {title}",
        f"folder: {folder}",
        f"note_id: {note_id_val}",
        f"word_count: {word_count}",
        f"modified: {note['mod_str']}",
        f"created: {note['cre_str']}",
        f"updated_at: {now_iso}",
        "source: apple-notes",
        "---",
        "",
        f"# {title}",
        "",
        body,
        "",
    ]
    return "\n".join(lines)


def write_vault_file(
    vault_root: Path, note: dict, note_id_val: str, now_iso: str, dry_run: bool
) -> Path:
    folder_dir = vault_root / "Personal-Corpus" / "Notes" / safe_filename(note["folder"])
    fname = safe_filename(note["title"]) + ".md"
    dest = folder_dir / fname
    if not dry_run:
        folder_dir.mkdir(parents=True, exist_ok=True)
        dest.write_text(build_markdown(note, note_id_val, now_iso), encoding="utf-8")
    return dest


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest Apple Notes into AIOS knowledge system.")
    parser.add_argument(
        "--db",
        default=str(Path.home() / "AIOS" / "data" / "aios.db"),
        help="Path to aios.db",
    )
    parser.add_argument(
        "--vault",
        default=str(Path.home() / "Vaults" / "Command-Center"),
        help="Obsidian vault root",
    )
    parser.add_argument(
        "--folder",
        default=None,
        help="Only ingest notes from this folder (default: all)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max notes to process, 0 = all (default: 0)",
    )
    parser.add_argument(
        "--no-vault",
        action="store_true",
        help="Skip vault file writing (DB only)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without writing anything",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    aios_db = Path(args.db).expanduser()
    vault_root = Path(args.vault).expanduser()

    if not aios_db.exists() and not args.dry_run:
        print(f"ERROR: AIOS DB not found: {aios_db}", file=sys.stderr)
        sys.exit(1)

    now_iso = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    print("Reading Apple Notes via AppleScript (this may take a moment)...")
    try:
        notes = fetch_notes_applescript()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    if not notes:
        print("No notes found.")
        return

    if args.folder:
        notes = [n for n in notes if n["folder"].lower() == args.folder.lower()]

    if args.limit and args.limit > 0:
        notes = notes[: args.limit]

    print(f"Found {len(notes)} notes to process.")

    aios_conn: sqlite3.Connection | None = None
    if not args.dry_run:
        aios_conn = sqlite3.connect(str(aios_db))
        ensure_apple_notes_table(aios_conn)

    db_upserted = 0
    vault_written = 0
    errors: list[str] = []
    prefix = "DRY RUN  " if args.dry_run else ""

    for note in notes:
        try:
            nid = note_id(note["title"], note["folder"], note["cre_str"])
            vault_path: str | None = None

            if not args.no_vault:
                dest = write_vault_file(vault_root, note, nid, now_iso, dry_run=args.dry_run)
                vault_path = str(dest)
                vault_written += 1

            if aios_conn is not None:
                upsert_note(aios_conn, note, nid, vault_path, now_iso)
            db_upserted += 1

            wc = len(note["body_text"].split())
            print(f"  {prefix}[{note['folder']:<16}] {note['title'][:50]:<50}  {wc:>5}w")
        except Exception as exc:
            errors.append(f"{note['folder']}/{note['title']}: {exc}")

    if aios_conn is not None:
        aios_conn.commit()
        aios_conn.close()

    banner = "DRY RUN — " if args.dry_run else ""
    print(f"\n{banner}Summary")
    print(f"  Notes processed   : {len(notes)}")
    print(
        f"  DB upserts        : {db_upserted if not args.dry_run else 0} (preview: {db_upserted})"
    )
    print(
        f"  Vault files       : {vault_written if not args.dry_run else 0} (preview: {vault_written})"
    )
    print(f"  Errors            : {len(errors)}")
    for err in errors:
        print(f"    ERROR: {err}", file=sys.stderr)

    if not args.dry_run:
        print(f"\n  AIOS DB  : {aios_db}")
        if not args.no_vault:
            print(f"  Vault    : {vault_root}/Personal-Corpus/Notes/")


if __name__ == "__main__":
    main()
