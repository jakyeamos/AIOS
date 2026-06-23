# Phase 13: Multi-Provider Session Ingestion And Second Brain Data Pipeline - Context

**Gathered:** 2026-06-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 13 extends the existing Claude/Codex session ingestion pipeline into a formal provider system for Claude, Codex, Cursor, and Antigravity. The phase delivers normalized, provenance-backed, privacy-safe session ingestion into the local SQLite operational database, plus structured summaries and governed writeback proposals. It does not replace existing Claude/Codex behavior, does not implement graph memory compilation, and does not write raw transcripts or reasoning traces into the curated vault.

</domain>

<decisions>
## Implementation Decisions

### Provider Boundaries
- Use a strict `NormalizedSession` contract with provider-specific raw metadata stored separately.
- Wrap Claude and Codex through adapter wrappers that preserve existing behavior instead of rewriting the current ingestion flow.
- Treat unknown Antigravity formats as metadata-only skips with a surfaced health warning.
- Read Cursor SQLite sources through read-only temp-copy safety rather than direct mutable database access.

### Redaction And Writeback
- Run secret redaction before summaries and writeback proposal generation.
- Hold sessions with `redaction_incomplete=true` when redaction safety is uncertain.
- Store raw session content only in SQLite or source pointers; do not create raw vault notes.
- Emit governed writeback proposals through the existing flow instead of automatic vault mutation.

### CLI, Sync, And Tests
- Add `bin/sessions.py` as the primary operator CLI with dry-run, backfill, repair, sync, debug, and status modes.
- Add `session_provider_cursors` for provider-aware incremental state and idempotent upserts, complementing existing `processed_files` behavior.
- Use fixture-driven acceptance tests for all four providers plus idempotency, redaction, summary, and writeback behavior.
- Produce a live dry-run backfill report under `docs/backfills/` instead of relying only on runtime logs.

### Claude's Discretion
Implementation details not covered above are at Claude's discretion, constrained by the existing Python service style, SQLite-first persistence, and GSD/AIOS governance requirements.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `bin/import_ai_history.py` contains existing Claude, Codex, and ChatGPT parsing logic and should be wrapped rather than rewritten.
- `bin/cron-ingest-codex.py` provides the current Codex cron ingestion pattern and `processed_files` dedup behavior.
- `bin/auto_ingest.sh` already promotes structured summary JSON from `logs/summaries/` into governed Obsidian handoff notes.
- `schema.sql` is the persistent schema authority for new SQLite tables.
- Existing root Python modules use the standard library heavily, especially `sqlite3`, `pathlib`, `json`, and narrow filesystem helpers.

### Established Patterns
- AIOS is local-first: files, SQLite, local logs, and explicit docs are authoritative runtime surfaces.
- Python code favors explicit dataclasses, `TypedDict` shapes, postponed annotations, and public helper return types.
- Operational scripts tolerate partial failure at lifecycle boundaries but keep failure surfaces narrow and inspectable.
- Cross-process or durable data shapes should be explicit and test-backed rather than loose dictionaries.
- Generated or operational artifacts under `logs/`, `staging/`, and local DB stores should not become source unless explicitly promoted.

### Integration Points
- Session provider imports should write durable state to `data/aios.db` and use checked-in schema/migration surfaces.
- New provider summaries should feed the existing `logs/summaries/` and `auto_ingest.sh` proposal path.
- Cursor source discovery targets local macOS Cursor workspace/global SQLite databases and JSONL transcript paths.
- Antigravity source discovery targets local Gemini/Antigravity brain, plugin, config, and session directories.
- Operator docs should land under `docs/session-providers/`, `docs/session-ingestion.md`, and `docs/backfills/`.

</code_context>

<specifics>
## Specific Ideas

- Preserve current Claude/Codex ingestion behavior and tests.
- Treat provider support as additive and governed, not a replacement migration.
- Keep raw private transcript material out of curated vault notes.
- Surface redaction failures, unknown binary Antigravity files, and provider health issues as operator-visible status.
- Make two consecutive no-change syncs produce identical DB state.

</specifics>

<deferred>
## Deferred Ideas

Graph memory compilation and cache-aware context compilation belong to Phase 12, not this provider ingestion phase.

</deferred>
