# Execution-Symmetric Planning

**Status:** Active principle  
**Requirement:** ESPL-02  
**Policy:** `config/planning/execution-symmetric-planning.json`

## Principle

Plans that guide execution are execution artifacts. If a plan will drive implementation, review, validation, handoff, or GSD execution, it must carry the standards that will later judge the work.

Execution-Symmetric Planning does not mean every task gets a large plan. It means plan depth scales with the task's complexity and risk. Trivial work can be handled directly. High-risk work needs explicit constraints, review gates, rollback, and escalation.

## Supported Invocation Sources

This principle applies when planning is requested or implied through:

- natural-language planning requests
- slash commands and GSD equivalents such as `/gsdplanphase`
- explicit GSD workflows
- CLI-shaped routing such as `aios start-work`, `aios harness-brief`, and packet generation
- generated implementation prompts
- audit-to-implementation prompts
- handoff/resume artifacts that direct future work

It preserves those sources. AIOS should add registries, planning lenses, schemas, and thin adapters around existing workflows rather than replacing GSD or slash-command behavior.

## Complexity Contract

### Trivial

Use a direct answer or minimal plan.

Examples include a one-line explanation, an isolated command, a typo fix, or a tiny doc edit with no governance, code path, or test impact.

Required shape:

- answer or action
- verification only when needed

Do not create a large plan for trivial work.

### Simple

Use a light plan.

Examples include a narrow one-file edit, a small doc update, or a low-risk local command where the path is obvious.

Required shape:

- objective
- safest next step
- validation

Optional shape:

- assumptions
- affected file
- done condition

### Moderate

Use an execution-symmetric plan.

Examples include non-trivial code edits, small multi-file work, workflow changes with bounded scope, or a task that touches existing tests, criteria, standards, routing, prompts, or skills.

Required shape:

- objective
- scope
- constraints
- assumptions
- selected planning lenses
- affected areas
- ordered execution steps
- validation strategy
- definition of done

Add failure modes or rollback when the task can leave durable state, change behavior, or affect a shared contract.

### Complex

Use a full execution plan.

Examples include cross-layer changes, data/schema work, multi-phase implementation, agent/workflow/orchestration changes, UI with meaningful state, migrations, performance-sensitive work, or changes that affect shared contracts.

Required shape:

- objective or mission
- scope and non-scope
- constraints and assumptions
- selected planning lenses
- affected areas and ownership boundaries
- ordered execution steps
- validation strategy with commands or concrete evidence
- failure modes
- rollback or recovery
- delegation strategy
- escalation conditions
- definition of done
- handoff/update artifacts

### High Risk

Use a full execution plan with explicit review gates.

Examples include security-sensitive work, privacy or secret handling, destructive actions, production deployment, schema/data migration, governance/rule changes, external service behavior, package-manager changes, or changes to always-loaded agent instructions.

Required shape:

- all complex-plan sections
- hard constraints
- approval or review gates
- rollback owner/action
- stop conditions
- escalation criteria
- accepted-risk recording
- post-change verification and handoff expectations

## GSD-Ready Plan Expectations

When the invocation source is GSD planning or a GSD equivalent, the plan must remain compatible with `.planning/phases/**` conventions and GSD execution.

GSD-ready plans should include:

- requirement IDs where available
- concrete artifacts
- key links between artifacts and behavior
- task-level file targets
- task-level action, verification, and done criteria
- validation strategy that can be run by a later executor
- explicit blockers or missing decisions instead of generic placeholders

Do not weaken existing GSD plan-phase gates. AIOS should treat GSD plan-phase as a planning source and lens, not as generic prose.

## Non-Overplanning Guardrail

Planning should reduce execution ambiguity, not create process drag.

Do not require a full execution-symmetric plan when:

- the task is trivial and can be answered directly
- the edit is isolated, reversible, and obvious
- the user asks for a quick explanation or command output
- the work is explicitly exploratory and creates no durable product state

Do require deeper planning when:

- the task changes shared behavior, workflow, schema, data, security, privacy, deployment, rules, prompts, skills, or agent instructions
- later validation will judge the outcome against standards
- another agent or future session must execute from the plan
- rollback, escalation, or handoff would be costly to reconstruct later

## Always-Loaded Rule Placement

When updating agent instruction files, decide whether the planning rule belongs in the always-loaded surface or an intent-specific pointer.

Default placement:

- full planning behavior in this spec
- machine-readable behavior in `config/planning/execution-symmetric-planning.json`
- future workflow/phase/lens behavior in planning registries
- skill-specific behavior in skills or skill-lens registries
- always-loaded files limited to short routing principles and safety triggers

Only add detailed planning instructions to always-loaded files when they are needed before intent can be classified.

## Definition Of Done

A planning output satisfies this principle when:

- its depth matches complexity and risk
- it names the standards or lenses that matter for execution
- it includes enough validation for the executor to prove the result
- it states rollback, escalation, and handoff expectations when warranted
- it preserves GSD and slash-command compatibility
- it avoids bloating always-loaded rules with intent-specific procedure
