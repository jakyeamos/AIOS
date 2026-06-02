---
phase: 10-operator-surfaces-query-and-daily-flow-visibility
plan: "06"
completed_at: "2026-06-02T00:00:00.000Z"
requirements:
  - OPER-01
  - OPER-02
  - OPER-03
  - OPER-04
---

# Phase 10 Plan 06 Summary

## Result

Shipped the rendered operator surfaces that make the Phase 10 backends usable from the UI: global operator search, faceted `/search`, next-action panels, daily-flow traces, phase/seed-data banners, writeback filters, automation triggers, and query answer launch controls.

## Changed Files

- `config/operator-surfaces/search-policy.json`
  - Added reviewable search policy thresholds for query length, limits, per-kind caps, recency boost, exact-key boost, and debounce timing.

- `aios-ui/lib/constants.ts`
  - Added `/search` to the primary navigation.

- `aios-ui/components/layout/TopBar.tsx`
  - Added `GlobalSearchInput` to the top bar.

- `aios-ui/components/search/GlobalSearchInput.tsx`
  - Added the 200ms debounced topbar search client component.
  - Calls `operatorSearch.search` and renders top-five suggestions plus a full-results link.
  - Clears the dropdown when navigating through a suggestion or the full-results link.

- `aios-ui/components/search/SearchResults.tsx`
  - Added faceted mixed-entity search results with counts, scores, last-updated metadata, and drill-in links.

- `aios-ui/components/next-action/NextActionPanel.tsx`
  - Added priority-bucket rendering for next actions.
  - Wires launch-remediation actions to `projects.launchRemediation`.
  - Invalidates overview, next-action, and project detail queries after mutation success.

- `aios-ui/components/daily-flow/DailyFlowTrace.tsx`
  - Added canonical daily-flow step cards with provenance badges, missing-step labels, and drill-in links.

- `aios-ui/components/command-center/PhaseStatusBanner.tsx`
  - Added constructively framed phase-population status messaging for partial or missing phase data.

- `aios-ui/components/command-center/SeedDataBanner.tsx`
  - Added demo-data labeling and refresh behavior for seed catalog rows.

- `aios-ui/components/automations/AutomationTriggerButton.tsx`
  - Added the client mutation button for `automations.triggerWorkflow`.

- `aios-ui/components/query/GroundedQueryStudio.tsx`
  - Added a launch-workflow action when a grounded answer includes `recommendedWorkflow`.

- `aios-ui/app/page.tsx`
  - Extended the Command Center with phase status, seed-data status, next actions, daily-flow trace, and learning-impact rollup.

- `aios-ui/app/search/page.tsx`
  - Added the global search landing page.

- `aios-ui/app/projects/[id]/page.tsx`
  - Added project-scoped next actions.

- `aios-ui/app/runs/[id]/page.tsx`
  - Added run-scoped daily-flow replay.

- `aios-ui/app/writebacks/page.tsx`
  - Migrated from `divergent.writebacks` to `writebacks.list`.
  - Added status, policy-class, source, and project filters.

- `aios-ui/app/automations/page.tsx`
  - Added a trigger-workflow action column.

- `aios-ui/server/aios/next-action.ts`
  - Hardened optional-column SQL projection for local schemas without `run_id`, `criterion_id`, `message`, or shared timestamp columns.

- `aios-ui/server/aios/daily-flow.ts`
  - Hardened evaluation ordering for schemas that lack `updated_at` or `created_at`.

- `aios-ui/server/aios/learning.ts`
  - Fixed the `improvement_writebacks` insert placeholder count so project detail can render when it backfills learning writebacks.

- `aios-ui/styles/globals.css`
  - Added responsive layout and visual treatment for search, next-action, daily-flow, phase-status, seed-data, and automation-action surfaces.

## Verification

- `cd aios-ui && pnpm exec tsc --noEmit` passed.
- `cd aios-ui && pnpm lint` passed with the existing 83 anti-slop warnings and 0 errors.
- `cd aios-ui && pnpm lint:architecture` passed.
- Browser verification against `http://localhost:3000` passed for:
  - `/` with Command Center next actions, daily-flow trace, and phase-status banner.
  - `/search?query=implementation` with facets and drill-in results.
  - `/writebacks` with `writebacks.list` filters.
  - `/automations` with trigger-workflow actions visible.
  - `/projects/be2139e874c1a02e` with project-scoped next actions.
  - `/runs/managed-invoke-manual-5a3df472-1a00-46ce-a2ba-02c271fde2b8` with daily-flow replay visible.

## Notes

- Browser validation intentionally did not click launch or trigger mutation buttons because those actions create workflow side effects.
- Local dev-server startup required rebuilding/copying the `better-sqlite3` native binding inside `aios-ui/node_modules`; that was environment repair only and is not part of the source commit.
