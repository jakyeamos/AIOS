# AIOS Control Plane Handoff

Date: 2026-04-18
Scope: audit + control-plane implementation pass + follow-on architecture steps

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

## Intentionally Deferred

- Real execution tracking beyond plan/ready/completed heuristics
- multi-agent registry tied to actual invocation backends
- contradiction/drift jobs that write structured findings
- persisted wiki indexing instead of read-time derivation
- stronger run matching than the current token-overlap heuristic in `hook-stop.py`
- explicit failure/cancel transitions from runtime events
- cleanup of pre-existing anti-slop warnings in older UI routes

## Exact Files To Continue From

- [aios-ui/server/aios/knowledge.ts](/Users/jakyeamos/AIOS/aios-ui/server/aios/knowledge.ts)
- [aios-ui/server/aios/control-plane.ts](/Users/jakyeamos/AIOS/aios-ui/server/aios/control-plane.ts)
- [aios-ui/server/aios/query.ts](/Users/jakyeamos/AIOS/aios-ui/server/aios/query.ts)
- [aios-ui/server/aios/cts.ts](/Users/jakyeamos/AIOS/aios-ui/server/aios/cts.ts)
- [aios-ui/server/aios/filesystem.ts](/Users/jakyeamos/AIOS/aios-ui/server/aios/filesystem.ts)
- [aios-ui/server/aios/changes.ts](/Users/jakyeamos/AIOS/aios-ui/server/aios/changes.ts)
- [aios-ui/components/control/ControlPlaneStudio.tsx](/Users/jakyeamos/AIOS/aios-ui/components/control/ControlPlaneStudio.tsx)
- [aios-ui/components/knowledge/KnowledgePageView.tsx](/Users/jakyeamos/AIOS/aios-ui/components/knowledge/KnowledgePageView.tsx)
- [aios-ui/components/query/GroundedQueryStudio.tsx](/Users/jakyeamos/AIOS/aios-ui/components/query/GroundedQueryStudio.tsx)
- [bin/hook-stop.py](/Users/jakyeamos/AIOS/bin/hook-stop.py)
- [schema.sql](/Users/jakyeamos/AIOS/schema.sql)
- [data/schema.sql](/Users/jakyeamos/AIOS/data/schema.sql)

## Unresolved Architectural Questions

- Should orchestration runs stay SQLite-first, or should some run metadata also be mirrored into the vault as curated operational narratives?
- Should knowledge pages remain derived-at-read-time from vault content, or should AIOS maintain a persisted page/index layer with explicit backlinks?
- Should grounded query remain deterministic for inspectability, or should it later gain an LLM answerer constrained by the same retrieval trace?
- How much of packet generation should come from CTS vs session/artifact history vs curated ADRs?
- Should run completion linkage move from token overlap to an explicit run/session handshake written at delegation time?

## Recommended Next Implementation Order

1. Add an explicit run/session handshake so completion updates do not depend on heuristic objective matching in [bin/hook-stop.py](/Users/jakyeamos/AIOS/bin/hook-stop.py)
2. Introduce `in_progress`, `failed`, and `canceled` transitions from real execution events and render those transitions in `/control`
3. Persist wiki-derived pages/backlinks into an index or cache layer so knowledge browsing is not rebuilt only at read time
4. Add contradiction/staleness detectors that write structured findings surfaced in `/query` and `/knowledge`
5. Tie workflow and agent registry entries to real invocation backends so AIOS becomes the actual control plane rather than a planner plus ledger
6. Clean up the remaining older dashboard routes and pre-existing anti-slop warnings
