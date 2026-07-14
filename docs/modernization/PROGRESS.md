# AIOS V2 Modernization Progress

**Status:** Milestone 1 in progress
**Updated:** 2026-07-13
**Plan:** [EXEC_PLAN.md](EXEC_PLAN.md)

## Current slice

Milestone 1 now establishes the first executable Python-owned storage boundary
for the main store. The shared connection contract resolves one `AIOS_DB`,
applies canonical SQLite pragmas, and supports read-only projections. The
versioned migration ledger, quarantine inventory, and backup/restore helpers
operate only against explicit disposable paths in this slice. The copied-store
runner now snapshots preflight health/counts, applies an explicit transformer,
requires zero FK violations before recording the ledger, and emits a post-
migration backup; the live store has not been migrated.

## Completed

- Added `aios-v2-vertical-fixtures-v0.1` with healthy, empty, blocked, failed,
  needs-review, and closed scenarios.
- Added a TypeScript runtime shape guard so the UI compiler validates the
  shared JSON shape without creating a second runtime model.
- Added Python coverage for state completeness, cross-reference integrity,
  Python ownership of route authority, persisted evidence/writeback rows, and
  daily-flow replay.
- Added a disposable SQLite projection that maps the closed fixture to
  `orchestration_runs`, `briefing_packets`, `evidence_artifacts`,
  `success_criteria_findings`, and `improvement_writebacks` without touching
  the live store.
- Added `services/storage.py` as the first Python-owned main-store contract:
  resolved `AIOS_DB` paths, `foreign_keys`/WAL/busy-timeout/query-only
  pragmas, an idempotent `schema_migrations` ledger, quarantine records,
  schema checksums, health checks, and immutable local backup/restore helpers.
- Routed the CLI's shared `_connect_db` path through the storage contract while
  preserving its existing missing-database error behavior.
- Added `services/migration_runner.py` for copied-store migrations with
  preflight/postflight health, scoped table-count reconciliation, explicit
  quarantine ids, forward-only ledger recording, and post-migration backup.
- Preserved user-owned guidance files and generated context artifacts outside
  the scoped implementation change.

## Verification

- `pnpm context:validate` — passed.
- `uv run pytest tests/test_v2_vertical_fixtures.py -q` — passed (3 tests).
- `pnpm --dir aios-ui exec tsc --noEmit` — passed.
- `.venv/bin/ruff check tests/test_v2_vertical_fixtures.py` — passed.
- `.venv/bin/basedpyright tests/test_v2_vertical_fixtures.py` — passed.
- `.venv/bin/pytest tests/test_storage.py tests/test_migration_runner.py tests/test_aios_cli.py -q` — passed (98 tests).
- `.venv/bin/ruff check services/storage.py services/aios_cli.py tests/test_storage.py` — passed.
- `.venv/bin/basedpyright services/storage.py services/aios_cli.py tests/test_storage.py` — passed.
- `pnpm --dir aios-ui lint:architecture` — passed (122 modules, 255 dependencies).
- `pnpm quality:eval` — interrupted after the broad vulture scan expanded into
  historical shadow worktrees; the focused checks above are the relevant proof.

## Complexity + simplification gate

### Gate A: complexity and performance

- The TypeScript guard and Python test walk fixture, evidence, and approval
  arrays once; complexity is linear in the fixture document and is not on a
  request or render path.
- No nested growing-collection scans, database calls, serialization loops, or
  client-side derived rendering were added.

### Gate B: simplification and maintainability

- The JSON remains the single fixture source; TypeScript validates it at the
  UI boundary and Python validates cross-reference integrity.
- The allowed-state lists are intentionally repeated in the two language
  validators because no shared runtime package exists yet. This is a low-risk
  deferred consolidation candidate for a future contract package, not a second
  state owner.
- The explicit fixture fields are retained because later slices need stable
  machine-readable evidence, approval, and projection semantics; no page-local
  UI behavior was introduced.
- The storage slice keeps migration execution, quarantine disposition, and
  restore orchestration separate from the connection contract; callers can
  adopt one owner without adding a second runtime schema or silently repairing
  live rows.
- The copied-store runner accepts an explicit transformer rather than embedding
  guessed parent-repair rules; known row mappings remain migration-specific and
  must be evidence-backed before they touch the production-shaped copy.

### Gate C: verification

Focused tests, type checks, lint, architecture, and context validation passed.
The broad quality-eval command is not a trustworthy focused signal while it
recurses through historical shadow worktrees, so its interruption is recorded
instead of being presented as a pass.

## Milestone 0 completion

The closed fixture replay produced the canonical eight-step trace. Route,
packet, run, evaluation, and writeback steps pointed to persisted row ids;
all fixture evidence ids were present in `evidence_artifacts`; and the replay
performed no writes. This is the seeded read-only evidence required before
live migration work.

## Remaining Milestone 1 work

- Route hooks, storage helpers, and UI adapters through the shared connection
  contract without changing the canonical `AIOS_DB` meaning.
- Add the first production-shaped migration transformer that captures preflight
  counts/checksums, quarantines ambiguous rows, and records every forward-only
  migration.
- Complete the backup/restore drill and reconcile the current store's FK
  violations before any write-capable v2 slice.

## Known blockers

- The baseline UI lint/build gates remain blocked by ADR-004's known external
  anti-slop dependency, font, root/tracing, and tRPC adapter issues.
- The main store still requires ADR-002 quarantine, migration, and restore
  proof before any write-capable slice.
