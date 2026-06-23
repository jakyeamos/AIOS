# Session Provider Backfill Report

**Generated:** 2026-06-23
**Mode:** local dry run / debug only

Verification coverage: pipeline summary; provider summaries; detected local paths; dry-run results; risks; next improvements.

## Existing Claude/Codex Pipeline

- Claude Code parsing is wrapped from `bin/import_ai_history.py`.
- Codex rollout parsing and existing cron behavior are preserved.
- Existing Codex cron still uses `bin/cron-ingest-codex.py`.
- Existing Obsidian promotion still uses `bin/auto_ingest.sh` and `~/AIOS/logs/summaries/`.

## Cursor Dry Run

Command:

```bash
python3 bin/sessions.py sync --provider cursor --dry-run
```

Observed output:

```text
[dry-run] cursor: 45 sources found, 45 new/changed, 0 unchanged, 0 imported
```

Debug health observed 44 workspace SQLite databases, 1 global SQLite database, 0 JSONL transcript files, 37 extractable sessions, and 21 sources with sessions. Four Cursor workspace databases were unreadable and surfaced as warnings, not fatal errors, because other sources were readable.

## Antigravity Dry Run

Command:

```bash
python3 bin/sessions.py debug --provider antigravity
```

Observed source counts:

- JSON: 439
- JSONL: 12
- Markdown: 752
- SQLite: 13
- Text: 513
- Unknown binary: 3
- Session candidates: 0

Warnings included a missing `~/.config/Antigravity` root and three unknown binary artifacts stored as metadata-only.

## Risks And Limitations

- Cursor source readability depends on live database locks and local permissions.
- Antigravity source layout may change because it is inferred from local Gemini/Antigravity paths.
- `memory_writeback_proposals` was originally designed for divergent strategy runs, so session writebacks use the existing proposal table conservatively.
- The first real non-dry sync should be run with a DB backup available.

## Next Recommended Improvements

1. Add a first-class `session_writeback_proposals` table if session writebacks need richer review semantics.
2. Add Windows path support for Cursor and Antigravity providers.
3. Add provider config loading to enforce `enabled`, ignore patterns, retention, and minimum word thresholds at runtime.
4. Add UI status for provider cursors and redaction-held sessions.
