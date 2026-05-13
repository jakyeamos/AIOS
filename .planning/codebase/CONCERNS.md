---
date: 2026-05-13
last_mapped_commit: c8817f21
---

# AIOS Concerns Map

This file captures the highest-signal technical debt, operational fragility, and planning gaps observed in the repository as mapped on 2026-05-13.
It is intended as a practical risk register, not a roadmap; every item below is tied to current code or repo state.

## Runtime trust gaps

- The runtime and UI share the same control-plane tables, but schema ownership is duplicated across Python and TypeScript.
  `services/aios_cli.py` creates and backfills `orchestration_runs`, `orchestration_invocations`, `orchestration_run_events`, and `briefing_packets`, while `aios-ui/server/aios/schema.ts` independently defines and migrates the same tables.
  This creates schema drift risk whenever one side adds defaults, `NOT NULL` constraints, or new columns first.

- The UI is tightly coupled to one operator machine layout.
  `aios-ui/server/db.ts` hardcodes the database path to `~/AIOS/data/aios.db`, which makes the app less portable and harder to test in isolated environments.
  This also encourages hidden local-state dependencies rather than explicit configuration.

- Runtime trust is still mixed between confirmed and synthesized signals.
  `services/capability_truth.py` and `aios-ui/server/routers/automations.ts` deliberately surface `missing` and `inferred` provenance for automation health, which is correct behavior, but it also means important dashboards remain only partially grounded.
  `aios-ui/server/routers/costs.ts` falls back to `seededCostSummary` when token telemetry is absent, so cost views can remain operationally useful while still not representing durable truth.

- Workflow and skill registry actions can write repo config directly from the UI server.
  `aios-ui/server/routers/workflows.ts` uses `writeFileSync` to mutate `config/workflows/skills.json`.
  That bypasses the CLI-oriented truth-file and review flow described elsewhere in the repo and raises the chance of silent config mutations from a local UI action.

## Missing automation history

- Confirmed automation history support exists, but confirmed history coverage does not.
  `services/capability_truth.py`, `services/automation_history.py`, and `aios-ui/server/aios/schema.ts` all support `automation_run_history`, yet the code explicitly warns when the table is missing or empty.
  The concern is not schema absence; the concern is weak ingestion coverage.

- Only one concrete backfill path is obvious in the code map.
  `services/automation_history.py` syncs pipeline history from `logs/pipeline.log`, and `services/aios_cli.py` exposes the sync entrypoint.
  The seeded automations in `services/capability_truth.py` and `aios-ui/server/routers/automations.ts` describe three automations, but only the pipeline-style automation has a visible durable importer.

- The repo itself documents this gap as unresolved.
  `docs/aios-ui-command-center-implementation-plan.md` calls out “Real automation run history and missed-run provenance” as a backend dependency not yet blocking MVP.
  That means automation health remains a known partial-trust surface, not an implementation accident.

## Repo and workspace drift

- The workspace is already drifting away from a clean-truth posture.
  Current repo state shows tracked modifications in `aios/context/compiled/latest.md`, `aios/context/compiled/latest.json`, `aios/context/receipts/latest.md`, and `aios/context/receipts/latest.json`, plus unrelated local changes such as `config/agent-rules.md` and `uv.lock`.
  These generated or semi-generated artifacts are useful, but they also make it easy for planning state to diverge from committed repo truth.

- Context compiler outputs are intentionally durable files, which makes them auditable and also easy to stale.
  `aios/context/index.md` and `aios/context/router.md` treat compiled packets and receipts as first-class artifacts.
  If operators do not regenerate them after meaningful task changes, `aios/context/compiled/latest.md` and `aios/context/receipts/latest.md` can look authoritative while lagging behind actual work.

- Project inventory sync is narrowly scoped and can miss broader workspace reality.
  `bin/sync-project-inventory.py` defaults to scanning `~/projects`, while `services/project_inventory.py` only discovers immediate `*/.git` children under that root.
  Nested repos, alternate workspace roots, or worktrees outside that convention can drift away from the AIOS project table without being visibly wrong.

- Weekly maintenance is script-driven and local-machine dependent.
  `bin/weekly-maintenance.sh` assumes shell access, specific vault locations, and direct execution of multiple Python scripts.
  This is operationally effective for one machine, but brittle as a reproducible team workflow.

## UI, build, and test risks

- The repository standard says `pnpm`, but the UI CI path uses `npm`.
  `README.md` instructs `pnpm install`, `pnpm lint`, and `pnpm build`, while `.github/workflows/aios-ui-quality.yml` uses `npm ci` and `npm --prefix aios-ui run ...`.
  The presence of both `aios-ui/pnpm-lock.yaml` and `aios-ui/package-lock.json` confirms active package-manager drift.

- Quality-pipeline inference also encodes that drift.
  `aios-ui/server/aios/quality-pipeline.ts` prefers `pnpm install --frozen-lockfile` only when `pnpm-lock.yaml` is present, but falls back to `npm ci` for any repo with `package.json`.
  `tests/test_quality_pipeline.py` explicitly asserts the npm fallback behavior.
  That makes package-manager inconsistency part of the expected product behavior, not just incidental CI setup.

- The UI quality gate is mostly lint/build oriented.
  `.github/workflows/aios-ui-quality.yml` runs lint, warning baseline, architecture checks, anti-slop fixtures, and `next build`, but there are no mapped frontend test files under `aios-ui/` and no active Playwright/Vitest/Cypress config in the app tree.
  For a UI with many operator surfaces under `aios-ui/app/`, regression protection is therefore structural rather than behavior-driven.

- Some UI routes still depend on seeded fallback data when live tables are absent or sparse.
  `aios-ui/server/routers/costs.ts` and `aios-ui/server/routers/workflows.ts` return seeded summaries or metrics in no-data cases.
  That is acceptable for bootstrapping, but it blurs the boundary between “product works” and “product is showing real operating state.”

- Next.js runtime settings remain minimal relative to the amount of local-state coupling.
  `aios-ui/next.config.ts` only enables `reactStrictMode`.
  There is no visible repo-level configuration here for runtime caching, error instrumentation, or environment validation despite the app depending on local SQLite state and many filesystem-backed registries.

## Planning and truth-file maintenance concerns

- The repo has explicit truth-file discipline, but the enforcement model is still easier to bypass in practice than on paper.
  `spec/success-criteria/truth-file-consistency.md` and `services/success_criteria.py` require `PROJECT.md` updates for substantial AIOS code changes.
  However, many important state changes in this repo happen through generated artifacts, registry JSON, logs, or UI-side file writes, which can move the effective system state without a matching `PROJECT.md` change.

- Planning and docs are abundant, but authority is distributed.
  `PROJECT.md`, `README.md`, `aios/context/compiled/latest.md`, `aios/context/receipts/latest.md`, `spec/success-criteria/index.md`, and multiple `docs/architecture/*.md` files all carry overlapping operational truth.
  The strength is traceability; the weakness is that operators must know which layer is authoritative for a given question.

- `.planning/codebase/` is an agent-owned map area rather than a native product surface.
  That makes it useful for orientation, but it will stale unless refreshed alongside the stronger truth anchors in `PROJECT.md` and the context compiler receipt set.
  Treat this folder as reference material, not primary runtime truth.

- The context compiler bootloader is a real discipline, but it increases maintenance load.
  `AGENTS.md`, `PROJECT.md`, `aios/context/index.md`, and `aios/context/router.md` all require selective loading, receipts, and writeback awareness before non-trivial work.
  The process improves rigor, but the cost is more generated state, more update obligations, and more opportunities for silent mismatch between execution and documentation.

## Practical follow-up targets

- Unify schema ownership for control-plane tables so `services/aios_cli.py` and `aios-ui/server/aios/schema.ts` cannot drift independently.
- Eliminate package-manager ambiguity by removing one lockfile path and updating `.github/workflows/aios-ui-quality.yml` plus `aios-ui/server/aios/quality-pipeline.ts` to the chosen standard.
- Convert seeded automation and workflow/cost fallbacks into clearly partitioned demo-only or bootstrap-only modes with stronger operator-visible warnings.
- Add at least one executable UI behavior layer for critical pages under `aios-ui/app/`, not just lint/build gates.
- Narrow the set of files treated as operational truth and define when `PROJECT.md`, context receipts, and generated registries must be updated together.
