# Requirements: AIOS

**Defined:** 2026-05-13
**Core Value:** AIOS should compile messy human intent into the right context, standards, workflow, agent instructions, evaluation, artifacts, and memory updates with less manual babysitting than direct model use.

## v1 Requirements

### Project And Intent Routing

- [ ] **ROUT-01**: User can submit a vague goal and AIOS can identify the target project or explicitly surface ambiguity requiring clarification
- [ ] **ROUT-02**: AIOS can classify the requested task type and select the smallest sufficient workflow for it
- [ ] **ROUT-03**: AIOS can explain why a workflow route was selected over nearby alternatives
- [ ] **ROUT-04**: AIOS can identify the recommended agent or harness for the selected workflow and include the reasoning

### Context Compilation

- [ ] **CONT-01**: AIOS can compile a task-specific context packet from project truth, standards, packets, and recent evidence without dumping unrelated knowledge
- [ ] **CONT-02**: AIOS records loaded and skipped context with explicit reasons in a durable receipt
- [ ] **CONT-03**: AIOS can surface missing, stale, or conflicting context needed for a task before execution continues
- [ ] **CONT-04**: AIOS can produce an agent-ready briefing packet with task objective, constraints, relevant files, workflow steps, and acceptance criteria

### Truth And Knowledge

- [ ] **TRUTH-01**: AIOS maintains a canonical truth file or equivalent structured record for each major linked project
- [ ] **TRUTH-02**: Project truth captures current goals, architecture, active risks, completed work, unresolved deltas, important decisions, and recommended next actions
- [ ] **TRUTH-03**: AIOS can answer what is being built, what changed, and what remains unresolved from its knowledge surfaces before manual assembly
- [ ] **TRUTH-04**: AIOS can link truth entries, decisions, notes, prompts, skills, and workflow artifacts through searchable, inspectable knowledge objects

### Workflow Execution And Run State

- [ ] **RUN-01**: AIOS tracks explicit run lifecycle states including not started, in progress, blocked, failed, completed, needs approval, needs follow-up, and partially completed
- [ ] **RUN-02**: AIOS durably links runs, invocations, sessions, artifacts, and lifecycle events for every serious workflow execution
- [ ] **RUN-03**: AIOS can resume a partially completed workflow with the original context packet, current state, and next recommended action intact
- [ ] **RUN-04**: AIOS surfaces what changed during a run, what checks were executed, and what remains unresolved at closeout

### Standards And Evaluation

- [ ] **STND-01**: AIOS maps each task to the correct success criteria and standards set before execution
- [ ] **STND-02**: AIOS evaluates outputs against explicit quality criteria rather than generic model judgment
- [ ] **STND-03**: AIOS requires execution-first verification for stateful, cross-system, or core-logic changes
- [ ] **STND-04**: AIOS preserves durable evaluation findings, blockers, warnings, passes, and accepted tradeoffs for completed runs

### Delta Scoring And Health

- [ ] **DELT-01**: AIOS can score project alignment against expected standards across architecture, testing, maintainability, security, UX, observability, documentation, launch readiness, agent-readiness, and standards compliance
- [ ] **DELT-02**: AIOS explains each health or delta score with concrete evidence, confidence, freshness, and remediation guidance
- [ ] **DELT-03**: AIOS distinguishes confirmed, inferred, missing, and contradictory signals in project and capability health views
- [ ] **DELT-04**: AIOS can recommend a prioritized backfill path for the biggest standards or capability gaps in a project

### Governance And Writeback

- [ ] **GOV-01**: AIOS creates reviewable writeback proposals for project truth, prompts, skills, workflows, standards, and context packets instead of silently mutating them
- [ ] **GOV-02**: AIOS requires approval gates for important truth changes, global rule changes, skill/prompt promotion, workflow behavior changes, and destructive actions
- [ ] **GOV-03**: Every meaningful run leaves durable writeback, follow-up, or no-learning evidence so the system becomes more accurate over time
- [ ] **GOV-04**: AIOS records unresolved risks, pending approvals, and follow-up actions at the end of a governed workflow

### Prompt, Skill, And Workflow Assets

- [ ] **ASSET-01**: AIOS tracks prompts, skills, and workflows as lifecycle-managed assets with purpose, applicability, status, and evidence of usefulness
- [ ] **ASSET-02**: AIOS can distinguish draft, candidate, approved, active, and deprecated reusable assets
- [ ] **ASSET-03**: AIOS links reusable assets to the workflows and task types where they have succeeded or failed
- [ ] **ASSET-04**: AIOS can recommend proven prompts, skills, and workflows during packet generation and handoff creation

### Continuous Improvement

- [ ] **LEARN-01**: AIOS can capture run evidence that informs future prompt, skill, workflow, and packet improvements
- [ ] **LEARN-02**: AIOS can identify recurring failure modes, ignored rules, bloated packets, or weak workflows from accumulated evidence
- [ ] **LEARN-03**: AIOS can propose conservative improvements to routing, context selection, and evaluation based on reviewed outcomes
- [ ] **LEARN-04**: AIOS makes compounding visible by showing what each meaningful run improved for future work

### Operator Surfaces

- [ ] **OPER-01**: AIOS provides searchable, inspectable operator views for projects, runs, workflows, knowledge, prompts, deltas, approvals, and recent changes
- [ ] **OPER-02**: AIOS can answer which project needs attention, what good looks like, which workflow should run, and which context an agent needs before manual prep
- [ ] **OPER-03**: AIOS exposes receipts, routing decisions, evidence trails, and drill-down paths for visible metrics and recommendations
- [ ] **OPER-04**: AIOS can surface the default-layer daily flow end to end: vague goal -> routing -> execution -> evaluation -> writeback -> unresolved deltas

## v2 Requirements

None currently. The full operating-system vision is intentionally being planned into v1 and sequenced through milestones rather than deferred into a later release bucket.

## Out of Scope

| Feature | Reason |
|---------|--------|
| None currently | The project is intentionally planning the full target capability set as v1 and managing scope through roadmap sequencing instead of exclusions |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| ROUT-01 | Phase 1: Project And Intent Routing | Pending |
| ROUT-02 | Phase 1: Project And Intent Routing | Pending |
| ROUT-03 | Phase 1: Project And Intent Routing | Pending |
| ROUT-04 | Phase 1: Project And Intent Routing | Pending |
| CONT-01 | Phase 2: Context Compilation And Briefing | Pending |
| CONT-02 | Phase 2: Context Compilation And Briefing | Pending |
| CONT-03 | Phase 2: Context Compilation And Briefing | Pending |
| CONT-04 | Phase 2: Context Compilation And Briefing | Pending |
| TRUTH-01 | Phase 4: Project Truth And Knowledge Grounding | Pending |
| TRUTH-02 | Phase 4: Project Truth And Knowledge Grounding | Pending |
| TRUTH-03 | Phase 4: Project Truth And Knowledge Grounding | Pending |
| TRUTH-04 | Phase 4: Project Truth And Knowledge Grounding | Pending |
| RUN-01 | Phase 3: Workflow Execution And Run State | Pending |
| RUN-02 | Phase 3: Workflow Execution And Run State | Pending |
| RUN-03 | Phase 3: Workflow Execution And Run State | Pending |
| RUN-04 | Phase 3: Workflow Execution And Run State | Pending |
| STND-01 | Phase 6: Standards Resolution And Evidence-Based Evaluation | Pending |
| STND-02 | Phase 6: Standards Resolution And Evidence-Based Evaluation | Pending |
| STND-03 | Phase 6: Standards Resolution And Evidence-Based Evaluation | Pending |
| STND-04 | Phase 6: Standards Resolution And Evidence-Based Evaluation | Pending |
| DELT-01 | Phase 7: Delta Scoring And Health Backfill | Pending |
| DELT-02 | Phase 7: Delta Scoring And Health Backfill | Pending |
| DELT-03 | Phase 7: Delta Scoring And Health Backfill | Pending |
| DELT-04 | Phase 7: Delta Scoring And Health Backfill | Pending |
| GOV-01 | Phase 5: Governed Writeback And Approval Control | Pending |
| GOV-02 | Phase 5: Governed Writeback And Approval Control | Pending |
| GOV-03 | Phase 5: Governed Writeback And Approval Control | Pending |
| GOV-04 | Phase 5: Governed Writeback And Approval Control | Pending |
| ASSET-01 | Phase 8: Prompt, Skill, And Workflow Asset Lifecycle | Pending |
| ASSET-02 | Phase 8: Prompt, Skill, And Workflow Asset Lifecycle | Pending |
| ASSET-03 | Phase 8: Prompt, Skill, And Workflow Asset Lifecycle | Pending |
| ASSET-04 | Phase 8: Prompt, Skill, And Workflow Asset Lifecycle | Pending |
| LEARN-01 | Phase 9: Continuous Learning And Conservative Optimization | Pending |
| LEARN-02 | Phase 9: Continuous Learning And Conservative Optimization | Pending |
| LEARN-03 | Phase 9: Continuous Learning And Conservative Optimization | Pending |
| LEARN-04 | Phase 9: Continuous Learning And Conservative Optimization | Pending |
| OPER-01 | Phase 10: Operator Surfaces And Daily-Flow Visibility | Pending |
| OPER-02 | Phase 10: Operator Surfaces And Daily-Flow Visibility | Pending |
| OPER-03 | Phase 10: Operator Surfaces And Daily-Flow Visibility | Pending |
| OPER-04 | Phase 10: Operator Surfaces And Daily-Flow Visibility | Pending |

**Coverage:**
- v1 requirements: 40 total
- Mapped to phases: 40
- Unmapped: 0

---
*Requirements defined: 2026-05-13*
*Last updated: 2026-05-13 after roadmap traceability mapping*
