# Requirements To Code Surface Matrix

**Created:** 2026-05-14  
**Purpose:** Map every v1 requirement to the current code surfaces, registries, stores, and planning contracts that must evolve for the requirement to reach tier-one.

## How To Use This Matrix

- **Primary surfaces** are the main implementation surfaces most likely to own the requirement
- **Supporting surfaces** are adjacent runtime, config, UI, or planning surfaces that must stay aligned
- **Tier-one build target** explains what the codebase must become true of, not just what file to edit
- **Evidence target** describes the kind of durable proof that should exist before the requirement is treated as satisfied

## Phase 1: Project, Workflow, And Prompt Routing

| Requirement | Primary Surfaces | Supporting Surfaces | Tier-One Build Target | Evidence Target |
|---|---|---|---|---|
| `ROUT-01` | `services/aios_cli.py`, project inventory sources, route-resolution logic | `PROJECT.md`, `.planning/PHASE_01_SUBROADMAP.md`, project dossier/query surfaces | vague intent resolves to one project or explicit ambiguity block | stored route records showing exact, ambiguous, and unsupported project outcomes |
| `ROUT-02` | `services/workflow_orchestration.py`, `services/execution_strategy.py`, `config/workflows/registry.json` | `.planning/WORKFLOW_MATRIX.md`, `.planning/ROADMAP.md` | task-family classification chooses the smallest sufficient workflow | route audit proving workflow choice across representative task families |
| `ROUT-03` | route rationale storage, workflow-selection logic | operator query surfaces, route metadata display surfaces | route decision includes inspectable explanation and nearby alternatives | durable route rationale with comparison evidence |
| `ROUT-04` | `services/invocation_backends.py`, `prompts/registry.json`, `bin/hook-prompt-submit.py` | `prompts/*`, `aios-ui/server/routers/prompts.ts`, backend capability truth | route includes agent/harness recommendation and prompt/handoff family | route records showing workflow, harness, and prompt-family linkage |

## Phase 2: Context, Query, And Briefing Compilation

| Requirement | Primary Surfaces | Supporting Surfaces | Tier-One Build Target | Evidence Target |
|---|---|---|---|---|
| `CONT-01` | `tools/context-compile.mjs`, `aios/context/**` | project truth, standards registries, packet sources, prompt assets, CTS surfaces | packet compiler selects only relevant context from truth, standards, packets, prompt assets, and recent evidence | receipts showing high-signal packet selection on representative tasks |
| `CONT-02` | context receipt generation and storage | `aios-ui/app/context/page.tsx`, packet history surfaces | loaded and skipped context are recorded durably with reasons | stored receipts retrievable by run and packet id |
| `CONT-03` | context compiler diagnostics | query surfaces, truth freshness checks, packet validators | missing, stale, or conflicting context blocks or warns before execution | receipts and audit output showing missing/stale/conflicting states |
| `CONT-04` | briefing packet generation, handoff assembly logic | prompt-family selection, workflow contracts, packet storage | agent-ready handoff packet includes objective, constraints, files, workflow steps, checks, and acceptance criteria | packet fixtures and handoff completeness audits |

## Phase 3: Workflow Execution And Run State

| Requirement | Primary Surfaces | Supporting Surfaces | Tier-One Build Target | Evidence Target |
|---|---|---|---|---|
| `RUN-01` | `orchestration_runs`, `orchestration_run_events`, lifecycle state logic | `bin/hook-session-start.py`, `bin/hook-stop.py`, lifecycle audit | explicit lifecycle states replace heuristic completion guesses | audit output showing supported lifecycle states only |
| `RUN-02` | `orchestration_invocations`, session linkage, artifact linkage | invocation backend handshake logic, run-event persistence | runs, invocations, sessions, artifacts, and events remain durably linked | stored runs with traceable invocation/session/artifact chains |
| `RUN-03` | run resume logic, packet/run linkage | lifecycle state transitions, approval state storage | partial workflows resume with packet, state, and next action intact | regression fixtures proving interrupted-run resumption |
| `RUN-04` | run closeout summaries, event finalization | validation records, approval references, artifact summaries | closeout explains what changed, what ran, what approvals mattered, and what remains unresolved | durable closeout records for representative serious runs |

## Phase 4: Project Truth, Knowledge, And Grounded Query

| Requirement | Primary Surfaces | Supporting Surfaces | Tier-One Build Target | Evidence Target |
|---|---|---|---|---|
| `TRUTH-01` | `PROJECT.md`, project truth files, truth-update workflow surfaces | project registries, writeback proposals, dossier views | each major project has one canonical truth authority | project inventory proving canonical truth exists for each major linked project |
| `TRUTH-02` | truth-file structures, truth-update logic | project dossier, decision records, follow-up surfaces | truth captures goals, architecture, risks, completed work, deltas, decisions, and next actions | truth freshness audit or diff evidence |
| `TRUTH-03` | `aios-ui/server/routers/query.ts`, grounded query logic | knowledge graph, project truth, recent evidence, CTS | AIOS answers what is being built, what changed, and what remains unresolved before manual assembly | grounded query outputs with cited sources |
| `TRUTH-04` | `knowledge_topics`, `knowledge_references`, `knowledge_relationships` | `aios-ui/server/routers/knowledge.ts`, truth/writeback logic | truth, decisions, prompts, skills, notes, and workflows are linked as inspectable knowledge objects | knowledge graph/backlink evidence for representative assets |

## Phase 5: Governed Writeback And Approval Control

| Requirement | Primary Surfaces | Supporting Surfaces | Tier-One Build Target | Evidence Target |
|---|---|---|---|---|
| `GOV-01` | `improvement_writebacks`, `memory_writeback_proposals`, writeback generation logic | workflow finalization, truth/prompt/skill/workflow mutation surfaces | AIOS emits reviewable proposals instead of silently mutating important state | stored proposal records across truth, prompts, skills, workflows, and standards |
| `GOV-02` | approval-gate logic, approval state storage | workflow contracts, operator approval surfaces | high-impact changes require explicit approval before becoming authoritative | approval audit proving gated classes cannot silently promote |
| `GOV-03` | run closeout writeback logic | workflow-learning events, no-learning evidence, follow-up creation | every meaningful run leaves writeback, follow-up, or explicit no-learning evidence | terminal run audit showing no silent drop-off |
| `GOV-04` | unresolved-risk and follow-up persistence | closeout summaries, approval state, operator surfaces | end-of-run state captures unresolved risks, pending approvals, and follow-up work | closeout artifacts showing unresolved items durably stored |

## Phase 6: Standards Resolution And Evidence-Based Evaluation

| Requirement | Primary Surfaces | Supporting Surfaces | Tier-One Build Target | Evidence Target |
|---|---|---|---|---|
| `STND-01` | `config/success-criteria/registry.json`, `config/success-criteria/skill-map.json`, `services/success_criteria.py` | hook startup packet, workflow contracts, standards context packets | each task resolves to the correct explicit standards set before execution | startup or preflight evidence showing criteria resolution per task |
| `STND-02` | `services/success_criteria.py`, evaluation artifact storage | file findings, evaluator metadata, operator surfaces | outputs are judged by explicit criteria rather than generic model taste | durable evaluations with blocker/warning/pass structure |
| `STND-03` | execution-first verification hooks and workflow bindings | CLI/runtime entrypoints, test harnesses, corpus harness | stateful or core changes require execution-first verification | run evidence proving real path execution occurred where required |
| `STND-04` | `success_criteria_evaluations`, `success_criteria_findings`, `data/success-criteria/evaluations/*` | hook-stop integration, UI evidence surfaces | evaluations persist blockers, warnings, passes, and accepted tradeoffs durably | queryable evaluation history tied to runs |

## Phase 7: Delta Scoring And Health Backfill

| Requirement | Primary Surfaces | Supporting Surfaces | Tier-One Build Target | Evidence Target |
|---|---|---|---|---|
| `DELT-01` | `services/standards_health.py`, project health routers | standards snapshots, capability truth, project dossier | project alignment is scored across required quality dimensions | repeatable standards-health proofs across priority projects |
| `DELT-02` | standards-health explainers, health evidence surfaces | capability truth, findings, remediation links | every score is explainable with evidence, confidence, freshness, and remediation | drill-downable score explanation records |
| `DELT-03` | `services/capability_truth.py`, trusted-signal state contracts | project health UI, automation/status audits | health views distinguish confirmed, inferred, missing, and contradictory signals | audit output proving signal-state distinctions are preserved |
| `DELT-04` | remediation prioritization logic, project health recommendations | standards backfill workflow, query surfaces | biggest gaps produce prioritized backfill recommendations | project backfill plans tied to score deltas |

## Phase 8: Prompt, Skill, Workflow Contracts, And Asset Lifecycle

| Requirement | Primary Surfaces | Supporting Surfaces | Tier-One Build Target | Evidence Target |
|---|---|---|---|---|
| `ASSET-01` | `prompts/registry.json`, `config/workflows/skills.json`, workflow registry surfaces | asset lifecycle UI, planning matrix, experiment surfaces | prompts, skills, and workflows behave as lifecycle-managed assets | asset records showing purpose, applicability, status, and evidence |
| `ASSET-02` | asset status storage and display | approval gates, promotion logic | reusable assets distinguish draft, candidate, approved, active, and deprecated states | lifecycle state transitions with auditability |
| `ASSET-03` | workflow-learning/event linkage, experiment results | prompt/skill/workflow views, writebacks | assets are linked to the workflows and task types where they succeeded or failed | evidence views showing success/failure history by asset |
| `ASSET-04` | route selection, packet generation, asset recommendation logic | Phase 1 and Phase 2 route/packet contracts | AIOS recommends proven prompts, skills, and workflows during routing and handoff creation | route and packet records showing asset recommendation provenance |
| `WFLO-01` | `config/workflows/registry.json`, `services/workflow_orchestration.py` | `.planning/WORKFLOW_MATRIX.md`, workflow UI surfaces | each governed workflow is a stage-based contract with required inputs, outputs, validations, and artifacts | registry or equivalent contract records for representative workflows |
| `WFLO-02` | stage-binding logic for prompts, skills, tools, standards, approvals, writebacks | prompt registry, success criteria, approval surfaces | stage-local bindings are explicit rather than informal | workflow contract evidence showing bound prompts/tools/criteria per stage |
| `WFLO-03` | workflow evaluation logic, run evidence aggregation | stage outputs, closeout summaries, learning events | workflow success is measured at both stage and run level | workflow evaluation records with stage-by-stage outcomes |
| `WFLO-04` | workflow comparison and lifecycle logic | learning surfaces, promotion/deprecation governance | workflows can be promoted, revised, or deprecated from evidence | comparative workflow effectiveness records over time |

## Phase 9: Continuous Learning And Conservative Optimization

| Requirement | Primary Surfaces | Supporting Surfaces | Tier-One Build Target | Evidence Target |
|---|---|---|---|---|
| `LEARN-01` | `workflow_learning_events`, `services/workflow_learning.py` | run closeout, packet history, evaluation records | runs capture evidence useful for future prompt, workflow, and packet improvement | durable learning-event history linked to runs |
| `LEARN-02` | learning analysis surfaces, experiment/query logic | corpus harness, failure recovery, standards health | recurring failures, weak rules, and bloated packets are detectable from accumulated evidence | periodic learning summaries showing repeated failure patterns |
| `LEARN-03` | conservative improvement proposal logic | approval gates, route/packet/standards surfaces | AIOS proposes reviewed improvements without silent policy drift | proposal records for routing/context/evaluation improvements |
| `LEARN-04` | compounding visibility surfaces | operator dashboards, project/run histories | AIOS shows what each meaningful run improved for future work | operator-visible before/after learning impact traces |

## Phase 10: Operator Surfaces, Query, And Daily-Flow Visibility

| Requirement | Primary Surfaces | Supporting Surfaces | Tier-One Build Target | Evidence Target |
|---|---|---|---|---|
| `OPER-01` | `aios-ui/app/**`, `aios-ui/server/routers/_app.ts` | project, run, workflow, prompt, approval, health, knowledge views | operator surfaces are searchable and inspectable across all default-layer objects | command-center navigation proving core entities are visible without seeded fallbacks |
| `OPER-02` | project/query/knowledge routers | grounded query, route results, packet history, asset recommendation surfaces | AIOS answers what project needs attention, what workflow to run, and what assets/context apply | operator queries returning actionable preflight answers |
| `OPER-03` | evidence drill-down surfaces, receipts/rationale UIs | route records, packet receipts, evaluations, health explainers | metrics and recommendations expose their evidence trail and drill-down path | UI and query evidence paths from summary metric to source record |
| `OPER-04` | end-to-end command-center flow surfaces | route, packet, run, evaluation, writeback, delta, approval surfaces | daily flow is visible from vague goal through unresolved deltas | end-to-end demonstrable operator flow with durable records at every stage |

## Cross-Cutting Surfaces With High Reuse

These surfaces support many requirements and should be treated as shared infrastructure:

| Surface | Why It Matters |
|---|---|
| `PROJECT.md` and project truth files | authority for current project state, goals, risks, and next actions |
| `config/workflows/registry.json` | workflow routeability and stage contracts |
| `prompts/registry.json` | prompt-family recommendation and lifecycle |
| `config/success-criteria/*` | standards resolution and explicit evaluation |
| `tools/context-compile.mjs` | packet assembly, receipts, and context discipline |
| orchestration run/invocation/event tables | durable execution and evidence spine |
| knowledge tables and query routers | grounded answers and asset linkage |
| approval/writeback storage | governed mutation and compounding memory |
| `aios-ui/app/**` plus `aios-ui/server/routers/**` | operator visibility and drill-down |

## Immediate Planning Implications

1. Phase plans should name the exact primary surfaces from this matrix instead of using broad category labels only.
2. Validation work should prove tier-one targets at the requirement level, not just the feature level.
3. Cross-cutting shared surfaces should be upgraded carefully because many later requirements depend on them.
4. A phase is not really done if its primary surfaces changed but its evidence target is still missing.

---
*Last updated: 2026-05-14*
