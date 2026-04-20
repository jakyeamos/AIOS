# AIOS Control Plane Handoff

Date: 2026-04-19
Scope: audit + control-plane implementation pass + topic-graph / ranked-packet vertical slice

## What Was Audited

- `aios-ui/` Next.js product surface
- SQLite-backed routers and schema shape
- `bin/` hook pipeline, especially `hook-session-start.py`, `hook-prompt-submit.py`, `hook-stop.py`
- `services/cts/`
- `docs/STORES.md` plus existing specs for knowledge/UI/CTS
- live `~/AIOS/data/aios.db` table counts and current surface area

## What Changed

- Added repo truth file updates in [PROJECT.md](/Users/jakyeamos/AIOS/PROJECT.md)
- Added audit artifact in [2026-04-18-aios-control-plane-audit.md](/Users/jakyeamos/AIOS/docs/architecture/2026-04-18-aios-control-plane-audit.md)
- Added ADRs:
  - [0001-explicit-state-layers.md](/Users/jakyeamos/AIOS/docs/adr/0001-explicit-state-layers.md)
  - [0002-control-plane-run-and-packet-ledger.md](/Users/jakyeamos/AIOS/docs/adr/0002-control-plane-run-and-packet-ledger.md)
- Added explicit control-plane tables and server modules in `aios-ui/server/aios/`
- Added routers:
  - `knowledge`
  - `controlPlane`
  - `query`
  - `changes`
- Added routes:
  - `/knowledge`
  - `/knowledge/[slug]`
  - `/control`
  - `/query`
- Reworked `/` into a knowledge/control-plane overview
- Reworked `/projects/[id]` into a dossier surface
- Updated `schema.sql`, `data/schema.sql`, and `bin/hook-stop.py` for post-run memory updates
- Added `aios-ui/server/aios/cts.ts` to bridge the existing Python CTS layer into the UI/server control plane
- Expanded `orchestration_runs` to include:
  - `session_id`
  - `updated_at`
  - `completed_at`
  - `result_summary`
  - `memory_update_id`
- Expanded `memory_updates` to include:
  - `run_id`
  - `packet_id`
- Linked `hook-stop.py` memory writes back to the best matching orchestration run and mark that run `completed`
- Added `superseded` handling for older pending runs when a new packet is planned for the same project
- Ingested curated vault wiki pages as first-class `concept` pages in `/knowledge`
- Added derived wiki backlinks and typed relationship resolution for concept pages
- Added CTS-backed topology sections and retrieval traces in packet generation and grounded query flows
- Updated `/control` to surface run status badges and result summaries
- Updated `/knowledge` to expose concepts and backlinks directly in the page surface
- Added persisted topic graph tables:
  - `knowledge_topics`
  - `knowledge_relationships`
  - `knowledge_references`
  - `knowledge_markers`
  - `knowledge_graph_state`
- Added compact ranked packet metadata to `briefing_packets`:
  - `policy_mode`
  - `token_budget`
  - `selection_trace_json`
  - `omitted_context_json`
- Added traced expansion logging in `packet_expansions`
- Added layered learning writebacks in `improvement_writebacks`
- Added topic-graph ingestion and search in [aios-ui/server/aios/topic-graph.ts](/Users/jakyeamos/AIOS/aios-ui/server/aios/topic-graph.ts)
- Added ranked packet assembly and expansion logic in [aios-ui/server/aios/packet-assembly.ts](/Users/jakyeamos/AIOS/aios-ui/server/aios/packet-assembly.ts)
- Added Taski-led project operating surface in:
  - [aios-ui/server/aios/taski.ts](/Users/jakyeamos/AIOS/aios-ui/server/aios/taski.ts)
  - [aios-ui/components/projects/TaskiProjectSurface.tsx](/Users/jakyeamos/AIOS/aios-ui/components/projects/TaskiProjectSurface.tsx)
- Reworked `/projects/[id]` to make the Taski summary the dominant operating tab
- Reworked `/control` packet generation around the hardened compact-ranked default and explicit targeted expansion
- Added architecture note in [2026-04-19-topic-graph-ranked-packets.md](/Users/jakyeamos/AIOS/docs/architecture/2026-04-19-topic-graph-ranked-packets.md)
- Added hook-stop writeback proposals into `improvement_writebacks`

## Intentionally Deferred

- Real execution tracking beyond plan/ready/completed heuristics
- multi-agent registry tied to actual invocation backends
- stronger contradiction/drift jobs beyond the current lexical/freshness heuristics
- exact run/session handshake instead of heuristic token-overlap matching in `hook-stop.py`
- explicit failure/cancel transitions from runtime events
- approval UI/workflow for applying or rejecting global and token-regressive writebacks
- cleanup of pre-existing anti-slop warnings in older UI routes

## Exact Files To Continue From

- [aios-ui/server/aios/topic-graph.ts](/Users/jakyeamos/AIOS/aios-ui/server/aios/topic-graph.ts)
- [aios-ui/server/aios/packet-assembly.ts](/Users/jakyeamos/AIOS/aios-ui/server/aios/packet-assembly.ts)
- [aios-ui/server/aios/taski.ts](/Users/jakyeamos/AIOS/aios-ui/server/aios/taski.ts)
- [aios-ui/server/aios/learning.ts](/Users/jakyeamos/AIOS/aios-ui/server/aios/learning.ts)
- [aios-ui/server/aios/knowledge.ts](/Users/jakyeamos/AIOS/aios-ui/server/aios/knowledge.ts)
- [aios-ui/server/aios/control-plane.ts](/Users/jakyeamos/AIOS/aios-ui/server/aios/control-plane.ts)
- [aios-ui/server/aios/query.ts](/Users/jakyeamos/AIOS/aios-ui/server/aios/query.ts)
- [aios-ui/server/aios/cts.ts](/Users/jakyeamos/AIOS/aios-ui/server/aios/cts.ts)
- [aios-ui/server/aios/filesystem.ts](/Users/jakyeamos/AIOS/aios-ui/server/aios/filesystem.ts)
- [aios-ui/server/aios/changes.ts](/Users/jakyeamos/AIOS/aios-ui/server/aios/changes.ts)
- [aios-ui/components/control/ControlPlaneStudio.tsx](/Users/jakyeamos/AIOS/aios-ui/components/control/ControlPlaneStudio.tsx)
- [aios-ui/components/knowledge/KnowledgePageView.tsx](/Users/jakyeamos/AIOS/aios-ui/components/knowledge/KnowledgePageView.tsx)
- [aios-ui/components/projects/TaskiProjectSurface.tsx](/Users/jakyeamos/AIOS/aios-ui/components/projects/TaskiProjectSurface.tsx)
- [aios-ui/components/query/GroundedQueryStudio.tsx](/Users/jakyeamos/AIOS/aios-ui/components/query/GroundedQueryStudio.tsx)
- [bin/hook-stop.py](/Users/jakyeamos/AIOS/bin/hook-stop.py)
- [schema.sql](/Users/jakyeamos/AIOS/schema.sql)
- [data/schema.sql](/Users/jakyeamos/AIOS/data/schema.sql)

## Unresolved Architectural Questions

- Should orchestration runs stay SQLite-first, or should some run metadata also be mirrored into the vault as curated operational narratives?
- Should knowledge pages fully pivot to the persisted topic graph for all detail rendering, or continue as hybrid dossier/wiki views with graph enrichment?
- Should grounded query remain deterministic for inspectability, or should it later gain an LLM answerer constrained by the same retrieval trace?
- How much of packet generation should come from CTS vs session/artifact history vs curated ADRs?
- Should run completion linkage move from token overlap to an explicit run/session handshake written at delegation time?
- Should writeback proposals be auto-generated only at session stop, or also continuously after packet expansion and run inspection?

## Recommended Next Implementation Order

1. Add an explicit run/session handshake so completion updates and writebacks do not depend on heuristic objective matching in [bin/hook-stop.py](/Users/jakyeamos/AIOS/bin/hook-stop.py)
2. Introduce `in_progress`, `failed`, and `canceled` transitions from real execution events and render those transitions in `/control` and the Taski surface
3. Add approval UI for `improvement_writebacks`, especially for `global_policy` and token-regressive proposals
4. Strengthen contradiction/drift detection so markers come from structured evaluation rather than only lexical overlap and freshness cues
5. Tie workflow and agent registry entries to real invocation backends so AIOS becomes the actual control plane rather than a planner plus ledger
6. Clean up the remaining older dashboard routes and pre-existing anti-slop warnings once the operating surfaces are stable
