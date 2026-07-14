# AIOS V2 Modernization Progress

**Status:** Milestone 1 data/recovery gate complete; UI ownership follow-up remains
**Updated:** 2026-07-14
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
Pipeline and lab schema migrations now use the same shared write boundary and
honor `AIOS_DB`; their schema/data changes remain explicitly disposable until
the main-store migration gate is accepted.
RTK execution and threshold tuning, GitHub-skill discovery, workflow synthesis,
and workflow experiment control now use the shared storage boundary as well;
analytics remain read-only and explicit `--db` paths are preserved.
The Flask review surface, vault-lint checks, and lab-trigger runner now use the
same storage boundary; vault and dry-run lab probes pass, while the review
surface remains runtime-unverified because Flask is not installed in the
repository environment.
Lifecycle-status migration now uses shared storage for file-backed databases
while preserving its explicit `:memory:` compatibility; commit-quality
evidence/verifier reads also use the shared read-only boundary.
The CTS registry's AIOS project metadata read now uses the shared read-only
boundary and honors `AIOS_DB`; CTS-owned graph stores remain unchanged.
The current recovery gate was rerun read-only against `~/AIOS/data/aios.db`:
the live copy remains healthy at the SQLite level but reports 561 FK
violations; a disposable transformer quarantined all 561, reached zero FK
violations, restored cleanly, and replayed the eight-step daily-flow preview.
The user then approved archive disposition for the 73 unresolved quality rows.
The guarded live runner captured immutable pre/post backups, applied the same
transform under `BEGIN IMMEDIATE`, recorded all 561 quarantine decisions, and
left the live store at zero FK violations with `user_version=1`.
The first ADR-004 UI validation pass now has clean ESLint, anti-slop fixture,
TypeScript, architecture, warning-baseline, native-module, and production-build
evidence; the final pinned browser contract and generated catalog checks are
also green, with no remaining NFT tracing warning.
The loopback runtime smoke also passed: `/` and the source-backed
`projects.list` tRPC route both returned HTTP 200 on a disposable dev server,
with no request errors in the server log.
The aggregate M1 retention decision packet now records the fresh disposable
counts and records the approved archive decision; the live store is now
reconciled with zero FK violations.
The M2 validation slice now vendors `eslint-plugin-anti-slop` 0.4.0 inside
`aios-ui/`, removes the external sibling-path dependency, and removes all
request-time UI DDL in favor of a Python-owned migration-ledger assertion.
Independent ESLint, anti-slop fixtures, TypeScript, architecture, and warning
baseline checks pass; the production build is warning-free, and a disposable
loopback smoke returned HTTP 200 for `/` and `projects.list`.

The M2 browser frontier then verified seeded `controlPlane.overview` (HTTP 200;
16 workflow templates, 20 runs, 12 packets, 25 findings) and typed
`controlPlane.runDetail` (HTTP 200; three events). The in-app browser passed
375×812, 768×1024, and 1440×900 without horizontal overflow or console errors;
same-origin capture observed 24 requests with no failed response. A duplicate
React key in run-detail standards deltas was fixed.

M2 is now resolved. Playwright 1.61.1 is pinned in `aios-ui`; the checked-in
browser contract passes seeded route typing, 375×812/768×1024/1440×900 layout
checks, same-origin response checks, console policy, screenshots, and real Tab
traversal with visible focus. Prompt and workflow registries are generated and
checked before build, and the managed-runtime spawn call is statically
traceable. `pnpm --dir aios-ui build` now completes without the NFT warning.

M3 is now resolved as a read-only operator shell. `/` is Today, `/start` is
Start work, and `/runs/:id` is the canonical control-plane Current run path;
legacy session ids still fall back to the existing detail surface. The shell
uses the existing tRPC projections, exposes source/freshness/authority and
next-action context, distinguishes healthy/blocked/stale/empty states, and
keeps mutations behind the Python owner. Primary navigation is task-centred
with contextual satellites behind disclosure, and the layout adds skip-link,
focus, responsive, and no-overflow behavior. The M2 and M3 Playwright suites
pass at all three viewports with zero mutation requests, console errors, bad
same-origin responses, or horizontal overflow. Full UI lint/typecheck,
architecture, warning-baseline, anti-slop, production build, and context
validation pass; M4 remains the governed Start work → Verify mutation slice.

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
- Routed `migrate-pipeline.py` and `migrate-lab-integration.py` through shared
  storage and made their canonical database paths honor `AIOS_DB`; a
  disposable combined migration proof passed for state renaming, schema
  additions, lab tables, processed-file tracking, and foreign-key integrity.
- Routed `rtk-run.py`, `rtk-tune-thresholds.py`, `discover-github-skills.py`,
  `synthesize-workflows.py`, and `run-experiment.py` through shared storage;
  read-only analytics and explicit `--db` behavior were preserved, and a
  disposable RTK/discovery/synthesis/experiment integration passed.
- Routed `review_app.py`, `vault-lint.py`, and `trigger-lab-experiment.py`
  through shared storage, made their canonical paths honor `AIOS_DB`, and
  preserved read-only vault checks plus dry-run lab behavior; a disposable
  vault/lab integration passed. Flask runtime verification remains blocked by
  the existing missing optional dependency.
- Routed `migrate-lifecycle-statuses.py` through shared storage for file-backed
  databases while preserving `:memory:` behavior, and routed the two
  commit-quality AIOS artifact checks through shared read-only storage; a
  disposable lifecycle migration proof passed.
- Routed `services/cts/registry.py`'s AIOS project metadata reads through
  shared read-only storage and made its default honor `AIOS_DB`; the CTS
  graph-store database remains CTS-owned, and a disposable registry proof
  passed.
- Scoped `aios-ui` Turbopack to its application working directory in
  `next.config.ts`; the workspace-root warning is gone and a clean production
  build now completes after rebuilding the local `better-sqlite3` binary.
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
- `.venv/bin/ruff check bin/migrate-pipeline.py bin/migrate-lab-integration.py` — passed.
- `.venv/bin/basedpyright bin/migrate-pipeline.py bin/migrate-lab-integration.py` — passed (0 errors).
- Disposable pipeline/lab migration integration — passed (state rename, added
  columns, migration tables, processed-file ledger, and foreign-key integrity).
- `.venv/bin/ruff check bin/rtk-run.py bin/rtk-tune-thresholds.py bin/discover-github-skills.py bin/synthesize-workflows.py bin/run-experiment.py` — passed.
- `.venv/bin/basedpyright bin/rtk-run.py bin/rtk-tune-thresholds.py bin/discover-github-skills.py bin/synthesize-workflows.py bin/run-experiment.py` — passed (0 errors).
- `.venv/bin/pytest tests/test_workflow_synthesis.py tests/test_workflow_experiments.py -q` — passed (14 tests).
- Disposable RTK/discovery/synthesis/experiment integration — passed (RTK
  event write, threshold dry-run, synthesis dry-run, experiment listing, and
  read-only discovery metrics path).
- `.venv/bin/ruff check bin/review_app.py bin/vault-lint.py bin/trigger-lab-experiment.py` — passed.
- `.venv/bin/basedpyright bin/review_app.py bin/vault-lint.py bin/trigger-lab-experiment.py` — passed (0 errors).
- Disposable vault/lab integration — passed (read-only lint checks and
  no-eligible-pattern lab dry-run).
- `review_app.py` runtime probe — blocked because Flask is not installed in
  the repository environment; no dependency was added in this slice.
- `.venv/bin/ruff check bin/migrate-lifecycle-statuses.py services/commit_quality_ladder.py` — passed.
- `.venv/bin/basedpyright bin/migrate-lifecycle-statuses.py services/commit_quality_ladder.py` — passed (0 errors).
- `.venv/bin/pytest tests/test_asset_lifecycle.py tests/test_commit_quality_ladder.py -q` — passed (29 tests).
- Disposable lifecycle migration integration — passed (file-backed status
  remap and explicit `:memory:` compatibility).
- `.venv/bin/ruff check services/cts/registry.py` — passed.
- `.venv/bin/basedpyright services/cts/registry.py` — passed (0 errors).
- Disposable CTS registry integration — passed (read-only project listing and
  normalized path lookup through the shared AIOS connection).
- Current live recovery preflight — passed for evidence capture only:
  `quick_check=ok`, `integrity_check=ok`, `user_version=0`, and 561 FK
  violations reported without live writes.
- Disposable copied-store recovery drill — passed: 561 quarantines, zero
  post-transform FK violations, restored `quick_check=ok` and
  `integrity_check=ok`, and eight-step read-only daily-flow replay.
- `pnpm --dir aios-ui exec tsc --noEmit` — passed.
- `pnpm --dir aios-ui lint:architecture` — passed (122 modules, 255 dependencies).
- `pnpm --dir aios-ui lint:warning-baseline` — passed (0/71 warnings).
- `pnpm --dir aios-ui build` — the initial pass exposed the prompt NFT tracing
  warning; the subsequent generated-catalog/static-runtime fix now produces a
  warning-free build.
- `pnpm --dir aios-ui exec next dev --hostname 127.0.0.1 --port 3100` plus
  local smoke requests — passed (`/` HTTP 200; `projects.list` tRPC HTTP 200;
  source-backed project payload returned; server stopped cleanly).
- `pnpm --dir aios-ui exec eslint .` — passed with 0 errors and 0 warnings
  against the committed `eslint-plugin-anti-slop` 0.4.0 package.
- `pnpm --dir aios-ui lint:anti-slop:fixtures` — passed against the committed
  plugin artifact.
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
  plus rule-bundle registration, pipeline/lab schema migrations, RTK,
  discovery, workflow synthesis, workflow experiment, review, vault-lint, and
  lab-trigger adapters, lifecycle migration, commit-quality evidence reads, and
  CTS AIOS metadata reads are now covered too.
- Retain the immutable pre/post backups and the 561-row quarantine inventory;
  the 73 unresolved quality rows are archived under the approved Option A
  decision in [M1_RETENTION_DECISION.md](M1_RETENTION_DECISION.md).
- Keep later write-capable v2 product features behind their UI, approval, and
  operator-validation gates; the M1 data/recovery gate itself is green.

## Production-shaped copied-store evidence

The disposable copy of `~/AIOS/data/aios.db` reported `quick_check=ok`,
`integrity_check=ok`, `user_version=0`, and 561 FK violations before the
transformer. The forward-only copied migration quarantined 561 original
payloads, mapped 255 quality rows by unique metadata working-directory,
archived 73 unresolved quality rows, nulled 180 missing session references,
and nulled 53 absent shadow-task references. The post-migration copy reported
zero FK violations and `user_version=1`; its restored backup passed quick,
integrity, and FK checks, and a read-only daily-flow replay produced the
canonical eight-step trace. The live archive migration produced the same
zero-FK result, restored from both immutable backups (pre-state retained the
original 561 violations; post-state retained zero), and replayed the canonical
eight-step trace against the migrated store.

## Known blockers

- The UI build and architecture/type gates now pass; ADR-004 remains blocked by
  one NFT tracing warning from the prompt filesystem adapter. The external
  anti-slop installation and prior workspace-root warning are resolved.
- ADR-002 quarantine, migration, and restore proof now pass for the main store;
  the UI schema module is now read-only, but existing UI mutation endpoints
  still need to route writes through the Python owner before v2 mutations are
  considered safe.
