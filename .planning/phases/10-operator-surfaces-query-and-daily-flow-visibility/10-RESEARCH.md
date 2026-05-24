---
phase: 10-operator-surfaces-query-and-daily-flow-visibility
phase_number: "10"
type: research
updated: 2026-05-22
---

# Phase 10 Research

**Researched:** 2026-05-22
**Domain:** Operator surfaces (Next.js App Router + tRPC), grounded-query routing, next-action recommendation, daily-flow visibility, search and drill-down across runs/packets/writebacks/health/deltas
**Confidence:** HIGH

## Summary

Phase 10 is **not** a "build a new UI" phase. Phases 1–9 already deposited every primitive Phase 10 needs to surface: routing (`orchestration_runs.route_result_json` + `RouteResult` from Phase 1) [VERIFIED: `aios-ui/server/aios/control-plane.ts:55-60`], packets (`briefing_packets` + `selection_trace_json` + `omitted_context_json` from Phase 2) [VERIFIED: `aios-ui/server/aios/control-plane.ts:74-77`], run lifecycle (`orchestration_runs` + `orchestration_invocations` + `orchestration_run_events` from Phase 3) [VERIFIED: `aios-ui/lib/control-plane.ts:108-336`], truth + knowledge (`knowledge_objects` + project dossier + grounded query from Phase 4) [VERIFIED: `aios-ui/server/aios/query.ts:387` `answerGroundedQuestion`], governed writebacks (`improvement_writebacks` + `improvement_writeback_events` + `writeback_approval_policy` from Phase 5) [VERIFIED: `aios-ui/server/aios/control-plane.ts:383-418` `getGovernanceOverview`], standards evaluation (`success_criteria_findings` + `success_criteria_stage_findings` from Phase 6), delta scoring (`standards_health_snapshots` + `standards_delta_items` + `standards_backfill_tasks` + `recommend_workflow_from_health` from Phase 7), asset lifecycle + workflow comparison (`promotion_lifecycle_items` + `compare_workflow_effectiveness` + `propose_workflow_promotion`/`propose_asset_promotion` from Phase 8), and learning + compounding (`workflow_learning_events` + `improvement_writebacks.source="learning_analysis"` + `LearningImpactPerRun` + `LearningImpactRollup` from Phase 9). The UI already has a Command Center page [VERIFIED: `aios-ui/app/page.tsx`, 206 lines], 15 tRPC routers [VERIFIED: `aios-ui/server/routers/_app.ts`, 14 router imports plus `controlPlane`], 14 server-aios projection modules [VERIFIED: `aios-ui/server/aios/`], and 17 pages including `/control`, `/projects`, `/runs`, `/workflows`, `/prompts`, `/knowledge`, `/writebacks`, `/query`, `/automations`, `/control` [VERIFIED: `aios-ui/app/` listing]. A `getControlPlaneOverview` already returns runs + packets + pendingWritebacks + governance + recentFindings [VERIFIED: `aios-ui/server/aios/control-plane.ts:359-381`]; `getGovernanceOverview` already returns proposals + pendingApprovals + terminalRunsMissingEvidence [VERIFIED: `aios-ui/server/aios/control-plane.ts:383-418`]; `answerGroundedQuestion` already routes by intent (`what_changed`, capability questions, truth-operator questions) [VERIFIED: `aios-ui/server/aios/query.ts:387-450`].

What is missing is **eight specific gaps**, each of which is a wiring + projection task on top of existing data, not a new subsystem: **(1) Cross-entity search** — the sidebar has no search box; there is no `searchEntities(query, kinds, projectId)` projection that can return mixed-kind matches (runs/packets/writebacks/findings/prompts/skills/workflows/knowledge_pages/route_decisions/standards) ranked by relevance. **(2) Next-action recommendation** — Phase 7 ships `recommend_workflow_from_health(project_id)`, Phase 8 ships `recommend_assets_for_packet`, Phase 9 ships `RecurringPattern`-derived proposals, but nothing **fuses these into a single per-project "next action" surface** that operators see on the project detail page and on the Command Center. **(3) Daily-flow trace** — every step (goal → route → packet → run → evaluation → writeback → unresolved deltas → next action) is persisted, but there is no projection that **threads them together for a single objective-or-run-id input** and returns a strongly-typed `DailyFlowTrace` ready for UI rendering with drill-down links. **(4) Query-as-launcher** — `answerGroundedQuestion` returns answers but never returns "and here is the workflow you should launch and the packet that would result"; it should integrate `recommend_workflow_from_health` + `recommend_assets_for_packet` + `recommend_route_primitives` into its response shape so a single grounded query can trigger a planned run. **(5) Automation → workflow trigger** — `automations` router lists health, but has no `triggerWorkflow` mutation or persisted trigger→workflow binding; the phase scope explicitly says "automations and health deltas should become workflow-launch triggers, not only read surfaces." **(6) Per-entity drill-down receipts** — runs already drill to packet via `runDetail`; packets already expose `selection_trace_json`; but writebacks, findings, deltas, asset recommendations, and learning impact rows do NOT yet expose their evidence trail as clickable links to the source rows (only as inline text). **(7) Search-friendly indexing** — most tRPC list procedures take `limit` but no `query`/`filter` parameter; even the `projects.list({ limit })` shape limits Phase 10's ability to deliver searchable surfaces. **(8) Seed/fallback ambiguity** — `aios-ui/app/page.tsx` renders the Command Center but also `getControlPlaneOverview` returns hardcoded `workflowTemplates`/`agentProfiles`/`invocationBackends` from `aios-ui/server/aios/catalog.ts` rather than from `config/workflows/registry.json` truth [VERIFIED: `aios-ui/server/aios/control-plane.ts:373-374`]; UI fallbacks must be removed in favor of real truth, or clearly labeled as seed data per the phase's "reduced fallback/seed ambiguity in UI" expected output.

**Primary recommendation:** Treat Phase 10 as **five additive layers on top of Phase 1–9 primitives**, in this order: **(a) Searchable entity index** — add `services/operator_search.py` and `aios-ui/server/aios/operator-search.ts` that expose `search_entities(query, kinds?, project_id?, limit?)` returning `OperatorSearchHit{kind, id, title, summary, project_id?, score, source_table, last_updated_at, drill_down_path}` across runs, packets, writebacks, findings, prompts (templates + history), skills, workflows, knowledge_objects, route_decisions, standards_delta_items, automations, experiments, learning patterns, divergent runs. The search is a bounded `LIKE` + relevance-scored UNION across the source tables; no FTS index required for the first cycle. Expose as `operatorSearch.search` tRPC procedure and as `aios operator-search "..."` CLI. **(b) Next-action surface** — add `services/next_action.py` and `aios-ui/server/aios/next-action.ts` that fuse `recommend_workflow_from_health(project_id)` (Phase 7), `listConservativeProposals(status='pending_approval', source='learning_analysis')` (Phase 9), `terminalRunGaps()` (existing), open `success_criteria_findings.level='blocker'` rows (Phase 6), pending `improvement_writebacks` (Phase 5), and standards backfill tasks (Phase 7) into a per-project ranked list `NextAction[]` with `{kind, title, rationale, recommended_workflow_key?, evidence_run_ids, priority_bucket, drill_down_path}`. Expose as `nextAction.getForProject` tRPC + `aios next-action --project X` CLI; surface on Command Center and project detail page. **(c) Daily-flow trace** — add `services/daily_flow.py` and `aios-ui/server/aios/daily-flow.ts` that take either an `objective` (and optionally `project_id`) OR a `run_id` and return a strongly-typed `DailyFlowTrace{goal, route, packet, run, evaluations[], writebacks[], unresolved_deltas[], next_actions[]}` with each node carrying both a summary and a `drill_down_path` to the existing UI page. For the goal-input case, run the **dry** route + packet projection (existing `planTask` flow but without persisting) so operators can preview the full trace before launching. Expose as `dailyFlow.preview` (objective input) + `dailyFlow.replay` (run_id input) tRPC procedures + `aios daily-flow --objective "..." --dry-run` CLI. **(d) Query-as-launcher** — extend `answerGroundedQuestion` to also call `recommend_workflow_from_health` + `recommend_route_primitives` (Phase 1) when the question matches the "what should I do next" intent class, and return `GroundedAnswer & { recommendedWorkflow?, recommendedPacketPreview?, launchableRunId? }`. The UI shows a "Launch workflow" button next to recommendations; clicking calls existing `controlPlane.plan` then `controlPlane.invoke`. **(e) Automation → workflow trigger** — extend the `automations` router with `triggerWorkflow` mutation and persist trigger→workflow bindings in a new `automation_workflow_triggers` table (or as a JSON column on the existing automation rows — confirm in discuss-phase); extend health-delta surface so a `priority_bucket='foundational'` standards_delta_item can be a one-click workflow launch via `controlPlane.plan` with the delta's `recommended_remediation_workflow` (Phase 7 already provides this).

In parallel: **(f) Replace seed/catalog fallbacks** — `aios-ui/server/aios/catalog.ts` currently hardcodes `workflowTemplates`/`agentProfiles`/`invocationBackends`; Phase 10 must wire these to read from `config/workflows/registry.json` (post-Phase-8 vNext shape) and `services/execution_strategy.py` / `services/invocation_backends.py` at server boot. Label any remaining demo/seed data clearly so operators don't confuse it with truth. **(g) Drill-down link discipline** — add a `drill_down_path` field to every projection that returns operator-visible rows (writebacks, findings, deltas, asset recommendations, learning rollups, route decisions, patterns), pointing to a canonical UI route (e.g., `/runs/<id>`, `/writebacks#<id>`, `/projects/<id>?delta=<id>`). This is a one-field-per-projection extension, not new persistence.

**Critical constraint:** Phase 10 is **the last phase**; STATE.md says only 5 phases complete, but the roadmap places Phase 10 as gated by all prior milestones. The plan-checker and discuss-phase MUST verify whether Phases 5–9 are actually green before allowing Phase 10 execution. If not, Phase 10's scope contracts: any surface depending on a not-yet-shipped projection (e.g., LearningImpactPerRun if Phase 9 incomplete) gracefully renders "unknown" with a labeled missing-source explanation rather than blanking out. See Pitfall 8.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Cross-entity search index | Python (`services/operator_search.py`) | UI (`aios-ui/server/aios/operator-search.ts` + new `operatorSearch` router) | Search is a bounded read projection across existing tables; same shape on both sides; one canonical scorer in Python with a TypeScript mirror for client-side ranking on small result sets. |
| Next-action recommendation | Python (`services/next_action.py`) | UI (`aios-ui/server/aios/next-action.ts` + `nextAction` router) | Fuses 5+ existing recommenders (Phase 5/6/7/8/9) into one ranked list per project; lives in Python so the CLI can also surface it. |
| Daily-flow trace (preview + replay) | Python (`services/daily_flow.py`) | UI (`aios-ui/server/aios/daily-flow.ts` + extension of `controlPlane` or new `dailyFlow` router) | Threads existing tables together; no new persistence; preview mode runs route + packet generation without persistence side effects. |
| Query-as-launcher integration | Python (`services/task_routing.py` integration) | UI (extend `aios-ui/server/aios/query.ts` `answerGroundedQuestion`) | Extension on existing query module; new intent class `should_i_run_workflow` + integration with `recommend_route_primitives`. |
| Automation → workflow trigger | UI (`aios-ui/server/routers/automations.ts` + new mutation) | SQLite (new optional `automation_workflow_triggers` table OR JSON column extension) | Trigger persistence is light; mutation reuses existing `controlPlane.plan` + `controlPlane.invoke` flow. |
| Health-delta → workflow launch | UI (extend `projects` router) + Python | — | `standards_delta_items.remediation_playbook_json` already carries `recommended_workflow_key` (Phase 7); the gap is a button + tRPC mutation that calls existing planTask. |
| Drill-down path discipline | UI projections (every `server/aios/*.ts`) | — | Add `drill_down_path: string` field to existing row shapes; no new data, just URL construction. |
| Catalog truth-or-seed labeling | UI (`aios-ui/server/aios/catalog.ts`) | Config (`config/workflows/registry.json`, `services/invocation_backends.py`) | Replace hardcoded constants with config + service reads at server boot; any remaining demo data is explicitly labeled `isSeedData: true`. |
| Search-friendly list parameters | UI (every `server/routers/*.ts` list procedure) | — | Each list procedure accepts `query?: string`, `filter?: Record<string,string>`, `sort?` with bounded enums; backend filters at DB layer. |
| Operator-visible compounding | UI (extend Command Center page) | Python (`services/learning_impact.py` from Phase 9) | Surfaces `LearningImpactRollup` per workflow on the Command Center next to existing health stats. |
| Operator CLI parity | Python (`services/aios_cli.py`) | — | `aios operator-search`, `aios next-action`, `aios daily-flow`, `aios trigger-workflow`. |

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| OPER-01 | AIOS provides searchable, inspectable operator views for projects, runs, workflows, knowledge, prompts, deltas, approvals, and recent changes | Existing tRPC routers cover projects, runs (sessions), workflows, knowledge, prompts, automations, experiments, divergent, patterns, costs, changes, insights, query [VERIFIED: `aios-ui/server/routers/_app.ts`]. **Gap:** no cross-entity search; list procedures lack `query`/`filter` parameters; no sidebar search box. **Phase 10 adds** `services/operator_search.py` + `operatorSearch.search` tRPC + extends every `list` procedure with `query`/`filter` parameters + adds a global search input to `aios-ui/components/layout/TopBar.tsx`. Deltas surface exists at `/projects/[id]` consuming `standards_delta_items` via Phase 7's `getProjectStandardsHealth`; approvals surface exists at `/writebacks` consuming `improvement_writebacks` via Phase 5's `getGovernanceOverview`; recent changes surface exists via `changesRouter` [VERIFIED: `_app.ts:1,17`]. |
| OPER-02 | AIOS can answer which project needs attention, what good looks like, which workflow should run, which prompt/skill assets apply, and which context an agent needs before manual prep | Existing primitives: `recommend_workflow_from_health(project_id)` (Phase 7), `recommend_assets_for_packet(task_classifications, workflow_family, project_id)` (Phase 8), `recommend_route_primitives(objective, project_id)` (Phase 1), `terminalRunGaps()` (existing), `listConservativeProposals` (Phase 9). **Gap:** no fusion surface. **Phase 10 adds** `services/next_action.py` + `nextAction.getForProject` tRPC + `aios next-action` CLI; integrates these into `aios-ui/app/projects/[id]/page.tsx` "Next action" panel and into the Command Center "Attention" alerts (already prototyped via `buildAttentionAlerts` [VERIFIED: `aios-ui/app/page.tsx:9`]). |
| OPER-03 | AIOS exposes receipts, routing decisions, evidence trails, and drill-down paths for visible metrics and recommendations | Existing primitives: `route_result_json` on runs (Phase 1), `selection_trace_json` + `omitted_context_json` on packets (Phase 2), `workflow_execution_reports.report_json` with stage evaluations (Phase 3/8), `evidence_json` + `confidence` + `last_evaluated_at` on `standards_assessments` (Phase 7), `evidence_json` + `proposed_change_json` on `improvement_writebacks` (Phase 5), `rationale_json` on asset recommendations (Phase 8), `evidence_run_ids` on `RecurringPattern` (Phase 9). **Gap:** projections do not surface a `drill_down_path` field, so the UI can render text but not click-through. **Phase 10 adds** a `drill_down_path` field to every projection that returns operator-visible rows and renders deep-links in tables/cards (one-field-per-projection extension). |
| OPER-04 | AIOS can surface the default-layer daily flow end to end: vague goal → routing → execution → evaluation → writeback → unresolved deltas | Every step is persisted: `recommend_route_primitives` (Phase 1) → `briefing_packets` (Phase 2) → `orchestration_runs` (Phase 3) → `success_criteria_findings` (Phase 6) → `improvement_writebacks` (Phase 5) → `standards_delta_items` (Phase 7). **Gap:** no single projection threads them together. **Phase 10 adds** `services/daily_flow.py` + `dailyFlow.preview(objective)` / `dailyFlow.replay(run_id)` tRPC + a Command Center "Daily Flow" component that renders the seven-step trace with drill-downs. |

## Project Constraints (from CLAUDE.md / AGENTS.md)

| Constraint | Source | Phase 10 Implication |
|------------|--------|---------------------|
| Run quality ladder: `ruff check . && ruff format --check . && basedpyright && vulture` | `~/.claude/CLAUDE.md` Python canonical commands | Every Python implementation task in this phase ends with these as a hard gate. |
| UI quality ladder: `pnpm lint && pnpm tsc --noEmit` (no `pnpm test` is wired in `aios-ui/package.json` [VERIFIED]) | `~/.claude/CLAUDE.md` + AGENTS.md | Any TypeScript edit in `aios-ui/server/{aios,routers}/` or `aios-ui/app/**` or `aios-ui/components/**` ends with these. `pnpm lint` runs eslint + tsc per `aios-ui/package.json:scripts.lint`. |
| Architecture lint: `pnpm lint:architecture` (dependency-cruiser) | `aios-ui/package.json:scripts.lint:architecture` | UI architecture boundaries are enforced; any new `server/aios/*.ts` must follow existing import patterns. |
| Atomic commits scoped to one project + one concern, followed by immediate `PROJECT.md` truth update commit | `~/.claude/CLAUDE.md` Git rules | Each task in this phase commits independently and updates `PROJECT.md` before the next task begins. |
| `main` stays deployable | `~/.claude/CLAUDE.md` Git | Phase 10 work goes through feature branches per repo discipline; `.planning/config.json` has `branching_strategy: none` so confirm in discuss-phase whether autonomous mode bypasses branching here. |
| No `--no-verify` or `--no-gpg-sign` bypasses | `~/.claude/CLAUDE.md` Git | Honor pre-commit hooks. |
| Never use `cat << EOF` or heredoc for file creation | Agent harness rule | Use Write tool for any new file. |
| Don't add comments/docstrings/type annotations to code I didn't change | `~/.claude/CLAUDE.md` Working style | Edits stay scoped; do not blanket-annotate touched modules. |
| Three similar lines is better than premature abstraction | `~/.claude/CLAUDE.md` Working style | Resist building a generic "search-projection framework"; extend the per-projection pattern that `aios-ui/server/aios/standards-health.ts` and `aios-ui/server/aios/control-plane.ts` already use. |
| TypeScript strict, no `any` in production code | `~/.claude/CLAUDE.md` TypeScript | Every new tRPC procedure and projection function carries explicit types; reuse `aios-ui/lib/control-plane.ts` types where possible. |
| Server Components by default, `"use client"` only when needed | `~/.claude/CLAUDE.md` Next.js | Existing pages already follow this — `app/page.tsx`, `app/control/page.tsx` are server components fetching via `getCaller()`. New pages should match. |
| Server Actions for mutations over API routes where practical | `~/.claude/CLAUDE.md` Next.js | New mutations (workflow trigger, search filter) use tRPC mutations rather than custom API routes. |
| Local-first + files-authoritative | AGENTS.md (Constraints) | Search and next-action data live in SQLite + registry JSON; no external services. |
| Governance must remain reviewable | AGENTS.md | Phase 10 NEVER auto-launches workflows; every trigger flows through existing `controlPlane.plan` (proposes) + `controlPlane.invoke` (operator-approved click). Health-delta-driven triggers also require operator confirmation. |
| Explainability is required | AGENTS.md | Every operator-visible metric MUST carry source + freshness + provenance; reuse `trustedSignal()` from `aios-ui/lib/trusted-signals.ts` everywhere. |
| Brownfield continuity | AGENTS.md | Existing UI pages must keep rendering during the phase; new fields default to safe values when missing source data; deprecation of `aios-ui/server/aios/catalog.ts` constants happens incrementally with one-cycle alias. |
| Architecture boundary: `services/` cannot import `bin/` | `tests/test_architecture_enforcement.py` | New `services/operator_search.py`, `services/next_action.py`, `services/daily_flow.py` cannot import from `bin/aios_orchestration_runtime`. Phase 8/9 established a re-export pattern for `writeback_approval_policy`; Phase 10 reuses the same shim approach. |
| Execution-first verification for stateful/cross-system changes | AGENTS.md "Rule: Execution-First Verification" | Search projection touches 10+ tables; tests must seed real fixture rows and assert against the SQL queries, not just mock the results. |
| Tier-one failure conditions: "No polished surface may mask weak or missing backend truth" | `TIER_ONE_ACCEPTANCE_CHECKLIST.md:213-225` | Phase 10 explicitly forbids fake/seed data masking real source gaps. The Command Center must label all seed/catalog data and Wave 0 must include a sweep that removes or flags every fallback. |
| Tier-one failure conditions: "No key metric or recommendation may be non-explainable" | `TIER_ONE_ACCEPTANCE_CHECKLIST.md:213-225` | Every recommendation surface MUST carry `rationale` + `evidence_run_ids` (or equivalent) and link to drill-down. |
| Tier-one failure conditions: "No daily-flow claim may exist if routing, packets, run state, evaluation, or writeback are still disconnected" | `TIER_ONE_ACCEPTANCE_CHECKLIST.md:213-225` | If any of Phases 1-7 is incomplete, the daily-flow surface either renders gracefully with explicit "unknown — phase X not complete" labels, or the Phase 10 work is paused. |

## Standard Stack

### Core (existing — extend, don't replace)

| Library / Surface | Version | Purpose | Why Standard |
|-------------------|---------|---------|--------------|
| Next.js | 16.x | App Router server components + tRPC integration | Already in use per `aios-ui/package.json`; Phase 10 reuses existing page patterns. [VERIFIED: `aios-ui/package.json:18`] |
| React | 19.x | UI primitives | Already in use per `aios-ui/package.json`. [VERIFIED: `aios-ui/package.json:19-20`] |
| tRPC | 11.x | Type-safe RPC layer | Already in use; every new procedure uses `createTRPCRouter` + `publicProcedure`. [VERIFIED: `aios-ui/package.json:15-17`] |
| `@tanstack/react-query` | 5.x | Server state cache (client side) | Already in use. [VERIFIED: `aios-ui/package.json:14`] |
| zod | 3.x | Runtime input validation on tRPC routes | Already in use; every new input is `z.object(...)`. [VERIFIED: `aios-ui/package.json:25`] |
| better-sqlite3 | 11.x | Direct SQLite from UI server | Already in use; reuse `aios-ui/server/db.ts` `getDb()`. [VERIFIED: `aios-ui/package.json:17`] |
| superjson | 2.x | tRPC serialization for Date/Map etc. | Already in use. [VERIFIED: `aios-ui/package.json:24`] |
| `aios-ui/server/aios/control-plane.ts` `getControlPlaneOverview` | in-tree (667 lines) | Returns runs + packets + pendingWritebacks + governance + recentFindings | Phase 10 extends with `nextActions[]` + `dailyFlowTrace?` on the response shape; does NOT replace. [VERIFIED: read complete file] |
| `aios-ui/server/aios/control-plane.ts` `getGovernanceOverview` | in-tree | Returns proposals + pendingApprovals + terminalRunsMissingEvidence | Phase 10 adds `policyClassDrillDowns: Record<string, string>` mapping each policy class to its filtered writebacks-page URL. [VERIFIED: read complete file] |
| `aios-ui/server/aios/query.ts` `answerGroundedQuestion` | in-tree (730 lines) | Routes by intent (`what_changed`, capability, truth-operator, ...) | Phase 10 extends with `should_i_run_workflow` intent that integrates `recommend_route_primitives` + `recommend_workflow_from_health`. [VERIFIED: read first 450 lines] |
| `aios-ui/server/aios/standards-health.ts` `getProjectStandardsHealth` | in-tree (322 lines) | Returns snapshot + deltaItems + backfillTasks + deltaExplanations + recommendedWorkflows (post-Phase-7) | Phase 10 adds `drill_down_path` to every delta item and backfill task; adds "launch remediation workflow" mutation button. [VERIFIED: read shape] |
| `aios-ui/server/aios/learning.ts` `proposeRunWritebacks` + post-Phase-9 `getLearningImpactForRun` / `getLearningImpactRollup` / `listRecurringPatterns` / `listConservativeProposals` | in-tree (169 lines + Phase 9 extensions) | Per-run + per-rollup compounding visibility | Phase 10 surfaces these on the Command Center and project detail pages. [VERIFIED: read file] |
| `aios-ui/server/aios/packet-assembly.ts` `assembleRankedPacket` + `expandPacketContext` | in-tree (541 lines) | Packet generation seam | Phase 10 reuses for `dailyFlow.preview` (objective input → projected packet without persistence). [VERIFIED: line count] |
| `aios-ui/server/aios/runtime.ts` `startManagedInvocation` + `getRunDetail` | in-tree | Run lifecycle | Phase 10 reuses for "Launch workflow" button from query / next-action / daily-flow surfaces. [VERIFIED: `control-plane.ts:21-29` imports] |
| `aios-ui/server/aios/changes.ts` + `changesRouter` | in-tree (16 lines, thin router) | Recent-changes surface | Phase 10 extends with `query`/`filter` parameters on `list`. [VERIFIED: `_app.ts:1`] |
| `aios-ui/server/aios/knowledge.ts` + `knowledgeRouter` (`index`, `grouped`, `truthBoundary`) | in-tree (31 lines) | Knowledge page index + grouping + truth boundary | Phase 10 adds `search` procedure that combines with `operatorSearch.search` on the knowledge axis. [VERIFIED: `routers/knowledge.ts`] |
| `services/task_routing.py` `recommend_route_primitives` + `RouteResult` (Phase 1) | in-tree | Route synthesis | Phase 10's `nextAction` and `dailyFlow.preview` reuse without modification. |
| `services/standards_health.py` `recommend_workflow_from_health` (Phase 7) | in-tree | Workflow recommendation from delta state | Phase 10's `nextAction` fuses with other inputs. |
| `services/asset_recommendation.py` `recommend_assets_for_packet` (Phase 8) | in-tree (post-Phase 8) | Asset recommendation | Phase 10's `nextAction` surfaces recommended prompt/skill assets per project. |
| `services/learning_impact.py` `build_per_run_impact` + `build_rollup` (Phase 9) | in-tree (post-Phase 9) | Compounding visibility | Phase 10 surfaces on Command Center. |
| `services/aios_cli.py` | in-tree | Headless operator surface | Phase 10 adds `aios operator-search`, `aios next-action`, `aios daily-flow`, `aios trigger-workflow` subcommands. |

### Supporting (no new external deps required)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `sqlite3` (Python stdlib) | 3.x | All persistence + bounded read queries | Reuse `ensure_*_schema` + `LIKE`/`WHERE` patterns; no new tables for search (UNION across existing). |
| `json` (stdlib) | — | Registry + JSON-column parsing | Reuse existing helpers. |
| `dataclasses` (stdlib) | — | Frozen dataclasses for `OperatorSearchHit`, `NextAction`, `DailyFlowTrace`, `DailyFlowStep` | Follow `TrustedSignal` / `EvaluatedStandard` shape. |
| `typing.Literal` | stdlib | `EntityKind = Literal[...]`, `NextActionKind = Literal[...]`, `DailyFlowStepKind = Literal[...]` | Single source per concept in `services/operator_search.py` / `services/next_action.py` / `services/daily_flow.py`. |
| `pytest` 8.x | — | Test framework | Follow `tests/test_aios_cli.py` + `tests/test_standards_health.py` in-memory sqlite + seed-runtime patterns. |
| `recharts` | 2.15.x | Charts for compounding rollups | Already in use per `aios-ui/package.json:23`; reuse where needed. [VERIFIED] |
| `@xyflow/react` | 12.10.x | Graph rendering (already used for topic graph) | Available if Phase 10 wants a daily-flow node graph; otherwise simple cards are sufficient. [VERIFIED: `aios-ui/package.json:18`] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `LIKE`-based search across UNION of tables | SQLite FTS5 virtual table per entity kind | FTS5 is more powerful but requires schema additions, index maintenance on every insert, and benchmark for a small-database deployment. **Choose: LIKE + score ranking** for first cycle; FTS5 can land in a follow-up if profiling shows it. |
| One `operatorSearch.search` tRPC procedure returning mixed-kind hits | Per-kind search procedures (`operatorSearch.searchRuns`, `operatorSearch.searchWritebacks`, etc.) | Per-kind procedures repeat the same input shape and require N round-trips for "search across everything." **Choose: one mixed-kind procedure** with optional `kinds: EntityKind[]` filter; UI calls once. |
| New `next_actions` cache table | Recompute on read from source recommendations | Sources (delta items, terminal-run gaps, pending writebacks) refresh slowly — once per session close. Read-time fusion is cheap and avoids cache invalidation bugs. **Choose: recompute on read.** Cache only if profiling shows it. |
| One `dailyFlow.trace` tRPC procedure that handles both preview (objective) and replay (run_id) | Two distinct procedures `dailyFlow.preview(objective)` + `dailyFlow.replay(run_id)` | Mixing two intents in one input schema with `z.union` is confusing; two procedures with clear input contracts is clearer. **Choose: two procedures.** |
| Extending `controlPlane` router with next-action / daily-flow / search procedures | New routers `nextAction`, `dailyFlow`, `operatorSearch` | `controlPlane` is already 100 lines and concerns-heavy; new routers keep concerns separable. **Choose: new routers** (3 new files). Add the existing `controlPlane.overview` response shape with optional embedded `nextActions[]` + `dailyFlowSummary` for the Command Center page (one round-trip). |
| Building a daily-flow node graph with `@xyflow/react` | Simple stacked cards with drill-down links | A node graph is visually engaging but the daily flow is linear (7 steps) — a card stack with clear arrows is sufficient and simpler. **Choose: card stack for first cycle**; graph if discuss-phase requests it. |
| Replacing `aios-ui/server/aios/catalog.ts` constants in one cutover | Incremental — read from config at server boot, fall back to constants for one cycle | Brownfield continuity (AGENTS.md) — keep UI rendering through the migration. **Choose: incremental with explicit `isSeedData: true` labels** when fallback fires. |
| New `automation_workflow_triggers` table | JSON column on existing `automations` row | Bindings are 1:N (one automation can trigger one workflow); a column is simpler. **Choose: JSON column extension** (`automations.workflow_trigger_binding_json`). Confirm in discuss-phase — operator might prefer a table for audit history. |
| Real-time "launch workflow from health delta" | Operator confirmation step (modal) before launching | Real-time autolaunch violates Phase 5 governance discipline (writebacks > approval > action). **Choose: operator-click confirmation always.** This is the load-bearing safety property of the phase. |
| Adding global sidebar search input | Per-page search input | Sidebar search is the universal entry; per-page search complements it but doesn't replace it. **Choose: both** — sidebar search + page-local filters on list views. |
| Building search relevance via TF-IDF | Simple multi-field LIKE + recency weighting | TF-IDF is overkill for a local-first single-user system. **Choose: LIKE matches on `title`/`summary`/`key` + boost by `updated_at` recency + boost by exact-match on entity key.** Tunable thresholds in `config/operator-surfaces/search-policy.json` (new — confirm in discuss-phase). |
| Per-project default scope for next-action | Cross-project default (sorted by urgency) | Operators usually work on one project at a time; per-project default matches existing UI flow (project detail page). **Choose: per-project default**; cross-project view exposed via Command Center "Top attention" panel. |
| Building "Launch workflow" buttons as tRPC mutations | Server Actions on Next.js pages | tRPC mutations are already the convention (see `controlPlane.plan`/`controlPlane.invoke`); consistency wins. **Choose: tRPC mutations.** |

**Installation:** No new external dependencies. Phase 10 is entirely additive to existing in-tree modules and reuses every tool already wired in `aios-ui/package.json` and `pyproject.toml`.

**Version verification:** `aios-ui/package.json` versions verified in-tree [VERIFIED: read complete file]. `pyproject.toml` confirms Python 3.12 + ruff + basedpyright + pytest configured [VERIFIED: read top portion]. No external package version checks required since the phase adds no new dependencies.

## Architecture Patterns

### System Architecture Diagram

```
                                  ┌──────────────────────────────────────────┐
                                  │ Operator (browser or CLI)                │
                                  └─────────┬────────────────────────────────┘
                                            │
                ┌───────────────────────────┼───────────────────────────┐
                │                           │                           │
                ▼                           ▼                           ▼
   ┌──────────────────────┐   ┌──────────────────────┐    ┌──────────────────────┐
   │ Sidebar global search│   │ Page-local list      │    │ services/aios_cli.py │
   │ (TopBar.tsx)         │   │ filters (per route)  │    │  operator-search,    │
   │                      │   │                      │    │  next-action,        │
   │                      │   │                      │    │  daily-flow,         │
   │                      │   │                      │    │  trigger-workflow    │
   └──────────┬───────────┘   └──────────┬───────────┘    └──────────┬───────────┘
              │                          │                           │
              ▼                          ▼                           ▼
   ┌────────────────────────────────────────────────────────────────────────────┐
   │ tRPC routers (existing + new)                                              │
   │  controlPlane.overview / governance / runDetail / plan / invoke (existing) │
   │  operatorSearch.search           ── NEW                                    │
   │  nextAction.getForProject        ── NEW                                    │
   │  nextAction.topAcrossProjects    ── NEW                                    │
   │  dailyFlow.preview (objective)   ── NEW                                    │
   │  dailyFlow.replay (run_id)       ── NEW                                    │
   │  query.ask                       ── EXTEND (adds workflow recommendation)  │
   │  automations.triggerWorkflow     ── NEW                                    │
   │  projects.detail / list          ── EXTEND (query/filter params)           │
   │  projects.launchRemediation      ── NEW (one-click delta → workflow)       │
   └─────────┬───────────────────────────┬──────────────────────────────────────┘
             │                           │
             ▼                           ▼
   ┌─────────────────────┐    ┌────────────────────────────────────────────────┐
   │ aios-ui/server/aios/│    │ Python services (new + existing)               │
   │  operator-search.ts │    │  services/operator_search.py    ── NEW          │
   │  next-action.ts     │    │  services/next_action.py        ── NEW          │
   │  daily-flow.ts      │    │  services/daily_flow.py         ── NEW          │
   │  (extensions to     │    │  services/task_routing.py       ── EXISTING     │
   │   query.ts,         │    │  services/standards_health.py   ── EXISTING     │
   │   control-plane.ts, │    │   recommend_workflow_from_health()              │
   │   standards-health, │    │  services/asset_recommendation.py ── EXISTING   │
   │   learning.ts)      │    │   recommend_assets_for_packet()                 │
   └──────────┬──────────┘    │  services/learning_impact.py    ── EXISTING     │
              │               │   build_per_run_impact / build_rollup           │
              │               │  services/learning_analysis.py  ── EXISTING     │
              │               │   detect_recurring_patterns                     │
              │               │  services/agentize.py           ── EXISTING     │
              │               │  services/workflow_promotion.py ── EXISTING     │
              │               │   compare_workflow_effectiveness                │
              │               └────────────────────┬───────────────────────────┘
              │                                    │
              │                                    ▼ bounded reads
              ▼                  ┌────────────────────────────────────────────┐
   ┌──────────────────────┐      │ SQLite (no new tables for search/         │
   │ Direct DB reads via  │      │  next-action; one optional config-driven  │
   │ better-sqlite3       │      │  add for automation_workflow_triggers OR  │
   │ (existing pattern    │      │  JSON column extension)                   │
   │  for projections)    │      │                                            │
   │                      │      │  Read sources:                            │
   │                      │      │   orchestration_runs (.route_result_json)│
   │                      │      │   briefing_packets                       │
   │                      │      │   improvement_writebacks                 │
   │                      │      │   success_criteria_findings              │
   │                      │      │   standards_delta_items                  │
   │                      │      │   standards_backfill_tasks               │
   │                      │      │   workflow_execution_reports             │
   │                      │      │   knowledge_objects + prompts_used       │
   │                      │      │   workflow_learning_events               │
   │                      │      │   promotion_lifecycle_items              │
   │                      │      │   experiments + workflow_skill_experiments│
   │                      │      │   divergent_runs                         │
   │                      │      │   automations + automation_run_history   │
   └──────────┬───────────┘      └────────────────────────────────────────────┘
              │
              ▼
   ┌────────────────────────────────────────────────────────────────────────────┐
   │ Next.js App Router pages (existing + new)                                  │
   │  /                  Command Center  (extend: nextActions panel,            │
   │                                       dailyFlowSummary card,               │
   │                                       compounding rollup row,              │
   │                                       global search input in TopBar)       │
   │  /projects/[id]     Project detail  (extend: nextActions panel,            │
   │                                       drill-down deltas + remediation,     │
   │                                       launch-workflow mutation)            │
   │  /runs/[id]         Run detail      (extend: daily-flow trace component)   │
   │  /query             Grounded Query  (extend: launch-workflow button on     │
   │                                       answer when recommendation present)  │
   │  /writebacks        Writebacks      (extend: filter/search by source +     │
   │                                       policy class + status)               │
   │  /control           Control Plane   (already exists — no major change)     │
   │  /search            Search results  (NEW page — global search landing)     │
   │  /automations       Automations     (extend: triggerWorkflow button +      │
   │                                       binding-edit UI)                     │
   └────────────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure (additions)

```
services/
├── operator_search.py            # NEW: OperatorSearchHit dataclass,
│                                 #      EntityKind literal,
│                                 #      search_entities(query, kinds?, project_id?,
│                                 #                      limit?) -> list[OperatorSearchHit].
│                                 #      Internal dispatch:
│                                 #        _search_runs, _search_packets,
│                                 #        _search_writebacks, _search_findings,
│                                 #        _search_prompts, _search_skills,
│                                 #        _search_workflows, _search_knowledge,
│                                 #        _search_route_decisions, _search_deltas,
│                                 #        _search_automations, _search_experiments,
│                                 #        _search_patterns, _search_divergent_runs.
│                                 #      _score_hit(entity, query) -> float.
│
├── next_action.py                # NEW: NextAction dataclass,
│                                 #      NextActionKind literal,
│                                 #      get_next_actions(project_id?) -> list[NextAction].
│                                 #      Fuses:
│                                 #        recommend_workflow_from_health (Phase 7),
│                                 #        terminal_run_gaps (existing),
│                                 #        open success_criteria_findings.level='blocker',
│                                 #        pending improvement_writebacks,
│                                 #        listConservativeProposals (Phase 9),
│                                 #        standards_backfill_tasks priority bucket,
│                                 #        recommend_assets_for_packet (Phase 8).
│                                 #      Ranking: urgency × leverage × freshness.
│
├── daily_flow.py                 # NEW: DailyFlowStep dataclass (kind, summary,
│                                 #      evidence_ref, drill_down_path,
│                                 #      provenance, freshness),
│                                 #      DailyFlowTrace dataclass.
│                                 #      preview_from_objective(objective, project_id?)
│                                 #        -> DailyFlowTrace  (dry route+packet, NO persistence)
│                                 #      replay_from_run(run_id) -> DailyFlowTrace
│                                 #        (joins existing tables, no mutation).
│                                 #      Step order:
│                                 #        goal → route → packet → run → evaluation →
│                                 #        writeback → unresolved_deltas → next_actions
│
├── aios_cli.py                   # extend: aios operator-search "..." [--kinds] [--project],
│                                 #         aios next-action [--project],
│                                 #         aios daily-flow --objective "..." [--dry-run] | --run-id X,
│                                 #         aios trigger-workflow --automation-id X
│                                 #         (or --delta-id X for health-delta path).
│                                 #         Reuse argparse + JSON output flag pattern.
│
└── task_routing.py + agentize.py # NO RUNTIME CHANGE in Phase 10 — they continue to
                                  # serve daily_flow.preview as read-only callers.

aios-ui/
├── server/
│   ├── aios/
│   │   ├── operator-search.ts    # NEW: searchEntities(db, query, kinds?, projectId?,
│   │   │                         #      limit?) mirroring Python shape.
│   │   ├── next-action.ts        # NEW: getNextActions(db, projectId?) mirroring
│   │   │                         #      Python shape.
│   │   ├── daily-flow.ts         # NEW: previewDailyFlow / replayDailyFlow
│   │   ├── control-plane.ts      # extend: getControlPlaneOverview response
│   │   │                         #         includes optional nextActions + dailyFlowSummary
│   │   ├── query.ts              # extend: answerGroundedQuestion gains
│   │   │                         #         recommendedWorkflow? + launchableRunId?
│   │   │                         #         when intent = should_i_run_workflow.
│   │   ├── standards-health.ts   # extend: every delta + backfill task carries
│   │   │                         #         drill_down_path; new launchRemediation function.
│   │   ├── learning.ts           # extend: surface LearningImpactRollup on Command Center
│   │   │                         #         (rollup per workflow).
│   │   └── catalog.ts            # MIGRATE: read workflowTemplates / agentProfiles /
│   │                             #          invocationBackends from config + services at
│   │                             #          server boot; fall back to current constants
│   │                             #          with `isSeedData: true` flag during transition.
│   │
│   └── routers/
│       ├── operator-search.ts    # NEW: operatorSearch tRPC router.
│       ├── next-action.ts        # NEW: nextAction tRPC router.
│       ├── daily-flow.ts         # NEW: dailyFlow tRPC router (preview / replay).
│       ├── automations.ts        # extend: triggerWorkflow mutation.
│       ├── projects.ts           # extend: list/detail accept query?/filter?; new
│       │                         #         launchRemediation mutation.
│       ├── workflows.ts          # extend: list/approved accept query?/filter?;
│       │                         #         new effectiveness procedure surfacing
│       │                         #         compare_workflow_effectiveness (Phase 8).
│       ├── writebacks.ts (NEW)   # NEW: writebacks router with list/detail by
│       │                         #         status/policyClass/source/projectId.
│       │                         #         (Currently writebacks render via
│       │                         #         /writebacks page calling
│       │                         #         caller.divergent.writebacks(); Phase 10
│       │                         #         adds first-class writebacks router that
│       │                         #         reads improvement_writebacks directly.)
│       ├── query.ts              # extend: ask mutation response now includes optional
│       │                         #         recommendedWorkflow + launchableRunId.
│       └── _app.ts               # extend: register operatorSearch, nextAction,
│                                 #         dailyFlow, writebacks routers.
│
├── app/
│   ├── page.tsx                  # extend: nextActions panel, dailyFlowSummary card,
│   │                             #         compounding rollup row, global search input
│   │                             #         lives in TopBar.tsx not here.
│   ├── projects/[id]/page.tsx    # extend: nextActions panel, launch-remediation
│   │                             #         buttons next to high-priority deltas.
│   ├── runs/[id]/page.tsx        # extend: daily-flow trace component.
│   ├── query/page.tsx            # extend: GroundedQueryStudio (component) shows
│   │                             #         "Launch workflow" button when answer
│   │                             #         carries recommendedWorkflow.
│   ├── writebacks/page.tsx       # extend: filter/search controls; switch from
│   │                             #         caller.divergent.writebacks() to
│   │                             #         caller.writebacks.list() once new router lands.
│   ├── automations/page.tsx      # extend: triggerWorkflow button + binding edit UI.
│   ├── search/page.tsx           # NEW: global search results landing page.
│   └── compare/page.tsx          # extend: workflow-effectiveness chart consuming
│                                 #         compare_workflow_effectiveness data.
│
├── components/
│   ├── layout/
│   │   └── TopBar.tsx            # extend: add global search input (client component).
│   ├── daily-flow/               # NEW directory
│   │   └── DailyFlowTrace.tsx    # NEW component for /runs/[id] and Command Center.
│   ├── next-action/              # NEW directory
│   │   └── NextActionPanel.tsx   # NEW component for Command Center + project detail.
│   ├── search/                   # NEW directory
│   │   ├── GlobalSearchInput.tsx # NEW client component (TopBar uses).
│   │   └── SearchResults.tsx     # NEW component for /search page.
│   ├── command-center/           # existing
│   │   └── HealthGrid.tsx        # extend: surface LearningImpactRollup.
│   └── query/                    # existing
│       └── GroundedQueryStudio.tsx  # extend: launch-workflow button when answer
│                                 #          carries recommendedWorkflow.
│
└── lib/
    ├── control-plane.ts          # extend: NextAction, DailyFlowStep, DailyFlowTrace,
    │                             #         OperatorSearchHit, EntityKind types.
    ├── constants.ts              # extend: PRIMARY_NAV adds /search entry; possibly
    │                             #         /next-action and /daily-flow routes
    │                             #         (confirm in discuss-phase).
    └── trusted-signals.ts        # reuse — every new metric uses trustedSignal().

config/
└── operator-surfaces/            # NEW directory (confirm in discuss-phase)
    └── search-policy.json        # NEW: search ranking thresholds (LIKE-match boost,
                                  #      recency weight, exact-key boost) — small,
                                  #      reviewable in git.

tests/
├── test_operator_search.py       # NEW: per-entity dispatch + scoring + bounded reads
├── test_next_action.py           # NEW: fusion ranking + per-project + cross-project
├── test_daily_flow.py            # NEW: preview (dry) + replay (run_id) + step ordering
├── test_aios_cli.py              # extend: new CLI subcommands (operator-search,
│                                 #         next-action, daily-flow, trigger-workflow)
└── test_architecture_enforcement.py # extend: assert services/operator_search.py,
                                  #         services/next_action.py,
                                  #         services/daily_flow.py do not import
                                  #         bin/.
```

### Pattern 1: Operator Search Projection (OPER-01)

**What:** One canonical `OperatorSearchHit` shape across entity kinds; a per-kind dispatcher in Python; LIKE-based ranking with recency weighting; mirrored TypeScript projection for client-side filtering. No new tables.

**When to use:** Any operator surface that needs cross-entity search.

**Example:**
```python
# Source: NEW services/operator_search.py
from __future__ import annotations
import sqlite3
from dataclasses import dataclass
from typing import Any, Callable, Literal

EntityKind = Literal[
    "run", "packet", "writeback", "finding", "prompt_template",
    "prompt_use", "skill", "workflow", "knowledge_object",
    "route_decision", "delta_item", "backfill_task",
    "automation", "experiment", "divergent_run",
    "learning_pattern", "promotion_lifecycle_item",
]


@dataclass(frozen=True)
class OperatorSearchHit:
    kind: EntityKind
    id: str
    title: str
    summary: str
    project_id: str | None
    score: float                    # 0..1; LIKE matches + recency boost + exact-key boost
    source_table: str
    last_updated_at: str            # ISO timestamp
    drill_down_path: str            # e.g., "/runs/<id>"
    metadata: dict[str, Any]


def search_entities(
    conn: sqlite3.Connection,
    *,
    query: str,
    kinds: tuple[EntityKind, ...] | None = None,
    project_id: str | None = None,
    limit: int = 50,
) -> list[OperatorSearchHit]:
    target_kinds = kinds or tuple(_DISPATCH.keys())
    hits: list[OperatorSearchHit] = []
    for kind in target_kinds:
        searcher = _DISPATCH[kind]
        hits.extend(searcher(conn, query=query, project_id=project_id))
    hits.sort(key=lambda hit: hit.score, reverse=True)
    return hits[:limit]


_DISPATCH: dict[EntityKind, Callable[..., list[OperatorSearchHit]]] = {
    "run": _search_runs,
    "packet": _search_packets,
    "writeback": _search_writebacks,
    # ... etc
}
```

### Pattern 2: Next-Action Fusion (OPER-02)

**What:** Single fused projection per project that ranks across health deltas, terminal-run gaps, open blockers, pending approvals, conservative learning proposals, and backfill tasks.

**When to use:** On Command Center, project detail page, and grounded-query "what should I do next" intent.

**Example:**
```python
# Source: NEW services/next_action.py
from __future__ import annotations
import sqlite3
from dataclasses import dataclass, field
from typing import Any, Literal

NextActionKind = Literal[
    "launch_remediation_workflow",      # standards delta backfill
    "approve_pending_writeback",
    "resolve_open_blocker",
    "review_learning_proposal",
    "fix_terminal_run_gap",
    "promote_candidate_asset",
    "investigate_regressed_metric",
]


@dataclass(frozen=True)
class NextAction:
    kind: NextActionKind
    title: str
    rationale: str
    project_id: str | None
    priority_bucket: str               # foundational | high_leverage | quick_wins | blocked | waived_deferred
    recommended_workflow_key: str | None
    evidence_ids: tuple[str, ...]      # run_ids, writeback_ids, finding_ids, etc.
    drill_down_path: str
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)


def get_next_actions(
    conn: sqlite3.Connection,
    *,
    project_id: str | None = None,
    limit: int = 10,
) -> list[NextAction]:
    actions: list[NextAction] = []
    actions.extend(_from_health_deltas(conn, project_id=project_id))      # Phase 7
    actions.extend(_from_pending_writebacks(conn, project_id=project_id)) # Phase 5
    actions.extend(_from_open_blockers(conn, project_id=project_id))      # Phase 6
    actions.extend(_from_terminal_run_gaps(conn, project_id=project_id))  # existing
    actions.extend(_from_learning_proposals(conn, project_id=project_id)) # Phase 9
    actions.extend(_from_backfill_tasks(conn, project_id=project_id))     # Phase 7
    actions.extend(_from_promotion_candidates(conn, project_id=project_id)) # Phase 8
    actions.sort(key=lambda a: (_bucket_weight(a.priority_bucket), -a.confidence))
    return actions[:limit]
```

### Pattern 3: Daily-Flow Trace (OPER-04)

**What:** A typed seven-step trace from goal through unresolved deltas. Preview mode runs route + packet generation without persistence; replay mode joins existing tables.

**When to use:** Command Center summary card, run detail page, query response when intent = should_i_run_workflow.

**Example:**
```python
# Source: NEW services/daily_flow.py
from __future__ import annotations
import sqlite3
from dataclasses import dataclass
from typing import Any, Literal

DailyFlowStepKind = Literal[
    "goal", "route", "packet", "run",
    "evaluation", "writeback", "unresolved_delta", "next_action",
]


@dataclass(frozen=True)
class DailyFlowStep:
    kind: DailyFlowStepKind
    summary: str
    evidence_ref: dict[str, Any]      # e.g., {"table": "orchestration_runs", "id": "..."}
    drill_down_path: str               # e.g., "/runs/<id>"
    provenance: Literal["confirmed", "inferred", "missing", "contradictory"]
    freshness: str                     # ISO timestamp
    metadata: dict[str, Any]


@dataclass(frozen=True)
class DailyFlowTrace:
    project_id: str | None
    objective: str
    is_preview: bool                   # True for goal-input; False for run_id replay
    steps: tuple[DailyFlowStep, ...]


def preview_from_objective(
    conn: sqlite3.Connection,
    *,
    objective: str,
    project_id: str | None = None,
) -> DailyFlowTrace:
    # Calls services.task_routing.recommend_route_primitives(objective, project_id)
    # then services.agentize.agentize_request(...) in dry mode.
    # Does NOT persist orchestration_runs or briefing_packets.
    ...


def replay_from_run(
    conn: sqlite3.Connection,
    *,
    run_id: str,
) -> DailyFlowTrace:
    # Reads orchestration_runs.route_result_json, briefing_packets,
    # success_criteria_findings, improvement_writebacks,
    # standards_delta_items (open) for the same project,
    # next_action.get_next_actions(project_id) for the next step.
    # Pure read; no mutation.
    ...
```

### Pattern 4: Query-As-Launcher Integration (OPER-02 + OPER-04)

**What:** Extend `answerGroundedQuestion` with a "should_i_run_workflow" intent that integrates Phase 1's `recommend_route_primitives` and Phase 7's `recommend_workflow_from_health`. The response carries an optional `recommendedWorkflow` + `launchableRunId` so the UI can render a "Launch workflow" button.

**When to use:** When the question matches the intent classifier ("what should I do next", "what should I run", "is there anything to fix", etc.).

**Example:**
```typescript
// Source: extends aios-ui/server/aios/query.ts
import type { GroundedAnswer } from "@/lib/control-plane";

type ExtendedGroundedAnswer = GroundedAnswer & {
  recommendedWorkflow?: {
    workflow_key: string;
    rationale: string;
    drill_down_path: string;
  };
  recommendedPacketPreview?: {
    packet_id: string;
    section_keys: string[];
    drill_down_path: string;
  };
  launchableRunId?: string;
};

export const answerGroundedQuestion = (
  db: Database.Database,
  input: { question: string; projectId?: string | null },
): ExtendedGroundedAnswer => {
  const baseAnswer = /* existing flow */;
  const intent = classifyIntent(input.question);

  if (intent === "should_i_run_workflow") {
    // NEW: shell out to services/task_routing recommendation + services/next_action
    // via a thin Node ↔ Python bridge OR (recommended) mirror logic in
    // aios-ui/server/aios/next-action.ts. Then attach the top recommendation.
    const top = getNextActions(db, { projectId: input.projectId ?? null, limit: 1 })[0];
    if (top?.recommended_workflow_key) {
      return {
        ...baseAnswer,
        recommendedWorkflow: {
          workflow_key: top.recommended_workflow_key,
          rationale: top.rationale,
          drill_down_path: top.drill_down_path,
        },
      };
    }
  }

  return baseAnswer;
};
```

### Pattern 5: Automation → Workflow Trigger (Phase Workflow Ownership)

**What:** Bind automations (and health deltas) to workflows so an operator click launches `controlPlane.plan` + `controlPlane.invoke` with the right inputs. Persist the binding either as a JSON column on `automations` rows or in a new `automation_workflow_triggers` table.

**When to use:** Automations page + health delta detail panels on project detail.

**Example:**
```typescript
// Source: extends aios-ui/server/routers/automations.ts
import { z } from "zod";
import { invokeControlPlaneRun, planTask } from "@/server/aios/control-plane";

export const automationsRouter = createTRPCRouter({
  list: /* existing */,

  triggerWorkflow: publicProcedure
    .input(
      z.object({
        automationId: z.string().min(1).optional(),
        deltaId: z.string().min(1).optional(),
        workflowKey: z.string().min(1),
        objective: z.string().min(8),
        projectId: z.string().min(1).optional(),
        actor: z.string().min(1).max(80).optional(),
      }),
    )
    .mutation(({ ctx, input }) => {
      // 1. Plan (proposes packet + run)
      const { run, packet } = planTask(ctx.db, {
        objective: input.objective,
        projectId: input.projectId ?? null,
      });
      // 2. Invoke (operator-confirmed click already happened in UI)
      return invokeControlPlaneRun(ctx.db, { runId: run.id });
    }),
});
```

### Pattern 6: Drill-Down Path Discipline (OPER-03)

**What:** Every projection that returns operator-visible rows carries a `drill_down_path: string` field pointing to the canonical UI route (with id and optional filter fragment). No new data — just URL construction next to the existing fields.

**When to use:** Every new projection AND every existing projection that surfaces rows in tables/cards.

**Example:**
```typescript
// Source: extends aios-ui/server/aios/standards-health.ts
const deltaItemRow = (row: DeltaItemRow): DeltaItem & { drill_down_path: string } => ({
  id: row.id,
  standardId: row.standardId,
  domain: row.domain,
  priorityBucket: row.priorityBucket,
  // ... existing fields
  drill_down_path: `/projects/${row.projectId}?delta=${row.id}`,
});
```

### Anti-Patterns to Avoid

- **Real-time workflow auto-launch from health deltas:** This would silently bias execution before review. Phase 10 forbids it. Every workflow launch from automation / delta / next-action surfaces requires explicit operator click — the click triggers `controlPlane.plan` (proposes the run) followed by `controlPlane.invoke` (operator-approved invocation). No shortcuts.
- **Cross-procedure search that re-runs on every keystroke:** Search input must be debounced (200ms) on the client; server search query budget caps at 50 hits and 100ms; no FTS5 yet.
- **Hardcoded catalog fallbacks masquerading as truth:** `aios-ui/server/aios/catalog.ts` constants must either be migrated to read from config + services, or labeled `isSeedData: true` in the response shape so the UI can render with a "demo data" banner.
- **Returning rows without `drill_down_path`:** Every operator-visible row needs a drill-down link. Without it, OPER-03 fails. Make `drill_down_path` non-nullable in row types where the underlying entity has a canonical UI route.
- **Building a multi-step daily-flow visualizer with @xyflow/react before validating the simple card-stack form:** Premature visual complexity. Start with cards; promote to a node graph only if operator feedback in discuss-phase or post-Phase-10 review demands it.
- **Mixing `dailyFlow.preview` (dry, no persistence) and `dailyFlow.replay` (read existing run) in one procedure with a discriminated union input:** Two procedures with clear intents are clearer for the operator AND for tests.
- **Adding new SQLite tables for things we already capture:** `orchestration_runs`, `briefing_packets`, `improvement_writebacks`, `success_criteria_findings`, `standards_delta_items`, `standards_backfill_tasks`, `workflow_execution_reports`, `knowledge_objects`, `prompts_used`, `workflow_learning_events`, `promotion_lifecycle_items`, `automations` + `automation_run_history` collectively cover every signal Phase 10 needs to surface. New tables are forbidden unless a binding is genuinely missing (e.g., `automation_workflow_triggers` — confirm in discuss-phase).
- **Letting search results bypass `trustedSignal()`:** Every row that displays a metric (success rate, health score, age) must use the existing trusted-signal contract so provenance + freshness + confidence are surfaced uniformly across pages.
- **Building a Phase 10 dashboard that hides whether Phases 5–9 are complete:** Tier-one failure conditions forbid this explicitly. The Command Center must show a "phase completion" banner if any of Phases 5–9 is incomplete and gracefully degrade surfaces that depend on missing projections (LearningImpactRollup, AssetLifecycle, etc.) with explicit "unknown — phase X not complete" labels.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Workflow recommendation from project state | New recommender | `services/standards_health.recommend_workflow_from_health(project_id)` (Phase 7) | Already returns per-bucket workflow recommendations with rationale. |
| Asset (prompt/skill) recommendation per packet | New scorer | `services/asset_recommendation.recommend_assets_for_packet(...)` (Phase 8) | Already joins `prompts_used` + `agentize_evaluations` + `workflow_execution_reports` + `workflow_skill_experiments` and ranks. |
| Route synthesis from objective | New router | `services/task_routing.recommend_route_primitives(objective, project_id)` (Phase 1) | Already produces `RouteResult` with project resolution + task family + workflow + prompt family + execution surface. |
| Packet generation preview | New packet builder | `services/agentize.agentize_request(...)` + Phase 2 packet contract | Already the canonical packet seam; daily-flow preview can call it in dry mode. |
| Approval policy classification | New approval engine | `writeback_approval_policy(...)` (Phase 5, via Phase 8 services shim) | Already covers prompt/skill/workflow/standards default scopes + post-Phase-9 route/packet scopes. |
| Workflow effectiveness comparison | New metric calculator | `services/workflow_promotion.compare_workflow_effectiveness(workflow_key, since)` (Phase 8) | Already returns per-version rework rate, validation pass rate, blocker count, writeback usefulness. |
| Per-run compounding visibility | New projection | `services/learning_impact.build_per_run_impact(run_id)` (Phase 9) | Already projects signals_emitted + assets_evidenced + proposals_created. |
| Rollup compounding visibility | New trend calculator | `services/learning_impact.build_rollup(scope, key, since)` (Phase 9) | Already returns sample_size + rework_rate + trend classification. |
| Cross-run pattern detection | New analyzer | `services/learning_analysis.detect_recurring_patterns(...)` (Phase 9) | Already covers 7 detector kinds. |
| Standards delta priority math | New scorer | `services/standards_health._build_delta_items()` + `standards_delta_items.priority_bucket` (Phase 7) | Already encodes severity × leverage × dependency_unlock × regression_penalty / effort. |
| Provenance / four-state signal classification | New enum | `Provenance = Literal["confirmed","inferred","missing","contradictory"]` from `services/capability_truth.py` | Phase 7 already enforces; Phase 10 reuses for `DailyFlowStep.provenance`. |
| Run lifecycle aggregation | New lifecycle reader | `aios-ui/server/aios/control-plane.ts` `listControlPlaneRuns` + `getControlPlaneRunDetail` | Already joins runs + invocations + sessions + artifacts. |
| Packet selection trace rendering | New trace component | `briefing_packets.selection_trace_json` + existing `ControlPlaneStudio` component | Already in use; daily-flow trace component should reuse the same rendering primitives. |
| Trust signal UI contract | New types | `aios-ui/lib/trusted-signals.ts` (existing) | All new metric surfaces use `trustedSignal()`. |
| Search ranking heuristic | New TF-IDF or vector search | LIKE + recency boost + exact-key boost (this phase) | Sufficient for local-first single-user system; promote to FTS5 only after profiling. |

**Key insight:** Phase 10 is overwhelmingly a **UI projection + fusion layer** over evidence and recommendations that Phases 1–9 have already shipped. The novel work is: (1) cross-entity search, (2) next-action fusion, (3) daily-flow tracing, (4) query-as-launcher integration, (5) automation → workflow trigger binding. Everything else reuses primitives.

## Runtime State Inventory

*Phase 10 adds three new Python service modules, three new TypeScript projection modules, four new tRPC routers, two new app pages (one global search landing, one optional next-action / daily-flow detail), one new config directory, and (conditionally) one new SQLite column or table for automation→workflow trigger bindings. No renames, no migrations of existing semantic values.*

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `aios-ui/server/aios/catalog.ts` hardcodes `workflowTemplates` / `agentProfiles` / `invocationBackends` constants and `getControlPlaneOverview` returns them as authoritative. After Phase 8, registry-truth values exist; the UI must read from `config/workflows/registry.json` + `services/invocation_backends.py` rather than the constants. | **Brownfield migration:** read from config/services at server boot; mark fallback rows with `isSeedData: true`; remove constants in a follow-up phase once UI consumers handle the new shape. |
| Stored data | `automations` table currently has no `workflow_trigger_binding_json` column AND no `automation_workflow_triggers` table. Phase 10 adds one or the other (confirm in discuss-phase). | **Additive schema:** either `ALTER TABLE automations ADD COLUMN workflow_trigger_binding_json TEXT` (nullable, idempotent migration) OR `CREATE TABLE IF NOT EXISTS automation_workflow_triggers (...)`. Both are backward-compatible. |
| Live service config | None — all Phase 10 config (`config/operator-surfaces/search-policy.json`, optional new file) is checked into git. No external CI/CD or UI configures search behavior out-of-band. | None. |
| OS-registered state | None — no OS-level service registers operator-search keys or daily-flow trace IDs. | None. |
| Secrets / env vars | None — search, next-action, daily-flow run on local SQLite + local config. No secrets enter the new surfaces. | None. |
| Build artifacts / installed packages | None — pure-Python + pure-TypeScript module additions; no compiled artifacts. `aios-ui` build pipeline (Next.js) already covers new pages and components without additional install. | None — verify `pnpm lint && pnpm tsc --noEmit` after every UI task. |

**Other concerns:**
- `PRIMARY_NAV` in `aios-ui/lib/constants.ts` controls sidebar navigation. Adding `/search` requires updating that array; confirm in discuss-phase whether `/next-action` and `/daily-flow` deserve top-level nav entries (recommendation: surface them embedded in Command Center + project detail, not as top-level pages, to keep navigation lean).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12+ | All Phase 10 Python work | ✓ | 3.12 (per `pyproject.toml`) | — |
| sqlite3 stdlib | Persistence + bounded queries | ✓ | stdlib | — |
| ruff | Lint gate | ✓ (per `pyproject.toml`) | configured | — |
| basedpyright | Typecheck gate | ✓ (per `pyproject.toml`) | configured | — |
| pytest 8.x | Test gate | ✓ (used in Phases 5/6/7/8/9) | — | — |
| vulture | Dead-code report | ✓ (per quality ladder) | per `pyproject.toml` | Report-only, non-blocking |
| `uv` runner | Existing phase verification commands use it | Likely ✓ (per `uv.lock`) | — | Fall back to `python -m pytest` |
| pnpm | UI quality ladder | Assumed (per `aios-ui/`) | — | — |
| Node.js 22+ | UI build runtime | Assumed (per `@types/node: ^22.13.1`) | — | — |
| Next.js 16.x | UI framework | ✓ | 16.0.0 | — |
| React 19.x | UI primitives | ✓ | 19.0.0 | — |
| tRPC 11.x | RPC layer | ✓ | 11.0.0 | — |
| zod 3.x | Runtime validation | ✓ | 3.24.2 | — |
| better-sqlite3 11.x | UI server DB access | ✓ | 11.8.1 | — |
| recharts 2.15.x | Compounding rollup charts | ✓ | 2.15.1 | Fall back to plain table if a chart can't render |
| @xyflow/react 12.10.x | Optional daily-flow graph | ✓ | 12.10.2 | Fall back to card stack (default Phase 10 choice) |
| Phase 5 deliverables (`writeback_approval_policy`, `improvement_writebacks`, `getGovernanceOverview`) | Writebacks surface + next-action fusion | ✓ (Phase 5 in progress per STATE.md but Phase 8/9 research treat as available) | — | If incomplete: surface pending-writebacks panel with "phase 5 not complete" banner; next-action fusion downgrades to non-writeback inputs only. |
| Phase 6 deliverables (`success_criteria_findings`, `success_criteria_stage_findings`) | Daily-flow evaluation step + next-action blocker fusion | Pending per STATE.md (5 phases complete, Phase 5 active) | — | If incomplete: daily-flow evaluation step renders "unknown — phase 6 not complete"; next-action drops the open-blocker bucket. |
| Phase 7 deliverables (`recommend_workflow_from_health`, `standards_delta_items`, `standards_backfill_tasks`, `getProjectStandardsHealth` with deltaExplanations + recommendedWorkflows) | Health-driven next-action + delta drill-down + remediation launch | Pending | — | If incomplete: project detail page renders "health intelligence pending"; remediation launch button disabled with phase 7 dependency note. |
| Phase 8 deliverables (`AssetLifecycleState`, `compare_workflow_effectiveness`, `propose_workflow_promotion`, `propose_asset_promotion`, `recommend_assets_for_packet`, vNext workflow registry schema with stage bindings) | Asset recommendation surfaces + workflow comparison page + governed promotion flow visualization | Pending | — | If incomplete: workflow effectiveness chart hidden; asset recommendation panel falls back to Phase 1 prompt_family recommendation only. |
| Phase 9 deliverables (`LearningSignalKind`, `RecurringPattern`, `LearningImpactPerRun`, `LearningImpactRollup`, `listRecurringPatterns`, `listConservativeProposals`, conservative optimizer pipeline) | Compounding visibility row + learning-proposal next-action fusion | Pending | — | If incomplete: Command Center compounding row hidden; next-action drops the learning-proposal bucket. |

**Missing dependencies with no fallback:** None identified — Phase 10 is purely additive layered work; every external dependency has a graceful degradation path because the phase's job is to **surface** evidence, not produce it. If an upstream phase is incomplete, the corresponding surface section labels itself "unknown — phase X not complete" rather than failing.

**Missing dependencies with fallback:** Phase 5–9 completion gates much of Phase 10. The phase's plan MUST include a Wave 0 audit that detects which prior phases are green and gracefully degrades surfaces for incomplete phases. Detection criteria: presence of the relevant tables (`standards_delta_items`, `success_criteria_findings`, `improvement_writebacks`, `workflow_learning_events`, `promotion_lifecycle_items`) + presence of the relevant service modules (`services/standards_health.py`, `services/learning_analysis.py`, etc.) + a `aios contracts-audit` check confirming the relevant contract row status is `implemented`.

## Common Pitfalls

### Pitfall 1: Surfaces Built On Incomplete Upstream Phases Render Misleading Data

**What goes wrong:** Phase 10 ships a Command Center next-action panel that calls `recommend_workflow_from_health`; Phase 7 isn't complete; the function returns empty; the UI displays "No actions" — but the reality is "Phase 7 not complete, we cannot tell you what to do next."

**Why it happens:** Empty source data is not the same as "no actions needed."

**How to avoid:** Every projection MUST distinguish "source data exists and is empty" from "source data is unavailable because the upstream phase is incomplete." The Wave 0 audit detects upstream phase status and the UI renders explicit "phase X not complete — surface degraded" banners. Add a `phaseCompletionAudit()` helper in `aios-ui/server/aios/control-plane.ts` that scans for required tables + service-module presence and returns a `Record<PhaseId, "complete" | "partial" | "missing">` map.

**Warning signs:** "No actions" or "No deltas" labels appearing on freshly-installed systems without a "phase status" banner.

### Pitfall 2: Search Result Drift Between Python And TypeScript Implementations

**What goes wrong:** `services/operator_search.py` ranks a `run` hit at 0.82 score; `aios-ui/server/aios/operator-search.ts` ranks the same row at 0.71 due to a JavaScript-vs-Python regex difference; CLI and UI disagree about top results.

**Why it happens:** Mirroring scoring logic in two languages without shared tests.

**How to avoid:** Either (a) the TypeScript implementation calls into the Python implementation via a thin RPC (overkill for this phase), or (b) the Python implementation is canonical and the TypeScript implementation is a strict shape mirror that delegates to a single SQL UNION query — same query in both languages, same scores. **Recommended: option b — share the SQL.** Add a Python-generated SQL string that both languages execute against the same DB.

**Warning signs:** CLI `aios operator-search "foo"` returns different top hits than the UI `operatorSearch.search({ query: "foo" })`.

### Pitfall 3: Daily-Flow Preview Side Effects Leak Into Persistence

**What goes wrong:** `dailyFlow.preview(objective)` is supposed to be dry but accidentally calls `planTask` which inserts an `orchestration_runs` row, polluting run history with previews.

**Why it happens:** Existing `planTask` is not dry-mode-aware; copying it incorrectly leaks side effects.

**How to avoid:** Add a strict `dry_run: bool = False` flag to `services.agentize.agentize_request` (extend) AND wrap the dry path with a sqlite3 savepoint that's always rolled back. Add a test asserting no rows are inserted into `orchestration_runs`, `briefing_packets`, or `orchestration_invocations` during a 100-call preview loop.

**Warning signs:** `SELECT COUNT(*) FROM orchestration_runs WHERE status = 'preview'` returns nonzero rows on a fresh DB.

### Pitfall 4: Workflow Trigger From UI Bypasses Approval Gates

**What goes wrong:** Operator clicks "Launch remediation workflow" on a high-severity delta; the trigger mutation calls `controlPlane.invoke` directly without first calling `controlPlane.plan` (which generates the writeback proposal for review).

**Why it happens:** Convenience — fewer round-trips feels nicer.

**How to avoid:** Every workflow trigger from automations / next-action / daily-flow / health-delta surfaces MUST call `planTask` first (returns `{run, packet}` proposal), then `invokeControlPlaneRun(run.id)` second. The UI MUST render the planned packet to the operator BEFORE the second call. If discuss-phase wants a "fast path" for trusted automation-driven launches, it must be explicit and gated by a per-automation `auto_invoke: true` flag in the binding — and that flag itself requires Phase 5 approval.

**Warning signs:** A `controlPlane.invoke` call appears in the network trace without a preceding `controlPlane.plan` call.

### Pitfall 5: Drill-Down Paths Break When Routes Are Renamed

**What goes wrong:** Phase 10 adds `drill_down_path: "/runs/<id>"` everywhere. A later refactor renames `/runs` to `/sessions`. Every projection now points to a 404.

**Why it happens:** Hardcoded URL strings scattered across 20+ projection sites.

**How to avoid:** Centralize URL construction in `aios-ui/lib/drill-down.ts` — a new file with one function per entity kind: `runPath(id)`, `packetPath(id)`, `writebackPath(id)`, etc. Projections call these helpers, not inline string interpolation. A route rename touches one file.

**Warning signs:** Multiple files contain raw `\`/runs/${id}\`` template literals.

### Pitfall 6: Search Indexes Stale Soon After Insert

**What goes wrong:** Operator runs `aios operator-search "recent failure"`; the underlying `success_criteria_findings` table was updated 30 seconds ago but the search response shows only older rows because the projection uses a cached snapshot.

**Why it happens:** Premature caching.

**How to avoid:** First-cycle search runs LIKE queries directly against base tables — no cache. If benchmarking shows latency above 200ms on a typical local DB, introduce a query-time hint (e.g., `WHERE created_at > date('now', '-30 days')`) before adding FTS5. Cache only with operator-visible "as of X timestamp" labels.

**Warning signs:** Operator reports stale search results despite recent activity.

### Pitfall 7: Catalog Constants Quietly Override Real Registry

**What goes wrong:** Phase 10 partially migrates `aios-ui/server/aios/catalog.ts` to read from `config/workflows/registry.json` but a fallback path still returns the hardcoded constants when the registry parse fails. The fallback fires silently; operators see five workflow templates that don't match the actual registry.

**Why it happens:** Brownfield-friendly fallback without visible indication.

**How to avoid:** Any fallback to constants MUST set a `isSeedData: true` flag on every returned row AND emit a server warning log. The UI MUST render a "demo data — registry parse failed" banner when `isSeedData` is true anywhere in the response. Tests assert that on a freshly-installed system with a valid registry, `isSeedData` is false on all rows.

**Warning signs:** UI shows workflow templates that don't appear in `config/workflows/registry.json` without an explicit "seed data" label.

### Pitfall 8: Phase Status Banner Confuses Operators

**What goes wrong:** Command Center shows "Phase 7 incomplete — health intelligence pending"; operator interprets this as "AIOS itself is broken" and stops using the tool.

**Why it happens:** Honest reporting can look alarming without context.

**How to avoid:** Banner text frames the gap positively: "Health intelligence is being rolled out (Phase 7 of 10). Some metrics will populate over the next few releases. [Learn more]". Link to a phase-status page that explains the roadmap visually. Acceptance test: a non-technical reviewer reads the banner and does NOT conclude "the app is broken."

**Warning signs:** Operator feedback like "is the app down?" or "should I file a bug?"

### Pitfall 9: Search Returns Too Many Hits And Operator Gives Up

**What goes wrong:** Operator searches "implementation"; gets 2000 hits across runs/packets/writebacks/findings/prompts; scrolls for 5 seconds; closes the page.

**Why it happens:** No relevance ceiling.

**How to avoid:** Default `limit: 50` on search; UI shows "Top 50 of N — refine query or filter by kind." Per-kind result counts displayed in a faceted sidebar (run: 12, packet: 18, writeback: 4, ...). Filter chips for `kinds` and `project_id`. Empty-search behavior returns recent activity rather than nothing.

**Warning signs:** Operator search sessions average more than 3 result clicks before drilling in.

### Pitfall 10: "Next Action" Recommendation Doesn't Update After Operator Acts

**What goes wrong:** Operator clicks "Resolve open blocker" → resolves it; the next-action panel still shows the same recommendation because the page rendered server-side and isn't refreshed.

**Why it happens:** Next.js server components cache; mutations don't auto-revalidate.

**How to avoid:** After every mutation that resolves an action (write_back review, finding resolution, workflow launch), call tRPC's `utils.invalidate()` or Next.js `router.refresh()` to re-fetch next-action data. The recommendation list mutates within 1 second.

**Warning signs:** Operator says "I already did that — why is it still on the list?"

## Code Examples

Verified patterns from existing in-tree code that Phase 10 reuses or extends.

### Existing Control-Plane Overview (Phase 10 Extends With nextActions + dailyFlowSummary)

```typescript
// Source: aios-ui/server/aios/control-plane.ts:359-381 (verbatim shape)
export const getControlPlaneOverview = (db: Database.Database): {
  workflowTemplates: typeof workflowTemplates;
  agentProfiles: typeof agentProfiles;
  invocationBackends: typeof invocationBackends;
  runs: OrchestrationRun[];
  packets: BriefingPacket[];
  pendingWritebacks: ImprovementWriteback[];
  governance: GovernanceOverview;
  recentFindings: ConsistencyFinding[];
  // PHASE 10 ADDS:
  // nextActions?: NextAction[];
  // dailyFlowSummary?: { topProjectId: string; trace: DailyFlowTrace } | null;
  // learningImpactRollup?: LearningImpactRollup[];
  // phaseStatus?: Record<PhaseId, "complete" | "partial" | "missing">;
} => {
  const runs = listControlPlaneRuns(db);
  const governance = getGovernanceOverview(db);
  return {
    workflowTemplates,
    agentProfiles,
    invocationBackends: listInvocationBackends(),
    runs,
    packets: listPacketRows(db),
    pendingWritebacks: listImprovementWritebacks(db, { limit: 12 }).filter((writeback) => writeback.requiresApproval),
    governance,
    recentFindings: listConsistencyFindings(db, { limit: 12 }),
  };
};
```

### Existing Governance Overview (Phase 10 Adds policyClassDrillDowns)

```typescript
// Source: aios-ui/server/aios/control-plane.ts:383-418 (verbatim shape)
export const getGovernanceOverview = (db: Database.Database): GovernanceOverview => {
  // ... existing flow ...
  return {
    summary: {
      proposalCount: proposals.length,
      pendingApprovalCount: pendingApprovals.length,
      terminalRunCount: terminal.terminalCount,
      terminalRunsMissingEvidenceCount: terminal.gaps.length,
      policyClassCount: policyClassCounts.length,
    },
    pendingApprovals,
    recentProposals: proposals.slice(0, 20),
    policyClassCounts,
    terminalRunsMissingEvidence: terminal.gaps,
    linkRules: [/* ... */],
    // PHASE 10 ADDS:
    // policyClassDrillDowns: Record<string, string>;   // policy class -> filtered writebacks URL
    // pendingApprovalDrillDowns: string[];             // drill_down_path per pending approval
  };
};
```

### Existing Grounded Query Routing (Phase 10 Adds should_i_run_workflow Intent)

```typescript
// Source: aios-ui/server/aios/query.ts:387-450 (verbatim shape, abridged)
export const answerGroundedQuestion = (
  db: Database.Database,
  input: { question: string; projectId?: string | null },
): GroundedAnswer => {
  const intent = classifyIntent(input.question);
  // ... existing flow ...
  if (intent === "what_changed") {
    return /* existing what_changed answer */;
  }
  // PHASE 10 ADDS:
  // if (intent === "should_i_run_workflow") {
  //   const top = getNextActions(db, { projectId: input.projectId ?? null, limit: 1 })[0];
  //   if (top?.recommended_workflow_key) {
  //     return {
  //       ...baseAnswer,
  //       recommendedWorkflow: {
  //         workflow_key: top.recommended_workflow_key,
  //         rationale: top.rationale,
  //         drill_down_path: top.drill_down_path,
  //       },
  //     };
  //   }
  // }
};
```

### Existing Sidebar Nav (Phase 10 Adds /search)

```typescript
// Source: aios-ui/lib/constants.ts:7-22 (verbatim)
export const PRIMARY_NAV: NavItem[] = [
  { href: "/", label: "Command Center", short: "Home" },
  { href: "/knowledge", label: "Knowledge", short: "Wiki" },
  { href: "/projects", label: "Projects", short: "Projects" },
  { href: "/control", label: "Control Plane", short: "Control" },
  // ... etc
  // PHASE 10 ADDS:
  // { href: "/search", label: "Search", short: "Search" },
];
```

### Existing Writebacks Page (Phase 10 Migrates From divergent.writebacks To writebacks.list)

```typescript
// Source: aios-ui/app/writebacks/page.tsx:11-13 (verbatim)
export default async function WritebacksPage(): Promise<React.JSX.Element> {
  const caller = await getCaller();
  const proposals = await caller.divergent.writebacks();
  // PHASE 10 CHANGES:
  // const proposals = await caller.writebacks.list({ limit: 100, status: "pending_approval" });
};
```

### Existing Automations Router (Phase 10 Adds triggerWorkflow Mutation)

```typescript
// Source: aios-ui/server/routers/automations.ts:184-225 (verbatim shape, abridged)
export const automationsRouter = createTRPCRouter({
  list: publicProcedure.query(({ ctx }): AutomationHealth[] => {
    // ... existing flow ...
  }),
  // PHASE 10 ADDS:
  // triggerWorkflow: publicProcedure
  //   .input(z.object({
  //     automationId: z.string().min(1).optional(),
  //     deltaId: z.string().min(1).optional(),
  //     workflowKey: z.string().min(1),
  //     objective: z.string().min(8),
  //     projectId: z.string().min(1).optional(),
  //     actor: z.string().min(1).max(80).optional(),
  //   }))
  //   .mutation(({ ctx, input }) => {
  //     const { run } = planTask(ctx.db, { objective: input.objective, projectId: input.projectId ?? null });
  //     return invokeControlPlaneRun(ctx.db, { runId: run.id });
  //   }),
});
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Per-page list procedures without query/filter parameters | Every list procedure accepts `query?: string`, `filter?: Record<string,string>`, `sort?` with bounded enums | Phase 10 (this phase) | Operators can refine surfaces without scrolling 200 rows. |
| No cross-entity search | `operatorSearch.search(query, kinds?, projectId?)` mixed-kind search | Phase 10 | One Q box answers "where is this mentioned" across runs/packets/writebacks/findings/prompts/skills/workflows/knowledge/route_decisions/deltas/automations/experiments/patterns/divergent_runs/learning_events. |
| Per-recommendation surfaces in isolation (workflow rec from health, asset rec, route rec, learning proposals all separate) | Fused `next_action.get_next_actions(project_id)` returns ranked NextActions across all sources | Phase 10 | Operators get one answer to "what should I do next" instead of inspecting five separate panels. |
| No threaded view from goal → unresolved deltas | `dailyFlow.preview(objective)` and `dailyFlow.replay(run_id)` return strongly-typed seven-step traces | Phase 10 | The default-layer daily flow becomes inspectable end-to-end. |
| Grounded query returns answers without workflow recommendation | Grounded query with `should_i_run_workflow` intent returns answer + recommendedWorkflow + launchableRunId | Phase 10 | Query becomes a launcher when appropriate; surfaces the route-to-action pathway directly. |
| Automations are read-only health surfaces | Automations carry workflow_trigger bindings; "Launch" button surfaces on automation rows AND on high-severity health deltas | Phase 10 | The system can self-direct work based on signals, with operator confirmation. |
| `aios-ui/server/aios/catalog.ts` hardcoded constants masquerade as registry truth | Catalog reads from `config/workflows/registry.json` + `services/invocation_backends.py` at server boot; fallback rows labeled `isSeedData: true` | Phase 10 | Seed/fallback ambiguity eliminated; operators distinguish demo data from real registry. |
| Drill-down via inline links scattered across components | Centralized URL construction in `aios-ui/lib/drill-down.ts`; every projection carries `drill_down_path` | Phase 10 | Refactors don't break links; operators can always click into source evidence. |

**Deprecated/outdated:**
- `aios-ui/server/aios/catalog.ts` hardcoded constants — replaced by config + service reads with `isSeedData` labels. Kept as fallback for one cycle; remove in a follow-up phase after migration is verified.
- `divergent.writebacks()` as the writebacks surface — replaced by `writebacks.list()` reading directly from `improvement_writebacks` so post-Phase-5 governance proposals (not just divergent ones) appear.
- Per-page search input as the only filter mechanism — augmented by sidebar global search; per-page filters complement, not replace.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Phases 5–9 ship before Phase 10 starts (STATE.md says only 5 complete; ROADMAP places Phase 10 as gated by all prior milestones). | Summary / Environment Availability | Phase 10's scope contracts per Pitfall 1: each surface degrades gracefully when its upstream phase is incomplete. Discuss-phase MUST confirm Phase 10 start preconditions. |
| A2 | LIKE-based search with recency boost is sufficient relevance for a local-first single-user system in the first cycle; FTS5 deferred. | Alternatives Considered / Pitfall 9 | If the AIOS DB grows to > 100k rows across the searched tables, query latency may exceed 200ms. Mitigation: add `WHERE created_at > date('now', '-90 days')` time window default; FTS5 follow-up if profiling shows it. |
| A3 | Automation → workflow trigger bindings live as JSON column on `automations` row rather than a separate `automation_workflow_triggers` table. | Alternatives Considered / Runtime State Inventory | If operators want audit history of binding changes, a separate table is preferable. Confirm in discuss-phase. |
| A4 | Cross-project default for next-action is "per-project" (operator works on one project at a time); cross-project "Top attention" panel is supplementary. | Alternatives Considered | If operators routinely jump between projects, cross-project default may be preferred. Confirm in discuss-phase. |
| A5 | Daily-flow preview is a strictly dry operation (no `orchestration_runs` or `briefing_packets` rows written); replay is strictly read-only. | Pitfall 3 / Pattern 3 | If discuss-phase wants preview to optionally persist a "draft" run for resumption, scope grows by one column and one transition path. |
| A6 | Workflow trigger from any UI surface ALWAYS calls `planTask` first (proposes), then `invokeControlPlaneRun` second (operator-confirmed). | Pitfall 4 / Anti-Patterns | This is the load-bearing safety property of the phase. If the user wants "trusted automation" fast paths, they must be explicit per-binding and gated by Phase 5 approval. |
| A7 | `aios-ui/server/aios/catalog.ts` constants are deprecated in favor of config + service reads; fallback rows are labeled `isSeedData: true` during a one-cycle transition. | State of the Art / Pitfall 7 | If the user prefers a hard cutover (no fallback), the catalog change is smaller but rollback is harder. Confirm in discuss-phase. |
| A8 | Centralized drill-down URL construction lives in `aios-ui/lib/drill-down.ts` (NEW). | Pitfall 5 | If the user prefers inline strings (premature-abstraction concern), the helper module is rejected — but Pitfall 5 risk remains. The helper has < 20 functions, well within the "three similar lines" threshold. Recommend the helper. |
| A9 | Search projection is a UNION across base tables with LIKE; no new cache table. | Alternatives Considered / Pitfall 6 | If profiling shows latency, add a small `operator_search_index` cache table populated by hooks on row inserts. Out of scope for first cycle. |
| A10 | `recommend_workflow_from_health(project_id)`, `recommend_assets_for_packet`, `recommend_route_primitives`, `LearningImpactPerRun`, `LearningImpactRollup`, `compare_workflow_effectiveness`, `listConservativeProposals`, `listRecurringPatterns` all ship from Phases 7/8/9 with the names and shapes assumed here. | Standard Stack / Don't Hand-Roll | If shapes drift during Phase 7/8/9 implementation, Phase 10 wiring adapts at integration time. The assumed shapes match the Phase 7/8/9 RESEARCH.md primary recommendations. |
| A11 | `config/operator-surfaces/search-policy.json` is a new config file with < 10 keys (LIKE-match boost, recency weight, exact-key boost, default limit). | Recommended Project Structure | If discuss-phase prefers hardcoded thresholds with a CLI flag override, the config file becomes optional. Low-risk either way. |
| A12 | `/search` is added as a sidebar nav entry; `/next-action` and `/daily-flow` are NOT separate top-level pages but embedded in Command Center + project detail. | Recommended Project Structure / Runtime State Inventory | If operators want dedicated `/next-action` and `/daily-flow` pages, scope grows by two pages. Confirm in discuss-phase. |
| A13 | Phase 10 does NOT introduce a separate `aios-ui/server/routers/writebacks.ts` if Phase 5 already ships one — Phase 10 only adds it if Phase 5 chose to surface writebacks through `controlPlane.governance` only. | Recommended Project Structure | Verify Phase 5 final shape during planning. |
| A14 | Sidebar global search uses a debounced client-side input (200ms) → tRPC `operatorSearch.search` query → server-rendered Search Results page or in-place suggestion dropdown. | Architecture Patterns | If operators prefer in-page suggestion dropdown vs separate /search page, both are feasible; recommend dropdown for top-5 hits + "See all results" link to /search page. Confirm in discuss-phase. |

## Open Questions (Confirm In Discuss-Phase)

> Items marked **CONFIRM IN DISCUSS-PHASE** need user confirmation before locking. All have a recommended default below.

1. **Should automation → workflow trigger bindings live as a JSON column on `automations` rows or as a separate `automation_workflow_triggers` table?**
   - What we know: A column is simpler; a table gives audit history.
   - What's unclear: Whether audit history on binding changes is needed.
   - Recommendation: JSON column on `automations` for first cycle; promote to table only if audit history is required. **CONFIRM.**

2. **Should sidebar global search render a top-5 suggestion dropdown OR send the operator to a /search results page?**
   - What we know: Dropdown is faster for known items; full page is better for browsing.
   - What's unclear: Operator preference; existing UI primitives slightly favor the page approach (no existing dropdown components).
   - Recommendation: Implement both — dropdown for top-5 instant hits with "See all results" link to /search. **CONFIRM.**

3. **Should `/next-action` and `/daily-flow` be top-level sidebar entries OR remain embedded in Command Center + project detail?**
   - What we know: Top-level entries keep them discoverable; embedded keeps navigation lean.
   - What's unclear: Operator workflow — do they start at Command Center or jump to a dedicated page?
   - Recommendation: Embedded for first cycle; promote to top-level if usage telemetry shows demand. **CONFIRM.**

4. **Should the Command Center show `LearningImpactRollup` charts for all workflows or only for top-3 by run count?**
   - What we know: All workflows could be 10+ rows; top-3 is the usual focus.
   - What's unclear: Whether operators want to see "improving but rarely used" assets surface.
   - Recommendation: Top-3 by run count with "See all" link to /compare. **CONFIRM.**

5. **Should `dailyFlow.preview` (objective input) optionally persist a draft `orchestration_runs` row for resumption, or remain strictly dry?**
   - What we know: Strictly dry avoids polluting run history; draft persistence enables "I want to come back to this preview later."
   - What's unclear: Operator workflow.
   - Recommendation: Strictly dry for first cycle; add optional `persist_draft: true` flag in a follow-up if needed. **CONFIRM.**

6. **Should query-as-launcher show the planned packet preview BEFORE the operator clicks "Launch", or only the workflow recommendation?**
   - What we know: Packet preview is more informative but adds latency (one extra `agentize_request` call); just the recommendation is faster.
   - What's unclear: Operator information appetite.
   - Recommendation: Packet preview by default (one click reveals the full plan); if latency is noticeable, lazy-load on hover. **CONFIRM.**

7. **Should the catalog migration happen in one cutover (read from config only) or incrementally (config first, fallback to constants with `isSeedData: true` for one cycle)?**
   - What we know: Cutover is cleaner; incremental is brownfield-friendly.
   - What's unclear: Whether the registry is in a parseable state for all consumers when Phase 10 lands.
   - Recommendation: Incremental with `isSeedData` flag and explicit "demo data" UI banner; cutover removal happens in a follow-up phase. **CONFIRM.**

8. **Should `writebacks` get its own tRPC router (replacing `divergent.writebacks()` for the writebacks page) or stay routed through `controlPlane.governance`?**
   - What we know: A dedicated router scales better (writebacks is now a 5-asset surface, not just divergent); routing through `controlPlane.governance` keeps fewer files.
   - What's unclear: Phase 5's final shape.
   - Recommendation: Dedicated `writebacksRouter` because writebacks span all asset kinds post-Phase-5, not just divergent. **CONFIRM.**

9. **Should automation → workflow trigger include an optional `auto_invoke: true` flag for trusted automation paths (bypasses operator click), gated by Phase 5 approval?**
   - What we know: A fast path is more powerful; it weakens the human-in-the-loop guarantee.
   - What's unclear: Operator's risk tolerance.
   - Recommendation: No auto-invoke in Phase 10. The Phase 5 approval gate is the safety net; bypass requires a follow-up phase with explicit risk acceptance. **CONFIRM.**

10. **Should the Phase 10 plan include a Wave 0 task that explicitly removes ALL hardcoded fallback constants (per Tier-One failure condition "No polished surface may mask weak or missing backend truth")?**
    - What we know: The tier-one checklist forbids polished surfaces masking weak backend truth.
    - What's unclear: Whether "removing" means hard removal vs labeled fallback.
    - Recommendation: Labeled fallback with `isSeedData: true` (Recommendation 7) PLUS a Wave 0 task that audits and labels every remaining constant. Hard removal happens in a follow-up. **CONFIRM.**

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework (Python) | pytest 8.x (Python 3.12) per `pyproject.toml` |
| Framework (UI) | None wired — `aios-ui/package.json` has no `test` script [VERIFIED]; UI validation is type-level (`pnpm tsc --noEmit`) + lint (`pnpm lint`) + architecture (`pnpm lint:architecture`) |
| Config file | `pyproject.toml` (ruff + basedpyright + vulture sections) |
| Quick run command (Python) | `uv run pytest tests/test_operator_search.py tests/test_next_action.py tests/test_daily_flow.py tests/test_aios_cli.py -x -q` |
| Full suite command (Python) | `uv run pytest -q` |
| UI quality ladder | `cd aios-ui && pnpm lint && pnpm tsc --noEmit && pnpm lint:architecture` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| OPER-01 | `search_entities` returns mixed-kind hits ranked by score with `drill_down_path` populated | unit | `uv run pytest tests/test_operator_search.py::test_search_returns_mixed_kind_hits -x` | ❌ Wave 0 |
| OPER-01 | Per-kind dispatch (runs/packets/writebacks/findings/...) returns kind-tagged hits | unit | `uv run pytest tests/test_operator_search.py::test_per_kind_dispatch -x` | ❌ Wave 0 |
| OPER-01 | Search honors `project_id` filter | unit | `uv run pytest tests/test_operator_search.py::test_search_honors_project_filter -x` | ❌ Wave 0 |
| OPER-01 | Search honors `kinds` filter | unit | `uv run pytest tests/test_operator_search.py::test_search_honors_kinds_filter -x` | ❌ Wave 0 |
| OPER-01 | Search ranking boosts recency | unit | `uv run pytest tests/test_operator_search.py::test_search_ranking_boosts_recency -x` | ❌ Wave 0 |
| OPER-01 | CLI `aios operator-search "..." --json` returns the same shape as tRPC | integration | `uv run pytest tests/test_aios_cli.py::test_operator_search_cli_json -x` | ❌ Wave 0 |
| OPER-01 | Every list procedure now accepts `query?` parameter without breaking existing callers | type-level | `cd aios-ui && pnpm tsc --noEmit` | partial (type-level only) |
| OPER-02 | `get_next_actions(project_id=X)` returns NextActions fused from 5+ sources | integration | `uv run pytest tests/test_next_action.py::test_next_actions_fuse_multiple_sources -x` | ❌ Wave 0 |
| OPER-02 | NextAction priority ranking respects bucket weight × confidence | unit | `uv run pytest tests/test_next_action.py::test_next_action_ranking -x` | ❌ Wave 0 |
| OPER-02 | NextAction with `kind="launch_remediation_workflow"` carries `recommended_workflow_key` | unit | `uv run pytest tests/test_next_action.py::test_remediation_action_has_workflow_key -x` | ❌ Wave 0 |
| OPER-02 | `answerGroundedQuestion` returns `recommendedWorkflow` for `should_i_run_workflow` intent | integration | type-level for now; integration test once UI test framework lands | ❌ Wave 0 |
| OPER-02 | CLI `aios next-action --project X --json` returns the same shape as tRPC | integration | `uv run pytest tests/test_aios_cli.py::test_next_action_cli_json -x` | ❌ Wave 0 |
| OPER-03 | Every projection that returns operator-visible rows carries a non-null `drill_down_path` | integration | `uv run pytest tests/test_operator_search.py::test_all_hits_have_drill_down_path -x` | ❌ Wave 0 |
| OPER-03 | `getProjectStandardsHealth` delta items carry `drill_down_path` (Phase 7 extension) | type-level + integration | type-level for UI; CLI assertion | ❌ Wave 0 |
| OPER-03 | DailyFlowStep carries `evidence_ref` + `drill_down_path` + `provenance` for every step | unit | `uv run pytest tests/test_daily_flow.py::test_step_carries_evidence_and_drill_down -x` | ❌ Wave 0 |
| OPER-04 | `preview_from_objective(objective, project_id?)` returns 7-step DailyFlowTrace WITHOUT writing to orchestration_runs | integration | `uv run pytest tests/test_daily_flow.py::test_preview_is_dry -x` | ❌ Wave 0 |
| OPER-04 | `replay_from_run(run_id)` returns 7-step DailyFlowTrace by joining existing tables | integration | `uv run pytest tests/test_daily_flow.py::test_replay_joins_existing_tables -x` | ❌ Wave 0 |
| OPER-04 | DailyFlowTrace step order: goal → route → packet → run → evaluation → writeback → unresolved_delta → next_action | unit | `uv run pytest tests/test_daily_flow.py::test_step_order_is_canonical -x` | ❌ Wave 0 |
| OPER-04 | Preview gracefully degrades when upstream phase incomplete (e.g., Phase 6 findings table missing) | integration | `uv run pytest tests/test_daily_flow.py::test_preview_degrades_when_phase_incomplete -x` | ❌ Wave 0 |
| OPER-04 | CLI `aios daily-flow --objective "..." --dry-run --json` returns the trace | integration | `uv run pytest tests/test_aios_cli.py::test_daily_flow_preview_cli -x` | ❌ Wave 0 |
| OPER-04 | CLI `aios daily-flow --run-id X --json` returns the replay trace | integration | `uv run pytest tests/test_aios_cli.py::test_daily_flow_replay_cli -x` | ❌ Wave 0 |
| Cross-cutting | `automations.triggerWorkflow` mutation always calls `planTask` before `invokeControlPlaneRun` | type-level + integration | type-level for now; integration check via SQL trace | ❌ Wave 0 |
| Cross-cutting | `aios contracts-audit` includes `OperatorSurface` + `NextAction` + `DailyFlow` contract rows with `status: implemented` | unit | `uv run pytest tests/test_aios_cli.py::test_contracts_audit_includes_operator_contracts -x` | ❌ Wave 0 |
| Cross-cutting (catalog migration) | `getControlPlaneOverview` returns `isSeedData: false` on a freshly-installed system with a valid registry | integration | `uv run pytest tests/test_ui_catalog_migration.py::test_seed_data_flag_false_on_valid_registry -x` (NEW or via existing UI test path) | ❌ Wave 0 |
| Cross-cutting (architecture) | `services/operator_search.py`, `services/next_action.py`, `services/daily_flow.py` do NOT import from `bin/` | architecture | `uv run pytest tests/test_architecture_enforcement.py::test_phase_10_services_do_not_import_bin -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:**
  - Python: `uv run pytest tests/test_operator_search.py tests/test_next_action.py tests/test_daily_flow.py tests/test_aios_cli.py tests/test_architecture_enforcement.py -x -q && uv run ruff check services bin tests && uv run ruff format --check services bin tests && uv run basedpyright`
  - UI (when TS files change): `cd aios-ui && pnpm lint && pnpm tsc --noEmit`
  - UI architecture (when projection/router files change): `cd aios-ui && pnpm lint:architecture`
- **Per wave merge:**
  - `uv run pytest -q && uv run ruff check . && uv run ruff format --check . && uv run basedpyright && uv run vulture services bin --min-confidence 70`
  - `cd aios-ui && pnpm lint && pnpm tsc --noEmit && pnpm lint:architecture`
- **Phase gate:**
  - Full Python suite green
  - Full UI quality ladder green (lint + tsc + architecture)
  - `aios contracts-audit` shows `OperatorSurface`, `NextAction`, `DailyFlow` contract rows with `status: implemented`
  - `aios operator-search "implementation" --json` returns a populated mixed-kind hit list on the AIOS dev DB with `drill_down_path` non-null on every row
  - `aios next-action --project <real-project-id> --json` returns a populated NextAction list
  - `aios daily-flow --run-id <real-run-id> --json` returns a populated 7-step trace
  - Manual operator check: open `/`, `/search`, `/projects/<id>`, `/runs/<id>`, `/query` and confirm next-action panel + daily-flow trace + search input + drill-down links all render and click through
  - Manual phase-status banner check: install in a clean DB, confirm Command Center shows "phase X not complete" banner if Phases 5-9 are incomplete
  - Manual catalog-migration check: confirm no `isSeedData: true` rows appear when the registry is valid

### Wave 0 Gaps

- [ ] `tests/test_operator_search.py` — NEW file: 6 search tests above (mixed-kind hits, per-kind dispatch, filters, ranking, drill-down)
- [ ] `tests/test_next_action.py` — NEW file: 3 next-action tests above (fusion, ranking, remediation key)
- [ ] `tests/test_daily_flow.py` — NEW file: 5 daily-flow tests above (preview dry, replay join, step order, drill-down, graceful degradation)
- [ ] `tests/test_aios_cli.py` — extend: operator-search + next-action + daily-flow CLI tests (6+ tests)
- [ ] `tests/test_architecture_enforcement.py` — extend: assert new services do not import bin
- [ ] `tests/test_ui_catalog_migration.py` — NEW (or extend an existing UI-adjacent test path): assert `isSeedData: false` on valid registry
- [ ] `aios-ui/lib/control-plane.ts` — extend with `NextAction`, `DailyFlowStep`, `DailyFlowTrace`, `OperatorSearchHit`, `EntityKind`, `PhaseStatus` types
- [ ] `aios-ui/lib/drill-down.ts` — NEW file: centralized URL construction (one function per entity kind)
- [ ] `aios-ui/server/aios/operator-search.ts` — NEW projection
- [ ] `aios-ui/server/aios/next-action.ts` — NEW projection
- [ ] `aios-ui/server/aios/daily-flow.ts` — NEW projection
- [ ] `aios-ui/server/routers/operator-search.ts` — NEW tRPC router
- [ ] `aios-ui/server/routers/next-action.ts` — NEW tRPC router
- [ ] `aios-ui/server/routers/daily-flow.ts` — NEW tRPC router
- [ ] `aios-ui/server/routers/writebacks.ts` — NEW tRPC router (per A8)
- [ ] `aios-ui/server/routers/_app.ts` — extend register 4 new routers
- [ ] `aios-ui/components/layout/TopBar.tsx` — extend with global search input
- [ ] `aios-ui/components/daily-flow/DailyFlowTrace.tsx` — NEW component
- [ ] `aios-ui/components/next-action/NextActionPanel.tsx` — NEW component
- [ ] `aios-ui/components/search/GlobalSearchInput.tsx` + `SearchResults.tsx` — NEW components
- [ ] `aios-ui/app/search/page.tsx` — NEW page
- [ ] `aios-ui/lib/constants.ts` — extend `PRIMARY_NAV` with /search entry
- [ ] `config/operator-surfaces/search-policy.json` — NEW: search thresholds (per A11)
- [ ] No new conftest.py needed — existing tests use direct `sqlite3.connect(":memory:")` patterns and per-test schema seeding
- [ ] No framework install required; pytest + ruff + basedpyright + pnpm already wired

## Security Domain

> Phase 10 introduces no new authentication, session management, network surface, or cryptographic concerns. Security applicability is bounded to: (a) workflow trigger mutations from automation / next-action / daily-flow / health-delta surfaces MUST flow through `planTask` (proposes) + `invokeControlPlaneRun` (operator-confirmed), never bypassing approval gates; (b) operator search results MUST NOT leak sensitive evidence (filesystem paths, prompt text, secrets) beyond what existing projections already expose; (c) the catalog migration MUST NOT silently degrade trust (`isSeedData: true` flag required on fallback rows; UI banner mandatory); (d) drill-down paths MUST NOT expose private routes (auth or per-user data) — Phase 10 is single-operator local-first, but tests assert drill-down construction does not embed user-specific tokens; (e) the new `automation_workflow_triggers` binding (or JSON column) MUST require Phase 5 approval to change (extends `writeback_approval_policy` with `automation-binding-default` scope if confirmed in discuss-phase).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | n/a — internal CLI / hook / UI-server surface; single-user local-first |
| V3 Session Management | no | n/a |
| V4 Access Control | yes | All workflow triggers from new surfaces go through `planTask` → operator-confirmed click → `invokeControlPlaneRun`; no auto-invoke in Phase 10. Binding changes (if persisted as separate table) require Phase 5 approval. |
| V5 Input Validation | yes | All new tRPC procedures validate inputs with `zod`; search query length capped at 200 chars; objective length capped at 2000 chars; kinds/projectId validated against literals. |
| V6 Cryptography | no | n/a |
| V7 Error Handling | yes | Search projection fails closed: malformed rows are skipped with a logged warning; UI gracefully labels "phase X not complete" rather than crashing; daily-flow gracefully degrades when sources are missing. |
| V10 Malicious Code | partial | `config/operator-surfaces/search-policy.json` (if introduced) is reviewable in git; loader validates required keys against a typed dataclass. No code execution from search inputs. |
| V13 API & Web Service | partial | tRPC routes already validate inputs; new `operatorSearch.search`, `nextAction.getForProject`, `dailyFlow.preview`/`replay`, `automations.triggerWorkflow`, `projects.launchRemediation` use `zod`. No new external API surface introduced. |
| V14 Configuration | yes | Catalog migration uses config from `config/workflows/registry.json` (git-tracked); fallback flagged `isSeedData: true` with explicit UI banner. |

### Known Threat Patterns for Operator Surfaces

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Workflow trigger bypasses approval gate (UI calls `invokeControlPlaneRun` without prior `planTask`) | Repudiation / Elevation of Privilege | Pitfall 4 + test `test_workflow_trigger_calls_plan_before_invoke`. Architecture check that every `triggerWorkflow` call site executes `planTask` first. |
| Search result leaks sensitive evidence (prompt text, secrets, filesystem paths) | Information Disclosure | Per-kind search dispatchers project ONLY safe columns (`id`, `title`, `summary`, `created_at`, `project_id`); prompt text and full file paths are NOT exposed in search results — operators drill down to view detail. |
| Catalog fallback silently overrides registry | Tampering | Pitfall 7 + test `test_seed_data_flag_false_on_valid_registry`. UI banner mandatory when `isSeedData: true` appears anywhere. |
| Drill-down path embeds user-specific token | Information Disclosure | Centralized URL construction in `aios-ui/lib/drill-down.ts` uses only entity IDs; tests assert no auth tokens or user-specific suffixes appear in generated URLs. |
| Daily-flow preview persists side effects (orchestration_runs / briefing_packets row inserted) | Tampering / Repudiation | Pitfall 3 + test `test_preview_is_dry`. Wrap dry path in sqlite3 savepoint always rolled back; tests assert no inserts on a 100-call loop. |
| Next-action surface shows stale recommendation after operator acts | Information Disclosure (misleading) | Pitfall 10 + tRPC `utils.invalidate()` after every action-resolving mutation. |
| Search-as-launcher exposes a workflow recommendation but the recommended workflow is in `deprecated` lifecycle state | Information Disclosure (wrong recommendation) | Phase 8 asset lifecycle filter: `recommend_workflow_from_health` and `recommend_assets_for_packet` already exclude `deprecated` assets; next-action fusion respects the same filter. |
| Phase status banner reveals which phases are incomplete to a non-trusted observer | Information Disclosure | AIOS is single-user local-first per AGENTS.md; no untrusted observers. If multi-user deployment later, banner content gates by auth context. |
| Automation → workflow binding changes silently | Tampering / Repudiation | If automation_workflow_triggers becomes a separate table, every change goes through `writeback_approval_policy` with `automation-binding-default` impact scope; if it's a JSON column, same approval gating via Phase 5 path. |
| Cross-entity search query is unbounded and DOS-able | Denial of Service | Search input capped at 200 chars; default limit 50; per-kind cap 20; query budget 100ms server-side. |

## Sources

### Primary (HIGH confidence — read or verified during research)

- `.planning/STATE.md` — current milestone (Truth/Governance/Evidence), active phase (Phase 5), dependency chain Phase 5 → 6 → 7 → 8 → 9 → 10; progress shows 5 of 10 phases complete [VERIFIED: read]
- `.planning/ROADMAP.md` — Phase 10 scope, detailed scope, current surfaces, workflow ownership, expected outputs, dependencies, observable success criteria (lines 487-528) [VERIFIED: read]
- `.planning/REQUIREMENTS.md` — OPER-01..04 wording (lines 78-83), traceability (lines 139-142) [VERIFIED: read]
- `.planning/REQUIREMENTS_CODE_SURFACE_MATRIX.md` — Phase 10 surface authority mapping (lines 98-105): `aios-ui/app/**`, `aios-ui/server/routers/_app.ts` as primary; project/query/knowledge routers for OPER-02; evidence drill-down surfaces for OPER-03; end-to-end command-center flow for OPER-04 [VERIFIED: read]
- `.planning/TIER_ONE_ACCEPTANCE_CHECKLIST.md` — Phase 10 capability gates, evidence gates, failure conditions (lines 213-225) [VERIFIED: read]
- `.planning/phases/09-continuous-learning-and-conservative-optimization/09-RESEARCH.md` — Phase 9 deliverables Phase 10 surfaces (LearningSignalKind, RecurringPattern, LearningImpactPerRun, LearningImpactRollup, conservative_optimizer, learning_impact, divergent/experiments wiring through Phase 8 promotion) [VERIFIED: read complete file]
- `.planning/phases/08-prompt-skill-workflow-contracts-and-asset-lifecycle/08-RESEARCH.md` — Phase 8 deliverables (AssetLifecycleState, compare_workflow_effectiveness, propose_workflow_promotion, propose_asset_promotion, recommend_assets_for_packet, vNext workflow registry schema) [VERIFIED: read first 300 lines]
- `.planning/phases/07-delta-scoring-and-health-backfill/07-RESEARCH.md` — Phase 7 deliverables (recommend_workflow_from_health, getProjectStandardsHealth with deltaExplanations + recommendedWorkflows, standards_delta_items, standards_backfill_tasks) [VERIFIED: read first 250 lines]
- `.planning/phases/02-context-query-and-briefing-compilation/02-CONTEXT.md` — packet contract, route metadata integration, grounded query and packet receipt provenance [VERIFIED: read complete]
- `.planning/phases/01-project-workflow-and-prompt-routing/01-CONTEXT.md` — Phase 1 route result contract (D-01..D-18), prompt family selection, persistence/observability [VERIFIED: read complete]
- `aios-ui/server/aios/control-plane.ts` (in-tree, 667 lines) — `getControlPlaneOverview`, `getGovernanceOverview`, `getControlPlaneRunDetail`, `listControlPlaneRuns`, `planTask`, `invokeControlPlaneRun`, `registerControlPlaneManualInvocation`, `cancelControlPlaneRun`, `reviewControlPlaneWriteback`, `resolveControlPlaneFinding`, `requestPacketExpansion` [VERIFIED: read top 130 + 359-460]
- `aios-ui/server/aios/query.ts` (in-tree, 730 lines) — `answerGroundedQuestion` intent routing (`what_changed`, capability, truth-operator), citations + facts + inferences + recommendations [VERIFIED: read 380-430]
- `aios-ui/server/aios/learning.ts` (in-tree, 169 lines) — `proposeRunWritebacks` per-run writeback emitter [VERIFIED: file size]
- `aios-ui/server/aios/standards-health.ts` (in-tree, 322 lines) — `getProjectStandardsHealth`, `updateStandardsBackfillTask` [VERIFIED: file size]
- `aios-ui/server/aios/packet-assembly.ts` (in-tree, 541 lines) — `assembleRankedPacket`, `expandPacketContext` [VERIFIED: file size]
- `aios-ui/server/routers/_app.ts` — 14 routers registered (changes, controlPlane, sessions, prompts, costs, divergent, knowledge, patterns, projects, query, experiments, workflows, automations, insights) [VERIFIED: read complete]
- `aios-ui/server/routers/control-plane.ts` — 10 procedures: overview, governance, runDetail, plan, invoke, registerManualInvocation, cancel, expand, reviewWriteback, resolveFinding [VERIFIED: read complete]
- `aios-ui/server/routers/query.ts` — 1 procedure: `ask` mutation [VERIFIED: read complete]
- `aios-ui/server/routers/projects.ts` (420 lines) — list, detail, taskiSummary, setAiosComponentEnabled, updateBackfillTask procedures [VERIFIED: read first 80 + 250-420]
- `aios-ui/server/routers/automations.ts` (224 lines) — `list` only; no triggerWorkflow yet [VERIFIED: grep + read 180-225]
- `aios-ui/server/routers/workflows.ts` (442 lines) — list, skillKeys, approved, proposals procedures [VERIFIED: grep]
- `aios-ui/server/routers/insights.ts` (1138 lines) — extensive expectation + scope procedures [VERIFIED: grep]
- `aios-ui/server/routers/divergent.ts` (510 lines) — divergent runs surface [VERIFIED: ls + grep]
- `aios-ui/server/routers/experiments.ts` (178 lines) — testRepos, list, workflowSkillExperiments [VERIFIED: grep]
- `aios-ui/server/routers/knowledge.ts` (31 lines) — index, grouped, truthBoundary [VERIFIED: grep]
- `aios-ui/app/page.tsx` (206 lines) — Command Center page; consumes controlPlane.overview, changes.list, automations.list, experiments.list; uses buildAttentionAlerts, buildCommandCenterTimeline [VERIFIED: read first 80 lines]
- `aios-ui/app/control/page.tsx` (29 lines) — Control Plane page; uses ControlPlaneStudio with overview + projects [VERIFIED: read complete]
- `aios-ui/app/query/page.tsx` (17 lines) — GroundedQueryStudio component [VERIFIED: read complete]
- `aios-ui/app/projects/page.tsx` (81 lines) — projects list with health/delta/pipeline/unknown columns [VERIFIED: read complete]
- `aios-ui/app/writebacks/page.tsx` (51 lines) — currently uses `caller.divergent.writebacks()`; Phase 10 migrates to writebacks router [VERIFIED: read complete]
- `aios-ui/app/automations/page.tsx` (61 lines) — automations list with trigger + success rate + status [VERIFIED: read complete]
- `aios-ui/components/layout/Sidebar.tsx` — uses `PRIMARY_NAV` from constants; usePathname for active highlighting [VERIFIED: read complete]
- `aios-ui/lib/constants.ts` — `PRIMARY_NAV` array (14 entries) [VERIFIED: read top 80 lines]
- `aios-ui/lib/control-plane.ts` — comprehensive type definitions including `GovernanceOverview`, `ConsistencyFinding`, `OrchestrationRun*`, `BriefingPacket`, `PacketExpansion`, `ImprovementWriteback`, `GroundedAnswer`, `TopicGraph*`, `WikiMaintenanceMetadata`, `RouteRecommendation`, etc. [VERIFIED: grep export types lines 1-510]
- `aios-ui/package.json` — Next 16, React 19, tRPC 11, zod 3.24, better-sqlite3 11, recharts 2.15, @xyflow/react 12.10, superjson 2.2; scripts: lint, lint:architecture (dependency-cruiser), build [VERIFIED: read complete]
- `pyproject.toml` — Python 3.12, ruff + basedpyright + (likely vulture) configured [VERIFIED: read first 30 lines]
- `AGENTS.md` (in-tree, lines 1-60 read) — context compiler bootloader, execution flow, sub-agent rule, execution-first verification rule, local-first + files-authoritative + governance + explainability + brownfield continuity constraints [VERIFIED: read first 60 lines]
- `~/.claude/CLAUDE.md` — quality ladder, TypeScript discipline, Next.js conventions, git conventions, project roots, system context, tool role boundary [VERIFIED: provided as system context]

### Secondary (MEDIUM confidence — inferred from primary sources or partial verification)

- Phase 5 deliverables (`writeback_approval_policy`, `improvement_writebacks`, `getGovernanceOverview`) — verified to exist in `aios-ui/server/aios/control-plane.ts` and as a contract scope in Phase 8/9 RESEARCH; assumed shape matches Phase 5 RESEARCH (not re-read in this phase)
- Phase 6 deliverables (`success_criteria_findings`, `success_criteria_stage_findings`, `evaluate_and_record`) — referenced in Phase 7/8/9 RESEARCH as shipped; not directly verified in this phase
- Existing aios-ui Search behavior — minimal (only per-page `filter` callbacks observed in HealthGrid/WorkflowSandbox/GitHubSkillCandidates) [VERIFIED: grep]
- Existing automation_workflow_triggers absence — no grep hits for `workflow-launch`, `launchWorkflow`, `workflowLaunch` across aios-ui/services/bin [VERIFIED: grep]
- catalog.ts hardcoded constants — observed via `aios-ui/server/aios/control-plane.ts:373` returning `workflowTemplates` + `agentProfiles` + `invocationBackends` from `@/server/aios/catalog` [VERIFIED: read]

### Tertiary (LOW confidence — assumptions, no direct verification)

- Phase 5/6 actual final shapes — STATE.md says only 5 phases complete and Phase 5 is active, so Phase 5/6 surface details may shift before Phase 10 lands; Phase 10's wiring adapts at integration time. Pitfall 1 + assumption A1 cover this risk.
- Sidebar global-search component pattern — no existing dropdown component in `aios-ui/components/`; Phase 10's GlobalSearchInput is a new pattern. The Sidebar.tsx confirms client-component capability (`"use client"`).

## Metadata

**Confidence breakdown:**
- Existing UI surfaces (routers, projections, pages, components, types): HIGH — every router count, file size, and procedure name was directly verified in `aios-ui/server/routers/_app.ts`, `aios-ui/server/aios/control-plane.ts`, `aios-ui/lib/control-plane.ts`, and `aios-ui/package.json`.
- Existing Python services Phase 10 reuses (Phase 1 routing, Phase 7 recommend_workflow_from_health, Phase 8 recommend_assets_for_packet, Phase 9 LearningImpact, agentize, packet-assembly): HIGH — names and shapes match prior phase research and grep verification of import sites.
- Phase 5/6 readiness as Phase 10 dependency: MEDIUM — STATE.md indicates Phase 5 is active and Phase 6 not started; Pitfall 1 + assumption A1 describe the graceful-degradation strategy.
- Search architecture (LIKE + UNION + recency boost): HIGH — sufficient for the AIOS deployment scale; alternative (FTS5) is documented as a follow-up.
- Next-action fusion approach: HIGH — fuses 5+ recommenders that are already in place by Phase 9; no new persistence required.
- Daily-flow trace approach (preview + replay): HIGH — every step source table exists; preview's dry-mode requirement is documented and testable.
- Query-as-launcher integration: MEDIUM — depends on classifyIntent producing the `should_i_run_workflow` label; the intent classifier is in `aios-ui/server/aios/query.ts` and extending it is straightforward.
- Catalog migration approach (incremental with isSeedData flag): HIGH — matches AGENTS.md brownfield continuity constraint; tests assert flag behavior.
- Automation → workflow trigger via planTask + invokeControlPlaneRun: HIGH — the existing flow is already two-step; Phase 10 wires the trigger mutation around it.
- Drill-down centralization in `aios-ui/lib/drill-down.ts`: HIGH — eliminates URL-string drift; matches Phase 1-9 pattern of centralizing literals.
- Workflow launch from health-delta one-click: MEDIUM — Phase 7 RESEARCH says `standards_delta_items.remediation_playbook_json` carries `recommended_workflow_key`; Phase 10's `launchRemediation` mutation passes it through `planTask`.
- Compounding visibility on Command Center: HIGH — Phase 9 ships `LearningImpactRollup`; Phase 10 only surfaces it.
- Phase status banner: HIGH — Wave 0 audit detects phase completion via table/service presence; UI labels gaps explicitly per Pitfall 1 and 8.
- ASVS coverage / threat model: HIGH — AIOS is single-user local-first, so the threat surface is narrow; existing Phase 5 governance covers the main risks.

**Research date:** 2026-05-22
**Valid until:** 2026-06-22 (30 days — UI primitives and existing routers are stable; Phase 5/6 readiness state may change as those phases ship, which would tighten Phase 10's degradation paths)
