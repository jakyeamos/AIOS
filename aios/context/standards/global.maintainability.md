---
id: global.maintainability
title: Global Maintainability Standard
tier: global
scope:
  - all_projects
priority: immutable
status: active
summary: Keep AIOS changes simple, bounded, readable, and aligned to existing architecture.
applies_when:
  - all_tasks
  - task_changes_core_logic
tags:
  - maintainability
  - architecture
  - simplicity
conflicts:
  protected_topics:
    - maintainability
    - architecture
last_reviewed: 2026-05-12
---

Prefer boring, inspectable logic over opaque routing or broad abstractions.
Read existing code and truth files before modifying behavior.
Keep file-backed rules thin and create packets only for repeated needs.
Architectural changes must update durable project truth.
Common error surfaces require durable fixes at the source of recurrence, not repeated local workarounds.
When context is limited, keep agent-facing files small enough to load, scan, and reason over in one pass; split by responsibility when a file becomes context-heavy.

## Applicability

- Load for most implementation work and always for compiler/routing changes.
- Pair with project truth when changing system behavior.

## Acceptance Criteria

- New code has a narrow surface and deterministic behavior.
- Recurring error surfaces are resolved with durable remediation or captured as explicit follow-up work.
- Agent-facing files fit a bounded context budget, or document why the larger surface remains coherent.
- Project truth or handoff files reflect meaningful architecture changes.
- Context routing remains auditable from receipt output.
