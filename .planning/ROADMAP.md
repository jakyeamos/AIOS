# AIOS Roadmap

**Planning Date:** 2026-05-14  
**Scope:** v1 is the full operating-system vision, delivered through sequenced milestones and phases rather than scope cuts.  
**Source Inputs:** [PROJECT.md](/Users/jakyeamos/AIOS/.planning/PROJECT.md), [REQUIREMENTS.md](/Users/jakyeamos/AIOS/.planning/REQUIREMENTS.md), [research/SUMMARY.md](/Users/jakyeamos/AIOS/.planning/research/SUMMARY.md), [FUNCTIONALITY_MAP.md](/Users/jakyeamos/AIOS/.planning/FUNCTIONALITY_MAP.md), [FUNCTIONALITY_PLAN.md](/Users/jakyeamos/AIOS/.planning/FUNCTIONALITY_PLAN.md), [WORKFLOW_MATRIX.md](/Users/jakyeamos/AIOS/.planning/WORKFLOW_MATRIX.md)

## Supporting Planning Artifacts

The roadmap is backed by deeper planning contracts:

- [PHASE_01_SUBROADMAP.md](/Users/jakyeamos/AIOS/.planning/PHASE_01_SUBROADMAP.md) for the governed entry-loop implementation sequence
- [REQUIREMENTS_CODE_SURFACE_MATRIX.md](/Users/jakyeamos/AIOS/.planning/REQUIREMENTS_CODE_SURFACE_MATRIX.md) for requirement-level code-surface traceability
- [TIER_ONE_ACCEPTANCE_CHECKLIST.md](/Users/jakyeamos/AIOS/.planning/TIER_ONE_ACCEPTANCE_CHECKLIST.md) for per-phase exit gates and proof expectations

## Roadmap Intent

This roadmap is the execution contract for turning AIOS from a strong local alpha into the default operating layer for serious AI-assisted work.

The roadmap is not just feature ordering. It is a dependency-managed build sequence for:

- governed entry into work
- trustworthy project truth and knowledge grounding
- evidence-backed standards and health scoring
- reusable workflow/prompt/skill infrastructure
- operator-visible default-layer behavior

## Sequencing Logic

The sequencing follows five hard constraints:

1. **Routing before polish**  
   AIOS must know what a task is, which project it belongs to, which workflow should run, and which prompt family applies before richer UX matters.

2. **Context before execution confidence**  
   Packets, grounded query, and truth freshness must become reliable before run state or evaluation can be trusted.

3. **Evidence before scores**  
   Standards and health intelligence should sit on top of durable truth, runtime evidence, and governed writeback rather than inference alone.

4. **Governance before self-improvement**  
   Prompt, skill, workflow, and truth mutation must be reviewable before AIOS is allowed to improve itself aggressively.

5. **Operator surfaces last**  
   The command center should expose trustworthy state, not give polished shape to weak primitives.

## Workflow Rollout Strategy

The workflow library should harden in the same order as the control plane.

### Early default workflows

These are the first workflows that must become tier-one enough to trust:

1. `implementation-delivery`
2. `failure-recovery`
3. `agent handoff generation`
4. `audit-only`
5. `audit-and-implement`

### Mid-sequence workflows

These become important after truth, governance, and evidence improve:

1. `project truth update`
2. `standards backfill`
3. `codebase architecture review`
4. `security review`
5. `test-first implementation`

### Later improvement workflows

These matter once the core loop is already trustworthy:

1. `prompt experiment`
2. `research-to-plan conversion`
3. `PRD / requirements generation`
4. `divergent-strategy`
5. `UI polish`

## Milestones

### Milestone 1: Governed Entry Loop

This milestone establishes deterministic entry into work. AIOS should be able to take a vague goal and convert it into the correct project, workflow, prompt family, packet, and run shell before any real execution begins.

#### Phase 1: Project, Workflow, And Prompt Routing

**Goal:** Turn vague goals into an explicit project target, workflow route, and recommended agent/harness plus prompt/handoff family with inspectable reasoning.

**Requirements:** ROUT-01, ROUT-02, ROUT-03, ROUT-04

**Detailed Scope:**
- Deterministic project resolution from vague intent.
- Task-family classification that uses explicit route hints, risk cues, and known workflow contracts.
- Workflow selection that chooses the smallest sufficient governed workflow rather than generic execution.
- Prompt-family or handoff-family selection as part of the route, not as a downstream afterthought.
- Initial agent/harness recommendation tied to workflow constraints and expected verification shape.
- Route rationale persistence in run metadata and operator surfaces.

**Current Surfaces To Evolve:**
- `services/workflow_orchestration.py`
- `services/execution_strategy.py`
- `services/invocation_backends.py`
- `prompts/registry.json`
- `bin/hook-prompt-submit.py`
- project inventory / planning truth inputs

**Workflow Ownership In This Phase:**
- Harden `implementation-delivery` and `failure-recovery` routing first.
- Define the route envelope for `audit-only`, `audit-and-implement`, and `agent handoff generation`.
- Make prompt-family selection explicit for all default serious-work routes.

**Expected Outputs:**
- route contract schema
- project candidate / ambiguity handling
- workflow recommendation rationale
- prompt-family recommendation logic
- persisted route metadata on runs/invocations

**Dependencies:**
- project inventory quality
- prompt registry quality
- workflow registry quality

**Observable Success Criteria:**
- A vague-goal submission either resolves to one target project or blocks for explicit clarification with the ambiguity surfaced.
- The selected workflow is the smallest sufficient option for the task type and is persisted as structured run context.
- Route selection exposes why the chosen workflow beat nearby alternatives.
- The recommended agent or harness is attached to the route with rationale tied to task type and workflow constraints.
- The route also identifies the appropriate prompt or handoff family so execution starts from a proven instruction shape rather than an empty shell.

#### Phase 2: Context, Query, And Briefing Compilation

**Goal:** Compile the smallest sufficient task packet, grounded project/query context, and prompt-aware briefing surface before execution.

**Requirements:** CONT-01, CONT-02, CONT-03, CONT-04

**Detailed Scope:**
- Task-specific packet compilation using truth, standards, packets, prompt assets, repo context, and recent evidence.
- Loaded/skipped receipts with reasons and stale/missing/conflict reporting.
- Grounded query support as part of packet assembly, not a separate convenience surface.
- Handoff packet generation that includes objective, constraints, relevant files, workflow steps, prompt/handoff instructions, required checks, and acceptance criteria.
- Packet identity and provenance persistence so runs, writebacks, and learning can point back to it.

**Current Surfaces To Evolve:**
- `tools/context-compile.mjs`
- `aios/context/**`
- `aios-ui/app/context/page.tsx`
- `briefing_packets`
- `aios-ui/server/routers/query.ts`
- prompt library/router surfaces

**Workflow Ownership In This Phase:**
- Make `agent handoff generation` a governed workflow contract.
- Add packet/handoff completeness expectations for `implementation-delivery`, `failure-recovery`, and `audit-only`.
- Define how all future workflows consume packets and prompt families.

**Expected Outputs:**
- packet schema contract
- query-backed context assembly rules
- prompt-aware handoff contract
- receipt integrity rules

**Dependencies:**
- Phase 1 route contract
- truth freshness inputs
- standards and packet registries

**Observable Success Criteria:**
- Packet compilation pulls from project truth, standards, packets, prompt assets, and recent evidence without unrelated context spill.
- Each run stores a durable receipt showing loaded and skipped context with explicit reasons.
- Missing, stale, or conflicting context blocks or warns before execution continues.
- The final packet is agent-ready and includes objective, constraints, relevant files, workflow steps, prompt/handoff instructions, and acceptance criteria.

#### Phase 3: Workflow Execution And Run State

**Goal:** Make serious workflow execution durable, resumable, approval-aware, and inspectable from start through closeout.

**Requirements:** RUN-01, RUN-02, RUN-03, RUN-04

**Detailed Scope:**
- Explicit lifecycle modeling for active, blocked, waiting, failed-validation, partial, complete, and follow-up-needed outcomes.
- Strong run/invocation/session/artifact linkage without residual heuristic ambiguity.
- Resume semantics that preserve packet id, pending approvals, current stage, and next recommended action.
- Closeout summaries that include checks run, approvals touched, changed artifacts, unresolved deltas, and writeback implications.
- Stage- and workflow-aware execution semantics for the default serious-work workflows.

**Current Surfaces To Evolve:**
- `orchestration_runs`
- `orchestration_invocations`
- `orchestration_run_events`
- `bin/hook-session-start.py`
- `bin/hook-stop.py`
- `services/invocation_backends.py`
- `aios lifecycle-audit`

**Workflow Ownership In This Phase:**
- Make `implementation-delivery` and `failure-recovery` truly durable end-to-end.
- Define resume and partial-state expectations for future workflow contracts.
- Make closeout behavior consistent enough for `audit-and-implement` and `test-first implementation`.

**Expected Outputs:**
- stronger lifecycle vocabulary and closeout rules
- explicit resume contract
- approval-aware run state
- stage-aware execution evidence model

**Dependencies:**
- Phase 1 route persistence
- Phase 2 packet identity
- current managed runtime closeout quality

**Observable Success Criteria:**
- Runs move through explicit lifecycle states without collapsing blocked, approval-gated, partial, and completed outcomes.
- Runs, invocations, sessions, artifacts, and lifecycle events remain durably linked for each serious execution.
- A partially completed run can be resumed with its original packet, current state, and next recommended action intact.
- Run closeout shows what changed, what checks ran, what approvals were involved, and what remains unresolved.

### Milestone 2: Truth, Governance, And Evidence

This milestone makes the system durable after execution. It ensures AIOS leaves behind correct truth, searchable knowledge, and reviewable writeback rather than shallow run history.

#### Phase 4: Project Truth, Knowledge, And Grounded Query

**Goal:** Maintain current project truth and linked operational knowledge as mandatory operating surfaces rather than best-effort documentation byproducts.

**Requirements:** TRUTH-01, TRUTH-02, TRUTH-03, TRUTH-04

**Detailed Scope:**
- Canonical truth surfaces for major projects.
- Truth freshness across goals, architecture, risks, decisions, completed work, unresolved deltas, and next actions.
- Knowledge linking across truth entries, prompts, skills, workflows, decisions, and research.
- Grounded query answers that combine truth, knowledge, and recent evidence before manual context assembly.
- Distinction between accepted truth, proposals, and inferred knowledge.

**Current Surfaces To Evolve:**
- `PROJECT.md` discipline and truth-file patterns
- knowledge object/relationship tables
- `aios-ui/server/routers/knowledge.ts`
- `aios-ui/server/routers/query.ts`
- project dossier / grounded query logic

**Workflow Ownership In This Phase:**
- Stand up `project truth update` as a governed workflow.
- Stand up `codebase architecture review` and `research-to-plan conversion` as explicit workflow contracts.
- Make `audit-only` and `standards backfill` consume truth and query as first-class inputs.

**Expected Outputs:**
- truth update contract
- knowledge/truth linkage rules
- query answer coverage for default-layer questions
- truth freshness and drift rules

**Dependencies:**
- Phase 2 packet/query structure
- Phase 3 durable closeout

**Observable Success Criteria:**
- Each major linked project has one canonical truth surface or equivalent structured authority.
- Truth records stay current on goals, architecture, risks, completed work, unresolved deltas, decisions, and recommended next actions.
- AIOS can answer what is being built, what changed, what remains unresolved, and which prior decisions or reusable assets are relevant before manual assembly.
- Truth entries, decisions, notes, prompts, skills, and workflow artifacts are linked through searchable knowledge objects.

#### Phase 5: Governed Writeback And Approval Control

**Goal:** Make writebacks, approvals, and unresolved follow-up durable parts of every meaningful run.

**Requirements:** GOV-01, GOV-02, GOV-03, GOV-04

**Detailed Scope:**
- Reviewable writeback proposals for truth, prompts, skills, workflows, standards, and packets.
- Approval-state modeling across accepted, rejected, pending, stale, and waived decisions where appropriate.
- Consistent unresolved follow-up capture at closeout.
- Strong distinction between draft/candidate proposal state and promoted accepted state.
- Governance boundaries for destructive actions and policy/asset promotion.

**Current Surfaces To Evolve:**
- `improvement_writebacks`
- `memory_writeback_proposals`
- writeback UI and router actions
- promotion lifecycle tables

**Workflow Ownership In This Phase:**
- Add explicit approval and writeback semantics to all default workflows.
- Make `project truth update`, `prompt experiment`, `divergent-strategy`, and `standards backfill` governed by uniform approval rules.

**Expected Outputs:**
- cross-asset writeback contract
- approval policy classes
- unresolved-follow-up contract
- workflow closeout governance rules

**Dependencies:**
- Phase 3 closeout quality
- Phase 4 truth/knowledge distinction

**Observable Success Criteria:**
- Truth, prompt, skill, workflow, standard, and packet changes are emitted as reviewable writeback proposals rather than silent mutation.
- Approval gates are enforced for important truth changes, policy changes, asset promotion, workflow behavior changes, and destructive actions.
- Every meaningful run ends with durable writeback, follow-up, or no-learning evidence.
- Unresolved risks, pending approvals, and follow-up actions are recorded at governed workflow closeout.

### Milestone 3: Standards And Health Intelligence

This milestone turns execution and truth evidence into quality judgment and remediation guidance.

#### Phase 6: Standards Resolution And Evidence-Based Evaluation

**Goal:** Bind execution to explicit standards and preserve evidence-backed evaluation outcomes.

**Requirements:** STND-01, STND-02, STND-03, STND-04

**Detailed Scope:**
- Resolve applicable criteria and standards before execution begins.
- Evaluate outcomes against those criteria with durable evidence.
- Enforce execution-first verification on tasks that need it.
- Preserve findings, blockers, tradeoffs, and validation outputs as real artifacts.
- Move workflow validation from loose “checklist” behavior toward explicit stage-level evaluation.

**Current Surfaces To Evolve:**
- `config/success-criteria/*`
- `services/success_criteria.py`
- hook evaluation integration
- existing tests and corpus harness

**Workflow Ownership In This Phase:**
- Make `audit-only`, `audit-and-implement`, `security review`, `test-first implementation`, and `repo cleanup` standards-aware from the start.
- Add workflow-stage validation semantics to current registry workflows where possible.

**Expected Outputs:**
- stronger standards resolution contract
- stage-level evaluation hooks
- execution-first verification integration with workflow shape
- evidence-preserving validation outputs

**Dependencies:**
- Phase 3 run-state integrity
- Phase 5 governance/closeout state

**Observable Success Criteria:**
- Each task resolves to the correct success criteria and standards set before execution begins.
- Completed work is evaluated against explicit criteria rather than generic model judgment.
- Execution-first verification is enforced for stateful, cross-system, and core-logic changes.
- Findings, blockers, warnings, passes, and accepted tradeoffs are stored durably per run.

#### Phase 7: Delta Scoring And Health Backfill

**Goal:** Turn evaluation and truth evidence into explainable project-health and standards-gap scoring.

**Requirements:** DELT-01, DELT-02, DELT-03, DELT-04

**Detailed Scope:**
- Domain-specific alignment scoring across the major quality dimensions.
- Concrete evidence, confidence, freshness, contradiction, and remediation on every major signal.
- Prioritized backfill path generation from the highest-value deltas.
- Health and delta views that influence what workflow should run next.

**Current Surfaces To Evolve:**
- `services/standards_health.py`
- `services/capability_truth.py`
- project routers / insights / health surfaces
- quality pipeline registry

**Workflow Ownership In This Phase:**
- Stand up `standards backfill` as a serious default remediation workflow.
- Make `audit-only` and `codebase architecture review` produce deltas that feed health views.
- Make operator surfaces and query recommend workflows from delta state.

**Expected Outputs:**
- explainable delta contract
- remediation-priority logic
- stronger project-health / capability-health consistency
- workflow recommendations from health state

**Dependencies:**
- Phase 4 truth quality
- Phase 6 evaluation evidence

**Observable Success Criteria:**
- AIOS produces domain-level alignment scores across architecture, testing, maintainability, security, UX, observability, documentation, launch readiness, agent-readiness, and standards compliance.
- Each score shows evidence, confidence, freshness, and remediation guidance.
- Health views distinguish confirmed, inferred, missing, and contradictory signals instead of collapsing them into one status.
- The system can prioritize a backfill path for the highest-value standards or capability gaps.

### Milestone 4: Reusable Improvement Loops

This milestone upgrades reusable assets and workflows into governed product infrastructure, then uses durable evidence to improve them carefully.

#### Phase 8: Prompt, Skill, Workflow Contracts, And Asset Lifecycle

**Goal:** Treat reusable prompts, skills, and workflows as governed assets and workflow contracts with evidence-backed applicability, stage bindings, and promotion rules.

**Requirements:** ASSET-01, ASSET-02, ASSET-03, ASSET-04, WFLO-01, WFLO-02, WFLO-03, WFLO-04

**Detailed Scope:**
- Normalize lifecycle metadata across prompts, skills, and workflows.
- Expand workflow schema to include:
  - required inputs
  - required outputs
  - validations
  - approval gates
  - expected artifacts
  - writeback behavior
  - learning signals
- Tie packet generation and handoff creation to approved or candidate asset selection.
- Support workflow comparison, promotion, revision, and deprecation.
- Separate stage-based workflow contracts from generic route hints.

**Current Surfaces To Evolve:**
- `config/workflows/registry.json`
- `config/workflows/skills.json`
- `prompts/registry.json`
- experiment/promotion lifecycle surfaces
- `services/workflow_orchestration.py`

**Workflow Ownership In This Phase:**
- Harden `implementation-delivery` and `failure-recovery` into richer stage contracts.
- Keep `academic_paper_v1` as a proof case for stage richness.
- Tighten `divergent-strategy` governance.
- Introduce explicit governed contracts for the planned workflow families from [WORKFLOW_MATRIX.md](/Users/jakyeamos/AIOS/.planning/WORKFLOW_MATRIX.md).

**Expected Outputs:**
- workflow contract schema vNext
- asset lifecycle normalization
- prompt/skill/workflow recommendation rules
- workflow comparison and promotion model

**Dependencies:**
- Phase 1 route contract
- Phase 2 packet/handoff quality
- Phase 5 approval gates
- Phase 6 evaluation evidence

**Observable Success Criteria:**
- Prompts, skills, and workflows are tracked with purpose, applicability, status, and usefulness evidence.
- Asset lifecycle states distinguish draft, candidate, approved, active, and deprecated artifacts.
- Reusable assets are linked to the workflows and task types where they succeeded or failed.
- Packet generation and handoff creation can recommend proven reusable assets.
- Each governed workflow is modeled as a stage-based contract with required inputs, outputs, validations, and expected artifacts.
- Workflow stages explicitly bind prompts, skills, tools, standards, approval gates, and writeback behavior.
- Workflow success can be evaluated at both the stage level and the overall run level from durable evidence.
- Workflow effectiveness can be compared over time to support promotion, revision, or deprecation decisions.

#### Phase 9: Continuous Learning And Conservative Optimization

**Goal:** Improve routing, packet selection, workflows, and evaluation from reviewed evidence without silent policy drift.

**Requirements:** LEARN-01, LEARN-02, LEARN-03, LEARN-04

**Detailed Scope:**
- Capture learning from prompts, skills, workflows, packet shapes, and route outcomes.
- Identify repeated failures, ignored rules, bloated packets, weak prompts, and weak workflows.
- Promote only conservative, explainable improvements from reviewed evidence.
- Make compounding visible to the operator.

**Current Surfaces To Evolve:**
- `workflow_learning_events`
- workflow learning audits
- experiments / divergent strategy
- promotion lifecycle items

**Workflow Ownership In This Phase:**
- Compare current governed workflows by rework rate, artifact quality, and writeback usefulness.
- Make `prompt experiment` and `divergent-strategy` feed directly into governed promotion flows.
- Feed route-quality and packet-quality signals back into Phase 1 and Phase 2 behavior.

**Expected Outputs:**
- learning signal taxonomy
- route/prompt/workflow comparison outputs
- conservative promotion rules
- operator-visible compounding surfaces

**Dependencies:**
- Phase 8 workflow and asset metadata
- Phase 6/7 evidence quality

**Observable Success Criteria:**
- Run evidence is captured in a form that can inform future prompt, skill, workflow, and packet improvements.
- Cross-run analysis can identify recurring failure modes, ignored rules, bloated packets, and weak workflows.
- Proposed improvements to routing, context selection, and evaluation are conservative and grounded in reviewed outcomes.
- Operator-visible compounding shows what each meaningful run improved for future work.

### Milestone 5: Default Operating Layer

This milestone makes the mature control plane visible and usable as the default operating layer instead of a collection of interesting subsystems.

#### Phase 10: Operator Surfaces, Query, And Daily-Flow Visibility

**Goal:** Expose the governed operating loop through operator surfaces only after routing, truth, evidence, reusable asset selection, and learning are trustworthy.

**Requirements:** OPER-01, OPER-02, OPER-03, OPER-04

**Detailed Scope:**
- Searchable, inspectable surfaces for projects, runs, workflows, prompts, knowledge, query, deltas, automations, approvals, and experiments.
- Route, packet, query, and health outputs that answer “what should happen next?” before manual prep.
- Operator views that expose receipts, route rationales, evidence trails, remediation paths, and pending approvals.
- End-to-end visibility for the canonical daily loop:
  - vague goal
  - project/workflow/prompt route
  - packet and handoff
  - execution and validation
  - truth/writeback updates
  - unresolved deltas and next actions

**Current Surfaces To Evolve:**
- `aios-ui/app/**`
- `aios-ui/server/routers/**`
- query, prompts, projects, runs, automations, workflows, experiments, and insights routes

**Workflow Ownership In This Phase:**
- Default workflows must be launchable, inspectable, and explainable from operator surfaces.
- Query should recommend the next likely workflow, prompt assets, and project target.
- Automations and health deltas should become workflow-launch triggers, not only read surfaces.

**Expected Outputs:**
- default-layer operator view design
- next-action and workflow-recommendation surfaces
- query-integrated operator loop
- reduced fallback/seed ambiguity in UI

**Dependencies:**
- all prior milestones

**Observable Success Criteria:**
- Operator views are searchable and inspectable across projects, runs, workflows, knowledge, prompts, deltas, approvals, and recent changes.
- The system can answer which project needs attention, what good looks like, which workflow should run, which prompt/skill assets apply, and which context an agent needs before manual prep.
- Visible metrics and recommendations drill down into receipts, routing decisions, evidence trails, and remediation paths.
- The end-to-end daily flow is visible from vague goal through routing, execution, evaluation, writeback, and unresolved deltas.

### Milestone 6: Testing, Benchmark Evaluation, And Shadow Workflows

This milestone makes AIOS's effectiveness measurable and falsifiable. It converts the agent eval foundation from Phase 10 (Plans 07–08) into running instrumentation. Every major workflow should produce durable evidence, not just output.

#### Phase 11: Testing, Benchmark Evaluation, And Shadow Workflows

**Goal:** Prove measurable workflow lift across real projects through shadow branches, paired comparisons, scorecards, ablations, second brain eval, peer passive trace, automated shadow benchmark execution, portable context packets, and external harness adapters.

**Requirements:** EVAL-01, EVAL-02, EVAL-03, EVAL-04, EVAL-05, EVAL-06, EVAL-07, EVAL-08

**Detailed Scope:**
- Durable eval_tasks and eval_runs tables capturing every major eval with context profile, condition, model, cost, and result.
- Second brain evaluation track with gold-set tasks, retrieval precision/recall/staleness metrics, and Second Brain Lift computation.
- Shadow branch testing infrastructure: isolated worktrees, contamination prevention, diff/test capture, Shadow Branch Delta.
- Feature ablation runner across 8 conditions proving which AIOS features create lift and which do not.
- Peer passive trace mode: observation-only, privacy-safe, shadow candidate detection with weighted scoring.
- Peer automated shadow benchmark pipeline: full 14-state automation state machine from in-person approval through comparison report and backlog creation.
- Portable context packet generator: task-specific packets that enable peer/core runs without the personal second brain.
- External harness adapters (SWE-bench, Terminal-Bench) and result normalization into eval_runs with external_clean_room context profile.
- Eval UI panels embedded in existing Phase 10 operator surfaces (collapsible, degradation-safe).

**Current Infrastructure To Extend:**
- `services/harness_eval.py` (existing harness eval — not replaced, extended)
- `bin/hook-session-stop.py` (peer trace session end capture)
- `schema.sql` (9 new tables)
- `aios-ui/app/**` (eval panels on runs, projects, command center)
- `config/agent-eval/` (ablation policies, eval schemas)
- `docs/evals/` (benchmark eval architecture, context profiles, templates from Phase 10)

**Expected Outputs:**
- Durable eval run record infrastructure
- Second brain lift measurement
- Shadow branch paired comparison
- Feature ablation scorecard
- Peer passive trace + shadow candidate queue
- Automated peer shadow benchmark pipeline
- Portable context packets
- External benchmark adapters
- Eval UI panels on existing operator surfaces

**Progress:**
- Plan 11-01 complete: durable eval task/run/score/failure/gold-set tables, `services.eval_run_service`, `aios eval` record/list/summary commands, and focused service/CLI contract tests are in place.
- Plan 11-02 complete: second-brain retrieval logging, retrieval metrics, deterministic gold-set context evaluation, Second Brain Lift computation, four second-brain ablation policies, and focused service/CLI tests are in place.
- Plan 11-03 complete: isolated shadow branch worktrees, contamination checks, diff/test deltas, Shadow Branch Delta scoring, and shadow CLI commands are in place.
- Plan 11-04 complete: feature ablation policies, ablation run execution, score comparison, and ablation CLI commands are in place.
- Plan 11-05 complete: observation-only peer trace capture, redacted trace metadata, shadow candidate scoring, and peer/shadow queue CLI surfaces are in place.
- Plan 11-06 complete: approval-gated automated shadow benchmark state transitions, contamination blocking, report creation, backlog follow-up creation, and shadow automation CLI commands are in place.
- Plan 11-07 complete: portable context packet generation, external benchmark adapters, external clean-room normalization, eval UI panels, and packet/benchmark CLI commands are in place.

**Dependencies:**
- Phase 10 (Plans 07–08): Agent eval foundation docs, templates, schemas, AGENTS.md rules

**Observable Success Criteria:**
- Every major AIOS run has a declared context profile and a durable EvalRun record.
- Second Brain Lift is measurable for any task with a full-second-brain run and a repo-only run.
- Shadow branch comparisons are reproducible from the same start SHA without contaminating the baseline branch.
- Ablation runner proves at least 3 features create measurable lift across the test suite.
- At least 3 peer passive trace sessions complete without harming peer workflow (no prompt mutation, no repo writes).
- At least 3 peer shadow candidates move through the full automation pipeline to COMPARISON_REPORT_CREATED.
- Portable context packets can be generated for any eval task without including personal notes, secrets, or vault content.
- External harness results normalize to EvalRun rows with external_clean_room context profile.

### Milestone 7: Graph-Native Memory Architecture

This milestone upgrades the AIOS memory layer from grep and flat semantic search into a four-layer structured system: raw source, normalized facts, graph relationships, and model-readable compiled briefing packets. It also hardens the context compiler for stable-prefix prompt caching and documents the future path to KV-cache-aware local serving.

#### Phase 12: Graph-Native Memory Architecture And Cache-Aware Context Compilation

**Goal:** Implement a production-ready layered memory model, a memory compiler that produces model-readable briefing packets, a cache-aware context compiler, a formal memory packet contract, retrieval quality checks, a memory backfill plan, and a future design note on KV-cache-aware local serving.

**Requirements:** MEM-01, MEM-02, MEM-03, MEM-04, MEM-05, MEM-06, MEM-07, MEM-08

**Detailed Scope:**
- Audit the current memory, retrieval, context-packing, and agent-briefing architecture
- Implement four memory layers: raw source (Layer A), normalized facts (Layer B), graph relationships (Layer C), and model-facing briefing packets (Layer D)
- Implement a MemoryCompiler that translates retrieved memory into readable markdown packets — never raw JSON
- Implement a ContextCompiler with stable-prefix-first ordering for API prompt cache compatibility
- Write a formal memory packet contract governing required/optional sections, provenance, staleness, contradictions, confidence, and token budget rules
- Add integration tests and a standalone validation script covering nine retrieval quality constraints
- Write a prioritized memory backfill plan identifying existing hotspots (truth files, PRDs, agent rules, skills, prompt libraries)
- Write a future design note on KV-cache-aware local runner as an optional optimization, not a core dependency
- Add the AIOS Memory Rule to `config/agent-rules.md`

**Current Surfaces To Evolve:**
- `schema.sql` (four new tables: memory_raw_sources, memory_facts, memory_relationships, memory_packet_receipts)
- `services/memory_layers.py` (new — composable layer modules)
- `services/memory_compiler.py` (new — Layer D compiler)
- `services/context_compiler.py` (new — cache-aware context assembly)
- `docs/audits/graph-native-memory-audit.md` (new)
- `docs/specs/memory-packet-contract.md` (new)
- `docs/backfills/graph-native-memory-backfill.md` (new)
- `docs/future/kv-cache-aware-local-runner.md` (new)
- `tests/memory/`, `tests/context/` (new test directories)
- `scripts/validate-memory-packets.py` (new)
- `config/agent-rules.md` (Rule 9 added)

**Expected Outputs:**
- Written memory architecture audit
- Four-layer memory schema in SQLite
- MemoryCompiler producing model-readable briefing packets
- ContextCompiler with deterministic stable-prefix ordering
- Memory packet contract spec
- Integration tests and validation script
- Prioritized backfill plan
- KV-cache future design note

**Dependencies:**
- Phase 2 (context packet compilation foundation)
- Phase 4 (project truth and knowledge layer)

**Observable Success Criteria:**
- AIOS has a documented memory architecture beyond grep/vector search
- Important memories can be represented as raw sources (Layer A), normalized facts (Layer B), and graph relationships (Layer C)
- Retrieved memory is compiled into model-readable briefing packets (Layer D) — never raw JSON
- Prompt/context layout separates stable cache-friendly memory from dynamic task context
- Stale, superseded, and contradictory memories are handled explicitly with validity_status markers
- Provenance is preserved in every model-facing packet
- Integration tests and validation script catch low-quality memory packets
- A prioritized backfill plan identifies existing memory hotspots for Layer B/C upgrade
- KV-cache-aware local serving is documented as a future optimization, not a required dependency

### Milestone 9: Code Quality Gates And Cross-Project Complexity Standards

This milestone adds algorithmic complexity and code simplification as mandatory quality gates across the AIOS agent workflow layer and all first-class linked projects. It produces agent rule additions, pre-check habits, a root quality gate specification, a local complexity pattern checklist, and backfill hotspot inventories for all seven projects in the portfolio. Remediation of discovered hotspots is a follow-on pass; this milestone establishes the gate, the documentation, and the first honest snapshot of where quality debts exist.

#### Phase 14: Code Quality Gates And Cross-Project Complexity Standards

**Goal:** Establish the Complexity + Simplification Gate as a mandatory agent workflow rule, create the quality gate documentation infrastructure, and produce observation-backed backfill inventories for every first-class project.

**Requirements:** QUAL-01, QUAL-02, QUAL-03, QUAL-04, QUAL-05, QUAL-06, QUAL-07, QUAL-08

**Detailed Scope:**
- Add Rule 10 (Complexity + Simplification Gate) to `config/agent-rules.md` with full trigger conditions, Gate A (complexity/performance), Gate B (simplification/maintainability), Gate C (verification), and record-before-fix policy
- Extend `AGENTS.md` with the gate section cross-referencing Rule 10
- Extend `~/.claude/CLAUDE.md` Quality Ladder with Step 5 (Complexity + Simplification Gate — Hard after large work)
- Create `docs/quality/implementation-pre-check.md` — 8 pre-check questions for during-implementation use
- Create `docs/quality/complexity-simplification-gate.md` — root gate specification (why, when, what, how, fix-vs-defer, Definition of Done)
- Create `docs/quality/complexity-checklist.md` — local 17-pattern algorithmic complexity checklist derived from codex-complexity-optimizer patterns; no external dependency
- Create `docs/backfill/complexity-simplification-backfill.md` — AIOS-specific backfill inventory
- Create backfill docs for all six linked projects: soundscape-app, portfolio, amos-saas, GitNexus, tm, Terrace
- Update AIOS backfill doc with Cross-Project Summary table linking all six external inventories

**Current Surfaces To Evolve:**
- `config/agent-rules.md` (Rule 10 added)
- `AGENTS.md` (gate section added)
- `~/.claude/CLAUDE.md` (Quality Ladder extended)
- `docs/quality/` (new directory with gate spec, checklist, pre-check)
- `docs/backfill/complexity-simplification-backfill.md` (new AIOS backfill)
- `~/projects/soundscape-app/docs/complexity-simplification-backfill.md` (new)
- `~/projects/portfolio/docs/complexity-simplification-backfill.md` (new)
- `~/projects/amos-saas/docs/complexity-simplification-backfill.md` (new)
- `~/projects/GitNexus/docs/complexity-simplification-backfill.md` (new)
- `~/projects/tm/docs/complexity-simplification-backfill.md` (new)
- `~/projects/Terrace/docs/complexity-simplification-backfill.md` (new)

**Expected Outputs:**
- Rule 10 in agent-rules.md
- Gate section in AGENTS.md
- Quality Ladder Step 5 in ~/.claude/CLAUDE.md
- Pre-check doc (docs/quality/implementation-pre-check.md)
- Root gate spec (docs/quality/complexity-simplification-gate.md)
- Complexity pattern checklist (docs/quality/complexity-checklist.md)
- AIOS backfill inventory
- Six external project backfill inventories
- Cross-project summary table

**Dependencies:**
- Additive — can run independently of Phase 6/7 infrastructure; findings will feed Phase 6/7 delta scoring once that infrastructure is ready
- Plan 10-08 (scripts/quality-eval.sh) must be complete to reference in gate docs

**Observable Success Criteria:**
- Rule 10 is in `config/agent-rules.md` and triggers after any large-work event.
- Gate sections are in `AGENTS.md` and `~/.claude/CLAUDE.md`.
- `docs/quality/` contains all three docs: gate spec, pre-check, complexity checklist.
- Every first-class project has a backfill doc with observation-backed findings or an honest "no major hotspots" statement.
- The backfill docs clearly distinguish "reported" from "fixed" — no silent remediations.
- The cross-project summary table in the AIOS backfill doc shows P0/P1/P2 counts for all six external projects.
- Quality commands (lint, typecheck, test) are run for each project and results recorded in the backfill doc.

### Milestone 8: Data Collection And Provider Extensibility

This milestone extends the AIOS data collection layer from a Claude/Codex-only ingestion pipeline into a formal, extensible provider system. It adds Cursor and Antigravity CLI as first-class local session providers so that all four tools contribute normalized, privacy-safe, provenance-backed session data to the operational database and second brain.

#### Phase 13: Multi-Provider Session Ingestion And Second Brain Data Pipeline

**Goal:** Extend the existing Claude/Codex session ingestion pipeline into a formal provider abstraction, then implement Cursor and Antigravity CLI as first-class providers with incremental sync, secret redaction, structured summarization, and governed writeback proposals.

**Requirements:** SESS-01, SESS-02, SESS-03, SESS-04, SESS-05, SESS-06, SESS-07, SESS-08

**Detailed Scope:**
- Audit the existing Claude/Codex ingestion pipeline (entry points, DB schema, dedup strategy, writeback flow, abstraction gaps)
- Introduce `SessionProvider` abstract interface with nine methods and a `NormalizedSession` model; wrap Claude and Codex as conforming providers without changing their behavior
- Implement Cursor provider: SQLite workspace DB discovery (read-only with temp-copy safety), ItemTable key inspection, agent-transcript JSONL parsing, workspace hash/path mapping, SQLite+JSONL deduplication
- Implement Antigravity provider: multi-path brain/session discovery, format detection, metadata-only handling for unknown binary files with health warning, reasoning trace pointer storage
- Add incremental sync with `session_provider_cursors` table; dry-run, backfill, and repair modes; idempotent upserts
- Add secret redaction running before any summary or writeback; configurable ignore patterns and retention policies; `redaction_incomplete` flag for sessions that cannot be safely redacted
- Generate 16-field structured session summaries; emit writeback proposals following the existing governed flow into `logs/summaries/` and `auto_ingest.sh`; detect skillification candidates across providers
- Write 12 acceptance-criteria tests with fixture data; write operator docs for all four providers and system overview; generate backfill report from live dry run

**Current Pipeline To Extend:**
- `bin/import_ai_history.py` (Claude/Codex parsing — not rewritten, wrapped)
- `bin/cron-ingest-codex.py` (Codex cron — not replaced, complemented)
- `bin/auto_ingest.sh` (Obsidian promotion — not changed, new providers plug into same flow)
- `aios.db:processed_files` (dedup table — complemented by `session_provider_cursors`)

**Expected Outputs:**
- `services/session_providers/` package with base class, Claude, Codex, Cursor, Antigravity implementations
- `services/session_redaction.py`, `services/session_summarizer.py`, `services/session_writeback.py`
- `bin/sessions.py` CLI, `bin/cron-ingest-sessions.py` cron wrapper
- `config/session-provider-config.yaml`
- DB migration: `session_provider_cursors` table
- `tests/test_session_providers.py`, `tests/fixtures/cursor/`, `tests/fixtures/antigravity/`
- `docs/session-providers/cursor.md`, `docs/session-providers/antigravity.md`, `docs/session-ingestion.md`
- `docs/backfills/session-provider-backfill.md`

**Dependencies:**
- Phase 4 (project truth and knowledge layer — for project association in NormalizedSession)
- Phase 5 (governed writeback — writeback proposals follow same approval flow)
- Phase 12 (memory architecture — ingested sessions populate Layer A raw sources)

**Observable Success Criteria:**
- Existing Claude/Codex ingestion behavior and tests are unchanged.
- Cursor sessions can be discovered and imported from local SQLite workspace databases and agent-transcript JSONL files.
- Antigravity sessions can be discovered and imported from brain/session directories; unknown binary files are skipped safely with a health warning.
- Sync is incremental and idempotent; two consecutive runs with no source changes produce identical DB state.
- Raw session content is stored in SQLite only; no raw transcripts or reasoning traces appear in curated vault notes.
- Secret redaction runs before any summary or writeback; sessions with redaction failures are held and surfaced in status.
- Session summaries follow the 16-field structure; writeback proposals are proposals, not automatic vault mutations.
- All 12 acceptance-criteria tests pass.
- Operator docs explain how to operate, debug, disable, and extend the provider system.

### Milestone 10: Agent Skill Portfolio Audit And External Library Integration

This milestone audits the local Claude Code skill portfolio against seven target skills from the mattpocock/skills external library, produces a structured merge/add/leave inventory, and delivers upgraded or new skill files. Two skills — `to-issues` and `handoff` — are wired into AIOS session/run infrastructure so that issue decompositions and session handoffs persist in `aios.db` rather than living only as ephemeral Markdown.

#### Phase 15: Agent Skill Portfolio Audit And External Library Integration

**Goal:** Audit local Claude Code skills against seven upstream targets, merge or add the valuable behaviors, and deliver agent-usable skill files with AIOS DB integration for `to-issues` and `handoff`.

**Requirements:** SKIL-01, SKIL-02, SKIL-03, SKIL-04, SKIL-05, SKIL-06, SKIL-07, SKIL-08

**Detailed Scope:**
- Audit all local Claude Code skill files across `~/.claude/skills/`, plugin namespaces, and project-level `.claude/` directories; produce a timestamped backup and a full inventory with overlap analysis and merge/add/leave decisions
- Upgrade `interrogate` skill with grill-with-docs behaviors: code-search-before-asking, codebase language challenge, CONTEXT.md glossary maintenance, ADR authorship discipline, canonical language sharpening, user-claim cross-check
- Add `diagnose` skill: fast feedback loop, reproduce-first discipline, ranked falsifiable hypotheses, one-hypothesis-at-a-time instrumentation, regression test seam authorship, debug artifact cleanup, postmortem, architecture handoff when bug exposes structural debt
- Upgrade `simplifier` skill with nine architecture lenses (deep/shallow modules, deletion test, interface as test surface, seams, adapters, locality, leverage, AI navigability) and mandatory report-first discipline for major refactors
- Add `to-issues` skill: vertical tracer-bullet slice decomposition, AFK/HITL labels, dependencies, acceptance criteria; backed by `services/issues_store.py` writing to `aios.db:issues` table with GitHub CLI opt-in and markdown fallback
- Add `prototype` skill: throwaway clearly-marked question-answering code, logic vs UI type selection, single-command run, no-persistence default, full state exposure, mandatory delete-or-absorb closeout
- Consolidate skill-authoring skills into one canonical `write-a-skill` skill: comparison matrix first, then single canonical file with progressive disclosure, trigger-rich description discipline, reference files, and script bundling
- Add `handoff` skill: compact focus-tailored cross-session continuation docs, saved outside workspace by default, suggested skills for next session, reference-not-duplicate discipline, secret redaction; backed by `services/handoff_store.py` writing to `aios.db:handoffs` table

**Current Surfaces To Evolve:**
- `~/.claude/skills/interrogate.md` (upgrade)
- `~/.claude/skills/diagnose.md` (create or merge into existing debugging skill)
- `~/.claude/skills/simplifier.md` (upgrade)
- `~/.claude/skills/to-issues.md` (create)
- `~/.claude/skills/prototype.md` (create)
- `~/.claude/skills/write-a-skill.md` (consolidate)
- `~/.claude/skills/handoff.md` (create)
- `~/AIOS/services/issues_store.py` (create)
- `~/AIOS/services/handoff_store.py` (create)
- `~/AIOS/data/aios.db` (issues and handoffs table migrations)
- `docs/phase-15-skill-inventory.md` (create)
- `docs/phase-15-skill-authoring-comparison.md` (create)

**Expected Outputs:**
- Timestamped backup of `~/.claude/skills/`
- Skill inventory with overlap analysis and merge decisions
- 7 upgraded or new skill files
- `issues_store.py` and `handoff_store.py` services
- `aios.db` issues and handoffs tables (idempotent migrations)
- Skill authoring comparison matrix
- Canonical `write-a-skill` skill

**Dependencies:**
- Phase 8 (asset lifecycle — skills wired into AIOS are aware of the registry model)
- Phase 13 (session ingestion — handoff_store writes session_id from the same session infrastructure)
- Additive to all phases: skills can be improved independently of AIOS runtime readiness

**Observable Success Criteria:**
- Backup of `~/.claude/skills/` exists before any modification.
- `docs/phase-15-skill-inventory.md` covers all seven upstream targets with merge/add/leave decisions and justifications.
- Each upgraded or new skill has a trigger-rich description that an agent would load without explicit invocation.
- `to-issues` writes to `aios.db:issues` and `handoff` writes to `aios.db:handoffs`; both fall back gracefully to markdown when the DB is unavailable.
- `issues` and `handoffs` table migrations are idempotent and do not break existing AIOS DB operations.
- No existing skill is deleted; merged skills retain a superseded-by header.
- The canonical `write-a-skill` skill is itself a good example of the principles it teaches.

### Milestone 11: Harness Determinism, Evidence, And Independent Verification

This milestone performs a cross-cutting integrity pass over the AIOS execution and evaluation harness. It borrows the strongest ideas from Case without creating a second harness: task state should be durable, phase transitions should be deterministic, evidence should be hard to fake, verification should be independent, context should be routed rather than dumped, retrospectives should become reviewable harness improvements, and model/agent selection should be inspectable.

#### Phase 16: Harness Determinism, Evidence, And Independent Verification

**Goal:** Audit the existing AIOS harness end to end, then implement targeted deltas that harden evidence, verifier gates, context routing, deterministic phase control, retrospective artifacts, model-selection instrumentation, and shadow-branch parity metadata.

**Requirements:** HARN-01, HARN-02, HARN-03, HARN-04, HARN-05, HARN-06, HARN-07, HARN-08

**Detailed Scope:**
- Produce an existing-harness audit mapping entrypoints, orchestration, lifecycle state, prompts/templates, model routing, context, second-brain usage, evaluation, evidence, recovery, shadow branches, retrospectives, docs, scripts, CI, and WIP areas
- Map current sources of truth for task objective, phase, owner/agent, context received, commands run, evidence produced, verification result, changed state, and future learning
- Compare AIOS lifecycle behavior against intake, context routing, planning, implementation, verification, review, closeout, and retrospective phases, then identify minimal deterministic patches
- Bind completion markers to durable evidence artifacts with command provenance, output paths/hashes, exit codes, parsed summaries, diff/commit hashes, status, and caveats
- Add independent verifier artifacts for implementation-bearing governed workflows, reviewing task spec, diff or changed files, and evidence before closeout
- Add context routing manifests that record loaded/skipped sources, reasons, second-brain availability, fallback behavior, context budget, and retrieval reasons
- Audit prompts/templates for duplicated instructions, stale rules, unclear boundaries, missing output schemas, and prompt-only state-machine responsibilities; move obvious gates into code/config where feasible
- Add structured retrospective artifacts, model-selection logs, and shadow parity metadata without silently mutating harness policy

**Current Surfaces To Evolve:**
- `bin/aios.py`
- `bin/aios-managed-run.py`
- `bin/aios_orchestration_runtime.py`
- `bin/hook-session-start.py`
- `bin/hook-prompt-submit.py`
- `bin/hook-post-tool-use.py`
- `bin/hook-stop.py`
- `services/workflow_orchestration.py`
- `services/task_routing.py`
- `services/invocation_backends.py`
- `services/success_criteria.py`
- `services/harness_eval.py`
- `services/standards_health.py`
- `services/workflow_learning.py`
- `services/execution_strategy.py`
- `services/shadow_branch_runner.py`
- `tools/context-compile.mjs`
- `config/workflows/registry.json`
- `prompts/registry.json`
- `schema.sql`
- `services/aios_cli.py`

**Expected Outputs:**
- Harness determinism audit report
- Evidence artifact persistence and closeout freshness validation
- Independent verifier artifact persistence and closeout gate
- Context routing manifest with second-brain fallback coverage
- Prompt/template boundary audit and targeted deterministic gate metadata
- Retrospective artifact schema and model-selection logging
- Shadow branch parity metadata and replay guidance

**Dependencies:**
- Phase 3 (run lifecycle and closeout semantics)
- Phase 6 (standards and evidence-backed evaluation)
- Phase 8 (workflow/prompt/skill contracts)
- Phase 9 (learning loop and governed proposals)
- Phase 11 (eval, ablation, and shadow-branch infrastructure)
- Phase 12 (context/memory routing and packet contract)

**Observable Success Criteria:**
- The audit identifies concrete AIOS components and files for every major harness concern before any implementation patch lands.
- Completion gates reject empty markers, stale evidence, and implementer-only "tests passed" claims for implementation-bearing governed workflows.
- Verifier artifacts are required or explicitly exempted before closeout, and verifier failures deterministically route to retry or human review.
- Context manifests can show with-second-brain and no-second-brain behavior without requiring peers to have the user's second brain.
- At least one prompt-only phase gate is moved into deterministic config/code, or the audit records why no safe minimal target exists.
- Retrospectives and model-selection records are queryable and reviewable; no major harness policy changes auto-apply.
- Shadow branch metadata can explain start SHA, condition, branch/worktree, comparison refs, parity checklist status, failure classification, and replay path.

### Milestone 12: Developer Experience Capability Pack

This milestone adds a measurable Developer Experience capability pack to AIOS. It adapts the strongest ideas from the `developer-experience` plugin without copying static agents or hardcoded model choices. The pack audits developer friction, improves onboarding and docs, reviews API/SDK/CLI ergonomics, performs contextual security review, invokes TypeScript expertise only when useful, routes spec-to-code work through a fidelity-preserving implementation mode, and records metrics and findings for future agents.

#### Phase 17: Developer Experience Capability Pack

**Goal:** Add a routed, measurable, context-aware Developer Experience capability pack with six capabilities, dynamic mode/model selection, second-brain parity, eval fixtures, and developer-first documentation.

**Requirements:** DXPK-01, DXPK-02, DXPK-03, DXPK-04, DXPK-05, DXPK-06, DXPK-07, DXPK-08

**Detailed Scope:**
- Audit current AIOS skills, agents, commands, routing rules, telemetry, eval specs, shadow-branch testing, second-brain integration, docs, generated concepts, quality gates, equivalents, duplication risks, conventions, and implementation seams
- Define DX optimizer, interface DX reviewer, documentation writer, security reviewer, TypeScript specialist, and spec-fidelity coder capabilities with purpose, responsibilities, triggers, modes, output schemas, assumptions policy, and evidence expectations
- Define measurable DX metrics for setup, clone-to-run, dev loop, validation commands, README quickstart, setup validation, ambiguous instructions, and agent/token cost where telemetry supports it
- Add capability routing metadata with compact audit, full audit, implementation, and review-only modes, plus dynamic reasoning/model metadata instead of fixed model-per-agent choices
- Support second-brain available and unavailable modes without making peer-run workflows depend on personal knowledge stores
- Integrate contextual security review, targeted TypeScript specialist routing, documentation style rules, and spec-fidelity implementation behavior without checklist bloat
- Add DX eval hooks and fixtures for poor onboarding repo, public CLI change, and TypeScript package boundary change
- Document pack usage, shadow-branch support, second-brain parity, metrics, routing, overrides, validation, and final implementation report format

**Current Surfaces To Evolve:**
- `config/workflows/registry.json`
- `config/workflows/skills.json`
- `prompts/registry.json`
- `config/execution-strategies/model-routing-policy.json`
- `services/workflow_orchestration.py`
- `services/execution_strategy.py`
- `services/harness_eval.py`
- `services/aios_cli.py`
- `config/agent-eval/**`
- `docs/audits/**`
- `docs/specs/**`
- `docs/evals/**`
- `docs/aios/**`

**Expected Outputs:**
- DX pack audit report
- Developer Experience pack contract
- Machine-readable capability metadata
- DX routing and mode-selection policy
- Dynamic model/reasoning metadata for DX task classes
- DX eval spec and three fixture scenarios
- Developer Experience pack documentation
- Validation and final report workflow

**Dependencies:**
- Phase 8 (asset/workflow lifecycle and registry conventions)
- Phase 14 (quality gate and simplification standards)
- Phase 15 (agent-facing skill portfolio integration patterns)
- Phase 16 (evidence, verifier, context manifest, and model-selection instrumentation)

**Observable Success Criteria:**
- The audit maps each desired DX capability to existing AIOS surfaces or a justified gap before implementation.
- Capability metadata is machine-readable and does not encode fixed model choices.
- DX metrics are measured when possible and honestly marked `not_measured` with measurement method when unavailable.
- Routing invokes TypeScript and security specialists only when justified by task context.
- Peer-run paths work without second-brain context.
- Evals cover poor onboarding, CLI change, and TypeScript package boundary scenarios.
- Documentation is concrete, developer-first, and avoids marketing language.

### Milestone 13: Meta-Learning Proposal Layer

This milestone adds a review-first meta-learning layer to AIOS. It adapts the strongest ideas from the `meta` plugin without copying the plugin shape: AIOS detects durable signals from user corrections, approvals, repeated commands, tool friction, context misses, model mismatch, and contradictions; scores and filters them; routes them to the right target layer; generates reversible proposals; separates auto-allow permission recommendations; and creates shadow-eval plans before durable promotion.

#### Phase 18: Meta-Learning Proposal Layer

**Goal:** Make AIOS self-improving but not self-mutating by adding session signal extraction, confidence scoring, quality filtering, target-layer routing, reviewable proposals, conflict resolution, auto-allow safety, shadow-eval plans, and a minimal meta CLI.

**Requirements:** META-01, META-02, META-03, META-04, META-05, META-06, META-07, META-08

**Detailed Scope:**
- Audit current instruction, skill, agent, command, memory, shadow-branch, session transcript, eval, model-routing, sub-agent, and preference/correction capture surfaces
- Extract normalized session signals from logs, transcript exports, or structured workflow traces
- Detect explicit corrections, repeated corrections, approvals, repeated manual commands, failed tool loops, context misses, model mismatches, contradictions, scope restatements, second-brain misses, and irrelevant context
- Score signals using weighted confidence, recency, explicit remember requests, multi-project evidence, project-specific scope, blast radius, security sensitivity, permission risk, and contradictions
- Filter out generic best practices, obvious framework rules, one-off preferences, contradictory weak signals, unsafe permission changes, and vague preferences
- Route accepted signals to global rules, project rules, skills, commands, agents, second-brain notes, eval/test cases, or observe-only with justification
- Generate reviewable proposals with rollback instructions and manual approval requirements
- Separate auto-allow permission recommendations from workflow-learning proposals with explicit risk scoring
- Generate shadow-branch eval plans for medium/high-impact proposals
- Expose minimal `aios meta` commands or equivalent script fallback
- Document routing, scoring, proposal format, auto-allow safety, and limitations

**Current Surfaces To Evolve:**
- `services/workflow_learning.py`
- `services/execution_strategy.py`
- `services/aios_cli.py`
- `services/harness_eval.py`
- `services/shadow_branch_runner.py`
- `schema.sql` only if the audit proves existing persistence is insufficient
- `data/meta-learning/**`
- `docs/audits/**`
- `docs/meta-learning/**`
- `tests/test_meta_learning_*.py`

**Expected Outputs:**
- Meta-learning audit report
- Session signal extractor
- Confidence scoring and quality filter
- Target-layer router
- Reviewable proposal generator
- Conflict resolver
- Auto-allow safety gate
- Shadow eval plan generator
- Minimal `aios meta` CLI
- Meta-learning docs and tests

**Dependencies:**
- Phase 9 (learning signal taxonomy and conservative improvement proposals)
- Phase 11 (shadow-branch eval and parity comparison)
- Phase 13 (session ingestion and transcript surfaces)
- Phase 16 (evidence, context manifests, verifier, model-selection instrumentation)
- Phase 17 (capability-pack routing patterns)

**Observable Success Criteria:**
- AIOS can analyze at least one session transcript or mock transcript.
- AIOS can detect explicit corrections and repeated patterns.
- AIOS can score signals and route them to target layers.
- AIOS can generate reviewable proposals and detect conflicts.
- Auto-allow recommendations are separated from ordinary learnings and dangerous actions are never auto-allowed by default.
- AIOS can produce a shadow-branch eval plan for meaningful proposals.
- Tests cover scoring, routing, conflict, proposal formatting, auto-allow risk, and shadow eval behavior.
- No core AIOS behavior is silently changed without a proposal.

### Milestone 14: Native Workflow Command Pack

This milestone adds AIOS-native workflow commands inspired by the essentials plugin without cloning it. The first command core is read-only: `zoom-out` for orientation, `handoff` for continuity, and `review squad` for multi-lane review. It then adds contextual `audit security`, guarded `cleanup de-slopify`, sandboxed `prototype`, lightweight command metadata logging, tests, and command documentation.

#### Phase 19: Native Workflow Command Pack

**Goal:** Implement a small, composable native command pack that improves context efficiency, continuity, review quality, security review, conservative cleanup, and sandboxed experimentation while preserving AIOS architecture and safety rules.

**Requirements:** CMDP-01, CMDP-02, CMDP-03, CMDP-04, CMDP-05, CMDP-06, CMDP-07, CMDP-08

**Detailed Scope:**
- Audit current command, skill, prompt, agent, workflow, CLI, sub-agent, model-routing, second-brain, and eval harness architecture
- Define command contracts, input/output schemas, safety classes, second-brain behavior, reviewer lane representation, validation gates, logging metadata, rollback expectations, and MVP order
- Implement read-only `aios zoom-out` for file, directory, and module orientation
- Implement `aios handoff` for compact continuation artifacts
- Implement read-only `aios review squad` with security, correctness, testing, architecture, maintainability, and project-alignment lanes
- Implement read-only `aios audit security` with strict and practical modes
- Implement guarded `aios cleanup de-slopify` that preserves behavior and applies only low-risk cleanup
- Implement sandboxed `aios prototype` for disposable experiments outside production code
- Add lightweight command metadata logging for eval and shadow comparison
- Add tests and docs for command registration, schemas, read-only guarantees, safety gates, and recommended workflows

**Current Surfaces To Evolve:**
- `services/aios_cli.py`
- `services/native_commands.py`
- `services/native_command_logging.py`
- `config/commands/native-workflow-commands.json`
- `docs/audits/aios-native-command-pack-audit.md`
- `docs/specs/native-workflow-command-contracts.md`
- `docs/aios/native-workflow-commands.md`
- `tests/test_native_commands.py`
- `tests/test_native_command_logging.py`
- `tests/test_aios_cli.py`

**Expected Outputs:**
- Native command pack audit
- Command contract and safety spec
- Machine-readable command metadata
- `aios zoom-out`
- `aios handoff`
- `aios review squad`
- `aios audit security`
- `aios cleanup de-slopify`
- `aios prototype`
- Local command metadata logging
- Tests and docs

**Dependencies:**
- Phase 15 (handoff skill and agent-facing command concepts)
- Phase 16 (evidence, verifier, context manifest, and command metadata patterns)
- Phase 17 (DX/security/docs capability semantics)
- Phase 18 (review-first proposal and safety patterns)

**Observable Success Criteria:**
- `zoom-out`, `handoff`, and `review squad` are read-only except for handoff writing to an established artifact location if configured.
- `squad-review` includes all six reviewer lanes and produces actionable severity-grouped findings.
- `audit security` supports strict and practical modes without generic checklist-only output.
- `de-slopify` refuses or flags risky structural changes and preserves public APIs unless explicitly approved.
- `prototype` writes only to allowed prototype locations and includes cleanup/promotion guidance.
- Command metadata is logged locally and is usable for future eval/shadow comparison.
- Tests cover registration, schemas, read-only behavior, required sections, reviewer lanes, safety refusals, prototype location restrictions, and security modes.

### Milestone 15: Execution-Symmetric Planning

This milestone makes AIOS and GSD planning execution-grade by construction. Plans are not lightweight prose; plans that guide execution are execution artifacts. They should inherit the relevant standards, risks, validation strategy, rollback concerns, delegation strategy, handoff requirements, and definition of done that execution will later require, while avoiding over-planning trivial work.

#### Phase 20: Execution-Symmetric Planning

**Goal:** Ensure AIOS-generated plans, GSD phase plans, slash-command-triggered plans, natural-language plans, generated implementation prompts, and audit-to-implementation prompts are directly usable by executors and shaped by relevant execution standards.

**Requirements:** ESPL-01, ESPL-02, ESPL-03, ESPL-04, ESPL-05, ESPL-06, ESPL-07, ESPL-08

**Detailed Scope:**
- Audit existing plan generation, GSD planning workflows, slash command handling, workflow routing, skill invocation, plan artifacts, validation strategy generation, and handoff formats
- Add Execution-Symmetric Planning as a core AIOS principle
- Define complexity-sensitive planning behavior for trivial, simple, moderate, complex, and high-risk tasks
- Recognize GSD workflow phases through a configurable phase registry
- Ensure `/gsdplanphase` and equivalents generate GSD-ready executor plans
- Add a planning lens registry mapping task types and workflow phases to execution standards
- Support review, validation, audit, and execution skills as planning lenses
- Update plan generation so non-trivial plans include mission, scope, constraints, assumptions, lenses, affected areas, ordered steps, validation, failure modes, rollback/recovery, delegation, escalation, and definition of done
- Add structured planning context and plan logs for evaluation
- Add tests/evals for natural-language planning, `/gsdplanphase`, explicit planning-lens requests, audit-to-implementation prompts, GSD handoff generation, simple task non-overplanning, and complex task planning

**Current Surfaces To Evolve:**
- `config/agent-rules.md`
- `config/planning/execution-symmetric-planning.json`
- `config/planning/gsd-workflow-phases.json`
- `config/planning/planning-lenses.json`
- `config/planning/skill-planning-lenses.json`
- `services/planning_workflow_detection.py`
- `services/planning_lenses.py`
- `services/planning_skill_lenses.py`
- `services/execution_symmetric_planner.py`
- `services/planning_context.py`
- `services/planning_log.py`
- `services/aios_cli.py`
- `docs/audits/aios-execution-symmetric-planning-audit.md`
- `docs/specs/execution-symmetric-planning.md`
- `docs/aios/execution-symmetric-planning.md`
- `docs/evals/execution-symmetric-planning-eval.md`
- `tests/test_planning_*.py`
- `tests/test_execution_symmetric_planner.py`

**Expected Outputs:**
- Planning-system audit
- Core planning principle and complexity contract
- GSD workflow phase registry
- Planning lens registry
- Skill-as-planning-lens registry
- Executor-ready plan generator
- Structured planning context and logs
- Documentation and evaluation coverage

**Dependencies:**
- Phase 1 (routing and workflow selection)
- Phase 2 (context/briefing compilation)
- Phase 8 (workflow contracts and stage metadata)
- Phase 16 (evidence, verifier, model-selection instrumentation)
- Phase 19 (native workflow command surfaces)

**Observable Success Criteria:**
- AIOS-generated plans reflect relevant execution standards.
- GSD planning phases produce executor-ready plans usable by implementation agents without major rewriting.
- Natural-language planning requests also benefit from automatic planning lenses.
- Slash commands remain supported as workflow hints and overrides.
- CLI-shaped internal routing is used only as structure, not as a replacement for GSD.
- Trivial/simple tasks are not over-planned.
- Plans include validation, risks, rollback, and definition of done when complexity warrants them.
- Plan logs can evaluate whether execution-symmetric planning reduces rework and clarification burden.

### Milestone 16: macOS Native App Skill Pack

This milestone adds a native macOS app development skill pack to AIOS by transforming the strongest production patterns from `fayazara/macos-app-skills` into AIOS/TMCP-compliant task skills. It preserves concrete command patterns and macOS domain knowledge while adding task-first routing, environment detection, permission gates, provenance, behavioral tests, validation, conflict detection, repair recommendations, and minimal context loading.

#### Phase 21: macOS Native App Skill Pack

**Goal:** Add an AIOS-native macOS platform skill pack covering project detection, build verification, native pattern modules, settings windows, Sparkle auto-updates, notch overlays, and dry-run-first release pipelines with TMCP routing, provenance, tests, and validation.

**Requirements:** MACS-01, MACS-02, MACS-03, MACS-04, MACS-05, MACS-06, MACS-07, MACS-08, MACS-09

**Detailed Scope:**
- Audit current AIOS skill, instruction, router, TMCP, manifest, validation, provenance, dependency-map, permission-gate, and behavioral-test conventions
- Audit `fayazara/macos-app-skills` and transform donor patterns into AIOS/TMCP task skills rather than copying donor files directly
- Add macOS project detection for native apps, Swift Packages, Xcode projects, Xcode workspaces, mixed apps, and not-applicable projects
- Add macOS build verification using workspace-first xcodebuild logic, scheme discovery, macOS destinations, signing-disabled local fallback, repair guidance, and post-fix rebuild
- Add a native macOS patterns router with small semantic modules for menu bar, windows/panels, screen geometry, keyboard shortcuts, file picker, pasteboard, drag/drop, navigation/inspector, launch/login, Quick Look/workspace, ScreenCaptureKit, and UserDefaults/AppStorage
- Add guarded settings window, Sparkle auto-update, and notch overlay skills with environment detection, permission gates, fallback behavior, and validation
- Add dry-run-first macOS release pipeline skill with hard approval gates for git, GitHub release, appcast, signing, notarization, publishing, and version/build changes
- Add TMCP routes, strict node IDs, manifests, provenance, dependency maps, related modules, behavioral tests, and validation command
- Add docs and final report workflow covering adopted, changed, rejected, and risky donor patterns

**Current Surfaces To Evolve:**
- `skills/macos/**`
- `config/tmcp/macos-skills-router.json`
- `config/skills/macos-manifest.json`
- `docs/audits/aios-skill-system-macos-pack-audit.md`
- `docs/audits/macos-app-skills-audit.md`
- `docs/skills/macos-dependency-map.md`
- `docs/skills/macos-native-app-skill-pack.md`
- `docs/skills/platform-skill-pack-pattern.md`
- `tests/skills/macos/**`
- `scripts/validate-skills.sh`

**Expected Outputs:**
- AIOS skill-system audit for macOS pack conventions
- Donor repository audit
- macOS project detection skill
- macOS build verification skill
- Native macOS pattern router and semantic modules
- Settings window skill
- Sparkle auto-update skill
- Notch overlay skill
- macOS release pipeline skill
- TMCP routing and manifest/provenance files
- Behavioral tests and validation command
- Documentation and final report workflow

**Dependencies:**
- Phase 15 (general skill portfolio and external skill integration patterns)
- Phase 17 (capability-pack routing patterns)
- Phase 19 (native command safety/logging patterns)
- Phase 20 (skill-as-planning-lens and execution-symmetric planning)

**Observable Success Criteria:**
- Donor repo audit records what was adopted, changed, rejected, and why.
- macOS skills use task-first triggers, anti-triggers, permission gates, provenance, and validation commands.
- Broad macOS knowledge is split into semantic modules and not loaded by default.
- Release, Sparkle, signing, notarization, appcast, dependency, and Info.plist mutations require explicit approval where specified.
- Behavioral tests cover routing, permission gates, validation steps, and repair recommendations.
- Validation checks unique IDs, TMCP pointer resolution, provenance, permission gates, private-key patterns, broad triggers, and release publish gates.

## Phase Dependency Chain

| Phase | Depends On | Unlocks |
|---|---|---|
| Phase 1 | project inventory, workflow registry, prompt registry | route contract, workflow launch discipline |
| Phase 2 | Phase 1 | packet contract, grounded query in preflight, handoff generation |
| Phase 3 | Phases 1-2 | durable execution, resume semantics, governed closeout |
| Phase 4 | Phases 2-3 | truth freshness, linked knowledge, grounded operator answers |
| Phase 5 | Phases 3-4 | governed writebacks, approval state, safe improvement |
| Phase 6 | Phases 3-5 | explicit standards-aware execution and durable evaluation |
| Phase 7 | Phases 4-6 | actionable health and standards-gap remediation |
| Phase 8 | Phases 1-7 | governed asset and workflow library |
| Phase 9 | Phases 6-8 | conservative self-improvement and workflow comparison |
| Phase 10 | Phases 1-9 | default operating layer behavior |
| Phase 11 | Phase 10 (Plans 07-08) | measurable lift evidence, shadow benchmarks, peer eval, external comparability |
| Phase 12 | Phases 2, 4 | layered memory model, memory compiler, cache-aware context compiler, packet contract |
| Phase 13 | Phases 4, 5, 12 | normalized session data from all four providers feeding Layer A raw sources |
| Phase 14 | Plan 10-08 (quality-eval.sh) | mandatory complexity+simplification gate in all agent workflows; cross-project backfill inventories; hotspot findings feeding Phase 6/7 delta scoring |
| Phase 15 | Phases 8, 13 | upgraded agent skill portfolio; AIOS-backed issue decomposition and session handoff persistence |
| Phase 16 | Phases 3, 6, 8, 9, 11, 12 | integrated harness determinism, hard evidence gates, independent verification, context manifests, retrospectives, model-selection logs, and shadow parity metadata |
| Phase 17 | Phases 8, 14, 15, 16 | measurable Developer Experience capability pack with routed DX, interface, docs, security, TypeScript, and spec-fidelity modes |
| Phase 18 | Phases 9, 11, 13, 16, 17 | review-first meta-learning proposals, session signal extraction, confidence scoring, target-layer routing, auto-allow safety, and shadow-eval plans |
| Phase 19 | Phases 15, 16, 17, 18 | native AIOS workflow commands for orientation, handoff, squad review, security audit, guarded cleanup, prototype, and command eval logging |
| Phase 20 | Phases 1, 2, 8, 16, 19 | execution-symmetric plan generation, GSD-ready planning, planning lenses, skill-as-planning-lens behavior, and plan-quality evals |
| Phase 21 | Phases 15, 17, 19, 20 | AIOS/TMCP-native macOS app skill pack with task routing, provenance, behavioral tests, validation, and guarded release workflows |
| Phase 22 | Phase 21 | progressive governance gates across planning, execution, review, validation, and completion; tier-one standards intake, audit, coverage, and backfill workflows |

## Requirement Coverage

| Phase | Requirements | Count |
|-------|--------------|-------|
| Phase 1 | ROUT-01, ROUT-02, ROUT-03, ROUT-04 | 4 |
| Phase 2 | CONT-01, CONT-02, CONT-03, CONT-04 | 4 |
| Phase 3 | RUN-01, RUN-02, RUN-03, RUN-04 | 4 |
| Phase 4 | TRUTH-01, TRUTH-02, TRUTH-03, TRUTH-04 | 4 |
| Phase 5 | GOV-01, GOV-02, GOV-03, GOV-04 | 4 |
| Phase 6 | STND-01, STND-02, STND-03, STND-04 | 4 |
| Phase 7 | DELT-01, DELT-02, DELT-03, DELT-04 | 4 |
| Phase 8 | ASSET-01, ASSET-02, ASSET-03, ASSET-04, WFLO-01, WFLO-02, WFLO-03, WFLO-04 | 8 |
| Phase 9 | LEARN-01, LEARN-02, LEARN-03, LEARN-04 | 4 |
| Phase 10 | OPER-01, OPER-02, OPER-03, OPER-04 | 4 |
| Phase 11 | EVAL-01, EVAL-02, EVAL-03, EVAL-04, EVAL-05, EVAL-06, EVAL-07, EVAL-08 | 8 |
| Phase 12 | MEM-01, MEM-02, MEM-03, MEM-04, MEM-05, MEM-06, MEM-07, MEM-08 | 8 |
| Phase 13 | SESS-01, SESS-02, SESS-03, SESS-04, SESS-05, SESS-06, SESS-07, SESS-08 | 8 |
| Phase 14 | QUAL-01, QUAL-02, QUAL-03, QUAL-04, QUAL-05, QUAL-06, QUAL-07, QUAL-08 | 8 |
| Phase 15 | SKIL-01, SKIL-02, SKIL-03, SKIL-04, SKIL-05, SKIL-06, SKIL-07, SKIL-08 | 8 |
| Phase 16 | HARN-01, HARN-02, HARN-03, HARN-04, HARN-05, HARN-06, HARN-07, HARN-08 | 8 |
| Phase 17 | DXPK-01, DXPK-02, DXPK-03, DXPK-04, DXPK-05, DXPK-06, DXPK-07, DXPK-08 | 8 |
| Phase 18 | META-01, META-02, META-03, META-04, META-05, META-06, META-07, META-08 | 8 |
| Phase 19 | CMDP-01, CMDP-02, CMDP-03, CMDP-04, CMDP-05, CMDP-06, CMDP-07, CMDP-08 | 8 |
| Phase 20 | ESPL-01, ESPL-02, ESPL-03, ESPL-04, ESPL-05, ESPL-06, ESPL-07, ESPL-08 | 8 |
| Phase 21 | MACS-01, MACS-02, MACS-03, MACS-04, MACS-05, MACS-06, MACS-07, MACS-08, MACS-09 | 9 |
| Phase 22 | TBD | 0 |

**Coverage Validation:**
- v1 requirements: 133 (124 prior + 9 MACS)
- Mapped to phases: 133
- Unmapped: 0
- Multi-mapped: 0

### Phase 22: Progressive governance and standards backfill workflows

**Goal:** [To be planned]
**Requirements**: TBD
**Depends on:** Phase 21
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd-plan-phase 22 to break down)

---
*Last updated: 2026-06-22 after adding Phase 22 progressive governance and standards backfill workflows*
