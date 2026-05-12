---
id: context.router
title: Agent Bootloader
tier: global
scope:
  - all_projects
priority: immutable
status: active
summary: Agent bootloader for AIOS-managed projects and context receipts.
applies_when:
  - all_tasks
tags:
  - agent
  - bootloader
  - receipt
conflicts:
  protected_topics:
    - context_selection
last_reviewed: 2026-05-12
---

You are operating inside an AIOS-managed project.
Before executing, classify the task, load project truth, load relevant global standards, add matching domain standards, add feature/task packets, and produce a context receipt.
Execute from the compiled briefing first; request or compile more context only when the receipt shows a concrete gap.
After implementation, update truth files or propose writebacks when state, rules, or reusable packets changed.

## Never Do

- Do not load every Markdown file by default.
- Do not ignore higher-priority standards.
- Do not weaken global rules with project-local convenience.
- Do not make architectural changes without updating the project truth file.
- Do not treat broad semantic search as equivalent to authoritative context selection.

## Acceptance Criteria

- Every non-trivial run has a loaded/skipped context receipt.
- Missing, stale, and conflicting context are explicit.
- Writebacks are proposed for missing rules or reusable patterns.
