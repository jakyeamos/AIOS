# AIOS

## What This Is

AIOS is a local-first, knowledge-aware agent operating system for AI-driven work. It acts as a second brain, orchestration layer, workflow harness, and quality-control system that turns vague goals into governed, context-rich, testable workflows, then learns from every run to improve future work.

The primary user is your agents. Over time, the project should become strong enough to open source, but its immediate purpose is to become the default operating layer you and your agents work through instead of manually assembling context, rules, workflows, and writebacks by hand.

## Core Value

AIOS should compile messy human intent into the right context, standards, workflow, agent instructions, evaluation, artifacts, and memory updates with less manual babysitting than direct model use.

## Requirements

### Validated

- ✓ Local-first control plane exists with Python operator entrypoints, SQLite-backed runtime state, and a Next.js operator UI — existing
- ✓ File-backed context compiler exists and can produce task-specific context packets and receipts from `aios/context/` — existing
- ✓ Success-criteria, capability-audit, lifecycle-audit, and invocation-audit primitives exist for governed execution and inspectable quality state — existing
- ✓ Durable workflow/orchestration concepts exist, including runs, invocations, events, knowledge surfaces, writebacks, and operator inspection routes — existing
- ✓ Brownfield codebase mapping now exists under `.planning/codebase/` to support GSD-driven planning and execution — existing

### Active

- [ ] AIOS reliably turns vague goals into the correct project selection, context packet, standards match, workflow route, and agent handoff without manual assembly
- [ ] AIOS becomes the default operating layer for serious project work by tracking explicit run state, evaluating outputs, updating truth files, and surfacing unresolved deltas and approvals
- [ ] AIOS maintains accurate, current project truth for every major linked project, including architecture, goals, risks, deltas, decisions, and recommended next actions
- [ ] AIOS provides explainable delta-from-expectation scoring across architecture, testing, maintainability, security, UX, observability, documentation, launch readiness, agent-readiness, and standards compliance
- [ ] AIOS manages prompts, skills, workflows, and evaluation criteria as governed lifecycle assets with evidence, approvals, and reusable writebacks
- [ ] AIOS continuously improves its prompts, skills, workflows, context packets, and agent-routing decisions from durable evidence gathered across runs
- [ ] AIOS exposes a searchable, inspectable knowledge UI that answers what is being built, what good looks like, what changed, what needs attention, and what should run next before manual context gathering

### Out of Scope

- None currently — the project is intentionally planning toward the full operating-system vision in sequenced milestones rather than trimming capability classes out of v1

## Context

- This is a brownfield repository with meaningful existing subsystems:
  - Python control-plane and hook/runtime entrypoints in `bin/` and `services/`
  - Next.js operator UI in `aios-ui/`
  - file-backed context compiler in `aios/context/` and `tools/context-compile.mjs`
  - SQLite schema authority in `schema.sql`
- The repo already contains strong partial implementations of the target system:
  - context compiler and receipts
  - orchestration runs/invocations/lifecycle audits
  - success criteria and capability truth
  - workflow learning and writeback proposals
  - knowledge object and grounded-query surfaces
- The strongest practical readiness test is an end-to-end daily flow:
  - start with a vague goal
  - AIOS selects project, context, standards, workflow, and agent handoff
  - execution runs with tracked state
  - AIOS evaluates the result
  - truth files and memory are updated
  - remaining deltas and approvals are surfaced
- Primary user is agentic workflows rather than casual dashboard browsing, so determinism, inspectability, and writeback accuracy matter more than UI polish alone
- The current codebase map in `.planning/codebase/` should be treated as reference material for planning, while `PROJECT.md`, context receipts, and the control-plane artifacts remain stronger truth surfaces
- The active v1 roadmap now extends through Phase 15, adding planned tracks for measurable eval/shadow workflows, graph-native memory, multi-provider session ingestion, cross-project complexity standards, and agent skill portfolio integration.
- The checked-in managed workflow report fixtures now reflect agent-rule-enriched invocation output from the current control-plane runtime.
- The repository now includes the standalone `research-domain-writing/` skill bundle, Cursor skill shims, and archived package for grounded domain writing workflows.
- Phase 6 has an execution-ready context artifact defining standards resolution, stage evaluation, execution-first evidence, and operator finding lifecycle boundaries.
- Phase 6 Plan 01 shipped registry-driven standards resolution before execution, briefing packet criteria/standards persistence columns, agentize registry-backed standards selection, and session-start standards/trigger previews.
- Phase 6 Plan 02 shipped durable workflow stage findings, including a `success_criteria_stage_findings` table, stage JSON artifacts, workflow-stage evaluation hooks, and closeout governance aggregation.
- Phase 6 Plan 03 shipped broader execution-first evidence ingestion plus CLI commands for standards resolution preview and criteria finding lifecycle transitions.
- Phase 6 is complete with summaries and verification artifacts; GSD now recognizes Phase 7, Delta Scoring And Health Backfill, as the active next phase.
- Phase 7 has an execution-ready context artifact defining additive standards-health scoring, delta explanation, provenance, workflow recommendation, and manual override boundaries.
- Phase 7 Plan 01 shipped ten-domain standards coverage, profile version `2026.06.0`, honest unknown-default evaluators for new health domains, and provenance import validation.
- Phase 7 Plan 02 shipped read-time `DeltaExplanation` projections, four-state provenance classification, recent-finding contradiction detection, and health-derived workflow recommendations.

## Constraints

- **Local-first**: The system should run from local files, local stores, and local operator tooling — this is part of the product identity
- **Primary user**: The main user is your agents — workflows, packets, and handoffs must optimize for machine execution as much as human inspection
- **Governance**: Important changes to truth, standards, prompts, skills, and workflows should remain reviewable instead of silently becoming default behavior
- **Brownfield continuity**: Existing runtime, UI, context, and audit subsystems must be extended and unified rather than replaced with a disconnected rewrite
- **Explainability**: Health, drift, routing, and workflow decisions must remain drill-downable to explicit sources, reasoning, and remediation paths
- **Compounding memory**: Meaningful runs should leave the system more accurate and more reusable through reliable writebacks and lifecycle-managed learning
- **Open-source trajectory**: The project should eventually be legible and portable enough for external contributors, even though immediate use is personal and agent-centered

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Plan the full operating-system vision as v1 | The goal is not a rushed MVP but a complete personal operating layer sequenced through many milestones/phases | — Pending |
| Treat agents as the primary user | The system’s core value is better AI execution, not just better human note browsing | — Pending |
| Use “default operating layer” as the practical success gate | The product is done enough when starting in AIOS beats manual model/tool orchestration for most serious work | — Pending |
| Use end-to-end vague-goal-to-writeback flow as the canonical workflow test | This is the clearest concrete expression of the target loop and exposes the weakest links between context, routing, execution, evaluation, and memory | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check -> still the right priority?
3. Audit Out of Scope -> reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-24 after shipping Phase 7 delta explanations*
