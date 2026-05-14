# Phase 1 Sub-Roadmap

**Phase:** 1  
**Name:** Project, Workflow, And Prompt Routing  
**Planning Date:** 2026-05-14  
**Parent Artifact:** [ROADMAP.md](/Users/jakyeamos/AIOS/.planning/ROADMAP.md)  
**Requirements:** `ROUT-01`, `ROUT-02`, `ROUT-03`, `ROUT-04`

## Purpose

Phase 1 is the governed entry gate for the whole AIOS operating loop.

It is complete only when a vague goal can be turned into:

- the right project target
- the right workflow
- the right prompt or handoff family
- the right execution surface
- an inspectable route rationale

without the operator manually stitching those choices together.

## Why This Phase Comes First

Later phases depend on route quality.

If routing is weak:

- packet compilation pulls the wrong context
- workflow execution starts from the wrong contract
- standards matching binds the wrong criteria
- writebacks update the wrong project or asset surfaces
- health and learning data become low-trust because the original route was wrong

This phase therefore establishes the identity and decision envelope for every later run.

## Phase 1 Scope

### Included

- project resolution from vague human goals
- explicit ambiguity handling when multiple projects fit
- task-family classification
- workflow selection from governed workflow contracts
- route rationale persistence
- agent or harness recommendation
- prompt-family or handoff-family selection
- route metadata storage for later packet, run, and learning stages

### Not Deferred Within Phase 1

- prompt selection as a first-class route outcome
- workflow reasoning visibility
- ambiguity blocking behavior
- route metadata durability

### Explicit Non-Goals For This Phase

- full packet compilation quality
- grounded query completeness
- durable run resumption
- truth writeback approval flows
- standards scoring
- operator-surface polish

Those are downstream phases. Phase 1 only owns the route contract and the decisions needed to start serious work correctly.

## Phase 1 Outcome Contract

At the end of Phase 1, AIOS should be able to receive a goal like:

`"Improve Soundscape onboarding and make sure it matches launch standards."`

and produce a route result containing at minimum:

- resolved project: `Soundscape`
- task family: `audit-and-implement`
- workflow: `audit-and-implement`
- prompt family: implementation + standards-backfill aware handoff
- recommended execution surface: managed harness / chosen agent
- route rationale: why this route was chosen over `audit-only`, `UI polish`, and `PRD generation`
- ambiguity state: clear or blocked
- required next stage: Phase 2 packet compilation

## Workstreams

### Workstream 1: Project Resolution

**Goal:** Resolve user intent to a single project or block with explicit ambiguity.

**Primary Requirements:** `ROUT-01`

**Current Surfaces To Evolve:**

- `services/aios_cli.py`
- project inventory and planning truth surfaces
- `PROJECT.md`
- project dossier / project listing sources
- any existing project-identification logic embedded in routing code

**Detailed Responsibilities:**

- define project candidate generation from task text
- define confidence and ambiguity thresholds
- distinguish:
  - exact project match
  - likely project match
  - ambiguous multi-project match
  - no supported project match
- persist project-candidate reasoning, not just final choice
- make “block for clarification” an explicit successful route outcome when necessary

**Tier-One Exit Conditions:**

- no silent guesses between plausible projects
- no route without a persisted project target or ambiguity block
- route outputs expose candidate set and final resolution basis

### Workstream 2: Task-Family Classification

**Goal:** Classify what kind of work the user is asking for before choosing a workflow.

**Primary Requirements:** `ROUT-02`

**Primary Surfaces:**

- `services/workflow_orchestration.py`
- `services/execution_strategy.py`
- `config/workflows/registry.json`
- future workflow-family registries and route heuristics

**Detailed Responsibilities:**

- define task-family classes for current and planned workflows
- separate classification from workflow selection so the system can explain both
- use explicit cues:
  - implementation
  - audit/review
  - planning/requirements
  - recovery/debugging
  - truth update
  - standards backfill
  - prompt/asset experimentation
- support bounded multi-signal classification rather than pure string matching

**Tier-One Exit Conditions:**

- every serious route has a persisted task family
- workflow choice is downstream of task-family classification, not conflated with it
- nearby alternatives are visible in route rationale

### Workstream 3: Workflow Selection

**Goal:** Choose the smallest sufficient governed workflow for the task.

**Primary Requirements:** `ROUT-02`, `ROUT-03`

**Primary Surfaces:**

- `config/workflows/registry.json`
- `services/workflow_orchestration.py`
- `.planning/WORKFLOW_MATRIX.md`
- `.planning/ROADMAP.md`

**Detailed Responsibilities:**

- define route-selection criteria per workflow family
- prefer the smallest governed workflow that safely satisfies the task
- encode “why not” logic for nearby alternatives
- ensure early default workflows are selectable:
  - `implementation-delivery`
  - `failure-recovery`
  - `audit-only`
  - `audit-and-implement`
  - `agent handoff generation`
- preserve planned workflow families as routeable targets even before full implementation

**Tier-One Exit Conditions:**

- workflow selection produces a clear winner or an ambiguity block
- selection is explainable in terms of task family, project state, and risk
- workflow recommendation is stable enough to become the basis for packet generation

### Workstream 4: Prompt And Handoff Family Selection

**Goal:** Make prompt-library selection part of routing, not a later side effect.

**Primary Requirements:** `ROUT-04`

**Primary Surfaces:**

- `prompts/registry.json`
- `prompts/*`
- `bin/validate-prompts.py`
- `bin/sync-prompts.py`
- `bin/hook-prompt-submit.py`
- `aios-ui/server/routers/prompts.ts`

**Detailed Responsibilities:**

- define prompt-family identities separate from individual prompt text
- bind routeable workflow families to prompt or handoff families
- support statuses that later phases will govern:
  - approved
  - candidate
  - deprecated
- record prompt-family provenance in route metadata
- expose when no approved prompt family exists for the chosen workflow

**Tier-One Exit Conditions:**

- every serious route recommends a prompt or handoff family
- prompt-family choice is stored with rationale
- route can explicitly say when it must fall back because no approved prompt family exists

### Workstream 5: Agent Or Harness Recommendation

**Goal:** Attach the right execution surface to the selected route.

**Primary Requirements:** `ROUT-04`

**Primary Surfaces:**

- `services/invocation_backends.py`
- `services/execution_strategy.py`
- managed runtime entrypoints
- workflow contracts and backend capabilities

**Detailed Responsibilities:**

- define backend selection factors:
  - workflow type
  - validation needs
  - approval sensitivity
  - expected writeback class
  - tool/runtime constraints
- distinguish recommendation from availability
- persist the chosen harness/agent and the rejected alternatives when useful

**Tier-One Exit Conditions:**

- every serious route includes an execution-surface recommendation
- the recommendation is tied to workflow constraints, not generic preference
- route metadata can be audited later against run outcomes

### Workstream 6: Route Persistence And Inspection

**Goal:** Make routing durable and inspectable for later phases and operator surfaces.

**Primary Requirements:** `ROUT-03`, `ROUT-04`

**Primary Surfaces:**

- route metadata storage
- run/invocation records
- hook surfaces
- query and operator routers

**Detailed Responsibilities:**

- define a route-result schema
- persist:
  - route id
  - project target
  - task family
  - selected workflow
  - prompt family
  - recommended harness
  - route rationale
  - ambiguity status
  - timestamp and source input
- make route outputs available to Phase 2 packet compilation and Phase 10 operator surfaces

**Tier-One Exit Conditions:**

- route decisions survive beyond a single session turn
- downstream packet/run/evaluation surfaces can retrieve route context
- route evidence can be audited and compared against outcomes

## Deliverables

Phase 1 should emit the following durable artifacts or code-level equivalents:

- route contract schema
- task-family classification contract
- workflow selection contract
- prompt-family recommendation contract
- harness recommendation contract
- route persistence contract
- ambiguity-handling contract
- operator-visible route rationale surface

## Proposed Implementation Sequence

1. Define the route result schema and persistence shape.
2. Define project candidate generation and ambiguity rules.
3. Define task-family taxonomy and route heuristics.
4. Bind workflow families to selection logic.
5. Bind prompt/handoff families to route results.
6. Bind execution-surface recommendations.
7. Expose route rationale and ambiguity details to downstream consumers.
8. Add audit/verification commands for route quality.

## Dependencies

### Inputs Required

- current project inventory quality
- current workflow registry quality
- prompt registry quality
- invocation backend capability truth
- planning workflow matrix

### Downstream Consumers

- Phase 2 packet compilation
- Phase 3 run-state execution
- Phase 5 governance/writeback
- Phase 8 prompt/workflow lifecycle
- Phase 10 operator routing visibility

## Risks

### Risk: Project inventory is too weak

**Effect:** Routing may guess or over-block.

**Mitigation:** Make ambiguity explicit and preserve candidate reasoning.

### Risk: Workflow taxonomy stays too coarse

**Effect:** AIOS routes to generic workflows and loses deterministic behavior.

**Mitigation:** Separate task-family classification from workflow-family resolution and keep `why not` explanations.

### Risk: Prompt families are not normalized enough

**Effect:** Prompt selection remains ad hoc even if workflow routing improves.

**Mitigation:** Route to prompt families first; let later phases manage specific prompt assets and lifecycle.

### Risk: Backend recommendation is based on habit rather than contract

**Effect:** Route metadata becomes decorative rather than operational.

**Mitigation:** Tie recommendation logic to workflow constraints and later compare recommendation quality against run outcomes.

## Verification And Evidence

Phase 1 should not be considered complete until there is durable proof for:

- route schema exists and is persisted
- project ambiguity can block unsafe routing
- workflow selection can explain nearest alternatives
- prompt-family recommendation exists on serious routes
- harness recommendation exists on serious routes
- route results can be retrieved by downstream packet/run surfaces

Example proof surfaces may include:

- route-focused CLI or JSON audit commands
- stored route records linked to runs
- regression fixtures for representative vague-goal submissions
- comparison cases showing why one workflow beat another

## Exit Checklist

- [ ] Route result schema is explicit and durable
- [ ] Project resolution supports exact, likely, ambiguous, and unsupported outcomes
- [ ] Task-family classification is separate from workflow resolution
- [ ] Workflow selection prefers the smallest sufficient governed workflow
- [ ] Route rationale records why the chosen workflow beat alternatives
- [ ] Prompt or handoff family is included in the route result
- [ ] Agent or harness recommendation is included in the route result
- [ ] Ambiguity blocks are surfaced instead of silent guesses
- [ ] Phase 2 consumers can retrieve route outputs
- [ ] Route quality can be audited with repeatable evidence

---
*Last updated: 2026-05-14*
