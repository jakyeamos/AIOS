# Phase 1: Project, Workflow, And Prompt Routing - Research

**Researched:** 2026-05-16
**Domain:** AIOS routing and orchestration control plane
**Confidence:** HIGH

## User Constraints

### Locked Decisions

#### Route Result Contract
- **D-01:** Phase 1 should introduce an explicit route-result contract rather than returning loosely shaped routing data from multiple helpers.
- **D-02:** The route result must persist at least: route id, objective, project candidate set, final project target or ambiguity block, task family, selected workflow, selected prompt/handoff family, recommended execution surface, rationale, and timestamp.
- **D-03:** Ambiguity is a valid route outcome. The system must block unsafe project guesses when multiple plausible projects fit the request.

#### Project Resolution
- **D-04:** Project resolution should be inventory-backed and candidate-based, not a single direct string match.
- **D-05:** Project resolution must support four explicit outcomes: exact match, likely match, ambiguous match, and unsupported/no match.
- **D-06:** Candidate reasoning should be preserved in route metadata so later query and operator surfaces can explain why a project won or why the route blocked.

#### Task Family And Workflow Selection
- **D-07:** Task-family classification should be implemented as a separate step from workflow selection so AIOS can explain both layers independently.
- **D-08:** Phase 1 should harden the early default serious-work routes first: `implementation-delivery`, `failure-recovery`, `audit-only`, `audit-and-implement`, and `agent handoff generation`.
- **D-09:** Workflow selection should prefer the smallest sufficient governed workflow rather than a generic implementation route.
- **D-10:** Route rationale must record nearby alternatives and why they lost, especially for `audit-only` vs `audit-and-implement`, `implementation-delivery` vs `failure-recovery`, and handoff-only vs execution workflows.

#### Prompt And Handoff Family Selection
- **D-11:** Prompt selection belongs in routing at the family level first; detailed prompt asset lifecycle and promotion can remain a later phase concern.
- **D-12:** The route must identify a prompt or handoff family even when the best available asset is only partial or candidate quality; in that case the fallback state should be explicit in route metadata.
- **D-13:** Existing prompt registry data should be extended toward prompt-family recommendation rather than replaced with a disconnected system.

#### Execution Surface Recommendation
- **D-14:** Route results should recommend an invocation backend or execution surface based on workflow constraints, not generic preference.
- **D-15:** Codex-managed runtime should be treated as the preferred surface for Codex serious-work routes when its required workflow constraints are satisfied.
- **D-16:** Manual legacy execution should never be the default route recommendation when a managed runtime is available.

#### Persistence And Observability
- **D-17:** Route decisions must be stored durably enough to be reused by Phase 2 packet compilation and later run/evaluation/operator views.
- **D-18:** Phase 1 success depends on inspectability. The system should preserve route rationale, selected alternatives, and fallback states in machine-readable form rather than prose-only logs.

### Claude's Discretion
- exact scoring heuristics for candidate ranking
- schema shape and storage location for route metadata, as long as it remains durable and inspectable
- whether to implement routing as a dedicated module or as a bounded extension of existing workflow/orchestration surfaces
- the precise mapping layer between prompt templates, prompt families, and workflow families

### Deferred Ideas
- Full packet compilation quality and receipt expansion belong to Phase 2.
- Rich lifecycle state and resume semantics belong to Phase 3.
- Governed truth-update and approval workflows belong to Phases 4 and 5.
- Full asset lifecycle, promotion/deprecation policy, and workflow-library scoring belong to Phases 8 and 9.

## Summary

AIOS already has most of the primitives needed for a credible Phase 1 route layer, but they are distributed and only partially composed. The strongest reusable surfaces are the typed workflow registry loader in `services/workflow_orchestration.py`, the task-family and per-surface strategy catalog in `services/execution_strategy.py`, the explicit backend contract in `services/invocation_backends.py`, the prompt metadata in `prompts/registry.json`, and the existing `start-work` orchestration tables and packet path in `services/aios_cli.py`. [VERIFIED: services/workflow_orchestration.py] [VERIFIED: services/execution_strategy.py] [VERIFIED: services/invocation_backends.py] [VERIFIED: prompts/registry.json] [VERIFIED: services/aios_cli.py]

The largest gap is not missing infrastructure. It is missing composition and missing contract clarity. Project resolution is currently weak and inventory-centric but not route-centric, the workflow registry only exposes two default implementation-focused task families plus bounded side workflows, prompt selection currently happens as a light template match rather than a route-result contract, and `start-work` still depends on user-supplied `--project`, `--workflow`, `--agent`, and `--backend` values instead of deriving them from a deterministic route decision. [VERIFIED: services/project_inventory.py] [VERIFIED: config/workflows/registry.json] [VERIFIED: bin/hook-prompt-submit.py] [VERIFIED: services/aios_cli.py]

**Primary recommendation:** extend the existing workflow/strategy/orchestration stack with a first-class route-result contract and routing module, then thread that result into `start-work`, persistence tables, and later packet/operator consumers instead of building a separate routing subsystem.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Project candidate generation and ambiguity blocking | Python control plane (`services/`, CLI/runtime) | UI query/control views | Route resolution is operational logic first, operator inspection second. [VERIFIED: services/project_inventory.py] |
| Task-family classification | `services/execution_strategy.py` and routing layer | workflow registry | The strategy catalog already owns task-family semantics by surface. [VERIFIED: services/execution_strategy.py] |
| Workflow selection | `services/workflow_orchestration.py` | `.planning/WORKFLOW_MATRIX.md` for contract truth | The workflow registry already defines stage-based workflow identities. [VERIFIED: services/workflow_orchestration.py] [VERIFIED: config/workflows/registry.json] |
| Prompt/handoff family recommendation | prompt registry + routing layer | hook/UI prompt telemetry | Prompt assets already exist, but route-time family selection does not. [VERIFIED: prompts/registry.json] [VERIFIED: bin/hook-prompt-submit.py] |
| Execution-surface recommendation | `services/invocation_backends.py` + strategy surface mapping | CLI defaults | Backend contracts and surface concepts already exist and should stay authoritative. [VERIFIED: services/invocation_backends.py] |
| Route persistence and retrieval | orchestration tables / packet spine | operator/query routers | Existing `orchestration_runs`, `orchestration_invocations`, and `briefing_packets` already form the durable spine. [VERIFIED: services/aios_cli.py] [VERIFIED: schema.sql] |

## Standard Stack

### Core

| Library / Surface | Version | Purpose | Why Standard |
|-------------------|---------|---------|--------------|
| Python 3.12+ dataclasses + typed registry loaders | repo runtime target | stable route/workflow/strategy contracts | Existing control-plane code already uses dataclasses and explicit schema validation for critical registries. [VERIFIED: services/workflow_orchestration.py] [VERIFIED: services/execution_strategy.py] |
| JSON registries under `config/` and `prompts/` | current repo files | workflow, skill, strategy, and prompt metadata | AIOS already treats file-backed registries as the authoritative change surface for routing-related metadata. [VERIFIED: config/workflows/registry.json] [VERIFIED: config/workflows/skills.json] [VERIFIED: config/execution-strategies/strategies.json] [VERIFIED: prompts/registry.json] |
| SQLite orchestration tables | current schema | durable runs, invocations, packets, and later route metadata | Existing orchestration state is already persisted here and can absorb Phase 1 route persistence. [VERIFIED: schema.sql] [VERIFIED: services/aios_cli.py] |

### Supporting

| Surface | Purpose | When to Use |
|---------|---------|-------------|
| `services/project_inventory.py` | project discovery / inventory sync | use for candidate project population and stable project ids, not for full route logic by itself. [VERIFIED: services/project_inventory.py] |
| `bin/hook-prompt-submit.py` | prompt telemetry and lightweight prompt-template match heuristics | reuse its classification and template-match ideas as inputs, but do not let it become the authoritative route system. [VERIFIED: bin/hook-prompt-submit.py] |
| `aios-ui/server/routers/workflows.ts` and `prompts.ts` | operator visibility over workflows and prompts | use after persistence exists; they are read-side consumers, not the routing source of truth. [VERIFIED: aios-ui/server/routers/workflows.ts] [VERIFIED: aios-ui/server/routers/prompts.ts] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| extending current registries and orchestration tables | build a separate route engine or standalone service | creates duplicated truth and a second contract surface to keep in sync with existing workflow/prompt/runtime systems |
| inventory-backed project candidate resolution | free-text direct project matching only | simpler to implement, but cannot explain ambiguity or support multi-project routing safely |
| route-time prompt family recommendation | defer all prompt choice to packet generation or the hook | easier short term, but leaves the most important execution-shape decision implicit |

**Installation:** No new external dependency is required for Phase 1 if the implementation stays inside the current Python + JSON + SQLite control plane. [VERIFIED: services/workflow_orchestration.py] [VERIFIED: services/execution_strategy.py]

## Architecture Patterns

### System Architecture Diagram

```text
vague goal
  -> project candidate generation
  -> ambiguity gate
      -> blocked route (if ambiguous or unsupported)
      -> task-family classification
          -> workflow selection
              -> prompt/handoff family selection
              -> execution-surface recommendation
                  -> persisted route result
                      -> start-work / packet compilation / operator inspection
```

### Recommended Project Structure

```text
services/
├── workflow_orchestration.py      # workflow registry loading and workflow assembly
├── execution_strategy.py          # task-family and per-surface strategy selection
├── invocation_backends.py         # backend contract definitions
├── project_inventory.py           # project discovery and stable project ids
└── [new routing module]           # project + workflow + prompt + backend route-result composition

config/
├── workflows/
│   ├── registry.json              # governed workflow identities
│   └── skills.json                # workflow-skill bindings
└── execution-strategies/
    ├── task-specs.json            # task-family semantics
    └── strategies.json            # per-surface strategy bundles

prompts/
└── registry.json                  # prompt template metadata and future family mapping
```

### Pattern 1: Typed Registry Loading
**What:** Load workflow, skill, and strategy catalogs into typed structures with validation before route logic consumes them.
**When to use:** For all routing decisions that depend on stable workflow/task/backend metadata.
**Example:** `load_workflow_registry()` and `load_task_specs()` each validate expected object structure before returning typed specs. [VERIFIED: services/workflow_orchestration.py] [VERIFIED: services/execution_strategy.py]

### Pattern 2: Surface-Aware Strategy Selection
**What:** Select execution behavior through an explicit `task_family` x `surface` strategy bundle.
**When to use:** When recommending Codex vs Claude managed runtime behavior and the quality/validation profile should differ by surface.
**Example:** `strategies.json` already contains validated `audit_and_implement` bundles for both `codex` and `claude_code`. [VERIFIED: config/execution-strategies/strategies.json]

### Pattern 3: Durable Orchestration Spine
**What:** Persist authoritative run, invocation, and packet records and attach new routing metadata to that spine.
**When to use:** For all route outputs that later phases, audits, or UI surfaces need to inspect.
**Example:** `_start_work_payload()` already creates `orchestration_runs`, `briefing_packets`, and `orchestration_invocations` records in a single flow. [VERIFIED: services/aios_cli.py]

### Anti-Patterns to Avoid
- **Second routing stack:** do not invent a parallel routing subsystem disconnected from the existing workflow/strategy/prompt registries.
- **String-only route outcomes:** do not return a chosen workflow or project without candidate reasoning, ambiguity state, and nearby alternatives.
- **UI-owned routing logic:** do not move core route decisions into `aios-ui` routers; UI should inspect the result, not own it.
- **Prompt-template-only thinking:** do not treat prompt selection as “pick one template” without a family-level route contract and fallback state.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| workflow identities and stages | a new ad hoc workflow map in a routing module | `config/workflows/registry.json` + `services/workflow_orchestration.py` | Existing registry already captures stage kinds, validations, and skills. [VERIFIED: config/workflows/registry.json] |
| backend recommendation vocabulary | string constants scattered across CLI/UI code | `services/invocation_backends.py` | Backend contracts already define surface, transport, and handshake requirements. [VERIFIED: services/invocation_backends.py] |
| task-family semantics | custom hand-written routing labels unconnected to strategy bundles | `config/execution-strategies/task-specs.json` and `strategies.json` | Strategy catalogs already carry quality rubric, context profile, and per-surface rollout metadata. [VERIFIED: config/execution-strategies/task-specs.json] [VERIFIED: config/execution-strategies/strategies.json] |
| prompt metadata store | a second prompt catalog for routing | `prompts/registry.json` | The registry already stores classification, tags, purpose, and file mapping. [VERIFIED: prompts/registry.json] |
| run-persistence primitives | a new route-results table disconnected from runs/packets | existing orchestration tables, extended if necessary | Phase 1 outputs must feed later run/packet/operator surfaces. [VERIFIED: services/aios_cli.py] [VERIFIED: schema.sql] |

**Key insight:** Phase 1 is a composition problem, not a greenfield tooling problem. The safest path is to deepen current contracts and connect them, not proliferate new parallel abstractions.

## Common Pitfalls

### Pitfall 1: Treating project inventory as equivalent to route resolution
**What goes wrong:** The system can list or sync projects but still cannot resolve a vague objective safely.
**Why it happens:** `services/project_inventory.py` only normalizes repo discovery and stable ids; it does not rank candidates or explain ambiguity. [VERIFIED: services/project_inventory.py]
**How to avoid:** Build candidate ranking and ambiguity outcomes on top of inventory, not inside it.
**Warning signs:** route logic expects a single project id input or silently defaults to the current repo.

### Pitfall 2: Letting `start-work` remain manual
**What goes wrong:** Phase 1 appears implemented, but the main CLI path still requires the user to pass `--project`, `--workflow`, and `--backend`.
**Why it happens:** current `start-work` packet creation assumes those fields are already known. [VERIFIED: services/aios_cli.py]
**How to avoid:** add a route resolution step before packet creation and persist the route result into the existing `start-work` flow.
**Warning signs:** route metadata exists only in memory or tests, not in the actual CLI entrypoint.

### Pitfall 3: Prompt selection remains telemetry only
**What goes wrong:** prompt matching exists in hooks or UI but execution still starts from an empty shell.
**Why it happens:** current prompt routing logic is light-weight and classification-oriented, not part of a route-result contract. [VERIFIED: bin/hook-prompt-submit.py]
**How to avoid:** elevate prompt-family recommendation into the route result and treat template matching as an implementation detail of that layer.
**Warning signs:** workflow selection is logged, but no prompt/handoff family is stored with it.

### Pitfall 4: New route metadata bypasses the orchestration spine
**What goes wrong:** route explanations are hard to audit and cannot be reused by packets, runs, or UI.
**Why it happens:** developers store route decisions in transient helper returns or logs.
**How to avoid:** attach route identity and rationale to persisted run/packet/invocation state or a tightly linked route record.
**Warning signs:** packet generation or operator views need to re-run routing logic to answer “why this workflow?”

## Code Examples

### Workflow Registry Loading Pattern

```python
workflows = load_workflow_registry()
skills = load_skill_registry()
errors = validate_workflow_bindings(workflows, skills)
if errors:
    raise ValueError(errors[0])
```

Source pattern: typed workflow and skill registry loading in `services/workflow_orchestration.py`. [VERIFIED: services/workflow_orchestration.py]

### Strategy Bundle Selection Pattern

```python
task_specs = load_task_specs()
catalog = load_strategy_catalog()
errors = validate_strategy_catalog(task_specs, catalog)
if errors:
    raise StrategySelectionError(errors[0])
```

Source pattern: task-family and per-surface strategy validation in `services/execution_strategy.py`. [VERIFIED: services/execution_strategy.py]

### Durable Run + Packet Persistence Pattern

```python
run_id = f"run-{uuid.uuid4()}"
packet_id = f"packet-{uuid.uuid4()}"
invocation_id = f"invoke-manual-{uuid.uuid4()}"

conn.execute("INSERT INTO orchestration_runs (...) VALUES (...)", ...)
conn.execute("INSERT INTO briefing_packets (...) VALUES (...)", ...)
conn.execute("INSERT INTO orchestration_invocations (...) VALUES (...)", ...)
```

Source pattern: `_start_work_payload()` in `services/aios_cli.py`. [VERIFIED: services/aios_cli.py]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| manual workflow/backend selection at CLI entry | explicit workflow registries, strategy bundles, and backend contracts exist but are not yet unified into one route-result | current repo state as of 2026-05-16 | Phase 1 can be implemented as contract composition rather than foundational rewrites |
| prompt matching as side telemetry | prompt registry plus hook/UI surfaces already capture template metadata and some classification | current repo state as of 2026-05-16 | Phase 1 can promote prompt recommendation into the route path with less new infrastructure |

**Deprecated/outdated:**
- Treating `manual-session-legacy` as a normal default backend is outdated; the backend contract already marks it deprecated. [VERIFIED: services/invocation_backends.py]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The best Phase 1 persistence shape is likely an extension of existing orchestration or packet records rather than an entirely separate storage model. [ASSUMED] | Summary / Architecture Patterns | medium — the planner may need a dedicated route table if current run/packet records prove too coupled |

## Open Questions

1. **Where should route metadata live durably?**
   - What we know: existing run/packet/invocation tables already persist the neighboring control-plane state. [VERIFIED: schema.sql] [VERIFIED: services/aios_cli.py]
   - What's unclear: whether route results fit cleanly as added columns/json fields or deserve a dedicated route record linked to runs.
   - Recommendation: decide this during planning based on reuse by Phase 2 and operator query needs.

2. **How much of the early planned workflow library should be encoded immediately versus mapped as aliases onto current workflows?**
   - What we know: current registry only has `implementation-delivery`, `failure-recovery`, `academic_paper_v1`, and `divergent-strategy`. [VERIFIED: config/workflows/registry.json]
   - What's unclear: whether `audit-only`, `audit-and-implement`, and `agent handoff generation` should ship as first-class registry entries in Phase 1 or be represented through route aliases and rationale first.
   - Recommendation: prefer the smallest change that yields explicit route outcomes and inspectable rationale, then deepen workflow contracts in later phases.

## Environment Availability

This phase requires no new external runtime dependency beyond the repo's existing Python, JSON, SQLite, and prompt-registry surfaces. [VERIFIED: services/workflow_orchestration.py] [VERIFIED: services/execution_strategy.py] [VERIFIED: schema.sql]

