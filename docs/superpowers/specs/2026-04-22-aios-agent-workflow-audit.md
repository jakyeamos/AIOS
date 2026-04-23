# AIOS Agent Workflow — CLI Surfaces + Control Plane Audit + Implementation Prompt

**Date:** 2026-04-22
**Status:** Ready to run
**Type:** Audit + implementation prompt
**Author:** jakyeamos

---

## Purpose

Extract the strongest agent-native workflow patterns (JSON-first CLI surfaces, structured metadata snapshots, semantic exit codes, skill installation) and fold them into the existing AIOS stack. Stealing patterns, not products.

**Core principle:** We are stealing patterns, not products.

---

## Prompt

You are conducting an AUDIT + IMPLEMENT pass on AIOS / my agent workflow.

Your job is NOT to adopt InsForge wholesale or turn my workflow into a backend-platform bet.
Your job IS to extract the strongest workflow ideas from InsForge-like agent-native systems and fold the valuable parts into my existing stack.

Core principle:
We are stealing patterns, not products.

---

### Objective

Audit my current workflow, control plane, CLI surfaces, skills system, metadata exposure, logs, and agent interaction model against the following high-value patterns:

1. JSON-first CLI surfaces for agents
2. Single-shot structured metadata snapshots before agent execution
3. Automatic skill installation / refresh tied to project linking or bootstrap across linked development projects
4. Stable semantic exit codes + structured logs for deterministic agent behavior
5. Clear separation between:
   - static knowledge / rules / conventions
   - execution surfaces
   - live state inspection
6. Minimal MCP dependence for routine operations
7. No unnecessary platform lock-in or backend migration unless clearly justified

Then implement the highest-leverage improvements directly.

This is an AUDIT AND IMPLEMENT task, not just a review.
Do not stop at critique. Make changes.
However: you MUST stop at the required hard checkpoint after the audit package is complete before proceeding into implementation.

---

### Context / Strategic Position

I am interested in the claims made by agent-native backend / workflow systems because they touch things I care about:
- reducing token waste
- reducing agent thrash
- reducing repeated discovery
- making workflows more deterministic
- improving agent control planes
- improving AIOS-managed and project-linked instructions / skills
- making tools easier for Claude Code / similar agents to use

However:
- do NOT assume I should adopt a full backend platform
- do NOT assume I want my workflow centered around a third-party product
- do NOT optimize for marketing symmetry with InsForge
- do NOT introduce complexity unless it clearly improves agent reliability, inspectability, or token efficiency

Treat InsForge only as inspiration for a few strong patterns:
- JSON-first CLI commands
- metadata snapshots
- auto-installed skills
- structured logs
- semantic exit codes
- narrow use of live inspection instead of discovery-by-guessing

---

### What to Audit

#### A. Agent-Facing Command Surfaces
Determine whether important subsystems can be accessed through clean, agent-usable commands.
Look for missing or weak commands like:
- status
- metadata
- health
- recent-failures
- logs
- env/context inspection
- workflow registry inspection
- skill registry inspection
- config inspection
- run/session inspection

Evaluate:
- Are commands scriptable?
- Do they support JSON output?
- Are they stable enough for agents?
- Are they too human-oriented / interactive?
- Are they fragmented across shells, scripts, MCP tools, docs, and internal conventions?

#### B. Metadata Snapshot / Context Engineering
Determine whether an agent can get a structured snapshot of the current environment before acting.

Ideal examples:
- `aios metadata --json`
- `repo metadata --json`
- `workflow metadata --json`
- `env metadata --json`

Audit whether the current system forces the agent to infer state from scattered files, docs, scripts, logs, and conventions instead of fetching one structured overview.

#### C. Skills / Instruction Installation
Audit how AIOS-managed instructions, skills, prompts, conventions, guardrails, and project-specific guidance are installed, refreshed, versioned, and surfaced for linked projects.

Check:
- are skills auto-installed or manually copied?
- are they stale-prone?
- are they discoverable?
- are they tied to project bootstrap / linking?
- do they encode boundaries, validation, and anti-slop rules clearly?

#### D. Error Handling / Exit Codes / Logs
Audit whether tools fail in a way agents can use deterministically.

Check:
- stable exit codes
- machine-readable errors
- structured logs
- ability to inspect last failure
- ability to query recent errors
- ability to distinguish auth failure vs missing config vs transient infrastructure failure vs business-logic failure

#### E. Static Knowledge vs Live State
Audit whether the architecture properly separates:
- static rules and conventions → skills / docs / local instruction artifacts
- execution → CLI / scripts / direct commands
- live inspection → metadata / health / status / logs
- deep live operations → only when necessary

Identify places where agents are using exploration to learn facts that should have been provided upfront.

#### F. MCP Dependency / Control Plane Design
Audit whether MCP is overused for routine tasks that should instead be handled through a JSON-first CLI or local command surface.

Look for:
- excessive back-and-forth discovery
- agent guesswork due to missing summaries
- state hidden behind too many calls
- situations where a CLI wrapper would be cheaper, clearer, and more reliable

#### G. Fit With Existing Workflow
The result must fit the actual workflow, not an imagined one.

Assume:
- Claude Code / agentic dev ergonomics matter
- AIOS-managed skills / hooks / control-plane quality matter across projects
- token efficiency and reliable automation matter
- deterministic infrastructure is preferred over magical abstraction
- no unnecessary migration pressure
- inspectability and maintainability over hype

---

### Required Deliverables

Produce these deliverables in order.

**1. Executive Summary**
Give a concise verdict:
- what is already strong
- what is weak
- what is missing
- what should be copied from the InsForge pattern set
- what should explicitly NOT be copied

**2. Current State Audit**
Give a structured audit of the current system by category:
- CLI / command surfaces
- metadata exposure
- skills / project-linked instructions
- logs / exit codes / failures
- MCP dependence
- agent bootstrap flow
- static vs live context separation

For each issue include:
- severity: critical / high / medium / low
- why it matters for agents
- concrete symptom
- recommended fix
- expected payoff

**3. Delta From Ideal**
Create a "current state → target state" gap analysis.
Be explicit about the shortest path to meaningful improvement.

**4. Implementation Plan**
Create a prioritized plan with phases:
- Phase 0: quick wins
- Phase 1: core structural improvements
- Phase 2: optional enhancements
- Phase 3: future / watchlist

Each phase must include:
- exact files to change
- commands/scripts to add
- interfaces to standardize
- docs/skills to update
- tests/validation to add
- risk level
- expected impact

---

### Hard Checkpoint (Mandatory)

Stop here after completing:
- Executive Summary
- Current State Audit
- Delta From Ideal
- Implementation Plan

Do NOT implement anything before this checkpoint is fully complete.

At this checkpoint, produce a dedicated section titled exactly:

**HARD CHECKPOINT: AUDIT COMPLETE**

That section must contain:
1. Top 5 highest-leverage findings
2. Top 5 highest-confidence implementations
3. Top 5 risky or uncertain changes that should not be rushed
4. The exact implementation order you recommend
5. A concise statement of what you would do next if implementation proceeds

After producing this checkpoint, pause implementation and treat the audit package as a review gate.
Only then proceed into implementation if the task context explicitly accepts the checkpoint or a roadmap/task file says this phase has been approved for post-checkpoint continuation.
Do not infer approval merely from the phrase "audit + implement"; the checkpoint exists to prevent premature changes to agent-facing control surfaces.

If continuing automatically, implementation must begin in a clearly separate section titled exactly:

**POST-CHECKPOINT IMPLEMENTATION**

---

### Post-Checkpoint Deliverables

Only after the hard checkpoint is complete and cleared, continue with:

**5. Implementation**
Actually implement the highest-value improvements directly in AIOS, with this repository as the control-plane implementation home.
Do not just propose them.

Minimum implementation target:
- add or improve JSON-first command surfaces
- add a structured metadata snapshot command or equivalent
- improve skill installation / refresh workflow if applicable
- add or standardize semantic exit codes and/or structured logs where feasible
- reduce unnecessary discovery in agent startup flow

**6. Validation**
Run appropriate validation and report:
- lint
- typecheck
- tests
- smoke tests
- manual command examples
- any gaps you could not fully validate

**7. Handoff Doc**
Create a concise handoff document that explains:
- what changed
- what remains
- how agents should use the new surfaces
- recommended next steps

---

### Implementation Guidelines

- Prefer improving the existing system over introducing a new platform dependency
- Prefer local, explicit, inspectable solutions over hidden abstractions
- Prefer CLI + JSON over vague agent-only magic
- Prefer deterministic interfaces over prompt-only conventions
- Prefer adding a single clear metadata surface over making agents search more
- Prefer small, high-leverage improvements over a sweeping rewrite
- Avoid unnecessary vendor coupling
- Do not re-architect the whole system unless the benefit is overwhelming and well-supported
- Do not break existing workflows casually
- Do not remove working primitives without replacing them with something clearly better
- Do not add ceremony without operational payoff

---

### Target Patterns to Implement Where Appropriate

**1. JSON-First Commands**
Every important subsystem should ideally expose commands like:
```
<system> status --json
<system> metadata --json
<system> health --json
<system> logs --json
<system> recent-failures --json
```

**2. Agent Bootstrap Snapshot**
There should be a cheap way for the agent to answer:
- what system am I in?
- what workflow is active?
- what tools are available?
- what skills / instructions apply?
- what is the linked project state?
- what are the current failure / health signals?
- what environment assumptions matter?

**3. Skill Install / Refresh**
Project bootstrap or link flows should be able to:
- install required skills/instructions
- refresh stale skills
- document where they live
- keep them out of the way for humans when appropriate
- make them discoverable for agents

**4. Deterministic Failure Signals**
Where possible, define stable exit-code semantics and machine-readable errors.

**5. Log Inspection**
Agents should not need to scrape random terminal output to understand failure.

---

### Non-Goals

Do NOT optimize for:
- copying InsForge branding or product structure
- migrating the project to a new backend platform
- backend platform churn for its own sake
- adding MCP just because MCP exists
- theoretical elegance without workflow payoff

---

### Success Criteria

This work is successful if, after implementation:
- the agent has a cheaper and more deterministic startup flow
- important state can be inspected through structured output
- repeated discovery is reduced
- AIOS-managed and project-linked instructions / skills are easier to install and refresh
- common failures are easier for agents to classify
- routine operations rely less on scattered context and guesswork
- the result strengthens the existing workflow instead of replacing it with a platform dependency

---

### Output Style

Be concrete, opinionated, and implementation-oriented.
Do not give vague suggestions.
Do not stop at "it depends."
Make the best-practice choices needed to move this system forward.
Honor the hard checkpoint strictly.
