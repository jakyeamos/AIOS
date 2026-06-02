---
phase: 10-operator-surfaces-query-and-daily-flow-visibility
plan: "05"
completed_at: "2026-06-01T23:59:59.000Z"
requirements:
  - OPER-01
  - OPER-02
  - OPER-03
  - OPER-04
---

# Phase 10 Plan 05 Summary

## Result

Shipped the UI router wiring, workflow-trigger glue, query-as-launcher response fields, catalog seed labeling, control-plane overview extensions, and TypeScript daily-flow projection needed by the Plan 10 operator surfaces.

## Changed Files

- `aios-ui/server/aios/daily-flow.ts`
  - Added the TypeScript mirror of `services/daily_flow.py`.
  - Exposes `previewDailyFlow` and `replayDailyFlow`.
  - Preserves the canonical eight-step order: `goal`, `route`, `packet`, `run`, `evaluation`, `writeback`, `unresolved_delta`, `next_action`.
  - Preview is read-only and does not call Python, agentize, `planTask`, `invokeControlPlaneRun`, or write SQL rows.

- `aios-ui/server/routers/operator-search.ts`
  - Added `operatorSearch.search` with zod-validated query, kind, project, and limit inputs.

- `aios-ui/server/routers/next-action.ts`
  - Added `nextAction.getForProject` and `nextAction.topAcrossProjects`.

- `aios-ui/server/routers/daily-flow.ts`
  - Added `dailyFlow.preview` and `dailyFlow.replay`.

- `aios-ui/server/routers/writebacks.ts`
  - Added direct `improvement_writebacks` list and detail procedures with drill-down paths, parsed detail JSON, and event history.

- `aios-ui/server/routers/automations.ts`
  - Added `triggerWorkflow`.
  - The mutation calls `planTask` before `invokeControlPlaneRun`.

- `aios-ui/server/routers/projects.ts`
  - Added `launchRemediation`.
  - Resolves `standards_delta_items.remediation_playbook_json.recommended_workflow_key`, then calls `planTask` before `invokeControlPlaneRun`.

- `aios-ui/server/routers/_app.ts`
  - Registered `operatorSearch`, `nextAction`, `dailyFlow`, and `writebacks`.
  - Preserved existing router registrations.

- `aios-ui/server/aios/control-plane.ts`
  - Extended `getControlPlaneOverview` with `nextActions`, `dailyFlowSummary`, `learningImpactRollup`, and `phaseStatus`.
  - Extended `getGovernanceOverview` with `policyClassDrillDowns`.
  - Added `phaseCompletionAudit`.
  - Switched catalog reads to `getCatalogSnapshot`.

- `aios-ui/server/aios/catalog.ts`
  - Added `getCatalogSnapshot`.
  - Reads workflow templates from `config/workflows/registry.json`.
  - Marks fallback catalog rows with `isSeedData: true`.

- `aios-ui/server/aios/query.ts`
  - Added the `should_i_run_workflow` intent.
  - Uses `getNextActions` and returns optional `recommendedWorkflow`, `recommendedPacketPreview`, and `launchableRunId`.

- `aios-ui/lib/control-plane.ts`
  - Added catalog `isSeedData` fields.
  - Added `should_i_run_workflow` and optional recommendation fields to `GroundedAnswer`.
  - Added `policyClassDrillDowns` to `GovernanceOverview`.

## Verification

- `cd aios-ui && pnpm exec tsc --noEmit` passed.
- `cd aios-ui && pnpm lint` passed with the existing 83 anti-slop warnings and 0 errors.
- `cd aios-ui && pnpm lint:architecture` passed.
- Grep checks confirmed:
  - daily-flow mirror header, canonical order, helpers, `previewDailyFlow`, and `replayDailyFlow`.
  - `_app.ts` registrations for `operatorSearch`, `nextAction`, `dailyFlow`, and `writebacks`.
  - `triggerWorkflow` and `launchRemediation` call `planTask` before `invokeControlPlaneRun`.
  - query intent branch contains `should_i_run_workflow`, `getNextActions`, `recommendedWorkflow`, `recommendedPacketPreview`, and `launchableRunId`.
  - control-plane overview contains `nextActions`, `dailyFlowSummary`, `learningImpactRollup`, `phaseCompletionAudit`, and `policyClassDrillDowns`.
  - daily-flow preview contains no SQL write statements, no `planTask`, no `invokeControlPlaneRun`, and no agentize call.

## Notes

- `phaseCompletionAudit` returns typed `PhaseStatusReport[]` for the UI contract instead of an unstructured status map.
- The catalog migration labels UI-owned fallback agent profiles and invocation backends as seed data because there is no checked-in JSON invocation-backend manifest yet.
