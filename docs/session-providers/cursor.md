# Cursor Session Provider

Verification coverage: what is imported; what is not; paths by OS; privacy warnings; backfill/sync/debug/disable instructions.

## What Is Imported

The Cursor provider imports local AI chat/session evidence from:

- Workspace SQLite databases: `~/Library/Application Support/Cursor/User/workspaceStorage/**/state.vscdb`
- Global SQLite database: `~/Library/Application Support/Cursor/User/globalStorage/state.vscdb`
- Agent transcript JSONL files: `~/.cursor/projects/**/agent-transcripts/*.jsonl`

It extracts chat messages, tool calls, command strings, file-edit metadata, workspace hash, and resolved workspace path when available.

## What Is Not Imported

The provider does not import Cursor settings, extensions, general editor state, non-AI cache entries, or raw database files. Unknown ItemTable values are skipped.

## Default Paths By OS

- macOS: `~/Library/Application Support/Cursor/User/...`
- Linux: `~/.config/Cursor/User/...`
- Windows: Cursor support should be added with a platform path adapter before use.

## Privacy And Security

Cursor databases are opened read-only. Locked databases are copied to a temporary snapshot under `~/AIOS/staging/cursor-snapshots/` and read from the copy. Cursor source files are never modified. Raw session content stays in SQLite; curated vault notes receive only structured summaries.

## Backfill

```bash
python3 ~/AIOS/bin/sessions.py backfill --provider cursor
```

Backfill scans all discovered Cursor sources and upserts by stable session id.

## Incremental Sync

```bash
python3 ~/AIOS/bin/sessions.py sync --provider cursor
```

The sync command compares source mtime, size, and SHA-256 hash against `session_provider_cursors`.

## Debug Provider Health

```bash
python3 ~/AIOS/bin/sessions.py debug --provider cursor
```

Debug output reports source counts and session counts without printing message content.

## Disable

Remove `cursor` from `session_providers.enabled` in `config/session-provider-config.yaml`.

## Add Another Provider

Implement `SessionProvider`, return `NormalizedSession`, add the provider to `services/session_providers/__init__.py`, and add fixture-backed tests.
