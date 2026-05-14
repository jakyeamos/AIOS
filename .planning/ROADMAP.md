# AIOS Roadmap

**Planning Date:** 2026-05-13
**Scope:** v1 is the full operating-system vision, delivered through sequenced milestones and phases rather than scope cuts.
**Source Inputs:** [PROJECT.md](/Users/jakyeamos/AIOS/.planning/PROJECT.md), [REQUIREMENTS.md](/Users/jakyeamos/AIOS/.planning/REQUIREMENTS.md), [research/SUMMARY.md](/Users/jakyeamos/AIOS/.planning/research/SUMMARY.md)

## Sequencing Logic

The roadmap follows the research bias and requirement dependencies:

1. Establish deterministic entry into the system: project selection, task classification, context compilation, and resumable run state.
2. Make truth freshness, governed writeback, and evidence capture mandatory before expanding broader quality intelligence.
3. Layer standards evaluation and delta scoring on top of trustworthy runtime evidence and governed project memory.
4. Use reviewed evidence to improve reusable assets and conservative learning loops.
5. Expand operator-facing surfaces after the control plane, governance, and evidence model are trustworthy enough to expose as the default operating layer.

## Milestones

### Milestone 1: Governed Entry Loop

#### Phase 1: Project And Intent Routing

**Goal:** Turn vague goals into an explicit project target, workflow route, and recommended agent/harness plus prompt/handoff family with inspectable reasoning.

**Requirements:** ROUT-01, ROUT-02, ROUT-03, ROUT-04

**Observable Success Criteria:**
- A vague-goal submission either resolves to one target project or blocks for explicit clarification with the ambiguity surfaced.
- The selected workflow is the smallest sufficient option for the task type and is persisted as structured run context.
- Route selection exposes why the chosen workflow beat nearby alternatives.
- The recommended agent or harness is attached to the route with rationale tied to task type and workflow constraints.
- The route also identifies the appropriate prompt or handoff family so execution starts from a proven instruction shape rather than an empty shell.

#### Phase 2: Context Compilation And Briefing

**Goal:** Compile the smallest sufficient task packet and make context inclusion, exclusion, prompt/handoff assets, and gaps inspectable before execution.

**Requirements:** CONT-01, CONT-02, CONT-03, CONT-04

**Observable Success Criteria:**
- Packet compilation pulls from project truth, standards, packets, prompt assets, and recent evidence without unrelated context spill.
- Each run stores a durable receipt showing loaded and skipped context with explicit reasons.
- Missing, stale, or conflicting context blocks or warns before execution continues.
- The final packet is agent-ready and includes objective, constraints, relevant files, workflow steps, prompt/handoff instructions, and acceptance criteria.

#### Phase 3: Workflow Execution And Run State

**Goal:** Make serious workflow execution durable, resumable, approval-aware, and inspectable from start through closeout.

**Requirements:** RUN-01, RUN-02, RUN-03, RUN-04

**Observable Success Criteria:**
- Runs move through explicit lifecycle states without collapsing blocked, approval-gated, partial, and completed outcomes.
- Runs, invocations, sessions, artifacts, and lifecycle events remain durably linked for each serious execution.
- A partially completed run can be resumed with its original packet, current state, and next recommended action intact.
- Run closeout shows what changed, what checks ran, what approvals were involved, and what remains unresolved.

### Milestone 2: Truth, Governance, And Evidence

#### Phase 4: Project Truth And Knowledge Grounding

**Goal:** Maintain current project truth and linked operational knowledge as mandatory operating surfaces rather than best-effort documentation byproducts.

**Requirements:** TRUTH-01, TRUTH-02, TRUTH-03, TRUTH-04

**Observable Success Criteria:**
- Each major linked project has one canonical truth surface or equivalent structured authority.
- Truth records stay current on goals, architecture, risks, completed work, unresolved deltas, decisions, and recommended next actions.
- AIOS can answer what is being built, what changed, what remains unresolved, and which prior decisions or reusable assets are relevant before manual assembly.
- Truth entries, decisions, notes, prompts, skills, and workflow artifacts are linked through searchable knowledge objects.

#### Phase 5: Governed Writeback And Approval Control

**Goal:** Make writebacks, approvals, and unresolved follow-up durable parts of every meaningful run.

**Requirements:** GOV-01, GOV-02, GOV-03, GOV-04

**Observable Success Criteria:**
- Truth, prompt, skill, workflow, standard, and packet changes are emitted as reviewable writeback proposals rather than silent mutation.
- Approval gates are enforced for important truth changes, policy changes, asset promotion, workflow behavior changes, and destructive actions.
- Every meaningful run ends with durable writeback, follow-up, or no-learning evidence.
- Unresolved risks, pending approvals, and follow-up actions are recorded at governed workflow closeout.

### Milestone 3: Standards And Health Intelligence

#### Phase 6: Standards Resolution And Evidence-Based Evaluation

**Goal:** Bind execution to explicit standards and preserve evidence-backed evaluation outcomes.

**Requirements:** STND-01, STND-02, STND-03, STND-04

**Observable Success Criteria:**
- Each task resolves to the correct success criteria and standards set before execution begins.
- Completed work is evaluated against explicit criteria rather than generic model judgment.
- Execution-first verification is enforced for stateful, cross-system, and core-logic changes.
- Findings, blockers, warnings, passes, and accepted tradeoffs are stored durably per run.

#### Phase 7: Delta Scoring And Health Backfill

**Goal:** Turn evaluation and truth evidence into explainable project-health and standards-gap scoring.

**Requirements:** DELT-01, DELT-02, DELT-03, DELT-04

**Observable Success Criteria:**
- AIOS produces domain-level alignment scores across architecture, testing, maintainability, security, UX, observability, documentation, launch readiness, agent-readiness, and standards compliance.
- Each score shows evidence, confidence, freshness, and remediation guidance.
- Health views distinguish confirmed, inferred, missing, and contradictory signals instead of collapsing them into one status.
- The system can prioritize a backfill path for the highest-value standards or capability gaps.

### Milestone 4: Reusable Improvement Loops

#### Phase 8: Prompt, Skill, And Workflow Asset Lifecycle

**Goal:** Treat reusable prompts, skills, and workflows as governed assets with evidence-backed applicability.

**Requirements:** ASSET-01, ASSET-02, ASSET-03, ASSET-04

**Observable Success Criteria:**
- Prompts, skills, and workflows are tracked with purpose, applicability, status, and usefulness evidence.
- Asset lifecycle states distinguish draft, candidate, approved, active, and deprecated artifacts.
- Reusable assets are linked to the workflows and task types where they succeeded or failed.
- Packet generation and handoff creation can recommend proven reusable assets.

#### Phase 9: Continuous Learning And Conservative Optimization

**Goal:** Improve routing, packet selection, and evaluation from reviewed evidence without silent policy drift.

**Requirements:** LEARN-01, LEARN-02, LEARN-03, LEARN-04

**Observable Success Criteria:**
- Run evidence is captured in a form that can inform future prompt, skill, workflow, and packet improvements.
- Cross-run analysis can identify recurring failure modes, ignored rules, bloated packets, and weak workflows.
- Proposed improvements to routing, context selection, and evaluation are conservative and grounded in reviewed outcomes.
- Operator-visible compounding shows what each meaningful run improved for future work.

### Milestone 5: Default Operating Layer

#### Phase 10: Operator Surfaces And Daily-Flow Visibility

**Goal:** Expose the governed operating loop through operator surfaces only after routing, truth, evidence, reusable asset selection, and learning are trustworthy.

**Requirements:** OPER-01, OPER-02, OPER-03, OPER-04

**Observable Success Criteria:**
- Operator views are searchable and inspectable across projects, runs, workflows, knowledge, prompts, deltas, approvals, and recent changes.
- The system can answer which project needs attention, what good looks like, which workflow should run, which prompt/skill assets apply, and which context an agent needs before manual prep.
- Visible metrics and recommendations drill down into receipts, routing decisions, evidence trails, and remediation paths.
- The end-to-end daily flow is visible from vague goal through routing, execution, evaluation, writeback, and unresolved deltas.

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
| Phase 8 | ASSET-01, ASSET-02, ASSET-03, ASSET-04 | 4 |
| Phase 9 | LEARN-01, LEARN-02, LEARN-03, LEARN-04 | 4 |
| Phase 10 | OPER-01, OPER-02, OPER-03, OPER-04 | 4 |

**Coverage Validation:**
- v1 requirements: 40
- Mapped to phases: 40
- Unmapped: 0
- Multi-mapped: 0

---
*Last updated: 2026-05-13 during roadmap creation*
