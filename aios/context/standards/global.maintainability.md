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

## Applicability

- Load for most implementation work and always for compiler/routing changes.
- Pair with project truth when changing system behavior.

## Acceptance Criteria

- New code has a narrow surface and deterministic behavior.
- Project truth or handoff files reflect meaningful architecture changes.
- Context routing remains auditable from receipt output.
