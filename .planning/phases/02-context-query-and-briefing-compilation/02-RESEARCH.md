# Phase 2: Context, Query, And Briefing Compilation - Research

## Current Surfaces

### File-backed compiler

- `tools/context-compile.mjs` already classifies tasks, selects context files, reports conflicts, and writes both compiled briefings and receipts.
- It has deterministic tests in `tests/context-compiler.test.mjs` covering route-like selection, immutable conflict handling, missing-context suggestions, and write-mode output.
- This is the authoritative file-backed selection engine, but it does not currently define the runtime packet record used by `start-work`.

### Runtime packet assembly

- `aios-ui/server/aios/packet-assembly.ts` builds ranked briefing packets from project dossier, CTS, topic graph, prior runs, memory updates, and policy/writeback signals.
- `aios-ui/server/aios/control-plane.ts` persists those packets in `briefing_packets`, but its row mapping and schema assumptions still reflect the older packet shape.
- This means the UI/control-plane packet path has useful retrieval signals but no explicit bridge to the context-compiler receipt model.

### Grounded query

- `aios-ui/server/aios/query.ts` composes grounded answers from dossier, topic graph, recent changes, CTS, and capability-audit logic.
- The query path emits its own retrieval trace shape rather than reusing a packet/receipt contract.

### Route-aware CLI packet creation

- `services/aios_cli.py` now routes `start-work` through `services/task_routing.py`.
- It stores `route_id`, `route_status`, and `route_result_json` on `orchestration_runs` and `briefing_packets`.
- The current CLI packet builder still uses `_packet_sections`, `_packet_retrieval_trace`, and `_packet_markdown`, which are separate from both `tools/context-compile.mjs` and `aios-ui/server/aios/packet-assembly.ts`.

## Main Gaps

1. There is no single durable packet schema shared by the compiler, CLI packet builder, and UI packet builder.
2. Grounded query and packet assembly are adjacent evidence systems, not one provenance model.
3. `aios-ui/server/aios/schema.ts` lags behind the new route-aware packet columns, so UI schema upkeep is already drifting.
4. Prompt-family and workflow instructions exist in routing data, but they are not yet explicit first-class packet contract fields.

## Recommended Plan Structure

### Plan 02-01

Define and persist the shared packet contract:

- route-aware `briefing_packets` shape in UI schema/runtime readers
- packet trace/receipt primitives shared across CLI and UI paths
- tests proving route metadata and packet provenance survive reads/writes

### Plan 02-02

Bridge compiler and query evidence into the packet contract:

- shared selection/receipt primitives
- route-aware packet trace composition
- missing/stale/conflict signaling that can surface both in packets and grounded query outputs

### Plan 02-03

Harden governed handoff generation:

- explicit handoff packet fields for workflow steps, prompt instructions, checks, acceptance criteria
- default serious-work workflow completeness rules
- end-to-end coverage for agent-ready packet generation

## Risks

- There is a real danger of creating a fourth packet path if Phase 2 only layers wrappers around existing systems.
- UI schema drift is already visible; if not corrected early in this phase, later operator-surface work will sit on inconsistent packet storage.
- Mixing unrelated local work into this phase is a concrete risk because the current worktree contains generated logs/receipts and a separate personalized-humanizer slice.
