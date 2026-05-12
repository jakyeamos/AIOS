---
id: global.testing
title: Global Testing Standard
tier: global
scope:
  - all_projects
priority: immutable
status: active
summary: Behavior must be validated with deterministic tests or equivalent execution evidence.
applies_when:
  - task_touches_testing
  - task_changes_core_logic
tags:
  - testing
  - validation
  - regression
conflicts:
  protected_topics:
    - testing
last_reviewed: 2026-05-12
---

Tests should verify real routing, validation, and output behavior rather than echoing mocks.
For stateful or cross-system work, run the exact modified path before completion.
Missing tests are a completion risk unless explicitly accepted.

## Applicability

- Load for compiler logic, scoring, validation, CLI behavior, and regressions.
- Use sample tasks as routing fixtures when compiler behavior changes.

## Acceptance Criteria

- Schema validation is exercised against real Markdown files.
- Routing tests assert selected files and receipt content.
- Conflict precedence is covered by executable tests.
