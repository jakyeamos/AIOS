# Phase 20: Execution-Symmetric Planning - Research

**Gathered:** 2026-06-01
**Status:** Ready for planning

<source_spec>
## Source Spec

Phase 20 is specified in the pasted "Execution-Symmetric Planning Across AIOS + GSD Workflows" prompt ingested on 2026-06-01. The spec asks AIOS to make generated plans inherit the execution standards that will later govern implementation, review, validation, handoff, and GSD workflows.

The feature is not "replace slash commands." The feature is that any plan that guides execution should be generated with execution-grade standards regardless of whether it came from natural language, slash commands, explicit GSD workflows, CLI-style internal routing, generated implementation prompts, audit-to-implementation prompts, or phase planning workflows such as `/gsdplanphase`.
</source_spec>

<domain>
## Phase Boundary

Phase 20 upgrades plan generation quality. It does not replace GSD, slash commands, routing, skills, or workflow contracts.

It overlaps earlier phases but has a distinct planning-quality boundary:

- Phase 1 routes work to project/workflow/prompt families.
- Phase 2 compiles context and briefing packets.
- Phase 8 defines workflow contracts and stage metadata.
- Phase 16 hardens evidence, verifier, lifecycle, and model-selection instrumentation.
- Phase 19 adds native command surfaces.

Phase 20 makes plans execution-symmetric: plans become execution artifacts that include relevant standards, constraints, validation strategy, risk controls, rollback/recovery, delegation, escalation, and completion criteria when complexity warrants them.
</domain>

<requirements>
## Phase 20 Requirements

### ESPL-01: Planning System Audit
AIOS must audit current plan generation, GSD planning workflows, slash command handling, workflow routing, skill invocation, plan artifacts, validation strategy generation, and handoff formats before implementation.

### ESPL-02: Core Principle And Complexity Contract
AIOS must document Execution-Symmetric Planning as a core principle and define planning behavior by complexity: trivial direct/minimal response, simple light plan, moderate execution-symmetric plan, complex full plan, and high-risk full plan with review gates, rollback, and escalation.

### ESPL-03: GSD Workflow Phase Recognition
AIOS must recognize GSD workflow phases such as planning, implementation, review, and validation through a configurable registry. `/gsdplanphase` and equivalents must produce GSD-ready plans instead of generic prose.

### ESPL-04: Planning Lens Registry
AIOS must define a planning lens registry mapping task types and workflow phases to execution standards such as testing, maintainability, regression safety, architecture, rollback safety, interface contracts, orchestration, context management, security, data validation, reproducibility, executor readiness, and escalation clarity.

### ESPL-05: Skill-As-Planning-Lens
AIOS must support using execution, review, validation, and audit skills in planning mode. Planning mode extracts principles from the skill and converts them into planning constraints rather than producing a completed-work review.

### ESPL-06: Executor-Ready Plan Generation
Non-trivial AIOS/GSD-generated plans must include objective/mission, scope, constraints, assumptions, selected planning lenses, affected areas, ordered execution steps, validation strategy, failure modes, rollback/recovery, delegation strategy, escalation conditions, and definition of done when relevant.

### ESPL-07: Internal Planning Schema And Logging
AIOS must represent planning context with structured fields including source invocation, workflow, phase, task type, complexity, risk level, selected lenses, handoff target, validation depth, output format, sub-agent strategy, model strategy, execution result, validation result, rework required, and notes.

### ESPL-08: Evaluation Coverage
AIOS must add tests or eval cases for natural-language planning requests, `/gsdplanphase`, explicit planning-lens requests, audit-to-implementation prompts, GSD handoff generation, simple tasks that should not be over-planned, and complex tasks requiring validation and rollback.
</requirements>

<plan_sequence>
## Recommended Plan Sequence

- **20-01**: Audit current plan generation and GSD/slash workflow surfaces.
- **20-02**: Add core principle and complexity-sensitive plan contract.
- **20-03**: Add GSD workflow phase recognition and configurable phase registry.
- **20-04**: Add planning lens registry and task/workflow-to-lens selection.
- **20-05**: Support skill-as-planning-lens behavior.
- **20-06**: Update plan generation to produce executor-ready plans.
- **20-07**: Add internal planning schema and plan logs.
- **20-08**: Add evaluation coverage and docs.
</plan_sequence>

<implementation_constraints>
## Implementation Constraints

- Do not over-plan trivial work.
- Do not replace GSD workflows or slash commands.
- Do not make routing the feature at the expense of plan quality.
- Keep slash commands as supported invocation sources and overrides.
- Use CLI-shaped internal routing only as structured representation, not a replacement for GSD commands.
- Preserve existing GSD plan-phase behavior unless improving it with tested equivalent output.
- Prefer configurable registries over hardcoded command-name assumptions.
</implementation_constraints>
