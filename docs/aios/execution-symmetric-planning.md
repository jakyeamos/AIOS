# Execution-Symmetric Planning

Execution-Symmetric Planning makes plans behave like execution artifacts. If a plan is meant to guide implementation, review, validation, handoff, or a GSD phase, it should carry the same constraints the executor will later be judged against.

This is not a routing feature. Routing identifies the source, workflow, phase, and likely task shape. Execution-Symmetric Planning uses that routing context to decide how much planning structure is needed and which execution standards must be visible in the plan.

## Supported Invocation Sources

AIOS recognizes planning intent from:

- natural-language planning requests
- GSD phase aliases such as `/gsdplanphase`
- slash-command requests with invocation hints or overrides
- generated implementation prompt requests
- audit-to-implementation prompts
- CLI-shaped planning contexts

GSD commands are preserved. A detected GSD planning source produces GSD-ready planning output instead of generic prose.

## Complexity Behavior

Plan depth scales with risk:

- `trivial`: answer directly or take the smallest safe action.
- `simple`: include only objective, safest next step, and validation.
- `moderate`: generate an execution-symmetric plan with selected lenses, ordered steps, validation, failure modes, rollback, delegation, escalation, and definition of done.
- `complex`: include broader affected areas, validation depth, rollback/recovery, and delegation strategy.
- `high_risk`: include required safety lenses, review gates, rollback, and escalation conditions.

The non-overplanning guardrail is part of the feature. Simple work should not receive a heavyweight implementation plan.

## Planning Lenses

Planning lenses convert execution standards into plan requirements. The registry maps task types, workflow phases, and risk levels to lenses such as testing, maintainability, rollback safety, interface contracts, security, reproducibility, executor readiness, and escalation clarity.

Manual lens requests supplement automatic selection. Unknown lens requests are preserved as unknowns rather than silently changing the plan.

## Skill-As-Planning-Lens

Execution, review, validation, and audit skills can be used in planning mode. Planning mode extracts skill principles, invariants, validation gates, reviewable artifacts, and disallowed outputs. It does not produce completed-work reviews or final pass/fail findings.

This keeps always-loaded agent rules thin. Detailed behavior lives in intent-specific services, registries, specs, and skills.

## GSD-Ready Planning

When `/gsdplanphase` or an equivalent alias is detected, AIOS sets:

- `workflow=gsd`
- `phase=plan`
- `handoff_target=gsd`
- `output_format=gsd_ready_plan`

GSD-ready plans include phase-compatible scope, ordered steps, validation strategy, risks, rollback/recovery, delegation notes, escalation conditions, and definition of done.

## Planning Context And Logs

Structured planning context is represented by `services/planning_context.py`. It records source invocation, workflow, phase, task type, complexity, risk, selected lenses, handoff target, validation depth, output format, sub-agent strategy, model strategy, TMCP evidence, execution result, validation result, rework, and notes.

`services/planning_log.py` writes lightweight JSONL planning events. The logs compare:

- generic vs execution-symmetric plans
- natural-language vs GSD phase planning
- slash-command-triggered vs auto-routed planning
- selected-lens vs no-lens plans

Non-trivial managed runs require TMCP packet and receipt evidence unless an explicit bypass reason is recorded.

## Primary Files

- `docs/specs/execution-symmetric-planning.md`
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
