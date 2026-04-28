#!/usr/bin/env python3
"""
AIOS: ingest-imessage — iMessage → AIOS knowledge system.

Reads ~/Library/Messages/chat.db (via /tmp copy to avoid WAL lock),
upserts contact activity into aios.db::imessage_contacts, and writes
per-contact markdown files to the Personal-Corpus vault.
"""

import argparse
import re
import shutil
import sqlite3
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

APPLE_EPOCH_OFFSET = 978307200  # seconds between 1970-01-01 and 2001-01-01
SNIPPET_MAX = 120  # characters for last_message_snippet
RECENT_OUTGOING = 5  # number of outgoing messages shown in vault file


# ---------------------------------------------------------------------------
# iMessage helpers
# ---------------------------------------------------------------------------


def apple_ts_to_unix(apple_ns: int) -> int:
    """Convert Apple nanosecond timestamp (epoch 2001-01-01) to Unix seconds."""
    return apple_ns // 1_000_000_000 + APPLE_EPOCH_OFFSET


def unix_to_iso(unix_ts: int) -> str:
    return datetime.fromtimestamp(unix_ts, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def safe_filename(name: str) -> str:
    """Strip characters that are problematic in file names."""
    clean = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    return clean.strip(". ") or "unknown"


def format_contact_id(phone_or_email: str) -> str:
    """Normalise to a stable primary key: strip whitespace, lowercase."""
    return phone_or_email.strip().lower()


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def open_imessage_db(source_path: Path) -> sqlite3.Connection:
    """Copy source_path to a temp file and open it read-only."""
    # delete=False so the file outlives the handle — sqlite3.connect() needs a path.
    tmp = tempfile.NamedTemporaryFile(  # noqa: SIM115
        suffix=".db", delete=False, prefix="aios-imessage-"
    )
    tmp.close()
    shutil.copy2(source_path, tmp.name)
    conn = sqlite3.connect(f"file:{tmp.name}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_imessage_contacts_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS imessage_contacts (
            id                  TEXT PRIMARY KEY,
            phone_or_email      TEXT NOT NULL,
            display_name        TEXT NOT NULL,
            message_count       INTEGER NOT NULL DEFAULT 0,
            last_message_at     TEXT NOT NULL,
            last_message_snippet TEXT NOT NULL DEFAULT '',
            updated_at          TEXT NOT NULL
        )
        """
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


def fetch_contacts(
    im_conn: sqlite3.Connection,
    cutoff_unix: int,
    limit: int,
) -> list[dict]:
    """
    Return one record per unique handle (contact) active since cutoff_unix.

    Aggregates across all chats that include the handle, so a person who
    appears in multiple group chats is counted once.  Outgoing snippets are
    pulled from 1:1 chats only (chat_identifier == handle.id) so they reflect
    direct messages, not group-chat blasts.

    Each record: {
        contact_id, phone_or_email, display_name,
        message_count, last_message_at (iso), last_message_snippet,
        outgoing_snippets: list[str]   # up to RECENT_OUTGOING outgoing texts
    }
    """
    # One row per handle that has sent/received at least one non-empty message
    # within the cutoff window.  Aggregate across all chats.
    handle_rows = im_conn.execute(
        """
        SELECT
            h.rowid         AS handle_rowid,
            h.id            AS handle_id,
            COUNT(m.rowid)  AS message_count,
            MAX(m.date)     AS last_date,
            -- grab text of the most-recent message for the snippet
            (
                SELECT m2.text
                FROM message m2
                WHERE m2.handle_id = h.rowid
                  AND m2.text IS NOT NULL AND m2.text != ''
                  AND (m2.date / 1000000000 + ?) >= ?
                ORDER BY m2.date DESC
                LIMIT 1
            ) AS last_text
        FROM handle h
        JOIN message m ON m.handle_id = h.rowid
        WHERE m.text IS NOT NULL
          AND m.text != ''
          AND (m.date / 1000000000 + ?) >= ?
        GROUP BY h.rowid
        ORDER BY last_date DESC
        LIMIT ?
        """,
        (
            APPLE_EPOCH_OFFSET,
            cutoff_unix,  # subquery args
            APPLE_EPOCH_OFFSET,
            cutoff_unix,  # outer WHERE args
            limit,
        ),
    ).fetchall()

    results: list[dict] = []

    for row in handle_rows:
        raw_handle_id: str = row["handle_id"] or ""
        contact_id = format_contact_id(raw_handle_id)
        if not contact_id:
            continue

        last_unix = apple_ts_to_unix(row["last_date"])
        snippet = (row["last_text"] or "")[:SNIPPET_MAX]

        # Outgoing messages from the 1:1 chat with this handle (if one exists)
        # chat_identifier for iMessage 1:1 chats equals the handle id.
        outgoing_all = im_conn.execute(
            """
            SELECT m.text
            FROM message m
            JOIN chat_message_join cmj ON cmj.message_id = m.rowid
            JOIN chat c               ON c.rowid = cmj.chat_id
            WHERE c.chat_identifier = ?
              AND m.is_from_me = 1
              AND m.text IS NOT NULL
              AND m.text != ''
            ORDER BY m.date DESC
            LIMIT ?
            """,
            (raw_handle_id, RECENT_OUTGOING),
        ).fetchall()

        outgoing_snippets = [r["text"] for r in outgoing_all]

        results.append(
            {
                "contact_id": contact_id,
                "phone_or_email": raw_handle_id,
                "display_name": raw_handle_id,  # phone/email — no Contacts DB access
                "message_count": row["message_count"],
                "last_message_at": unix_to_iso(last_unix),
                "last_message_snippet": snippet,
                "outgoing_snippets": outgoing_snippets,
            }
        )

    return results


# ---------------------------------------------------------------------------
# AIOS DB writes
# ---------------------------------------------------------------------------


def upsert_contact(aios_conn: sqlite3.Connection, contact: dict, now_iso: str) -> None:
    aios_conn.execute(
        """
        INSERT INTO imessage_contacts
            (id, phone_or_email, display_name, message_count,
             last_message_at, last_message_snippet, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            phone_or_email       = excluded.phone_or_email,
            display_name         = excluded.display_name,
            message_count        = excluded.message_count,
            last_message_at      = excluded.last_message_at,
            last_message_snippet = excluded.last_message_snippet,
            updated_at           = excluded.updated_at
        """,
        (
            contact["contact_id"],
            contact["phone_or_email"],
            contact["display_name"],
            contact["message_count"],
            contact["last_message_at"],
            contact["last_message_snippet"],
            now_iso,
        ),
    )


# ---------------------------------------------------------------------------
# Vault markdown
# ---------------------------------------------------------------------------


def build_markdown(contact: dict, now_iso: str) -> str:
    display_name = contact["display_name"]
    phone_or_email = contact["phone_or_email"]
    last_at = contact["last_message_at"]
    outgoing = contact["outgoing_snippets"]

    lines: list[str] = [
        "---",
        "type: contact",
        f"updated_at: {now_iso}",
        f"phone_or_email: {phone_or_email}",
        "source: imessage",
        "---",
        "",
        f"# {display_name}",
        "",
        f"**Last message:** {last_at}  ",
        f"**Messages (last 30 days):** {contact['message_count']}  ",
        "",
        "## Recent Outgoing Messages",
        "",
    ]

    if outgoing:
        for text in outgoing:
            safe = text.replace("\n", " ").replace("\r", " ")
            lines.append(f"- {safe}")
    else:
        lines.append("_No outgoing messages found._")

    lines.append("")
    return "\n".join(lines)


def write_vault_file(vault_root: Path, contact: dict, now_iso: str, dry_run: bool) -> Path:
    contacts_dir = vault_root / "Personal-Corpus" / "Contacts"
    fname = safe_filename(contact["display_name"]) + ".md"
    dest = contacts_dir / fname

    if dry_run:
        return dest

    contacts_dir.mkdir(parents=True, exist_ok=True)
    dest.write_text(build_markdown(contact, now_iso), encoding="utf-8")
    return dest


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest iMessage conversations into AIOS knowledge system."
    )
    parser.add_argument(
        "--db",
        default=str(Path.home() / "AIOS" / "data" / "aios.db"),
        help="Path to aios.db (default: ~/AIOS/data/aios.db)",
    )
    parser.add_argument(
        "--messages-db",
        default=str(Path.home() / "Library" / "Messages" / "chat.db"),
        help="Path to iMessage chat.db (default: ~/Library/Messages/chat.db)",
    )
    parser.add_argument(
        "--vault",
        default=str(Path.home() / "Vaults" / "Command-Center"),
        help="Obsidian vault root (default: ~/Vaults/Command-Center)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Only process contacts active in last N days (default: 30)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Max contacts to process (default: 200)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without writing to DB or vault",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    messages_db = Path(args.messages_db).expanduser()
    aios_db = Path(args.db).expanduser()
    vault_root = Path(args.vault).expanduser()

    if not messages_db.exists():
        print(f"ERROR: iMessage DB not found: {messages_db}", file=sys.stderr)
        sys.exit(1)

    if not aios_db.exists() and not args.dry_run:
        print(f"ERROR: AIOS DB not found: {aios_db}", file=sys.stderr)
        sys.exit(1)

    now_iso = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    cutoff_unix = int((datetime.now(UTC) - timedelta(days=args.days)).timestamp())

    # Open iMessage DB via /tmp copy
    print(f"Copying {messages_db} → /tmp (avoid WAL lock)...")
    try:
        im_conn = open_imessage_db(messages_db)
    except Exception as exc:
        print(f"ERROR: could not open iMessage DB: {exc}", file=sys.stderr)
        sys.exit(1)

    # Fetch contacts
    print(f"Extracting contacts active in last {args.days} days (limit={args.limit})...")
    try:
        contacts = fetch_contacts(im_conn, cutoff_unix, args.limit)
    except Exception as exc:
        print(f"ERROR: extraction failed: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        im_conn.close()

    if not contacts:
        print("No active contacts found in the specified window.")
        return

    # Open AIOS DB
    aios_conn: sqlite3.Connection | None = None
    if not args.dry_run:
        aios_conn = sqlite3.connect(str(aios_db))
        ensure_imessage_contacts_table(aios_conn)

    db_upserted = 0
    vault_written = 0
    errors: list[str] = []

    prefix = "DRY RUN  " if args.dry_run else ""

    for contact in contacts:
        try:
            # DB upsert
            if aios_conn is not None:
                upsert_contact(aios_conn, contact, now_iso)
                db_upserted += 1
            else:
                db_upserted += 1  # count for dry-run display

            # Vault file
            dest = write_vault_file(vault_root, contact, now_iso, dry_run=args.dry_run)
            vault_written += 1

            print(
                f"  {prefix}{contact['display_name']:<30}  "
                f"{contact['message_count']:>4} msgs  "
                f"last={contact['last_message_at'][:10]}  "
                f"→ {dest.name}"
            )
        except Exception as exc:
            errors.append(f"{contact['display_name']}: {exc}")

    if aios_conn is not None:
        aios_conn.commit()
        aios_conn.close()

    # Summary
    banner = "DRY RUN — " if args.dry_run else ""
    print(f"\n{banner}Summary")
    print(f"  Contacts processed : {len(contacts)}")
    print(f"  DB upserts         : {db_upserted}")
    print(f"  Vault files written: {vault_written if not args.dry_run else 0}")
    if args.dry_run:
        print(f"  Vault files preview: {vault_written}")
    print(f"  Errors             : {len(errors)}")
    for err in errors:
        print(f"    ERROR: {err}", file=sys.stderr)

    if not args.dry_run:
        print(f"\n  AIOS DB  : {aios_db}")
        print(f"  Vault    : {vault_root}/Personal-Corpus/Contacts/")


if __name__ == "__main__":
    main()
