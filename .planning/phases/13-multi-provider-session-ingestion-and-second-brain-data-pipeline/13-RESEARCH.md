# Phase 13: Multi-Provider Session Ingestion And Second Brain Data Pipeline — Research

**Gathered:** 2026-05-23
**Status:** Ready for planning

<source_spec>
## Source Architecture

Phase 13 is specified in the "Add Cursor and Antigravity as First-Class Local Session Providers" prompt (ingested 2026-05-23). The spec extends the existing Claude/Codex session ingestion pipeline into a formal provider system supporting Cursor and Antigravity CLI.

The source prompt is the authoritative design for this phase. This document distills implementation-ready constraints from that prompt and from a live audit of the existing pipeline code.
</source_spec>

<domain>
## Phase Boundary

Phase 13 is a data collection layer that feeds the memory architecture defined in Phase 12. It does not implement memory compilation or graph relationships — those belong to Phase 12. Phase 13 ensures that session data from all four providers (Claude, Codex, Cursor, Antigravity) flows into the operational SQLite database in a normalized, provenance-backed, privacy-safe form that Phase 12's Layer A (raw source memory) can consume.

Phase 13 must not disrupt or rewrite the existing Claude/Codex ingestion behavior. All existing tests must continue to pass. New providers are additive.
</domain>

<existing_pipeline>
## Existing Pipeline Audit (Live Code)

### Claude ingestion
- Source: `~/.claude/projects/**/*.jsonl` — scanned by hooks (hook-session-start, hook-stop, hook-prompt-submit)
- Processing: hooks write to `aios.db` in real time; `bin/import_ai_history.py` handles bulk/export parsing
- No provider abstraction: Claude-specific logic is embedded directly in `import_ai_history.py`

### Codex ingestion
- Source: `~/.codex/sessions/**/*.jsonl` (rollout files)
- Processing: `bin/cron-ingest-codex.py` — runs hourly, uses `processed_files` table for dedup, calls `import_ai_history.parse_codex_rollout()`
- Minimum quality filter: `MIN_WORDS = 50`
- Marks files with `INSERT OR IGNORE INTO processed_files (path, processed_at)`

### Deduplication
- Table: `processed_files` in `aios.db` — tracks path + processed_at
- Strategy: file-path identity; no content hash or mtime check currently

### Obsidian writeback
- Script: `bin/auto_ingest.sh` — hourly cron, reads `logs/summaries/*.json`, writes structured markdown to vault at `02 AI OS/02 Session Handoffs/`
- Not raw transcript dumps: structured note template with session metadata fields
- Does not write raw message content into vault notes

### No provider abstraction exists
`import_ai_history.py` handles Claude, Codex, and ChatGPT export parsing in one monolithic module. No `SessionProvider` protocol or registry pattern is present.

### Staging area
`~/AIOS/staging/ai-history/codex/` exists for codex staging; no equivalent for cursor/antigravity yet.
</existing_pipeline>

<key_questions>
## Key Questions Resolved from Design Spec

### Q1: Does Phase 13 replace the existing Claude/Codex ingestion?
No. Existing behavior is preserved and unchanged. The provider abstraction is introduced as a new module that wraps existing logic. `import_ai_history.py` is not rewritten — it is wrapped.

### Q2: Where do raw session imports go?
SQLite operational database (`~/AIOS/data/aios.db`). Specifically: a new `session_imports` table (or equivalent extension of existing session tracking) records the normalized session record. Raw content may be stored as a path pointer, not as a full blob in the DB by default.

### Q3: How does deduplication work for the new providers?
The existing `processed_files` table (path + processed_at) is extended or complemented with a richer `session_provider_cursors` table that tracks: provider_id, source_path, last_mtime, last_size, last_hash, last_provider_session_id, last_scanned_at. This enables incremental sync beyond simple path-based dedup.

### Q4: What are the Cursor data sources on macOS?
- `~/Library/Application Support/Cursor/User/workspaceStorage/**/state.vscdb` — per-workspace SQLite DBs (open read-only; copy to temp before reading)
- `~/Library/Application Support/Cursor/User/globalStorage/state.vscdb` — global SQLite DB
- `~/.cursor/projects/**/agent-transcripts/*.jsonl` — agent transcript JSONL files
- Useful `ItemTable` keys: `aiService.prompts`, `workbench.panel.aichat.view.aichat.chatdata`, any key containing `chat`, `composer`, `aichat`, `agent`, `conversation`

### Q5: What are the Antigravity data sources?
- `~/.gemini/antigravity-cli/brain/**` — primary brain/session directory
- `~/.gemini/antigravity-cli/plugins/**` — plugin state
- `~/.gemini/GEMINI.md` — config
- `~/.gemini/**` and `~/.config/Antigravity/**` — any config, log, cache, session directories
- File formats: JSON, JSONL, SQLite, Markdown, text logs, unknown binary
- Unknown formats: store metadata only, skip content, emit health warning

### Q6: How does Obsidian writeback work for new providers?
Same governed proposal flow as Claude/Codex: sessions generate a structured summary JSON in `logs/summaries/`, then `auto_ingest.sh` promotes approved candidates to vault notes. No raw chain-of-thought or reasoning traces in vault by default.

### Q7: What CLI commands does the spec require?
- `aios sessions sync --provider cursor`
- `aios sessions sync --provider antigravity`
- `aios sessions sync --all`
- `aios sessions status`
- `aios sessions sync --provider cursor --dry-run`
- `aios sessions debug --provider cursor` (lists sources, counts, no private content)
- `aios sessions debug --provider antigravity`
- `aios sessions backfill --provider cursor`
- `aios sessions repair --provider cursor`

### Q8: What must never go into the curated Obsidian vault?
- Raw transcripts or message dumps
- Reasoning traces / chain-of-thought
- API keys, tokens, .env contents, auth blobs
- Private credentials
These are flagged by secret redaction before any summary generation. Summaries that cannot be redacted safely are held in SQLite only.

### Q9: What docs does the spec require?
- `docs/session-providers/cursor.md`
- `docs/session-providers/antigravity.md`
- `docs/session-ingestion.md` (or update of existing)
- `docs/backfills/session-provider-backfill.md`
</key_questions>

<open_questions>
## Open Questions

All questions resolved from the design spec and live code audit. No blockers for planning.
</open_questions>
