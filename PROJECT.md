# AIOS Project Truth

Last updated: 2026-04-23

## What AIOS Is

AIOS is the local operating system for work context, agent workflows, and durable project memory.
It is the orchestration layer for agents across all linked development projects, not just a dashboard or standards system for this repository. It is intended to unify:

- structured knowledge pages
- grounded retrieval and query surfaces
- workflow and orchestration state
- task-specific delegation packets
- durable continuity across long-running sessions

## Current Reality

The repository currently contains three meaningful subsystems:

1. `aios-ui/`
   A Next.js local dashboard over `~/AIOS/data/aios.db`. It is strongest at session/run observability.

2. `bin/` and `services/`
   Python hooks, importers, storage maintenance tools, and the CTS prototype.

3. `docs/`
   Design intent for storage, knowledge, CTS, and the current UI, but not yet a single implemented architecture.

## Current Product Boundary

Shipped AIOS behavior today is primarily:

- session logging
- prompt logging
- artifact logging
- bug capture
- pattern extraction
- lightweight startup retrieval
- dashboard-style visibility into runs, prompts, projects, and costs

It is not yet a real knowledge OS or orchestration control plane.

## Target Architecture Direction

AIOS must separate and expose these layers explicitly:

1. Durable knowledge
2. Project memory
3. Live workflow/orchestration state
4. Briefing packet generation
5. Grounded retrieval/query logic
6. Inspectability for routing, retrieval, assumptions, and changes

## This Pass

This implementation pass establishes:

- an audit artifact documenting the gap to the target system
- first-class control-plane schema and modules inside `aios-ui`
- knowledge-oriented information architecture instead of dashboard-only navigation
- grounded query and inspectable retrieval surfaces
- orchestration run logging and briefing packet generation
- ADR support and handoff documentation for continuation
- post-run memory updates written into dedicated control-plane state
- explicit run/session handshake and invocation records
- event-driven lifecycle transitions with durable history
- approval review surfaces for gated writebacks
- structured evaluator outputs for contradiction, drift, and stale-truth detection
- a real managed invocation backend path tied to the workflow/agent registry

## Implemented On 2026-04-18

The current app now includes:

- `knowledge` routes for projects, decisions, workflows, agents, and system pages
- `control` route for workflow selection, agent registry, run history, and packet generation
- `query` route for grounded, inspectable internal answers
- dedicated control-plane schema:
  - `orchestration_runs`
  - `briefing_packets`
  - `memory_updates`
- ADR-backed decision logging in `docs/adr/`
- upgraded project dossiers with memory, rules, likely files, decisions, and recent changes
- `hook-stop.py` memory update writes on session close
- orchestration run lifecycle closure from `hook-stop.py`, including:
  - `session_id`
  - `memory_update_id`
  - `result_summary`
  - `completed_at`
- curated vault wiki ingestion into first-class `concept` knowledge pages
- derived wiki backlinks and relationship resolution inside the knowledge surface
- CTS-backed enrichment for:
  - control-plane packet generation
  - grounded query project-state answers
  - grounded query agent brief answers
  - inspectable retrieval traces

## Implemented On 2026-04-19

This pass adds the first persisted topic-graph and compact-packet vertical slice:

- persisted indexed knowledge layer:
  - `knowledge_topics`
  - `knowledge_relationships`
  - `knowledge_references`
  - `knowledge_markers`
  - `knowledge_graph_state`
- compact ranked packet delivery as the default orchestration policy
- explicit packet trace and omitted-context storage in `briefing_packets`
- traced targeted expansion logging in `packet_expansions`
- improvement writeback storage in `improvement_writebacks`
- Taski-led project operating surface on `/projects/[id]`
- topic-graph-backed retrieval in grounded query
- concept pages enriched with persisted references, relationships, and drift markers
- post-run improvement writeback proposals from `hook-stop.py`
- architecture note for the hardened retrieval policy:
  - `docs/architecture/2026-04-19-topic-graph-ranked-packets.md`

This pass also turns the execution layer into a real control-plane path:

- explicit durable handshake through:
  - `orchestration_runs.id`
  - `sessions.run_id`
  - `sessions.invocation_id`
  - `orchestration_invocations`
- first-class lifecycle and trace tables:
  - `orchestration_run_events`
  - `improvement_writeback_events`
- event-driven run statuses now written from runtime events:
  - `planned`
  - `ready`
  - `in_progress`
  - `completed`
  - `failed`
  - `canceled`
  - `superseded`
- structured run state on `orchestration_runs`:
  - `backend_key`
  - `active_invocation_id`
  - `started_at`
  - `failed_at`
  - `canceled_at`
  - `superseded_by_run_id`
  - `status_reason_json`
- approval decision persistence on `improvement_writebacks`
- structured evaluation storage:
  - `consistency_evaluations`
  - `consistency_findings`
- `/control` upgraded from packet planning only to:
  - managed run invocation
  - runtime status inspection
  - approval review
  - event timeline / evaluator trace
- Taski project surface upgraded to show:
  - structured findings
  - approval queue
  - event-driven run state
- managed backend runner in `bin/aios-managed-run.py`
- `hook-session-start.py` now moves explicitly linked runs to `in_progress`
- `hook-stop.py` now resolves the exact run by handshake first and only falls back to heuristic matching as a legacy escape hatch

## Implemented On 2026-04-23

Phase 0a architecture enforcement baseline is now live as an AIOS-managed profile system:

- AIOS registry for reusable architecture profiles:
  - `config/architecture-enforcement/profiles.json`
  - `config/architecture-enforcement/projects.json`
- new enforcement runner and CLI:
  - `services/architecture_enforcement.py`
  - `bin/architecture-enforcement.py`
- Python profile (`python-service-v1`) enforcing:
  - `services -> bin` import boundary denial
  - cycle detection for local Python modules
  - optional ruff adapter when local tooling exists
- Next.js profile (`ts-nextjs-v1`) enforcing:
  - Dependency Cruiser layer boundaries + cycle detection
  - existing ESLint/TypeScript lint checks
- proof-target wiring in `aios-ui`:
  - `.dependency-cruiser.cjs`
  - `npm run lint:architecture`
- architecture audit + rollout doc:
  - `docs/architecture/2026-04-23-aios-architecture-enforcement.md`

Phase 0b agent workflow CLI surfaces are now implemented after the hard checkpoint:

- audit package (checkpoint gate):
  - `docs/architecture/2026-04-23-aios-agent-workflow-audit.md`
- unified JSON-first command surface:
  - `bin/aios.py`
  - `services/aios_cli.py`
- implemented command family:
  - `aios status --json`
  - `aios health --json`
  - `aios metadata --json`
  - `aios logs --json`
  - `aios recent-failures --json`
  - `aios skills status --json`
  - `aios skills refresh --json [--apply]`
- standardized semantic exit-code envelope on unified surfaces:
  - usage, not-found, dependency/config, runtime
- instruction/skills refresh flow moved to declarative registry:
  - `config/instruction-registry.json`
- implementation handoff:
  - `docs/handoffs/2026-04-23-aios-agent-workflow-cli-handoff.md`

Phase 0c success criteria control-plane baseline is now live:

- criteria registry + skill mapping:
  - `config/success-criteria/registry.json`
  - `config/success-criteria/skill-map.json`
- canonical criteria docs and discovery index:
  - `spec/success-criteria/index.md`
  - `spec/success-criteria/_template.md`
  - normalized criteria docs for:
    - `code-simplicity`
    - `testing-trust`
    - `security-review`
    - `observability`
    - `truth-file-consistency`
    - `repo-boundary-discipline`
    - `workflow-state-integrity`
- runtime evaluator and artifact persistence:
  - `services/success_criteria.py`
  - `data/success-criteria/evaluations/*.json`
- hook integration:
  - `hook-session-start.py` now previews applicable criteria before implementation
  - `hook-stop.py` now evaluates changed patch paths and records criteria findings
- durable schema additions:
  - `success_criteria_evaluations`
  - `success_criteria_findings`
- metadata snapshot visibility:
  - `aios metadata --json` now exposes criteria catalog + latest evaluation
- phase architecture note:
  - `docs/architecture/2026-04-23-aios-success-criteria-system.md`

## Still Missing

- more than one production-grade invocation backend beyond the new managed local runtime
- richer backend adapters for external/manual agent sessions so they emit the same handshake without fallback
- broader evaluator rule coverage and explicit finding resolution workflows
- deeper packet/result inspection at file/topic delta level
- richer Taski operator controls beyond summary, approvals, and run/evaluator inspection
- legacy heuristic run matching still exists only as a fallback for older sessions that lack explicit handshake metadata
- linked-project profile ratchet completion (`amos-saas`, `soundscape-app`, `GitNexus`, `Terrace`, `portfolio`) so each has native profile config + CI wiring in-repo

## Spec Roadmap Corrections On 2026-04-23

The spec execution roadmap has been corrected before execution:

- The roadmap now treats AIOS as the global orchestration/control layer for all linked development projects. This repo is the implementation home and first self-check target, not the whole scope.
- Anti-Slop ESLint is now treated as an existing integration to audit and ratchet, not a greenfield build.
- Workflow orchestration must extend the existing control-plane primitives instead of recreating them.
- Phase 0 is serial by default because architecture enforcement, agent CLI surfaces, and success criteria share scripts, hooks, docs, and runtime contracts.
- Prompt Library Phase 1 uses the schema in `2026-04-08-prompt-library-design.md` as canonical.
- Agent Workflow CLI work must honor the hard checkpoint before implementation.
- Success criteria own judging rubrics; Standards Delta owns project health scoring and remediation.
- Prompt Library Phase 2 is scoped by the Improvement Engine audit rather than requiring full replay/shadow/canary infrastructure up front.
- UI Command Center now has an explicit MVP gate before the broader ten-surface target.

## Guardrails

- SQLite remains authoritative for machine-readable operational state
- Vault remains authoritative for curated human-readable knowledge
- staging remains non-canonical
- AIOS should prefer explicit inspectable pipelines over hidden prompt behavior
- default agent context policy is locked:
  - broad retrieval may happen inside AIOS
  - only compact ranked output reaches the agent by default
  - targeted expansion must be explicit and traced
