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
requires zero FK violations before recording the ledger, and emits a
post-migration backup. The lifecycle hooks and UI database adapter now
converge on the same `AIOS_DB` override and baseline pragmas; UI-owned
request-time DDL remains a known blocker rather than an implicit migration
path.
Issues, handoffs, the read-only query CLI, the statusline, and the high-traffic
prompt-submit, precompact, post-tool-use, and session-stop hooks now use the
same storage connection contract as well. The managed runtime's six main-store
connection sites, Codex ingestion job, and session CLI now use that contract
too. Codex, Claude, Cursor, and Antigravity canonical session upserts now use
the same write boundary; provider source inspection remains provider-owned.
Stale-session repair, prompt-library sync, and workflow-experiment queue/run
utilities now use the same contract for their main-store connections.
The session-metric recorder is write-routed, while session evaluation and lab
reporting use read-only shared connections.
AI-history import and project-inventory sync now use the shared write boundary
and honor `AIOS_DB`; their source parsing and repository discovery remain
unchanged.
The iMessage and Apple Notes jobs now route only their AIOS writes through the
shared boundary; source database reads continue through disposable/read-only
provider paths.
The CLI doctor SQLite health probe now uses the same read-only connection
contract rather than a one-off connection.
The daily pipeline's pending-rule bundle query now uses the same read-only
connection contract and honors `AIOS_DB`.
The one-time pattern schema migration now uses the shared write connection and
honors `AIOS_DB`; its schema/data changes remain explicitly disposable until
the main-store migration gate is accepted.
Pattern extraction now uses the same shared write boundary while preserving its
idempotent workflow extraction and rollback-on-`--dry-run` behavior.
Pattern scoring now uses the same shared write boundary while preserving its
promotion/demotion rules and rollback-on-`--dry-run` behavior.
Pattern promotion now uses the same shared write boundary while preserving
noise/threshold gates and dry-run staging behavior.
Pattern confirmation, approval, and contradiction tools now use the same shared
write boundary while preserving their event ledger and state-transition gates.
Interactive observation review now uses the same shared write boundary while
preserving its human-choice state/event transitions.
Noise-pattern purging now uses the same shared write boundary while preserving
its idempotent discard filter and dry-run report.
The business-memory CLI suite now uses the same shared write boundary; its
path resolver honors `AIOS_DB` while source sync, compilation, lint, query, and
daemon behavior remain unchanged.
Bug-motif extraction now uses the same shared write boundary while preserving
known-motif seeding, bug-log scanning, and dry-run behavior.
Handoff-learning extraction now uses the same shared write boundary while
preserving frontmatter/project mapping, processed-file idempotency, and dry-run
behavior.
Personal-pattern extraction now uses the same shared write boundary while
preserving multi-session signal gates and dry-run behavior.
Personal-pattern promotion now uses the same shared write boundary while
preserving human-approval gating and dry-run vault behavior.
Agent synthesis now uses shared storage for both read-only corpus scans and
pattern writes while preserving title/tag clustering and dry-run behavior.
Domain-file generation now uses shared read-only storage while preserving
human-annotation retention, domain projections, and dry-run behavior.
DOCX and PDF indexers now use the shared write boundary while preserving
metadata extraction, optional dependency fallbacks, and dry-run behavior.
Rule-bundle registration now uses the shared write boundary while preserving
task generation, artifact updates, and bundle-status transitions.

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
- Added `services/migration_transformers.py` for the three documented FK
  classes: unique working-directory project mappings, quarantine/nulling of
  missing session references, and quarantine/nulling of shadow references to
  absent `eval_tasks`; it never creates synthetic parents.
- Routed `hook-stop.py`, `hook-session-start.py`, and `hook-update-focus.py`
  through `services.storage.connect`; updated `aios-ui/server/db.ts` to honor
  `AIOS_DB` and the same foreign-key/WAL/busy-timeout pragmas.
- Routed `issues_store`, `handoff_store`, `aios-query.py`, and
  `aios-statusline.py` through the shared storage connection; the query/status
  surfaces are explicitly read-only.
- Routed `hook-prompt-submit.py`, `hook-precompact.py`, and
  `hook-post-tool-use.py` through the shared storage connection, including the
  `AIOS_DB` override for precompact's previously fixed path.
- Routed `hook-session-stop.py` through the shared storage connection and
  repaired its direct-script repository import path; a disposable peer-trace
  start/stop integration passed without touching live rows.
- Routed all six `aios-managed-run.py` main-store connection sites through the
  shared storage contract; the managed-runtime handshake, TMCP shortcut,
  strategy-routing, and closeout-repair tests passed.
- Routed `cron-ingest-codex.py` through the shared storage connection and made
  its database path honor `AIOS_DB`; a disposable empty-rollout ingestion run
  exercised the processed-file ledger without touching live rows.
- Routed `bin/sessions.py` canonical database access through the shared storage
  contract while preserving its `:memory:` and missing read-only behavior;
  provider fixture sync and disposable pragma/schema checks passed.
- Routed the four provider canonical `upsert_session` paths through shared
  storage and made their default database paths honor `AIOS_DB`; source-store
  inspection connections were left unchanged.
- Routed `repair-stale-open-sessions.py`, `sync-prompts.py`,
  `queue-workflow-experiments.py`, and `run-workflow-skill-experiments.py`
  through shared storage, including `AIOS_DB` defaults and direct-script import
  paths where needed.
- Routed `record-metric.py`, `eval-session.py`, and `lab-report.py` through
  shared storage; reporting paths are explicitly read-only and all three now
  honor `AIOS_DB`.
- Routed `import-ai-history.py` and `sync-project-inventory.py` through shared
  storage, fixing their direct-script import paths and honoring `AIOS_DB`.
- Routed the AIOS write connections in `ingest-imessage.py` and
  `ingest-apple-notes.py` through shared storage, preserving their source
  database readers and direct-script import paths.
- Routed the CLI doctor SQLite health probe through shared read-only storage;
  the existing doctor/health release checks still pass.
- Routed the AIOS pipeline's pending-rule query through shared read-only
  storage and made its database path honor `AIOS_DB`.
- Routed `migrate-patterns.py` through shared storage and made its canonical
  database path honor `AIOS_DB`; a disposable schema/data migration smoke
  passed without touching live rows.
- Routed `extract-patterns.py` through shared storage and made its canonical
  database path honor `AIOS_DB`; workflow extraction tests and a disposable
  dry-run rollback smoke passed.
- Routed `score-patterns.py` through shared storage and made its canonical
  database path honor `AIOS_DB`; a disposable dry-run scoring smoke passed.
- Routed `promote-patterns.py` through shared storage and made its canonical
  database path honor `AIOS_DB`; a disposable dry-run staging smoke passed.
- Routed `approve-pattern.py`, `confirm-pattern.py`, and
  `contradict-pattern.py` through shared storage and made their canonical
  database paths honor `AIOS_DB`; a disposable lifecycle integration passed.
- Routed `review-observations.py` through shared storage and made its canonical
  database path honor `AIOS_DB`; a patched-input disposable review passed.
- Routed `purge-noise-patterns.py` through shared storage and made its canonical
  database path honor `AIOS_DB`; its focused tests and disposable dry-run passed.
- Routed the business-memory path resolver and five CLI entrypoints through
  shared storage; disposable init, compile dry-run, query, lint, and daemon
  connection proofs passed.
- Routed `extract-bug-motifs.py` through shared storage and made its canonical
  database path honor `AIOS_DB`; a disposable dry-run detection proof passed.
- Routed `extract-handoff-learnings.py` through shared storage and made its
  canonical database path honor `AIOS_DB`; a disposable handoff dry-run proof
  passed.
- Routed `extract-personal-patterns.py` through shared storage and made its
  canonical database path honor `AIOS_DB`; a disposable multi-session dry-run
  proof passed.
- Routed `promote-personal-patterns.py` through shared storage and made its
  canonical database path honor `AIOS_DB`; a disposable dry-run vault proof
  passed.
- Routed `agent-synthesis.py` through shared storage, keeping corpus scans
  read-only and making its canonical database path honor `AIOS_DB`; a
  disposable dry-run synthesis proof passed.
- Routed `build-domain-files.py` through shared read-only storage and made its
  canonical database path honor `AIOS_DB`; a disposable domain projection
  dry-run proof passed.
- Routed `index-docx.py` and `index-pdfs.py` through shared storage and made
  their canonical database paths honor `AIOS_DB`; disposable indexer dry-run
  proofs passed without live or indexed-row writes.
- Routed `generate-rule-bundle.py` through shared storage and made its
  canonical database path honor `AIOS_DB`; disposable bundle registration
  proof passed with FK enforcement.
- Preserved user-owned guidance files and generated context artifacts outside
  the scoped implementation change.

## Verification

- `pnpm context:validate` — passed.
- `uv run ruff check bin/aios-pipeline.py` — passed.
- `uv run basedpyright bin/aios-pipeline.py` — passed (0 errors).
- Disposable pipeline storage smoke — passed (pending-rule query through
  shared read-only storage with `query_only=1`).
- `uv run ruff check bin/migrate-patterns.py` — passed.
- `uv run basedpyright bin/migrate-patterns.py` — passed (0 errors).
- Disposable `migrate-patterns.py` integration — passed (columns, views,
  indexes, state/domain backfill, and human-approval quarantine).
- `uv run pytest tests/test_extract_patterns.py -q` — passed (2 tests).
- `uv run ruff check bin/extract-patterns.py tests/test_extract_patterns.py` — passed.
- `uv run basedpyright bin/extract-patterns.py tests/test_extract_patterns.py` — passed (0 errors).
- Disposable `extract-patterns.py --dry-run` integration — passed (workflow
  extraction rolled back with zero pattern writes).
- `uv run ruff check bin/score-patterns.py` — passed.
- `uv run basedpyright bin/score-patterns.py` — passed (0 errors).
- Disposable `score-patterns.py --dry-run` integration — passed (one pattern
  scored without persisted score/state writes).
- `uv run ruff check bin/promote-patterns.py` — passed.
- `uv run basedpyright bin/promote-patterns.py` — passed (0 errors).
- Disposable `promote-patterns.py --dry-run` integration — passed (candidate
  stub plan generated with no pattern or staging writes).
- `uv run ruff check bin/approve-pattern.py bin/confirm-pattern.py bin/contradict-pattern.py` — passed.
- `uv run basedpyright bin/approve-pattern.py bin/confirm-pattern.py bin/contradict-pattern.py` — passed (0 errors).
- Disposable pattern lifecycle integration — passed (confirmation, gated
  promotion, contradiction demotion, approval reset, and event ledger).
- `uv run ruff check bin/review-observations.py` — passed.
- `uv run basedpyright bin/review-observations.py` — passed (0 errors).
- Disposable `review-observations.py` integration — passed (observation→knowledge
  transition and promotion event ledger).
- `uv run pytest tests/test_purge_noise_patterns.py -q` — passed (2 tests).
- `uv run ruff check bin/purge-noise-patterns.py tests/test_purge_noise_patterns.py` — passed.
- `uv run basedpyright bin/purge-noise-patterns.py` — passed (0 errors).
- Disposable `purge-noise-patterns.py --dry-run` integration — passed (eligible
  noise counted with no discard writes).
- `uv run ruff check services/business/paths.py bin/business-lint.py bin/business-compile.py bin/business-ingest.py bin/business-query.py bin/business-daemon.py` — passed.
- `uv run basedpyright services/business/paths.py bin/business-lint.py bin/business-compile.py bin/business-ingest.py bin/business-query.py bin/business-daemon.py` — passed (0 errors).
- `uv run pytest tests/test_memory_layers.py -q` — passed (8 tests).
- Disposable business CLI integration — passed (init, compile dry-run, query,
  lint, and daemon writable/FK-enforced connection).
- `uv run ruff check bin/extract-bug-motifs.py` — passed.
- `uv run basedpyright bin/extract-bug-motifs.py` — passed (0 errors).
- Disposable `extract-bug-motifs.py --dry-run` integration — passed (known
  motif and repeated bug-log candidates detected with zero writes).
- `uv run ruff check bin/extract-handoff-learnings.py` — passed.
- `uv run basedpyright bin/extract-handoff-learnings.py` — passed (0 errors).
- Disposable `extract-handoff-learnings.py --dry-run` integration — passed
  (learned items parsed with zero pattern or processed-file writes).
- `uv run ruff check bin/extract-personal-patterns.py` — passed.
- `uv run basedpyright bin/extract-personal-patterns.py` — passed (0 errors).
- Disposable `extract-personal-patterns.py --dry-run` integration — passed
  (multi-session signal scanned with zero pattern writes).
- `uv run ruff check bin/promote-personal-patterns.py` — passed.
- `uv run basedpyright bin/promote-personal-patterns.py` — passed (0 errors).
- Disposable `promote-personal-patterns.py --dry-run` integration — passed
  (approved pattern planned with zero vault or database writes).
- `uv run ruff check bin/agent-synthesis.py` — passed.
- `uv run basedpyright bin/agent-synthesis.py` — passed (0 errors).
- Disposable `agent-synthesis.py --dry-run` integration — passed (title/tag
  candidates generated with zero pattern writes).
- `uv run ruff check bin/build-domain-files.py` — passed.
- `uv run basedpyright bin/build-domain-files.py` — passed (0 errors).
- Disposable `build-domain-files.py --dry-run` integration — passed (domain
  projection targets generated with zero filesystem writes).
- `uv run ruff check bin/index-docx.py bin/index-pdfs.py` — passed.
- `uv run basedpyright bin/index-docx.py bin/index-pdfs.py` — passed (0 errors).
- Disposable DOCX/PDF indexer integration — passed (index plans generated with
  zero indexed-row writes; DOCX used a local optional-dependency stub).
- `uv run ruff check bin/generate-rule-bundle.py` — passed.
- `uv run basedpyright bin/generate-rule-bundle.py` — passed (0 errors).
- Disposable rule-bundle registration integration — passed (bundle row
  inserted and `patterns.lab_status` updated with foreign-key enforcement).
- `uv run pytest tests/test_v2_vertical_fixtures.py -q` — passed (3 tests).
- `pnpm --dir aios-ui exec tsc --noEmit` — passed.
- `.venv/bin/ruff check tests/test_v2_vertical_fixtures.py` — passed.
- `.venv/bin/basedpyright tests/test_v2_vertical_fixtures.py` — passed.
- `.venv/bin/pytest tests/test_storage.py tests/test_migration_runner.py tests/test_aios_cli.py -q` — passed (98 tests).
- `.venv/bin/ruff check services/storage.py services/aios_cli.py tests/test_storage.py` — passed.
- `.venv/bin/basedpyright services/storage.py services/aios_cli.py tests/test_storage.py` — passed.
- `.venv/bin/pytest tests/test_migration_transformers.py -q` — passed (2 tests).
- `.venv/bin/ruff check services/migration_transformers.py tests/test_migration_transformers.py` — passed.
- `.venv/bin/basedpyright services/migration_transformers.py tests/test_migration_transformers.py` — passed.
- `.venv/bin/pytest tests/test_hook_stop.py tests/test_hook_lifecycle.py tests/test_orchestration_runtime.py tests/test_agent_rules_runtime.py -q` — passed (51 tests).
- `pnpm --dir aios-ui exec tsc --noEmit` — passed after adapter adoption.
- `pnpm --dir aios-ui lint:architecture` — passed (122 modules, 255 dependencies) after adapter adoption.
- `.venv/bin/pytest tests/test_issues_store.py tests/test_handoff_store.py tests/test_session_effectiveness.py -q` — passed (10 tests).
- `AIOS_DB=~/AIOS/data/aios.db .venv/bin/python bin/aios-query.py --status` — passed against the live store through a read-only connection.
- `.venv/bin/pytest tests/test_hook_prompt_submit.py tests/test_hook_post_tool_use.py tests/test_hook_lifecycle.py -q` — passed (15 tests) after high-traffic hook adoption.
- `.venv/bin/ruff check bin/hook-prompt-submit.py bin/hook-precompact.py bin/hook-post-tool-use.py` — passed.
- `.venv/bin/basedpyright bin/hook-prompt-submit.py bin/hook-precompact.py bin/hook-post-tool-use.py` — passed (0 errors).
- `.venv/bin/ruff check bin/hook-session-stop.py` — passed.
- `.venv/bin/basedpyright bin/hook-session-stop.py` — passed (0 errors).
- Disposable `hook-session-stop.py` peer-trace start/stop integration — passed.
- `PYTHONPATH=. .venv/bin/pytest tests/test_orchestration_runtime.py -k 'managed_runtime or managed_closeout' -q` — passed (5 tests).
- `.venv/bin/ruff check bin/aios-managed-run.py` — passed.
- `.venv/bin/basedpyright bin/aios-managed-run.py` — passed (0 errors).
- `.venv/bin/pytest tests/test_meta_learning_session_ingest.py -q` — passed (3 tests).
- `.venv/bin/ruff check bin/cron-ingest-codex.py` — passed.
- `.venv/bin/basedpyright bin/cron-ingest-codex.py` — passed (0 errors).
- Disposable `cron-ingest-codex.py` empty-rollout ingestion integration — passed.
- `.venv/bin/pytest tests/test_session_providers.py -q` — passed (11 tests).
- `.venv/bin/ruff check bin/sessions.py` — passed.
- `.venv/bin/basedpyright bin/sessions.py` — passed (0 errors).
- Disposable `bin/sessions.py` storage integration — passed (WAL, foreign keys,
  query-only read-only mode, schema creation, and missing-database fallback).
- `.venv/bin/pytest tests/test_session_providers.py tests/test_session_intelligence_loop.py -q` — passed (39 tests).
- `.venv/bin/ruff check services/session_providers/codex.py services/session_providers/claude.py services/session_providers/cursor.py services/session_providers/antigravity.py` — passed.
- `.venv/bin/basedpyright services/session_providers/codex.py services/session_providers/claude.py services/session_providers/cursor.py services/session_providers/antigravity.py` — passed (0 errors).
- Disposable canonical upsert integration for all four providers — passed with foreign-key enforcement.
- `.venv/bin/pytest tests/test_hook_lifecycle.py -q` — passed (8 tests) after stale-session adapter adoption.
- `.venv/bin/ruff check bin/repair-stale-open-sessions.py bin/sync-prompts.py bin/queue-workflow-experiments.py bin/run-workflow-skill-experiments.py` — passed.
- `.venv/bin/basedpyright bin/repair-stale-open-sessions.py bin/sync-prompts.py bin/queue-workflow-experiments.py bin/run-workflow-skill-experiments.py` — passed (0 errors).
- Disposable utility integration — passed for stale-session abandonment, prompt-library sync, workflow queue, and empty workflow run.
- `.venv/bin/ruff check bin/record-metric.py bin/eval-session.py bin/lab-report.py` — passed.
- `.venv/bin/basedpyright bin/record-metric.py bin/eval-session.py bin/lab-report.py` — passed (0 errors).
- Disposable metrics/reporting integration — passed for metric write, session evaluation, and lab report read-only paths.
- `.venv/bin/ruff check bin/import-ai-history.py bin/sync-project-inventory.py` — passed.
- `.venv/bin/basedpyright bin/import-ai-history.py bin/sync-project-inventory.py` — passed (0 errors).
- Disposable history/inventory integration — passed for one ChatGPT import and one discovered Git repository.
- `.venv/bin/ruff check bin/ingest-imessage.py bin/ingest-apple-notes.py` — passed.
- `.venv/bin/basedpyright bin/ingest-imessage.py bin/ingest-apple-notes.py` — passed (0 errors).
- Apple-backed ingestion disposable write integration — passed for contact and note upserts with shared pragmas.
- `PYTHONPATH=. .venv/bin/pytest tests/test_aios_cli.py -k 'doctor_json_reports_release_preflight or health_json_release_contract' -q` — passed (2 tests).
- `.venv/bin/ruff check services/aios_cli.py` — passed.
- `.venv/bin/basedpyright services/aios_cli.py` — passed.
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
- The production-shaped transformer is deterministic by construction: path
  mappings require exactly one project row, unresolved required project rows are
  archived with payloads, and nullable session/task references are cleared only
  after quarantine records are written.

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

- Migrate remaining lower-traffic Python adapters through the shared
  connection contract; the managed runtime, Codex ingestion, session CLI,
  provider canonical upserts, core utility scripts, and metrics/reporting
  paths, history import, and inventory sync are now complete. Remove UI
  request-time DDL only after deterministic UI and migration gates are
  accepted; source-backed Apple ingestion writes, the doctor probe, and the
  daily pipeline pending-rule query, pattern schema migration, pattern
  extraction, pattern scoring, pattern promotion, and pattern lifecycle tools
  plus observation review, noise purging, business-memory CLI adapters, and
  bug-motif, handoff-learning, personal-pattern extraction, personal
  promotion, agent synthesis, domain-file projection, and document indexers
  plus rule-bundle registration are now covered too.
- Reconcile the live preflight count drift (the current read-only check reports
  561 violations while older audit documents record 555/557) and retain the
  command output as migration evidence.
- Complete the restore drill and a human-reviewed deletion/retention decision
  for the 73 unresolved quality rows archived by the copied transformer.
- Complete the backup/restore drill and reconcile the current store's FK
  violations before any write-capable v2 slice.

## Production-shaped copied-store evidence

The disposable copy of `~/AIOS/data/aios.db` reported `quick_check=ok`,
`integrity_check=ok`, `user_version=0`, and 561 FK violations before the
transformer. The forward-only copied migration quarantined 561 original
payloads, mapped 255 quality rows by unique metadata working-directory,
archived 73 unresolved quality rows, nulled 180 missing session references,
and nulled 53 absent shadow-task references. The post-migration copy reported
zero FK violations and `user_version=1`; its restored backup passed quick,
integrity, and FK checks, and a read-only daily-flow replay produced the
canonical eight-step trace.

## Known blockers

- The baseline UI lint/build gates remain blocked by ADR-004's known external
  anti-slop dependency, font, root/tracing, and tRPC adapter issues.
- The main store still requires ADR-002 quarantine, migration, and restore
  proof before any write-capable slice.
