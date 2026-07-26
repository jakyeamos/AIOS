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
wiki_status: current
wiki_confidence: high
last_validated_at: 2026-05-14
validated_by: agent
source_coverage: partial
source_refs:
  - doc:AGENTS.md|Repository agent bootloader contract|2026-05-14
  - code:tools/context-compile.mjs|Context selection and receipt compiler|2026-05-14
  - test:tests/context-compiler.test.mjs|Context routing tests|2026-05-14
known_stale_areas:
  - Agent bootloader expectations also live in runtime prompts and may need revalidation after hook or AGENTS.md changes.
related_pages:
  - context.index
  - context.schema
---

You are operating inside an AIOS-managed project.
Before executing, classify the task, load relevant global standards, add matching domain standards, add feature/task packets, and produce a context receipt. Optional project context may be loaded when it is relevant, but it is never a prerequisite for execution or commit.
Execute from the compiled briefing first; request or compile more context only when the receipt shows a concrete gap.
After implementation, propose writebacks only when a reusable rule, packet, or memory lesson was actually learned. Project notes remain optional.

## Never Do

- Do not load every Markdown file by default.
- Do not ignore higher-priority standards.
- Do not weaken global rules with project-local convenience.
- Do not block architectural changes on a project note; rely on executable evidence and reviewable artifacts.
- Do not treat broad semantic search as equivalent to authoritative context selection.

## Acceptance Criteria

- Every non-trivial run has a loaded/skipped context receipt.
- Missing, stale, and conflicting context are explicit.
- Writebacks are proposed for missing rules or reusable patterns.
