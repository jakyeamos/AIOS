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

**Coverage Validation:**
- v1 requirements: 44
- Mapped to phases: 44
- Unmapped: 0
- Multi-mapped: 0

---
*Last updated: 2026-05-14 after full roadmap expansion*
