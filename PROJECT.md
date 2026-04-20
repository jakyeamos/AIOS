# AIOS Project Truth

Last updated: 2026-04-19

## What AIOS Is

AIOS is the local operating system for work context, agent workflows, and durable project memory.
It is intended to unify:

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

## Still Missing

- explicit `in_progress` and failure/cancel transitions driven by real execution events rather than session-close heuristics
- richer task routing tied to real subagent registries and invocation backends
- stronger contradiction/drift detection beyond current lexical and freshness heuristics
- explicit run/session handshake instead of heuristic session-close run matching
- approval workflows that let the user review and apply global or token-regressive writebacks inside the UI
- richer Taski operating controls beyond the first summary surface
- packet/result inspection surfaces that show exact post-run deltas at file and topic level

## Guardrails

- SQLite remains authoritative for machine-readable operational state
- Vault remains authoritative for curated human-readable knowledge
- staging remains non-canonical
- AIOS should prefer explicit inspectable pipelines over hidden prompt behavior
- default agent context policy is locked:
  - broad retrieval may happen inside AIOS
  - only compact ranked output reaches the agent by default
  - targeted expansion must be explicit and traced
