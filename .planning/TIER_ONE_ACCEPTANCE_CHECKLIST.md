# Tier-One Acceptance Checklist

**Created:** 2026-05-14  
**Purpose:** Define what each roadmap phase must prove before AIOS can claim tier-one progress toward default operating-layer readiness.

## How To Use This Checklist

- A phase is not complete because code changed. It is complete when the acceptance evidence below exists.
- “Tier-one” means trustworthy enough to become part of the default operating loop, not merely present in the codebase.
- The checklist is stricter than the roadmap summary. It focuses on exit gates and demonstration quality.

## Phase 1: Project, Workflow, And Prompt Routing

### Capability Gates

- [ ] AIOS can resolve a vague goal to one target project or explicitly block on ambiguity.
- [ ] AIOS can classify task family separately from workflow choice.
- [ ] AIOS can select the smallest sufficient governed workflow for representative serious-work tasks.
- [ ] AIOS can explain why the selected workflow beat nearby alternatives.
- [ ] AIOS can recommend a prompt or handoff family as part of the route.
- [ ] AIOS can recommend an execution surface tied to workflow constraints.
- [ ] Route decisions persist in a durable record for downstream packet and run consumers.

### Evidence Gates

- [ ] Representative route fixtures exist for exact-match, ambiguous, unsupported, and cross-project cases.
- [ ] Route records expose project candidate set, rationale, chosen workflow, prompt family, and harness recommendation.
- [ ] Route audits prove that unsafe project guesses are blocked.

### Failure Conditions

- [ ] No silent project guesses across plausible alternatives.
- [ ] No serious route proceeds without workflow and prompt-family selection.
- [ ] No route logic is explainable only from code reading; rationale is queryable at runtime.

## Phase 2: Context, Query, And Briefing Compilation

### Capability Gates

- [ ] AIOS can compile a task-specific packet from truth, standards, packets, prompt assets, repo context, and recent evidence.
- [ ] AIOS records loaded and skipped context with reasons in a durable receipt.
- [ ] AIOS surfaces stale, missing, or conflicting context before execution continues.
- [ ] AIOS can generate an agent-ready briefing packet with objective, constraints, files, workflow steps, prompt instructions, checks, and acceptance criteria.
- [ ] Packet outputs are linked back to Phase 1 route identity.

### Evidence Gates

- [ ] Packet fixtures exist for audit, implementation, debugging, and truth-update tasks.
- [ ] Receipt records can be retrieved by packet id and run id.
- [ ] Packet audits show that irrelevant context is excluded, not only that relevant context is included.

### Failure Conditions

- [ ] No packet dumps broad vault or repo context without task justification.
- [ ] No serious run begins with missing/stale/conflicting context hidden from the operator.
- [ ] No handoff packet omits prompt/handoff instructions or acceptance criteria.

## Phase 3: Workflow Execution And Run State

### Capability Gates

- [ ] Serious runs use explicit lifecycle states rather than heuristic completion guesses.
- [ ] Runs, invocations, sessions, artifacts, and lifecycle events remain durably linked.
- [ ] Partially completed runs can resume with original packet identity and next action intact.
- [ ] Run closeout reports changed artifacts, checks run, approvals touched, and unresolved work.
- [ ] Default serious-work workflows have durable stage-aware execution semantics.

### Evidence Gates

- [ ] Lifecycle audits show zero unsupported terminal states for governed workflows.
- [ ] Resume fixtures prove blocked and partial runs can continue safely.
- [ ] Closeout records exist for representative implementation and recovery runs.

### Failure Conditions

- [ ] No authoritative run may remain in an ambiguous “ready but really done” state.
- [ ] No terminal run may disappear without closeout evidence.
- [ ] No resume path may lose packet identity, approval state, or current stage.

## Phase 4: Project Truth, Knowledge, And Grounded Query

### Capability Gates

- [ ] Every major linked project has a canonical truth authority.
- [ ] Truth captures goals, architecture, risks, completed work, unresolved deltas, decisions, and next actions.
- [ ] AIOS can answer default-layer questions from truth plus knowledge before manual assembly.
- [ ] Truth, prompts, skills, workflows, decisions, and notes are linked as searchable knowledge objects.
- [ ] Grounded query results cite or clearly point to their sources.

### Evidence Gates

- [ ] Canonical truth inventory exists for major linked projects.
- [ ] Grounded query examples answer “what are we building,” “what changed,” and “what remains unresolved.”
- [ ] Knowledge linking is inspectable through backlinks, references, or equivalent object relations.

### Failure Conditions

- [ ] No major project depends on scattered notes without one canonical truth surface.
- [ ] No grounded answer may overclaim beyond available truth/evidence.
- [ ] No knowledge surface may behave like a dump without inspectable linkage.

## Phase 5: Governed Writeback And Approval Control

### Capability Gates

- [ ] AIOS emits reviewable writeback proposals for important truth and asset changes.
- [ ] AIOS enforces approval gates for high-impact mutations and destructive actions.
- [ ] Every meaningful run ends with writeback, follow-up, or explicit no-learning evidence.
- [ ] Unresolved risks and pending approvals are durably stored at workflow closeout.
- [ ] Truth updates are clearly distinguished from proposed truth updates.

### Evidence Gates

- [ ] Proposal records exist for truth, prompt, skill, workflow, and standards-related changes.
- [ ] Approval audits prove gated changes cannot silently promote.
- [ ] Terminal run audits show no silent closeout drop-off.

### Failure Conditions

- [ ] No important system surface mutates silently after a serious run.
- [ ] No approval-sensitive change is treated as complete before review.
- [ ] No closeout may omit unresolved risk or follow-up state.

## Phase 6: Standards Resolution And Evidence-Based Evaluation

### Capability Gates

- [ ] AIOS resolves task-appropriate success criteria before execution.
- [ ] Outputs are evaluated against explicit criteria, not generic taste.
- [ ] Execution-first verification is enforced for stateful, cross-system, or core-logic changes.
- [ ] Evaluations preserve blockers, warnings, passes, and accepted tradeoffs durably.
- [ ] Workflow contracts bind the right validations to the right task types.

### Evidence Gates

- [ ] Preflight or startup artifacts show criteria resolution for representative tasks.
- [ ] Evaluation artifacts exist with blocker/warning/pass structure and file/task scope.
- [ ] Execution-first cases include proof of real-path execution.

### Failure Conditions

- [ ] No serious code change may be called complete on narrative confidence alone.
- [ ] No evaluation may collapse blockers and warnings into an undifferentiated score.
- [ ] No core workflow may bypass execution-first verification where required.

## Phase 7: Delta Scoring And Health Backfill

### Capability Gates

- [ ] AIOS can score project alignment across required quality dimensions.
- [ ] Each score is explainable with evidence, confidence, freshness, and remediation guidance.
- [ ] Health views distinguish confirmed, inferred, missing, and contradictory signals.
- [ ] AIOS can recommend a prioritized backfill path from the biggest gaps.
- [ ] Delta views are usable for project triage, not just observation.

### Evidence Gates

- [ ] Repeatable standards-health proofs exist for priority projects.
- [ ] Project health surfaces include drill-downable explanations.
- [ ] Backfill recommendations tie directly to evidence-backed gaps.

### Failure Conditions

- [ ] No score may appear without a drill-down path.
- [ ] No health state may overclaim certainty when evidence is inferred or missing.
- [ ] No backfill recommendation may be detached from concrete remediation work.

## Phase 8: Prompt, Skill, Workflow Contracts, And Asset Lifecycle

### Capability Gates

- [ ] Prompts, skills, and workflows are lifecycle-managed assets.
- [ ] Asset states distinguish draft, candidate, approved, active, and deprecated.
- [ ] Assets are linked to the workflows and task types where they succeeded or failed.
- [ ] AIOS recommends proven assets during routing and packet generation.
- [ ] Governed workflows are explicit stage-based contracts with bound inputs, validations, approvals, artifacts, and writebacks.
- [ ] Workflow success is measurable at stage and run level.

### Evidence Gates

- [ ] Asset records include purpose, applicability, status, and evidence of usefulness.
- [ ] Workflow contracts exist for current default serious-work workflows.
- [ ] Workflow comparison records exist for promotion/revision/deprecation decisions.

### Failure Conditions

- [ ] No reusable prompt/skill/workflow remains a free-floating text blob with no lifecycle status.
- [ ] No workflow used for serious work lacks an explicit stage contract.
- [ ] No asset promotion occurs without evidence and governance.

## Phase 9: Continuous Learning And Conservative Optimization

### Capability Gates

- [ ] Meaningful runs emit evidence that can improve routing, packets, prompts, workflows, or evaluation.
- [ ] AIOS can identify recurring failures, ignored rules, bloated packets, or weak workflows from accumulated evidence.
- [ ] AIOS proposes conservative improvements rather than silently changing behavior.
- [ ] AIOS makes compounding visible by showing what each run improved.
- [ ] Learning remains reviewable and governance-compatible.

### Evidence Gates

- [ ] Learning-event history is queryable and linked to runs.
- [ ] Recurring-pattern summaries exist for repeated failure or weak-output classes.
- [ ] Improvement proposals exist for routing/context/evaluation with approval paths.

### Failure Conditions

- [ ] No learning loop may silently rewrite core policy or workflow behavior.
- [ ] No compounding claim may exist without durable before/after evidence.
- [ ] No experiment outcome may be treated as default behavior without review.

## Phase 10: Operator Surfaces, Query, And Daily-Flow Visibility

### Capability Gates

- [ ] Operator surfaces expose projects, runs, workflows, prompts, approvals, knowledge, health, and recent changes.
- [ ] AIOS can answer what needs attention, what good looks like, what workflow to run, and what context/assets apply.
- [ ] Receipts, route rationale, evaluations, and score explanations are drill-downable from summary views.
- [ ] The end-to-end default-layer daily flow is visible from vague goal through unresolved deltas.
- [ ] Operator surfaces favor trustworthy state over seeded/demo fallbacks.

### Evidence Gates

- [ ] The command center can demonstrate the full serious-work loop end to end.
- [ ] Queries can surface route, packet, run, evaluation, writeback, and delta evidence without manual DB inspection.
- [ ] Representative operator flows exist for implementation, audit, recovery, and truth-update work.

### Failure Conditions

- [ ] No polished surface may mask weak or missing backend truth.
- [ ] No key metric or recommendation may be non-explainable.
- [ ] No daily-flow claim may exist if routing, packets, run state, evaluation, or writeback are still disconnected.

## Program-Level Tier-One Readiness

AIOS should not claim “default operating layer” status until all of the following are true:

- [ ] A vague goal can enter through AIOS and receive correct routing, packet compilation, execution, evaluation, and writeback without manual orchestration.
- [ ] The result is safer and more deterministic than starting directly in a raw model chat for most serious work.
- [ ] Truth, approvals, and unresolved deltas remain visible after the run.
- [ ] Prompt, skill, and workflow assets improve through governed evidence rather than drift.
- [ ] The operator can inspect how and why AIOS made each major decision.

## Immediate Planning Implications

1. Phase completion should be reviewed against this checklist, not only roadmap prose.
2. Validation and audit commands should eventually map cleanly onto these acceptance gates.
3. Tier-one claims should be blocked when a phase has functionality but lacks the evidence gates listed here.

---
*Last updated: 2026-05-14*
