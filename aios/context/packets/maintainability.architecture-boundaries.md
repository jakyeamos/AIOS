---
id: packets.maintainability.architecture-boundaries
title: Architecture Boundaries Packet
tier: packet
scope:
  - all_projects
priority: normal
status: active
summary: Packet for preserving AIOS module and ownership boundaries during implementation.
applies_when:
  - task_changes_core_logic
tags:
  - architecture
  - boundaries
  - maintainability
last_reviewed: 2026-05-12
---

Keep compiler, CLI, UI, and durable-store responsibilities separated.
File-backed context can feed UI later, but the first compiler should not require DB migration.
Update optional project context only when a boundary change would otherwise be lost.

## Acceptance Criteria

- New modules have a clear owner and caller.
- Cross-layer changes are deliberate and documented.
