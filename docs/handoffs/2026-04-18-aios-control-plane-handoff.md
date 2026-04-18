# AIOS Control Plane Handoff

Date: 2026-04-18
Scope: audit + first control-plane implementation pass

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

## Intentionally Deferred

- Real execution tracking beyond packet generation
- multi-agent registry tied to actual invocation backends
- contradiction/drift jobs that write structured findings
- richer vault/wiki ingestion into the knowledge index
- CTS-backed likely-file and architecture sections in packet generation
- cleanup of pre-existing anti-slop warnings in older UI routes

## Exact Files To Continue From

- [aios-ui/server/aios/knowledge.ts](/Users/jakyeamos/AIOS/aios-ui/server/aios/knowledge.ts)
- [aios-ui/server/aios/control-plane.ts](/Users/jakyeamos/AIOS/aios-ui/server/aios/control-plane.ts)
- [aios-ui/server/aios/query.ts](/Users/jakyeamos/AIOS/aios-ui/server/aios/query.ts)
- [aios-ui/server/aios/changes.ts](/Users/jakyeamos/AIOS/aios-ui/server/aios/changes.ts)
- [aios-ui/components/control/ControlPlaneStudio.tsx](/Users/jakyeamos/AIOS/aios-ui/components/control/ControlPlaneStudio.tsx)
- [aios-ui/components/query/GroundedQueryStudio.tsx](/Users/jakyeamos/AIOS/aios-ui/components/query/GroundedQueryStudio.tsx)
- [bin/hook-stop.py](/Users/jakyeamos/AIOS/bin/hook-stop.py)
- [schema.sql](/Users/jakyeamos/AIOS/schema.sql)
- [data/schema.sql](/Users/jakyeamos/AIOS/data/schema.sql)

## Unresolved Architectural Questions

- Should orchestration runs stay SQLite-first, or should some run metadata also be mirrored into the vault as curated operational narratives?
- Should knowledge pages remain derived-at-read-time, or should AIOS maintain a persisted page/index layer with explicit backlinks?
- Should grounded query remain deterministic for inspectability, or should it later gain an LLM answerer constrained by the same retrieval trace?
- How much of packet generation should come from CTS vs session/artifact history vs curated ADRs?

## Recommended Next Implementation Order

1. Add explicit run lifecycle transitions and result statuses to `orchestration_runs`
2. Write a post-run updater that links `memory_updates` back to `orchestration_runs.packet_id`
3. Expand `knowledge.ts` to ingest curated vault wiki pages and typed backlinks
4. Integrate CTS into packet generation for likely files, architecture summaries, and risk surfaces
5. Add contradiction/staleness detectors that surface drift in `/query` and `/knowledge`
6. Clean up the remaining older dashboard routes and pre-existing anti-slop warnings
