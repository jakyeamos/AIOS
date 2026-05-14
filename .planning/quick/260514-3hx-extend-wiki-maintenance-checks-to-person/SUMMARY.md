# Summary

Extended wiki maintenance source refs to validate personal corpus records, not only repo files.

## Delivered

- Added corpus-aware source ref types to the UI shared model.
- Extended `pnpm wiki:check` to index `aios.db` through the local `sqlite3` CLI when available.
- Added validation for patterns, sessions, runs, briefing packets, memory updates, knowledge topics, vault notes, imported conversations, agent summaries, and task/writeback records.
- Documented corpus source-ref syntax in `docs/wiki-maintenance.md`.
- Added tests for corpus ref resolution and unresolved corpus drift findings.

## Verification

- `pnpm test:wiki`
- `pnpm wiki:check`
- `pnpm context:validate`
- `pnpm --dir aios-ui lint`
