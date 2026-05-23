# Phase 10: Operator Surfaces, Query, And Daily-Flow Visibility - Context

**Gathered:** 2026-05-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 10 is a UI projection and fusion layer over primitives deposited by Phases 1–9. It does not build new data subsystems. The novel work is: (1) cross-entity search across runs, packets, writebacks, findings, prompts, skills, workflows, knowledge objects, route decisions, deltas, automations, experiments, and learning patterns; (2) a fused per-project next-action surface that ranks across health deltas, pending writebacks, open blockers, terminal-run gaps, learning proposals, backfill tasks, and promotion candidates; (3) a daily-flow trace that threads the full vague-goal → routing → packet → run → evaluation → writeback → unresolved-deltas sequence for both preview (dry, no persistence) and replay (existing run) modes; (4) a query-as-launcher extension so grounded queries can recommend and trigger workflows; (5) automation → workflow trigger binding so health deltas and automations become workflow-launch surfaces with operator confirmation. Everything else reuses existing primitives from prior phases.

</domain>

<decisions>
## Implementation Decisions

### Navigation and Surface Placement
- `/next-action` and `/daily-flow` are NOT top-level nav entries — they are embedded as panels in the Command Center page and in project detail pages; this keeps the sidebar lean.
- `/search` gets a top-level nav entry in `PRIMARY_NAV` (`aios-ui/lib/constants.ts`) as the global search landing page.
- The daily-flow trace component on `/runs/[id]` is collapsible — it preserves existing run detail density and does not replace the current invocation/event view.
- The TopBar global search input is always-visible (not icon-toggled) — standard UX, no extra click required to access.

### Automation Workflow Trigger Binding
- Trigger binding is stored in a new `automation_workflow_triggers` table (not a JSON column on `automations`) — this provides a better audit trail and allows 1:N bindings if needed.
- Trigger bindings are editable in the UI on the automations page — operator-visible, not CLI-only.
- Every workflow launch from automation, delta, next-action, or query surfaces requires an explicit confirmation modal before `controlPlane.plan` + `controlPlane.invoke` are called — governance constraint, no shortcuts.
- Health-delta-triggered launch modals show the full delta context (domain, priority bucket, recommended remediation, rationale) so the operator can make an informed decision.

### Phase Completion Degradation
- Top-level banner on the Command Center AND inline `unknown — phase X not complete` labels per surface when Phases 5–9 are incomplete — both are required.
- Phase completion check runs automatically on each page load (not CLI-only) — the check reads the `contracts_audit` rows (or infers from table existence) and stores the result in a short-lived server-side cache to avoid repeated DB scans per request.
- `catalog.ts` seed data is labeled with a visible `isSeedData: true` flag in the UI response shape, which renders as a "demo data" badge on the relevant UI surfaces — tier-one failure condition forbids masking.
- Incomplete prior phases do NOT block Phase 10 deployment — graceful degradation with explicit labels is required; surfaces still render.

### Search Ranking and Result Presentation
- Default search results cover all entity kinds, sorted by score descending with recency boost from `last_updated_at` and an exact-key boost when the query matches a row's primary key.
- Search ranking thresholds (LIKE-match boost, recency weight, exact-key boost) are stored in `config/operator-surfaces/search-policy.json` — tunable in git, reviewed like any config change.
- The sidebar TopBar search shows at most 5 hits per entity kind before linking to the `/search` landing page for full results.
- Empty query state returns recent activity across all entity kinds (most-recently-updated rows, no LIKE filter) — the sidebar search has a sensible non-empty default state.

### Claude's Discretion
- Exact SQL `ORDER BY` column names and `LIKE` field selection per entity kind — follow the existing pattern in `services/standards_health.py` and `services/capability_truth.py`.
- Component styling for `NextActionPanel`, `DailyFlowTrace`, `GlobalSearchInput`, `SearchResults` — follow existing component patterns in `aios-ui/components/command-center/` and `aios-ui/components/query/`.
- Whether `dailyFlow.preview` and `dailyFlow.replay` live in one tRPC router file or two — the interface contract (two procedures with distinct input shapes) is fixed; file organization is Claude's call.
- Exact `PRIMARY_NAV` entry label and icon for `/search` — follow the pattern of existing nav entries in `aios-ui/lib/constants.ts`.
- Internal cache TTL for the per-page-load phase completion check — short (30s) is sufficient for local-first single-user deployment.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `aios-ui/server/aios/control-plane.ts` (667 lines) — `getControlPlaneOverview`, `getGovernanceOverview`, `listControlPlaneRuns`, `getControlPlaneRunDetail`, `planTask`, `invokeControlPlaneRun`; Phase 10 extends the overview response shape with optional `nextActions[]` + `dailyFlowSummary`.
- `aios-ui/server/aios/query.ts` (730 lines) — `answerGroundedQuestion` with intent routing (`what_changed`, capability, truth-operator); Phase 10 extends with `should_i_run_workflow` intent class.
- `aios-ui/server/aios/standards-health.ts` (322 lines) — `getProjectStandardsHealth` returning snapshot + deltaItems + backfillTasks + recommendedWorkflows; Phase 10 adds `drill_down_path` to every delta item.
- `aios-ui/server/aios/learning.ts` (169 lines) — `proposeRunWritebacks` + Phase-9 extensions `getLearningImpactForRun` / `getLearningImpactRollup` / `listRecurringPatterns` / `listConservativeProposals`.
- `aios-ui/server/aios/packet-assembly.ts` (541 lines) — `assembleRankedPacket` + `expandPacketContext`; reused by `dailyFlow.preview` for dry packet projection.
- `aios-ui/lib/trusted-signals.ts` — `trustedSignal()` contract; every new metric uses this.
- `aios-ui/lib/control-plane.ts` (108-336 lines) — existing TypeScript types for runs, invocations, sessions, artifacts; Phase 10 adds `NextAction`, `DailyFlowStep`, `DailyFlowTrace`, `OperatorSearchHit`, `EntityKind`.
- `services/task_routing.py` `recommend_route_primitives` (Phase 1) — reused by `nextAction` and `dailyFlow.preview` without modification.
- `services/standards_health.py` `recommend_workflow_from_health` (Phase 7) — fused into `next_action.py`.
- `services/asset_recommendation.py` `recommend_assets_for_packet` (Phase 8) — fused into `next_action.py`.
- `services/learning_impact.py` `build_per_run_impact` / `build_rollup` (Phase 9) — surfaced on Command Center.
- `services/aios_cli.py` — extended with `aios operator-search`, `aios next-action`, `aios daily-flow`, `aios trigger-workflow`.

### Established Patterns
- Projection modules in `aios-ui/server/aios/` are read-only TypeScript modules that call `getDb()` from `aios-ui/server/db.ts` via `better-sqlite3`; they do not call Python at runtime (Python is for CLI + hooks).
- tRPC routers in `aios-ui/server/routers/` use `createTRPCRouter` + `publicProcedure` with `zod` input validation; registered in `_app.ts`.
- Server Components are the default for pages; `"use client"` only for components with hooks or browser APIs (e.g., `GlobalSearchInput.tsx` requires client component for debounce).
- Python services follow: `@dataclass(frozen=True)` for return types; `Literal[...]` for enums; `sqlite3.Connection` as the first arg; no imports from `bin/`.
- Tests follow: in-memory SQLite with `ensure_*_schema` seed patterns (see `tests/test_aios_cli.py`, `tests/test_standards_health.py`).

### Integration Points
- `aios-ui/server/routers/_app.ts` — register `operatorSearch`, `nextAction`, `dailyFlow`, `writebacks` new routers.
- `aios-ui/lib/constants.ts` `PRIMARY_NAV` — add `/search` entry.
- `aios-ui/components/layout/TopBar.tsx` — add `GlobalSearchInput` client component.
- `aios-ui/app/page.tsx` Command Center — add `NextActionPanel`, `DailyFlowSummary` card, compounding rollup row.
- `aios-ui/app/projects/[id]/page.tsx` — add `NextActionPanel`, launch-remediation buttons.
- `aios-ui/app/runs/[id]/page.tsx` — add collapsible `DailyFlowTrace` component.
- `schema.sql` — add `automation_workflow_triggers` table (CREATE TABLE IF NOT EXISTS, additive migration).

</code_context>

<specifics>
## Specific Ideas

- The `automation_workflow_triggers` table (not a JSON column) is the explicit decision for trigger binding storage — it supports audit history and future 1:N bindings.
- Page-load phase completion check auto-runs and caches result for ~30s; drives the Command Center banner and per-surface degradation labels.
- Sidebar search shows 5 hits per entity kind max, then links to the full `/search` page.
- `config/operator-surfaces/search-policy.json` holds LIKE-match boost, recency weight, and exact-key boost thresholds.

</specifics>

<deferred>
## Deferred Ideas

- FTS5 virtual table for search — research recommends LIKE + scoring for first cycle; FTS5 only after profiling shows it needed.
- `@xyflow/react` node graph for daily-flow — deferred in favor of card stack; promote only if operator feedback demands it post-Phase-10.
- Cross-project `/next-action` top-level page — deferred; cross-project view is surfaced as a "Top attention" panel on Command Center, not a dedicated route.
- `/daily-flow` dedicated page — deferred; daily-flow surfaces are embedded on Command Center (summary card) and `/runs/[id]` (collapsible trace component).

</deferred>
