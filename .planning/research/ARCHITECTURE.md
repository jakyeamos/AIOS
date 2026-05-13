# AIOS Architecture Research

Date: 2026-05-13

## Purpose

This note summarizes how local-first AI orchestration platforms and personal agent operating systems are typically structured, then tailors that model to AIOS as it exists today. The goal is not a greenfield rewrite. The goal is a clearer target architecture for converging the current brownfield system into a coherent local-first control plane for agent work.

## Executive View

Systems in this category usually succeed when they separate five concerns cleanly:

1. intent intake and routing
2. execution orchestration
3. durable state and evidence
4. context and knowledge compilation
5. operator inspection and governance

AIOS already has real pieces of each:

- intent and orchestration entrypoints in `bin/` and `services/`
- durable state in `data/aios.db`, `logs/`, `staging/`, and file-backed artifacts
- context compilation in `aios/context/` plus `tools/context-compile.mjs`
- governance through workflow registries, success criteria, writebacks, and audits in `config/` and `services/`
- operator inspection in `aios-ui/`

The architecture recommendation is therefore not "build a smarter chat app." It is "tighten AIOS into an explicit control plane with authoritative write paths, deterministic context assembly, governed execution, and durable learning."

## Typical Reference Architecture For Local-First Agent OS Systems

### 1. Intent And Session Layer

This layer receives vague goals, session hooks, CLI commands, or UI-triggered tasks and turns them into a normalized work request. In strong systems, this layer does not execute core logic directly. It creates a task envelope with:

- user or agent intent
- selected project or workspace
- current session identity
- requested workflow shape
- trust level and approval requirements
- links to prior runs, memory, and evidence

For AIOS, this maps to `bin/aios.py`, session hooks, and the run and invocation handshake already referenced across the control-plane code.

### 2. Routing And Planning Layer

This layer answers:

- what project does this belong to
- what context should load
- what workflow should run
- what backend or agent profile should execute it
- what standards and success criteria apply

In mature systems, routing is partly deterministic and partly heuristic, but it always emits a trace that can be inspected later. Silent or implicit routing becomes unmaintainable quickly.

For AIOS, the existing registries in `config/workflows/`, `config/execution-strategies/`, `config/success-criteria/`, and the context compiler are the natural foundation for this layer.

### 3. Execution Control Plane

This is the system nucleus. It owns run state, invocation identity, workflow stages, artifacts, evaluator calls, retries, and approval gates. It should be authoritative for writes and for the lifecycle of work in progress.

Strong local-first systems usually keep this layer thin in protocol and strict in state transitions:

- create run
- attach packet and criteria
- launch invocation
- record events and artifacts
- evaluate outcome
- queue writebacks or approvals
- close run with unresolved deltas visible

For AIOS, this clearly belongs in Python services rather than in the UI. The repository already follows that direction.

### 4. Context Compilation Layer

This layer is separate from transient execution. Its job is to decide what the agent should know before it acts. In local-first systems, this is usually file-backed because human-editable source material is a strategic advantage and easier to govern than opaque embeddings-only behavior.

Typical responsibilities:

- select standards, domain guidance, feature packets, and handoffs
- emit a compact packet for execution
- emit a receipt explaining loaded and skipped context
- suggest writebacks when reusable knowledge is missing or stale

AIOS already has an unusually strong implementation direction here. The current split between file-backed context authority and SQLite-backed runtime state is correct and should be preserved.

### 5. Durable Knowledge And Memory Layer

These systems need memory, but the best versions distinguish between:

- canonical knowledge
- operational evidence
- ephemeral staging
- learned proposals pending approval

If all four are mixed, memory quality collapses. Good systems store observed facts and traces durably, but promote reusable knowledge only through a governed writeback path.

AIOS already reflects this pattern with `aios/context/`, `docs/`, `logs/`, `staging/`, writebacks, and knowledge surfaces. The main architectural need is stronger boundary language and more consistent promotion rules.

### 6. Governance And Evaluation Layer

Local-first agent systems become noisy or unsafe unless evaluation is first-class. The mature pattern is:

- criteria registry
- run-time evidence capture
- post-execution evaluation
- blocker vs warning classification
- explicit approvals for consequential writebacks

AIOS already contains much of this in success criteria, standards health, workflow approvals, and lifecycle audits. That is a major brownfield advantage and should remain central rather than treated as secondary tooling.

### 7. Operator Read Layer

The UI should explain and inspect the control plane, not replace it. In this class of system, the UI is best treated as a read layer plus a few carefully scoped control actions:

- inspect current runs
- inspect routing traces and packets
- inspect health and drift
- review pending approvals and writebacks
- query knowledge and project truth

This matches AIOS's current Next.js dashboard direction.

## Major Components Recommended For AIOS

### A. Intent Intake

Responsibilities:

- receive vague goals, hook events, operator commands, and UI actions
- normalize them into a work request
- bind them to project, session, and actor identity

Current AIOS anchors:

- `bin/aios.py`
- `bin/hook-session-start.py`
- `bin/hook-prompt-submit.py`
- related lifecycle entrypoints in `bin/`

Boundary:

- no domain decision logic should live only in a UI route or ad hoc script

### B. Project And Context Resolver

Responsibilities:

- choose project
- choose standards and domain packets
- select feature and task packets
- emit context packet and receipt

Current AIOS anchors:

- `tools/context-compile.mjs`
- `aios/context/`
- project and routing helpers in Python and UI mirrors

Boundary:

- file-backed context remains authoritative for what should load
- runtime state may reference compiled packets, but should not replace source context files as authority

### C. Workflow Router

Responsibilities:

- choose workflow template
- choose execution strategy
- choose invocation backend and agent profile
- emit a selection trace with reasons

Current AIOS anchors:

- `config/workflows/registry.json`
- `config/workflows/skills.json`
- `config/execution-strategies/*`
- orchestration services in `services/`

Boundary:

- routing policy belongs in registries and control-plane services, not scattered across prompts, UI code, and shell scripts

### D. Run And Invocation Manager

Responsibilities:

- create and advance run state
- create invocation records
- track stage transitions, artifacts, and links to sessions
- enforce approval gates and completion rules

Current AIOS anchors:

- orchestration services
- invocation backend contracts
- control-plane database tables and UI inspection routes

Boundary:

- this should remain the authoritative write owner for run lifecycle

### E. Evidence And Artifact Store

Responsibilities:

- persist structured runtime state in SQLite
- persist logs, receipts, generated artifacts, and staged writebacks on disk
- preserve source attribution and timestamps

Current AIOS anchors:

- `data/aios.db`
- `logs/`
- `staging/`
- generated context receipts and compiled packets

Boundary:

- SQLite stores operational state and queryable facts
- filesystem stores human-readable artifacts, source material, and generated evidence

### F. Evaluation And Delta Engine

Responsibilities:

- evaluate outcomes against success criteria and standards
- compute blockers, warnings, unresolved deltas, and trust signals
- feed operator views and learning loops

Current AIOS anchors:

- `services/success_criteria.py`
- `services/standards_health.py`
- supporting registries in `config/success-criteria/` and `config/standards/`

Boundary:

- evaluation should consume execution evidence, not guess from final text alone

### G. Knowledge Promotion And Learning

Responsibilities:

- transform repeated evidence into candidate workflow, prompt, packet, or truth-file updates
- require approval where promotion is consequential
- separate proposals from accepted canon

Current AIOS anchors:

- writeback flows
- workflow synthesis and experiment services
- knowledge and learning surfaces in the UI

Boundary:

- learned proposals are not canonical until approved

### H. Operator UI

Responsibilities:

- expose control-plane state
- expose packet, trace, approval, and evaluation visibility
- allow bounded operator actions

Current AIOS anchors:

- `aios-ui/app/`
- `aios-ui/server/`

Boundary:

- UI mirrors system state
- core business authority stays in Python services, registries, SQLite, and file-backed context

## Recommended Data Flow For AIOS

The most important AIOS flow should be:

1. vague goal or hook event enters through CLI or lifecycle hook
2. intake layer binds session, project candidate, and actor
3. context compiler selects standards, domain, feature, and handoff material
4. workflow router selects workflow, strategy, backend, and approval posture
5. run manager creates run, invocation, packet reference, and criteria attachment
6. execution backend runs the task and streams artifacts, logs, and events
7. evaluation layer scores the result against criteria, standards, and observed evidence
8. learning layer emits writeback proposals, truth updates, or workflow synthesis candidates
9. operator UI exposes completed work, unresolved deltas, and approvals
10. approved writebacks promote durable memory back into canonical sources

That flow preserves AIOS's desired properties:

- local-first
- explainable
- reviewable
- durable
- agent-centered

## Boundaries AIOS Should Preserve Aggressively

### 1. Control Plane vs UI

The UI should never become the hidden source of workflow truth. It can initiate actions and inspect results, but the authoritative state machine belongs in services and registries.

### 2. Runtime State vs Context Authority

SQLite should track runs, events, evaluations, approvals, and indices. It should not replace `aios/context/` as the editorial source of standards, packets, and handoffs.

### 3. Canonical Knowledge vs Staging

Generated suggestions, agent scratch output, and experimental learnings must stay out of canonical truth until promoted intentionally.

### 4. Routing Policy vs Prompt Text

Workflow choice, backend selection, approval rules, and success criteria should come from registries and services. Prompts should consume those decisions, not silently redefine them.

### 5. Execution Evidence vs Narrative Summary

Agent summaries are useful, but evaluation should anchor to artifacts, files changed, logs, receipts, and persisted run facts.

### 6. Shared Platform vs Specialized Subsystems

CTS, workflow experiments, standards health, and knowledge search should remain bounded subsystems. They may publish signals into the control plane, but they should not merge into one indistinct service blob.

## Brownfield Assessment Of AIOS Against The Reference Model

### Strong Existing Foundations

- file-backed context compiler with receipts already exists
- Python control-plane pattern already exists
- workflow and strategy registries already exist
- success-criteria and standards-evaluation primitives already exist
- UI is already mostly a read and inspection surface
- writeback and approval concepts already exist

### Current Architectural Risks

- authority may feel split unless run state, routing, context, and writeback promotion are named more explicitly as separate ownership zones
- policy may drift if backend choice, workflow choice, and context selection are implemented in too many places at once
- learning loops can degrade trust if proposals and canonical truth are not visibly separated everywhere
- brownfield breadth can create "many useful subsystems, weak single spine" unless the canonical end-to-end flow is treated as the product center

### Architectural Thesis For AIOS

AIOS should treat the canonical product as:

"A local control plane that converts intent into governed execution by compiling context, selecting workflows, tracking run state, evaluating outcomes, and promoting approved learning back into durable project truth."

That thesis is specific enough to guide boundaries and broad enough to absorb current subsystems without a rewrite.

## Suggested Build Order For AIOS

The right build order is not feature-by-feature UI expansion. It is spine-first convergence.

### Phase 1. Normalize The Canonical Run Contract

Priority:

- one authoritative run envelope
- one authoritative invocation handshake
- one place to attach packet, criteria, workflow, strategy, and backend

Why first:

- every other layer depends on run identity and comparable evidence

Likely AIOS focus:

- tighten shared contracts between `bin/`, `services/`, SQLite schema usage, and `aios-ui/server/aios/control-plane.ts`

### Phase 2. Harden Deterministic Context Assembly

Priority:

- make packet selection reproducible
- keep receipts first-class
- make loaded vs skipped context visible on every serious run

Why second:

- context quality determines downstream execution quality more than dashboard polish does

Likely AIOS focus:

- strengthen packet references from runs back to compiled receipt and source context

### Phase 3. Consolidate Workflow Routing

Priority:

- central workflow selection trace
- explicit backend and agent-profile choice
- explicit approval posture

Why third:

- intent-to-execution coherence is impossible if routing policy is fragmented

Likely AIOS focus:

- registry-driven routing with fewer parallel sources of truth

### Phase 4. Standardize Evidence Capture And Evaluation

Priority:

- attach artifacts and observed outputs to runs
- evaluate using actual evidence
- surface blocker vs warning outcomes consistently

Why fourth:

- learning and trust both depend on reliable evaluation

Likely AIOS focus:

- unify success criteria, standards deltas, lifecycle audits, and workflow reports around shared run evidence

### Phase 5. Formalize Knowledge Promotion

Priority:

- separate suggestion, staging, proposal, approval, and canonical promotion states
- make writeback lineage inspectable

Why fifth:

- this is where AIOS compounds value instead of acting as a transient runner

Likely AIOS focus:

- durable writeback metadata and stronger promotion contracts into `PROJECT.md`, context files, docs, or registries

### Phase 6. Unify Operator Views Around The Canonical Flow

Priority:

- one operator story from intent to packet to run to evaluation to writeback
- fewer disconnected dashboards

Why sixth:

- once the spine is stable, the UI can explain it cleanly instead of compensating for ambiguity

Likely AIOS focus:

- align `/control`, `/runs`, `/workflows`, `/projects`, and knowledge views around the same identifiers and traces

### Phase 7. Expand Adaptive Learning And Automation Carefully

Priority:

- workflow synthesis
- proposal ranking
- retrieval and routing improvement
- recurring maintenance loops

Why last:

- adaptive systems amplify whatever foundation exists; they should not be trusted before the control plane is legible

## Practical Recommendations For AIOS

### Recommended Core Authorities

- `aios/context/`: canonical editorial source for standards, packets, handoffs, and routing context
- `config/`: canonical machine-readable policy source for workflows, strategies, criteria, and enforcement
- `services/`: canonical business logic and write authority for orchestration, evaluation, and learning
- `data/aios.db`: canonical queryable operational state
- `logs/` and generated artifacts: canonical execution evidence
- `aios-ui/`: operator read and bounded action surface

### Recommended Cross-Component Contracts

- every serious run gets a stable run id, invocation id, packet reference, receipt reference, workflow key, strategy key, backend key, and evaluation record
- every routing decision emits a machine-readable selection trace
- every writeback proposal records source evidence, target authority, approval requirement, and promotion status
- every UI page that claims system truth reads from the same underlying identifiers and control-plane records

### Recommended Architectural Question To Use As A Gate

For any new subsystem or feature, ask:

"Does this strengthen the canonical intent -> packet -> run -> evidence -> evaluation -> writeback loop, or does it create another side path?"

If it creates another side path, it should be redesigned or explicitly isolated as an experiment.

## Final Recommendation

AIOS already resembles the architecture of a serious local-first agent OS more than most systems do. Its main need is not new categories of capability. Its main need is convergence around one explicit control-plane spine with clearly named authorities, contracts, and promotion paths.

The best architectural direction is:

- preserve the file-backed context compiler as a first-class authority
- preserve Python as the write-owning control plane
- preserve SQLite plus filesystem artifacts as dual durable substrates
- preserve the UI as inspection-first
- strengthen the canonical end-to-end run flow until it becomes the clear center of the whole product

If AIOS executes that build order, the existing brownfield architecture can evolve into a coherent personal agent operating system without discarding the subsystems it already has.
