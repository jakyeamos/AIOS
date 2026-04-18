---
date: 2026-04-18
status: accepted
project: AIOS
---

# Explicit State Layers For AIOS

## Context

AIOS already had meaningful raw state capture across SQLite, vault, CTS, and staging, but the shipped app and helper scripts still exposed the system mostly as session telemetry. Knowledge, project memory, live orchestration state, and delegation packets were conceptually documented but not first-class product objects.

## Decision

AIOS will explicitly separate and expose these layers:

1. Durable knowledge
2. Project memory
3. Live orchestration state
4. Briefing packets
5. Grounded query/retrieval logic

Each layer must have a clear responsibility, a clear authority boundary, and an inspectable UI or data representation. The app must not collapse them into one generic “context” abstraction.

## Consequences

- Knowledge browsing becomes a first-class route and page model.
- Orchestration runs and packets are logged separately from durable knowledge.
- Post-run memory updates become durable records rather than transient prose.
- Retrieval and routing logic must explain themselves in product surfaces.
