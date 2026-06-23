# Session Ingestion

## Architecture

```text
provider discovery
  -> cursor comparison
  -> extract raw provider payload
  -> normalize to NormalizedSession
  -> redact session content
  -> upsert SQLite session_imports
  -> summarize into SessionSummary
  -> emit governed writeback proposals
  -> auto_ingest.sh promotes approved summary JSON
```

Providers implement `services.session_providers.base.SessionProvider`. The registry in `services/session_providers/__init__.py` exposes `claude`, `codex`, `cursor`, and `antigravity`.

## Session Lifecycle

1. `discover_sources()` lists local files or databases.
2. `session_provider_cursors` records mtime, size, hash, and provider session id.
3. Changed sources are extracted and normalized.
4. `redact_session()` runs before summary or writeback generation.
5. `session_imports` stores normalized session content.
6. `summarize_session()` produces the 16-field summary contract.
7. `emit_writeback_candidates()` writes proposal JSON under `logs/summaries/`.
8. `bin/auto_ingest.sh` remains the governed promotion path into the vault.

## Add A Provider

- Implement all nine `SessionProvider` methods.
- Return `SourcePath`, `RawSession`, and `NormalizedSession` objects.
- Keep provider source files read-only.
- Never write raw transcripts to the curated vault.
- Register the provider in `PROVIDERS`.
- Add fixture-backed tests for discovery, extraction, normalization, redaction, sync, and writeback.

## Cron Wiring

Suggested cron entry:

```cron
0 * * * * python3 ~/AIOS/bin/cron-ingest-sessions.py >> ~/AIOS/logs/cron.log 2>&1
```

This complements `cron-ingest-codex.py`; it does not replace it.

## Privacy Model

Raw provider content stays in SQLite or provider-local source pointers. Redaction runs before summaries and writeback candidates. Sessions with incomplete redaction are held with `summary_status='redaction_incomplete'` and do not produce vault note candidates.

## Writeback Flow

`services/session_writeback.py` emits structured proposals only. It writes JSON compatible with the existing `logs/summaries/` flow and optionally records `memory_writeback_proposals` rows. Vault mutation remains governed by `auto_ingest.sh`.
