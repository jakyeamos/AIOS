---
date: 2026-04-18
status: accepted
project: AIOS
---

# Control Plane Run And Packet Ledger

## Context

Prior AIOS behavior generated startup packets and contextual retrieval implicitly inside hooks. That context was useful, but it was not inspectable, reusable, or queryable as its own workflow artifact. AIOS therefore influenced delegation without owning it.

## Decision

AIOS will persist control-plane activity in dedicated tables:

- `orchestration_runs`
- `briefing_packets`
- `memory_updates`

The control plane chooses a workflow template and agent profile explicitly, records the rationale and context trace, and stores the resulting briefing packet for later inspection.

## Consequences

- Delegation context becomes durable and reviewable after the fact.
- “Why was this agent/workflow chosen?” becomes answerable from data, not memory.
- Post-run continuity improves because memory updates can be tied back to execution.
- Control-plane behavior is no longer hidden inside opaque prompt glue alone.
