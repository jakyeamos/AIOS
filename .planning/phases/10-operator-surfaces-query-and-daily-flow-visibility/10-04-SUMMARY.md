---
phase: 10-operator-surfaces-query-and-daily-flow-visibility
plan: "04"
subsystem: ui-projections
tags: [operator-surfaces, typescript, drill-down, search, next-action]
requires:
  - phase: 10-operator-surfaces-query-and-daily-flow-visibility
    provides: Python operator-search, next-action, and daily-flow contracts
provides:
  - TypeScript drill-down path builders
  - UI operator-search projection mirror
  - UI next-action projection mirror
  - operator-surface type extensions
  - drill-down paths on standards-health and learning projections
affects: [aios-ui, operator-search, next-action, drill-down-paths, standards-health, learning]
tech-stack:
  added: []
  patterns:
    - centralized TypeScript URL construction
    - better-sqlite3 read projections
    - Python-to-TypeScript projection parity comments
    - safe-column search projection
key-files:
  created:
    - aios-ui/lib/drill-down.ts
    - aios-ui/server/aios/operator-search.ts
    - aios-ui/server/aios/next-action.ts
    - .planning/phases/10-operator-surfaces-query-and-daily-flow-visibility/10-04-SUMMARY.md
  modified:
    - aios-ui/lib/control-plane.ts
    - aios-ui/lib/types.ts
    - aios-ui/server/aios/standards-health.ts
    - aios-ui/server/aios/learning.ts
key-decisions:
  - "TypeScript path builders use encodeURIComponent for every interpolated id or key."
  - "Operator-search and next-action TS files point back to their Python canonical modules in header comments."
  - "Existing standards-health and learning callers remain compatible through additive optional drillDownPath fields."
requirements-completed: []
requirements-partial: [OPER-01, OPER-02, OPER-03]
duration: 28min
completed: 2026-06-01
---

# Phase 10 Plan 04 Summary

**UI projection layer and drill-down path discipline**

## Drill-Down API

`aios-ui/lib/drill-down.ts` exports 18 pure URL builders:

`runPath`, `packetPath`, `writebackPath`, `findingPath`, `promptTemplatePath`, `promptUsePath`, `skillPath`, `workflowPath`, `knowledgePath`, `routeDecisionPath`, `deltaItemPath`, `backfillTaskPath`, `automationPath`, `experimentPath`, `divergentRunPath`, `learningPatternPath`, `promotionLifecycleItemPath`, `goalSearchPath`.

All interpolated values use `encodeURIComponent`, and every returned value starts with `/`.

## Type Additions

`aios-ui/lib/control-plane.ts` now exports:

`EntityKind`, `OperatorSearchHit`, `NextActionKind`, `PriorityBucket`, `NextAction`, `DailyFlowStepKind`, `DailyFlowStep`, `DailyFlowTrace`, `PhaseId`, `PhaseStatus`, `PhaseStatusReport`.

Existing standards-health types gained optional `drillDownPath`:

- `StandardsDeltaItem`
- `StandardsBackfillTask`
- `RecommendedWorkflow`

Existing learning row types in `aios-ui/lib/types.ts` gained optional `drillDownPath`:

- `LearningImpactRollup`
- `RecurringPattern`
- `ConservativeProposalRow`

## Projection Mirrors

`aios-ui/server/aios/operator-search.ts` mirrors `services/operator_search.py` with:

- 17 entity dispatchers
- bounded per-kind reads
- matching scoring constants
- safe-column projection only
- `drillDownPath` from `aios-ui/lib/drill-down.ts`

`aios-ui/server/aios/next-action.ts` mirrors `services/next_action.py` with:

- six source fetchers
- matching priority bucket weights
- bounded read-time fusion
- `drillDownPath` from `aios-ui/lib/drill-down.ts`

## Extended Existing Projections

`aios-ui/server/aios/standards-health.ts` now attaches:

- delta items -> `deltaItemPath`
- backfill tasks -> `backfillTaskPath`
- recommended workflows -> `workflowPath`

`aios-ui/server/aios/learning.ts` now attaches:

- learning rollups -> `workflowPath`, `promptTemplatePath`, or `skillPath`
- recurring patterns -> `learningPatternPath`
- conservative proposals -> `writebackPath`

`proposeRunWritebacks` was not changed.

## Safe Projection Check

Operator search SELECT lines do not project `proposed_change_json` or `evidence_json`. The only learning/proposal JSON read remains in the next-action/learning proposal path where it is needed to classify learning proposals, not to render search hit bodies.

## Verification

- `cd aios-ui && pnpm lint` -> passed with the existing 83 anti-slop warnings, 0 errors
- `cd aios-ui && pnpm exec tsc --noEmit` -> passed
- `cd aios-ui && pnpm lint:architecture` -> passed
- path builder grep: 18 builders, 20 `encodeURIComponent` uses
- projection grep: 17 search dispatchers, six next-action source fetchers
- safe search grep: `grep "SELECT" aios-ui/server/aios/operator-search.ts | grep -c "proposed_change_json\|evidence_json" || true` -> 0

## Next Plan Readiness

Plan 10-05 can add tRPC routers for operator search, next action, daily flow, and writebacks using these shared types and path builders. Plan 10-06 will render the React surfaces on top of those router procedures.

---
*Phase: 10-operator-surfaces-query-and-daily-flow-visibility*
*Completed: 2026-06-01*
