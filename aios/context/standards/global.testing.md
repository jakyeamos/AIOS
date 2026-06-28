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
In TDD-heavy projects, adoption/backfill scans must judge test value by protected behavior and maintenance cost, not by count or coverage growth alone.
TDD is not a license to add low-value tests. Tiny static presentation/copy edits can be verified with typecheck, build, and runtime/browser inspection when a render-text test would only duplicate implementation copy.

## Applicability

- Load for compiler logic, scoring, validation, CLI behavior, and regressions.
- Use sample tasks as routing fixtures when compiler behavior changes.

## Acceptance Criteria

- Schema validation is exercised against real Markdown files.
- Routing tests assert selected files and receipt content.
- Conflict precedence is covered by executable tests.
- New tests protect behavior, public contracts, domain logic, or confirmed regressions; brittle static render/copy assertions are omitted unless their value is documented.
