# Phase 2: Context, Query, And Briefing Compilation - Context

**Gathered:** 2026-05-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 2 takes the routed serious-work objective from Phase 1 and turns it into the smallest sufficient governed packet before execution. The product target is not “another packet builder.” It is one inspectable packet contract that can:

- compile task-specific context from authoritative sources
- record what was loaded and skipped with reasons
- include prompt-aware handoff instructions
- carry grounded query and repo/knowledge evidence forward into execution
- persist packet identity and provenance so later phases can inspect, score, and write back against the exact packet that drove the run

</domain>

<decisions>
## Implementation Decisions

### Working assumptions

- The current system has three adjacent but not yet unified paths:
  - file-backed context compilation in `tools/context-compile.mjs`
  - ranked packet assembly in `aios-ui/server/aios/packet-assembly.ts`
  - grounded question answering in `aios-ui/server/aios/query.ts`
- `aios start-work` now persists route metadata, so Phase 2 should consume that route metadata instead of rebuilding packet assumptions from scratch.
- Packet governance should stay local-first and machine-readable; durable receipts matter as much as Markdown output.

### Likely phase split

1. Define a durable packet contract that can represent route metadata, sources loaded, omissions, prompt/handoff state, and receipt provenance across CLI and UI paths.
2. Connect the file-backed compiler and grounded query surfaces to that contract instead of leaving them as neighboring systems.
3. Make handoff generation explicit and governed for the default serious-work workflows.

</decisions>

<code_context>
## Existing Code Insights

- `tools/context-compile.mjs` already performs deterministic file-backed selection and receipt generation, but it is separate from the runtime packet records.
- `services/aios_cli.py` creates `briefing_packets` and now stores `route_id` plus `route_result_json`, but packet sections remain custom CLI assembly.
- `aios-ui/server/aios/packet-assembly.ts` has a ranked packet builder with topic graph, CTS, recent runs, memory updates, and policy candidates.
- `aios-ui/server/aios/query.ts` answers grounded questions through dossier/topic/change lookups, but does not share one packet or receipt contract with packet assembly.
- `aios-ui/server/aios/schema.ts` still backfills only the older `briefing_packets` columns and does not yet know about the new route metadata columns added to `schema.sql` and `services/aios_cli.py`.

</code_context>

<specifics>
## Specific Ideas

- Create one packet/receipt schema that both CLI and UI code can parse and persist.
- Promote route metadata into packet selection traces instead of treating route and packet provenance as separate stories.
- Pull prompt-family and workflow instructions into the packet as first-class fields, not only freeform Markdown lines.
- Expand tests around:
  - packet schema persistence
  - route-aware packet traces
  - grounded query provenance
  - missing/stale/conflicting context signaling

</specifics>

<deferred>
## Deferred Ideas

- Rich operator-surface polish for packet drilldown belongs later unless it is required to validate the packet contract.
- Broad truth freshness/writeback governance is primarily later-phase work, but Phase 2 must leave enough packet provenance for those phases to attach to.

</deferred>
