---
phase: 06-standards-resolution-and-evidence-based-evaluation
phase_number: "06"
title: Standards Resolution And Evidence-Based Evaluation
status: ready-for-execution
autonomous: true
updated: 2026-05-23
---

# Phase 6: Standards Resolution And Evidence-Based Evaluation - Context

**Gathered:** 2026-05-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Bind every serious execution path to explicit standards and success criteria before work begins, then preserve evidence-backed evaluation results after run and workflow-stage execution. This phase extends the existing success criteria, standards health, hook, workflow orchestration, and CLI surfaces. It does not replace the current registry, workflow, or closeout model.

</domain>

<decisions>
## Implementation Decisions

### Resolution Contract
- Use one registry-driven `resolve_task_standards()` surface that returns criteria, standards, execution-first triggers, workflow key, profile metadata, and resolution status.
- Preserve missing standards-profile state explicitly with `no_profile_attached` rather than returning an apparently successful empty standards list.
- Persist selected criteria and standards on briefing packets so the pre-execution preview and closeout evaluation do not drift.
- Keep hardcoded agentize criteria/standards helpers only as short-lived fallback/deprecated surfaces.

### Stage Evaluation
- Add stage-level findings as structured rows and JSON artifacts rather than embedding opaque JSON inside workflow reports.
- Evaluate only validate-like stages by default; non-validation stages such as parse_request must not produce noise unless a criterion explicitly opts into that stage kind.
- Reuse the existing per-criterion evaluator dispatch and blocker-promotion behavior instead of creating a generic evaluator framework.
- Keep existing free-form `stage_issues` for one transition cycle while adding structured stage findings beside it.

### Execution-First Evidence
- Broaden execution evidence ingestion to include tool events and workflow report stage outputs, in addition to existing artifact and RTK evidence.
- Treat path markers as execution-first triggers only for code paths, so markdown documentation under code directories does not create false blockers.
- Continue requiring real execution evidence for stateful, cross-system, and core/shared logic changes.
- Prefer direct, durable evidence strings that can be stored in findings and closeout artifacts.

### Operator Lifecycle
- Add CLI affordances to preview standards resolution without launching a full session.
- Add a lifecycle transition path for both run-level and stage-level findings so accepted, resolved, waived, and stale states are reachable.
- Surface open and stale stage findings in governance audit output.
- Keep writeback, follow-up, and accepted-tradeoff semantics aligned with Phase 5 governance.

### Claude's Discretion
Implementation may choose the narrowest existing helper names and test fixtures that satisfy the plans, but must preserve AIOS layering: Python control-plane writes, SQLite durability, registry-backed policy, and UI/read surfaces as consumers.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `services/success_criteria.py` already owns criterion registry loading, applicability resolution, evaluator dispatch, run-level persistence, and JSON evaluation artifacts.
- `services/standards_health.py` already loads the standards registry and models standards profile data.
- `bin/hook-session-start.py` already previews applicable criteria before execution.
- `bin/hook-stop.py` already gathers execution evidence, records run-level criteria evaluations, and emits governed closeout summaries.
- `services/workflow_orchestration.py` already has stage boundaries and workflow execution reports.
- `services/aios_cli.py` already exposes governance and contract audit command patterns.

### Established Patterns
- SQLite schema changes are represented in `schema.sql` and mirrored by idempotent `ensure_*` or `ensure_column` runtime migrations.
- Evaluation artifacts are stored under `data/success-criteria/evaluations/`.
- Tests commonly use in-memory SQLite fixtures and targeted `uv run pytest ... -k ...` verification.
- Public Python helpers use explicit return types and typed dictionaries/dataclasses where shapes are stable.

### Integration Points
- Pre-execution resolution flows through `hook-session-start`, `agentize`, and `briefing_packets`.
- Stage-level evaluation flows through `workflow_orchestration.execute_workflow`, `success_criteria_stage_findings`, and closeout governance.
- Execution-first evidence flows through `hook-stop.execution_evidence_for_session` and the existing execution-first criterion evaluator.
- Operator transitions flow through `aios criteria-finding resolve`, `aios standards-resolution preview`, and `aios governance-audit`.

</code_context>

<specifics>
## Specific Ideas

Follow the three existing Phase 6 plans in order:

1. `06-01-PLAN.md` establishes resolve-before-execute and briefing packet persistence.
2. `06-02-PLAN.md` adds stage-level findings and closeout aggregation.
3. `06-03-PLAN.md` broadens execution-first evidence and adds operator CLI lifecycle commands.

No new external dependencies are needed.

</specifics>

<deferred>
## Deferred Ideas

Workflow-family contract expansion for audit-only, audit-and-implement, security review, test-first implementation, and repo cleanup should remain aligned with Phase 8 asset/workflow lifecycle work. UI-specific stage-finding displays can follow once the control-plane state is durable.

</deferred>
