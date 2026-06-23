# AIOS Execution-Symmetric Planning Audit

**Date:** 2026-06-23  
**Requirement:** ESPL-01  
**Scope:** Current AIOS and GSD surfaces that create, route, enrich, hand off, validate, or log plans.

## Executive Finding

AIOS already has strong routing, context selection, success-criteria preview, workflow-stage metadata, and GSD phase planning conventions. The missing layer is a first-class planning contract that converts those ingredients into executor-ready plans for every non-trivial invocation source.

Today, plan quality is split across three places:

- AIOS registries and services route work, attach context, recommend workflows, and preview gates.
- GSD skills and external workflow files produce high-quality phase plans for `/gsd-*` style work.
- Agent instructions and session hooks inject broad standards into always-loaded context.

That split works operationally, but it is not execution-symmetric. A routed AIOS task can know the workflow, context, criteria, and prompt family without requiring the resulting plan to state validation strategy, rollback/recovery, delegation, escalation, failure modes, and definition of done. GSD plan-phase has many of those rules, but they are not yet reusable as an AIOS planning lens for natural-language, CLI-style, audit-to-implementation, or handoff-driven planning.

## Current Surface Map

| Surface | Current source | What it does | Planning gap |
| --- | --- | --- | --- |
| Natural-language classification | `bin/hook-prompt-submit.py` | Classifies prompts as debug, plan, refactor, implement, review, explain, or other; retrieves prompt templates, rules, handoff decisions, next actions, and selected vault context. | Classification influences context retrieval, not plan shape or required plan sections. |
| Session-start context | `bin/hook-session-start.py` | Injects agent rules, success criteria, standards, execution-first triggers, CTS context, recent handoff actions, and resume snapshots. | Context packet can contain standards, but it does not decide which planning lenses must become plan requirements. |
| Context compiler | `tools/context-compile.mjs` | Selects task-specific context files and emits receipts with loaded/skipped reasons. `ALWAYS_LOAD_IDS` is intentionally small. | Receipts are context-selection evidence, not a planning schema. They do not enforce validation, rollback, escalation, or definition-of-done fields. |
| Workflow routing | `services/task_routing.py` | Resolves project, selects workflow, prompt family, backend, agent, skills, and workflow alternatives. | Route results are ready/blocked decisions. They do not include complexity, risk level, selected planning lenses, or executor-ready plan sections. |
| Workflow registry | `config/workflows/registry.json`, `services/workflow_orchestration.py` | Defines stage kinds, stage skills, validations, prompt bindings, standards bindings, expected artifacts, writebacks, and learning signals. | Stage contracts govern workflow execution but lack a dedicated planning phase registry and plan-output schema. |
| Skill metadata | `config/workflows/skills.json` | Defines lifecycle-managed skills, allowed stages, schemas, invariants, failure conditions, side effects, and execution mode. | Skills can state verification and handoff requirements, but AIOS does not yet extract skill principles as planning constraints. |
| Prompt registry | `prompts/registry.json` | Maps prompt families to workflow families, classifications, tags, required inputs, optional inputs, and template files. | Prompt selection can pick a planning-oriented template, but it does not guarantee execution-symmetric structure. |
| Harness briefing | `services/harness.py` | Builds backend-neutral briefings with selected packets, standards, criteria, risks, expected artifacts, gates, and approval requirements. | Briefing gates are useful, but the harness brief is not a plan generator and omits ordered execution, rollback, delegation, escalation, and done criteria. |
| Native handoff | `services/native_commands.py`, `services/aios_cli.py` | `aios handoff` records goal, state, git status, decisions, tests, failed approaches, blockers, references, and next actions. | Handoff captures continuation context, but it does not require the next plan to inherit validation depth, selected lenses, or rollback strategy. |
| CLI run start | `services/aios_cli.py` | `aios start-work`, `harness-brief`, `packet generate`, `recommend-workflow`, and related commands expose routing and briefing paths. | CLI commands create structured route/briefing artifacts, not a plan-quality contract shared with GSD or slash commands. |
| GSD plan-phase | `/Users/jakyeamos/.agents/skills/gsd-plan-phase/SKILL.md` and `references/codex-planning-standard.md` | Preserves upstream GSD plan-phase gates, reads researcher/planner/checker prompts, enforces requirement coverage, validation strategy, security/UI/schema gates, and executable tasks. | Strongest planning surface today, but external to AIOS registries and not automatically available for non-GSD planning requests. |
| GSD execute-phase | `/Users/jakyeamos/.agents/skills/gsd-execute-phase/SKILL.md` | Executes GSD plans with phase discovery, wave ordering, checkpoints, verification, summaries, and state updates. | Execution expects good plans but does not provide a reusable planning lens contract for earlier routing surfaces. |
| GSD dispatcher | `/Users/jakyeamos/.agents/skills/gsd-do/SKILL.md` | Routes freeform natural language to the right GSD command. | Slash/GSD compatibility is skill-triggered rather than represented in an AIOS workflow-phase registry. |
| GSD pause/handoff | `/Users/jakyeamos/.agents/skills/gsd-pause-work/SKILL.md` | Creates `.continue-here.md` handoff with current state, completed work, remaining work, decisions, blockers, WIP commit, and resume instructions. | Good continuation artifact, but not structurally connected to AIOS planning schema or lens selection. |
| Plan/eval logging | `services/harness.py`, `services/workflow_orchestration.py`, `services/aios_cli.py`, `schema.sql` | Records orchestration runs, events, briefing packets, success-criteria evaluations, workflow learning, workflow reports, and eval runs. | Durable run evidence exists, but plan context fields such as source invocation, complexity, selected lenses, sub-agent strategy, model strategy, validation depth, rework, and planning notes are not first-class. |

## Entry Points

### Natural-Language Planning

Primary entry points are `bin/hook-prompt-submit.py`, `bin/hook-session-start.py`, `services/task_routing.py`, and `services/harness.py`.

The prompt hook classifies natural language and retrieves targeted hints. Session start injects applicable criteria, standards, active rules, and CTS context. Routing resolves the project/workflow/prompt/backend/agent combination. Harness briefing compiles packets, risks, criteria, expected artifacts, and gates.

Loss point: natural-language "plan" classification currently improves retrieval but does not force an execution-grade plan. The resulting agent can still produce generic prose unless a separate skill or developer instruction supplies stronger structure.

### GSD Phase Planning

Primary entry points are the GSD skills under `/Users/jakyeamos/.agents/skills/`, especially `gsd-plan-phase`, `gsd-execute-phase`, `gsd-plan-complete-phase`, `gsd-autonomous`, `gsd-next`, and `gsd-resume-work`.

`gsd-plan-phase` is the strongest existing planning contract. It requires phase initialization, hard gates, research, planner/checker loops, requirement coverage, validation strategy, security threat-model checks, UI contract checks, schema-push detection, existing-plan handling, and task-level executable detail. Its Codex-specific planning standard requires a fresh agent to execute without rediscovering scope, architecture, file ownership, or verification.

Loss point: this strength is not yet represented as AIOS data. AIOS cannot select "GSD planning phase" as a structured workflow phase and then require GSD-ready plan output for equivalent natural-language or CLI invocations.

### Slash Command Handling

Slash command compatibility currently lives primarily in skills and agent runtime routing, not in a central AIOS slash-command parser. The available GSD command equivalents are represented as skills such as `gsd-plan-phase`, `gsd-execute-phase`, `gsd-do`, `gsd-pause-work`, and `gsd-autonomous`.

Loss point: because slash commands are external skill invocations, AIOS does not have a configurable mapping from `/gsdplanphase` and equivalents to workflow phase, planning complexity, output schema, selected lenses, and validation depth.

### CLI-Style Routing

Primary entry points are `services/aios_cli.py`, `services/task_routing.py`, `services/workflow_orchestration.py`, `services/harness.py`, and `services/portable_context_packet_generator.py`.

`aios start-work` creates a routed run packet and session handshake. `aios harness-brief` generates backend-neutral briefings. `aios packet generate` produces portable context packets. `aios recommend-workflow` and `workflow-gates` expose workflow routing and stage metadata.

Loss point: CLI-style routing is structured enough to carry planning metadata, but it currently stops at routing/briefing. It does not yet generate an executor-ready plan or log planning decisions.

### Generated Implementation Prompts

Implementation prompt selection is based on `prompts/registry.json` plus workflow-stage prompt bindings in `config/workflows/registry.json`. The prompt hook can also surface prompt-template matches from data-backed templates.

Loss point: prompt families such as `reasoning_handoff`, `implementation_handoff`, and `research_handoff` can support planning, but they are not required to include the same execution constraints that later validation and review will apply.

### Audit-To-Implementation Prompts

Audit/review flows exist through workflow families, native commands, GSD audit/review/validate skills, and prior phase artifacts such as `docs/audits/*`. AIOS can produce audits and then execute plans derived from them.

Loss point: audit findings are not currently transformed through a structured audit-to-implementation planner that forces each finding to map to scope, files, constraints, validation, rollback, and acceptance criteria.

## Where Plan Quality Degrades

1. **Execution constraints are context, not plan fields.** Success criteria and standards appear in packets and session-start context, but generated plans are not required to name which standards became constraints.
2. **Validation strategy is inconsistent.** GSD plan-phase requires task-level verification, while AIOS route and harness outputs list gates/criteria without ordered validation depth or exact commands.
3. **Rollback and recovery are sparse.** Native cleanup/prototype commands include rollback/promotion notes, but general implementation plans and harness briefings do not require rollback/recovery sections.
4. **Delegation strategy is not structured.** Agent/sub-agent recommendations exist at routing time, and GSD can run inline or delegated, but plans do not record why work should be inline, sequential, parallel, or independently reviewed.
5. **Escalation conditions are implicit.** Approval requirements and blockers exist, but plan artifacts do not consistently state when to stop, ask, split, escalate, or create a follow-up.
6. **Definition of done is uneven.** GSD plan tasks include measurable done fields. AIOS briefings and prompts can omit observable completion criteria.
7. **Workflow phases are not first-class planning inputs.** Existing workflow stage kinds cover execution, validation, and finalization, but there is no GSD-compatible planning phase registry.
8. **Skill principles do not become planning lenses.** Skill invariants and failure conditions are available in metadata, but AIOS does not translate them into plan requirements.
9. **Plan logs lack planning context.** Durable run/eval evidence exists, but planning source, complexity, risk, selected lenses, validation depth, model/sub-agent strategy, rework, and plan outcome are not consistently queryable.
10. **Always-loaded rules can grow too broad.** Agent files can accumulate rules that are only relevant to specific development intents. TMCP should keep always-loaded instruction thin and route intent-specific planning lenses through pointers, registries, or skills unless the rule is truly universal.

## Minimal Implementation Seams

### 20-02: Core Principle And Complexity Contract

Add a small principle document and complexity contract rather than expanding always-loaded agent rules. Candidate files:

- `docs/specs/execution-symmetric-planning.md`
- `aios/context/standards/` only if the principle must participate in context compilation
- a short pointer in any always-loaded agent file only if needed to route agents to the spec

TMCP placement decision: keep the detailed rule intent-specific. Always-loaded text should only say that planning changes must decide "always-loaded rule vs intent-specific pointer."

### 20-03: GSD Workflow Phase Recognition

Add a configurable phase/command registry that maps invocation sources to planning phases without replacing GSD. Candidate files:

- `config/planning/gsd-workflow-phases.json`
- `services/planning_phase_registry.py`
- focused tests under `tests/`

The registry should preserve slash command names and GSD skill behavior while giving AIOS a machine-readable phase target.

### 20-04: Planning Lens Registry

Add a planning lens registry mapping task type, workflow family, workflow phase, and risk signals to execution standards. Candidate files:

- `config/planning/lenses.json`
- `services/planning_lenses.py`
- tests for task/workflow-to-lens selection

This should reference existing standards and skills rather than copying their full instructions.

### 20-05: Skill-As-Planning-Lens

Extend skill metadata handling so execution/review/validation/audit skills can be used in planning mode. Candidate files:

- `config/workflows/skills.json`
- `services/workflow_orchestration.py`
- `services/planning_lenses.py`

The planning-mode extraction should use skill purpose, invariants, failure conditions, side effects, and output schema as constraints. It should not run the skill as though work is already complete.

### 20-06: Executor-Ready Plan Generation

Add a plan generator/schema that consumes route result, context receipt, workflow phase, selected lenses, complexity, and risk. Candidate files:

- `services/execution_symmetric_planning.py`
- `config/planning/plan-output-schema.json`
- `services/harness.py` or `services/aios_cli.py` only as thin adapters

For non-trivial tasks, generated plans should include objective, scope, constraints, assumptions, selected lenses, affected areas, ordered steps, validation strategy, failure modes, rollback/recovery, delegation strategy, escalation conditions, and definition of done.

### 20-07: Internal Planning Schema And Logging

Add structured planning context persistence without overloading existing run tables. Candidate files:

- `schema.sql`
- `services/planning_log.py`
- `services/aios_cli.py` adapter commands or flags

Minimum fields should cover source invocation, workflow, phase, task type, complexity, risk level, selected lenses, handoff target, validation depth, output format, sub-agent strategy, model strategy, execution result, validation result, rework required, and notes.

### 20-08: Evaluation Coverage

Add focused tests/evals for:

- natural-language planning request
- `/gsdplanphase` or equivalent GSD plan-phase mapping
- explicit planning-lens request
- audit-to-implementation prompt
- GSD handoff continuation
- simple task that must not be over-planned
- complex/high-risk task requiring validation and rollback

Candidate files:

- `tests/test_execution_symmetric_planning.py`
- `tests/test_planning_phase_registry.py`
- `tests/test_planning_lenses.py`
- optional eval fixtures under `docs/evals/` or `config/evals/`

## Compatibility Requirements

- Preserve GSD workflows and slash command behavior. AIOS should add registries/adapters around them, not replace them.
- Keep GSD plan-phase output compatible with existing `.planning/phases/**` artifacts.
- Keep CLI routing as structured representation, not a replacement for GSD commands.
- Do not over-plan trivial work. The complexity contract should explicitly allow direct/minimal responses.
- Keep always-loaded agent files thin. New planning rules should default to intent-specific TMCP pointers, registries, or skill metadata unless they are universal execution safety rules.
- Preserve local-first behavior. Planning logs, schemas, registries, and generated plans should remain file/SQLite backed.

## Conclusion

The next phase work should not rewrite routing, GSD, or slash commands. The minimal path is to add an AIOS planning layer that sits between routing/context selection and execution. That layer should recognize the invocation source, select a workflow phase, choose planning lenses, produce a complexity-sensitive executor-ready plan, and log planning decisions for later evaluation.
