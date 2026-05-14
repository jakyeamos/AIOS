# Quick Task: Audit and implement AIOS wiki maintenance layer

## Scope

Add the minimum useful maintenance system for AIOS wiki/context pages so agents can distinguish current truth from planned, deprecated, historical, experimental, and unverified notes; inspect source refs; generate compact task packets; and run a drift check.

## Context Loaded

- `pnpm context:compile --task "Audit and implement AIOS wiki maintenance metadata, scoring, drift checks, agent packet generation, and UI indicators"`
- `aios-ui/server/aios/knowledge.ts`
- `aios-ui/server/aios/topic-graph.ts`
- `aios-ui/server/aios/packet-assembly.ts`
- `tools/context-compile.mjs`
- `bin/hook-prompt-submit.py`
- `docs/specs/2026-04-03-knowledge-layer-design.md`

## Implementation Plan

1. Add typed wiki maintenance metadata and scoring helpers.
2. Expose metadata on knowledge summaries/details.
3. Add an agent packet generator and route.
4. Add a CI-friendly `pnpm wiki:check` drift script.
5. Render maintenance badges, stale areas, source refs, and packet guidance in the UI.
6. Add tests for scoring, packet generation, and drift checks.
7. Update project truth and quick-task state.

## Constraints

- Do not redesign the whole knowledge UI.
- Do not make the wiki the source of truth.
- Keep source files/docs/tests as authoritative and use wiki data as a compressed map.
