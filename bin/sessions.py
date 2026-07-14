#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.session_providers import (  # noqa: E402
    PROVIDERS,
    ProviderCursor,
    SessionProvider,
    SourcePath,
)
from services.session_providers.base import NormalizedSession  # noqa: E402
from services.storage import connect as connect_storage  # noqa: E402

DB_PATH = Path(
    os.environ.get("AIOS_DB", str(Path.home() / "AIOS" / "data" / "aios.db"))
).expanduser()


@dataclass(frozen=True)
class SourceState:
    path: str
    mtime: float
    size: int
    content_hash: str


@dataclass(frozen=True)
class SyncResult:
    provider_id: str
    sources_found: int
    new_or_changed: int
    unchanged: int
    imported: int
    dry_run: bool
    errors: list[str]


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def connect(db_path: Path = DB_PATH, *, read_only: bool = False) -> sqlite3.Connection:
    if str(db_path) == ":memory:":
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        if not read_only:
            ensure_schema(conn)
        return conn
    if read_only and not db_path.exists():
        return sqlite3.connect(":memory:")
    conn = connect_storage(db_path, read_only=read_only)
    if not read_only:
        ensure_schema(conn)
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS session_provider_cursors (
          provider_id TEXT NOT NULL,
          source_path TEXT NOT NULL,
          last_mtime REAL,
          last_size INTEGER,
          last_hash TEXT,
          last_provider_session_id TEXT,
          last_scanned_at TEXT,
          PRIMARY KEY (provider_id, source_path)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS session_imports (
          stable_session_id TEXT PRIMARY KEY,
          provider_id TEXT NOT NULL,
          provider_session_id TEXT NOT NULL,
          workspace_path TEXT,
          workspace_id TEXT,
          project_id TEXT,
          started_at TEXT,
          updated_at TEXT,
          imported_at TEXT NOT NULL,
          source_files_json TEXT NOT NULL DEFAULT '[]',
          source_file_mtimes_json TEXT NOT NULL DEFAULT '{}',
          content_hash TEXT NOT NULL,
          title TEXT NOT NULL,
          participants_json TEXT NOT NULL DEFAULT '[]',
          messages_json TEXT NOT NULL DEFAULT '[]',
          tool_calls_json TEXT NOT NULL DEFAULT '[]',
          file_edits_json TEXT NOT NULL DEFAULT '[]',
          commands_run_json TEXT NOT NULL DEFAULT '[]',
          decisions_extracted_json TEXT NOT NULL DEFAULT '[]',
          todos_extracted_json TEXT NOT NULL DEFAULT '[]',
          errors_extracted_json TEXT NOT NULL DEFAULT '[]',
          summary_status TEXT NOT NULL,
          writeback_status TEXT NOT NULL,
          confidence REAL NOT NULL,
          provider_metadata_json TEXT NOT NULL DEFAULT '{}',
          redaction_incomplete INTEGER NOT NULL DEFAULT 0
        )
        """
    )


def source_state(source: SourcePath) -> SourceState:
    stat = source.path.stat()
    digest = hashlib.sha256()
    with source.path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return SourceState(
        path=str(source.path),
        mtime=stat.st_mtime,
        size=stat.st_size,
        content_hash=digest.hexdigest(),
    )


def load_cursors(conn: sqlite3.Connection, provider_id: str) -> dict[str, ProviderCursor]:
    try:
        rows = conn.execute(
            """
            SELECT provider_id, source_path, last_mtime, last_size, last_hash,
                   last_provider_session_id, last_scanned_at
            FROM session_provider_cursors
            WHERE provider_id = ?
            """,
            (provider_id,),
        ).fetchall()
    except sqlite3.OperationalError as exc:
        if "no such table" not in str(exc):
            raise
        rows = []
    return {
        str(row["source_path"]): ProviderCursor(
            provider_id=str(row["provider_id"]),
            source_path=str(row["source_path"]),
            last_mtime=row["last_mtime"],
            last_size=row["last_size"],
            last_hash=row["last_hash"],
            last_provider_session_id=row["last_provider_session_id"],
            last_scanned_at=row["last_scanned_at"],
        )
        for row in rows
    }


def source_changed(state: SourceState, cursor: ProviderCursor | None, *, backfill: bool) -> bool:
    if backfill or cursor is None:
        return True
    return not (
        cursor.last_mtime == state.mtime
        and cursor.last_size == state.size
        and cursor.last_hash == state.content_hash
    )


def upsert_session_import(conn: sqlite3.Connection, normalized: NormalizedSession) -> None:
    conn.execute(
        """
        INSERT INTO session_imports (
          stable_session_id, provider_id, provider_session_id, workspace_path,
          workspace_id, project_id, started_at, updated_at, imported_at,
          source_files_json, source_file_mtimes_json, content_hash, title,
          participants_json, messages_json, tool_calls_json, file_edits_json,
          commands_run_json, decisions_extracted_json, todos_extracted_json,
          errors_extracted_json, summary_status, writeback_status, confidence,
          provider_metadata_json, redaction_incomplete
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(stable_session_id) DO UPDATE SET
          workspace_path = excluded.workspace_path,
          workspace_id = excluded.workspace_id,
          project_id = excluded.project_id,
          updated_at = excluded.updated_at,
          imported_at = excluded.imported_at,
          source_files_json = excluded.source_files_json,
          source_file_mtimes_json = excluded.source_file_mtimes_json,
          content_hash = excluded.content_hash,
          title = excluded.title,
          participants_json = excluded.participants_json,
          messages_json = excluded.messages_json,
          tool_calls_json = excluded.tool_calls_json,
          file_edits_json = excluded.file_edits_json,
          commands_run_json = excluded.commands_run_json,
          decisions_extracted_json = excluded.decisions_extracted_json,
          todos_extracted_json = excluded.todos_extracted_json,
          errors_extracted_json = excluded.errors_extracted_json,
          summary_status = excluded.summary_status,
          writeback_status = excluded.writeback_status,
          confidence = excluded.confidence,
          provider_metadata_json = excluded.provider_metadata_json,
          redaction_incomplete = excluded.redaction_incomplete
        """,
        (
            normalized.stable_session_id,
            normalized.provider,
            normalized.provider_session_id,
            normalized.workspace_path,
            normalized.workspace_id,
            normalized.project_id,
            normalized.started_at,
            normalized.updated_at,
            normalized.imported_at,
            json.dumps(normalized.source_files),
            json.dumps(normalized.source_file_mtimes),
            normalized.content_hash,
            normalized.title,
            json.dumps(normalized.participants),
            json.dumps(normalized.messages),
            json.dumps(normalized.tool_calls),
            json.dumps(normalized.file_edits),
            json.dumps(normalized.commands_run),
            json.dumps(normalized.decisions_extracted),
            json.dumps(normalized.todos_extracted),
            json.dumps(normalized.errors_extracted),
            normalized.summary_status,
            normalized.writeback_status,
            normalized.confidence,
            json.dumps(normalized.provider_metadata),
            1 if normalized.redaction_incomplete else 0,
        ),
    )


def update_cursor(
    conn: sqlite3.Connection,
    provider_id: str,
    state: SourceState,
    provider_session_id: str,
) -> None:
    conn.execute(
        """
        INSERT INTO session_provider_cursors (
          provider_id, source_path, last_mtime, last_size, last_hash,
          last_provider_session_id, last_scanned_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(provider_id, source_path) DO UPDATE SET
          last_mtime = excluded.last_mtime,
          last_size = excluded.last_size,
          last_hash = excluded.last_hash,
          last_provider_session_id = excluded.last_provider_session_id,
          last_scanned_at = excluded.last_scanned_at
        """,
        (
            provider_id,
            state.path,
            state.mtime,
            state.size,
            state.content_hash,
            provider_session_id,
            now_iso(),
        ),
    )


def provider_ids(args: argparse.Namespace) -> list[str]:
    selected = getattr(args, "provider", None)
    if selected:
        if selected not in PROVIDERS:
            raise ValueError(f"Unknown provider: {selected}")
        return [selected]
    if getattr(args, "all", False):
        return sorted(PROVIDERS)
    raise ValueError("Specify --provider <id> or --all")


def instantiate_provider(provider_id: str) -> SessionProvider:
    return PROVIDERS[provider_id]()


def sync_provider(
    conn: sqlite3.Connection,
    provider_id: str,
    *,
    dry_run: bool,
    backfill: bool,
) -> SyncResult:
    provider = instantiate_provider(provider_id)
    cursors = load_cursors(conn, provider_id)
    sources = provider.discover_sources()
    changed = 0
    unchanged = 0
    imported = 0
    errors: list[str] = []

    for source in sources:
        try:
            state = source_state(source)
            if not source_changed(state, cursors.get(state.path), backfill=backfill):
                unchanged += 1
                continue
            changed += 1
            if dry_run:
                continue
            raw = provider.extract_raw_session(source)
            normalized = provider.normalize_session(raw)
            provider.upsert_session(normalized)
            upsert_session_import(conn, normalized)
            update_cursor(conn, provider_id, state, normalized.provider_session_id)
            imported += 1
        except Exception as exc:  # noqa: BLE001 - provider sync reports per-source failures.
            errors.append(f"{source.path}: {exc}")

    if not dry_run:
        conn.commit()

    return SyncResult(
        provider_id=provider_id,
        sources_found=len(sources),
        new_or_changed=changed,
        unchanged=unchanged,
        imported=imported,
        dry_run=dry_run,
        errors=errors,
    )


def print_sync_result(result: SyncResult) -> None:
    prefix = "[dry-run] " if result.dry_run else ""
    print(
        f"{prefix}{result.provider_id}: {result.sources_found} sources found, "
        f"{result.new_or_changed} new/changed, {result.unchanged} unchanged, "
        f"{result.imported} imported"
    )
    for error in result.errors:
        print(f"{result.provider_id}: error: {error}", file=sys.stderr)


def command_sync(args: argparse.Namespace) -> int:
    with connect(read_only=bool(args.dry_run)) as conn:
        exit_code = 0
        for provider_id in provider_ids(args):
            result = sync_provider(
                conn,
                provider_id,
                dry_run=bool(args.dry_run),
                backfill=False,
            )
            print_sync_result(result)
            if result.errors:
                exit_code = 1
        return exit_code


def command_backfill(args: argparse.Namespace) -> int:
    with connect() as conn:
        exit_code = 0
        for provider_id in provider_ids(args):
            result = sync_provider(conn, provider_id, dry_run=False, backfill=True)
            print_sync_result(result)
            if result.errors:
                exit_code = 1
        return exit_code


def command_repair(args: argparse.Namespace) -> int:
    with connect() as conn:
        result = sync_provider(conn, str(args.provider), dry_run=False, backfill=True)
        print_sync_result(result)
        return 1 if result.errors else 0


def command_status(_args: argparse.Namespace) -> int:
    with connect(read_only=True) as conn:
        try:
            rows = conn.execute(
                """
                SELECT c.provider_id,
                       COUNT(*) AS source_count,
                       MAX(c.last_scanned_at) AS last_scanned_at,
                       COUNT(i.stable_session_id) AS imported_sessions
                FROM session_provider_cursors c
                LEFT JOIN session_imports i ON i.provider_id = c.provider_id
                GROUP BY c.provider_id
                ORDER BY c.provider_id
                """
            ).fetchall()
        except sqlite3.OperationalError as exc:
            if "no such table" not in str(exc):
                raise
            rows = []
    if not rows:
        print("No provider cursor state recorded.")
        return 0
    for row in rows:
        print(
            f"{row['provider_id']}: {row['source_count']} sources, "
            f"{row['imported_sessions']} imported sessions, "
            f"last scanned {row['last_scanned_at'] or 'never'}"
        )
    return 0


def command_debug(args: argparse.Namespace) -> int:
    provider = instantiate_provider(str(args.provider))
    health = provider.health_check()
    print(json.dumps(health.__dict__, indent=2, sort_keys=True))
    return 0 if health.ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AIOS session provider operations")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sync = subparsers.add_parser("sync", help="Run incremental provider sync")
    sync.add_argument("--provider", choices=sorted(PROVIDERS))
    sync.add_argument("--all", action="store_true")
    sync.add_argument("--dry-run", action="store_true")
    sync.set_defaults(func=command_sync)

    status = subparsers.add_parser("status", help="Show recorded provider sync status")
    status.set_defaults(func=command_status)

    backfill = subparsers.add_parser("backfill", help="Scan all sources ignoring cursors")
    backfill.add_argument("--provider", choices=sorted(PROVIDERS))
    backfill.add_argument("--all", action="store_true")
    backfill.set_defaults(func=command_backfill)

    repair = subparsers.add_parser("repair", help="Re-normalize sessions for one provider")
    repair.add_argument("--provider", required=True, choices=sorted(PROVIDERS))
    repair.set_defaults(func=command_repair)

    debug = subparsers.add_parser("debug", help="Show provider health without private content")
    debug.add_argument("--provider", required=True, choices=sorted(PROVIDERS))
    debug.set_defaults(func=command_debug)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except ValueError as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
