# AIOS Control Plane Audit

Date: 2026-04-18
Scope: `aios-ui/`, `bin/`, `services/`, `docs/`, live `~/AIOS/data/aios.db`

## 1. Current-State Summary

AIOS already has meaningful foundations:

- A durable operational store in `~/AIOS/data/aios.db`
- Hook-driven ingestion for sessions, prompts, tool events, artifacts, and bugs
- A documented four-store contract in [docs/STORES.md](/Users/jakyeamos/AIOS/docs/STORES.md)
- A pattern/rule pipeline and domain-file generation path
- A Code Topology Service prototype in `services/cts/`
- A local Next.js UI in `aios-ui/` over SQLite via tRPC

The live database is non-trivial:

- `projects`: 17
- `sessions`: 105
- `tool_events`: 4966
- `prompts_used`: 484
- `artifacts`: 4214
- `bug_log`: 114
- `patterns`: 731
- `ai_history_imports`: 552

What is actually shipped in the UI today is narrower than the system vision:

- command-center metrics
- run inspection
- prompt/pattern browsing
- project lists
- workflow and cost reporting
- expectation tracking

The UI is strongest as an observability console for session telemetry. It is weak as a knowledge system, weak as a workflow OS, and only implicit as an orchestration layer.

## 2. Gap Analysis Against the Target AIOS Vision

### Knowledge UI

What exists:

- `projects`, `patterns`, `prompts`, and some supporting docs
- storage rules that distinguish canonical vs staging data
- vault search wrappers and generated domain files

What is missing:

- first-class page model for projects, decisions, workflows, systems, agents, and entities
- backlinks and typed relationships
- page summaries with drill-down sections
- explicit freshness/confidence/staleness markers in the UI
- relationship maps and navigation between knowledge surfaces

Assessment:
The current UI is dashboard-like and shallow. It does not yet support Wikipedia-style browsing or synthesis.

### Grounded Chat

What exists:

- prompt classification
- retrieval hints in `hook-prompt-submit.py`
- access to vault notes, handoffs, bugs, rules, and CTS summaries

What is missing:

- a real query surface
- structured answer generation from internal sources
- citation display
- explicit separation of facts vs inference vs recommendation
- inspectable retrieval trace

Assessment:
Grounding exists as a hidden hook behavior, not as a first-class product surface.

### Orchestration / Control Plane

What exists:

- session-start packet generation
- some active rules injection
- workflow metrics tables
- CTS context enrichment

What is missing:

- agent registry
- workflow registry
- orchestration run log
- task routing layer
- inspectable routing rationale
- durable packet history
- post-run memory updates tied to orchestration objects

Assessment:
AIOS influences orchestration today, but it does not visibly own orchestration.

### Briefing Packet Generation

What exists:

- startup packet generation in `bin/hook-session-start.py`
- handoff summaries and open-action extraction

What is missing:

- task-scoped briefing packets with explicit sections
- deterministic reusable packet generation
- packet inspectability in the UI
- packet history linked to tasks/runs/projects

Assessment:
The packet mechanism is useful but compact, implicit, and session-start-centric rather than delegation-centric.

### Durable Memory + Continuity

What exists:

- sessions, prompts, artifacts, bugs, patterns, imports
- handoff pointers and project note integration

What is missing:

- project memory snapshots
- preserved failed attempts in a queryable knowledge surface
- durable change summaries
- clear linkage from decisions to later implementation runs
- explicit state separation between knowledge and live workflow state

Assessment:
There is a lot of raw memory, but not enough usable memory architecture.

## 3. Major Architectural Flaws

### 3.1 Product/UI architecture is telemetry-first, not knowledge-first

`aios-ui` was intentionally designed as an operator dashboard. That made sense for the first product cut, but it now blocks the stated AIOS vision. The navigation begins from runs, prompts, workflows, costs, and alignment rather than from knowledge pages, project intelligence, or orchestration surfaces.

### 3.2 Knowledge, memory, and workflow state are conceptually documented but not explicitly modeled in the shipped app

`docs/STORES.md` already separates SQLite, vault, CTS, and staging, but `aios-ui` mostly collapses the product view down to session tables. The app has no first-class domain objects for:

- decision records
- briefing packets
- orchestration runs
- query results with retrieval traces
- knowledge pages and typed links

### 3.3 Orchestration is hidden inside hooks and prompts

The closest existing control-plane behavior lives in:

- `bin/hook-session-start.py`
- `bin/hook-prompt-submit.py`
- `bin/hook-stop.py`

Those scripts retrieve context and synthesize packets, but the reasoning is hidden inside operational scripts. There is no inspectable product surface that answers:

- why this context was chosen
- why this workflow was selected
- what packet was generated
- what changed after execution

### 3.4 State boundaries are blurred in implementation

Examples:

- `hook-stop.py` writes `handoff_path`, but the base schemas in [schema.sql](/Users/jakyeamos/AIOS/schema.sql) and [data/schema.sql](/Users/jakyeamos/AIOS/data/schema.sql) do not fully reflect the live state shape
- the UI treats prompts as “patterns” in [aios-ui/server/routers/patterns.ts](/Users/jakyeamos/AIOS/aios-ui/server/routers/patterns.ts), which muddies the intended knowledge model
- `insights.ts` is a 946-line aggregation module carrying too much cross-domain logic

### 3.5 Inspectability is incomplete

There is some explainability around metrics in `insights.ts`, but not for:

- retrieval
- routing
- packet construction
- knowledge freshness
- contradiction or drift

### 3.6 Existing docs describe stronger architecture than the shipped product

There is real design work in:

- [docs/STORES.md](/Users/jakyeamos/AIOS/docs/STORES.md)
- [docs/specs/2026-04-03-knowledge-layer-design.md](/Users/jakyeamos/AIOS/docs/specs/2026-04-03-knowledge-layer-design.md)
- [docs/superpowers/specs/2026-04-08-aios-code-topology-service-design.md](/Users/jakyeamos/AIOS/docs/superpowers/specs/2026-04-08-aios-code-topology-service-design.md)

But the current product is not organized around those ideas yet.

## 4. Highest-Leverage Opportunities

1. Make control-plane concepts first-class in `aios-ui`
2. Introduce explicit modules for knowledge, orchestration, briefing, grounded query, and change tracking
3. Replace dashboard-first navigation with knowledge/control/query-first navigation
4. Create durable orchestration run and packet tables
5. Add ADR support so architectural decisions become queryable product objects
6. Expose retrieval and routing traces directly in the product
7. Upgrade project pages into dossiers instead of recent-session lists

## 5. Proposed Target Architecture

### Layer 1: Durable knowledge

Canonical concepts:

- projects
- decisions / ADRs
- workflows
- agents
- systems
- patterns / rules / hypotheses
- related docs and artifacts

Responsibilities:

- browseable pages
- typed relationships
- freshness/confidence/status markers
- backlinks and recent changes

### Layer 2: Project memory

Responsibilities:

- recent sessions
- open loops
- failures and bugs
- active rules
- notable implementation history
- current state snapshots

### Layer 3: Live workflow/orchestration state

Responsibilities:

- current task routing
- chosen workflow template
- selected agent profile
- execution rationale
- run status
- post-run outcomes

### Layer 4: Briefing packets

Responsibilities:

- deterministic packet generation from the right layers
- inspectable packet sections
- run linkage and history

### Layer 5: Grounded query pipeline

Responsibilities:

- retrieve from internal sources only
- distinguish fact vs inference vs recommendation
- cite sources
- expose retrieval trace and assumptions

### Layer 6: Change intelligence

Responsibilities:

- recent system changes
- project-level changes
- notable decisions and run outcomes
- contradiction/drift hooks

## 6. Recommended Implementation Sequence

1. Establish repo truth file and audit artifact
2. Add control-plane schema for orchestration runs and briefing packets
3. Add ADR support and a typed knowledge-page repository
4. Build knowledge index + dossier pages
5. Build grounded query surface with inspectable citations
6. Add control-plane page for routing + packet generation + run history
7. Upgrade project pages to show memory, decisions, changes, and related entities
8. Move remaining dashboard/reporting pages behind the knowledge/control-plane navigation

## 7. Risks and Tradeoffs

### Tradeoff: derived knowledge vs manual curation

This pass should favor explicit derived knowledge pages and inspectable generation, not fully automated canonical wiki authoring. That keeps the system reliable without pretending it has human-grade curation.

### Risk: schema drift

The live database already appears ahead of the checked-in schemas in places. New control-plane tables must be created idempotently and not assume a pristine schema.

### Risk: feature breadth

The full target vision is larger than one pass. The right move is to establish durable architecture and a continuation path, not to ship shallow versions of every requested capability.

### Tradeoff: deterministic grounded query instead of full LLM chat

For this pass, an inspectable, deterministic query layer is more valuable than a magical chat box with weak provenance.

### Risk: UI churn

Changing navigation and information architecture is disruptive, but preserving the current dashboard model would lock in the wrong product shape.

## Bottom Line

AIOS has enough raw infrastructure to become a real knowledge/workflow/orchestration system, but the product and state model lag behind the infrastructure. The highest-leverage move is to make knowledge, orchestration, briefing packets, and grounded query first-class objects in the app and data model, then rebuild the UI around those concepts.
