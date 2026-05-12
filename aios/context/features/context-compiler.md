---
id: features.context-compiler
title: AIOS Context Compiler Feature
tier: feature
scope:
  - aios
priority: high
status: active
summary: Feature context for tiered Markdown routing, scoring, receipts, and writeback candidates.
applies_when:
  - task_touches_context_compiler
  - task_touches_agent_harness
tags:
  - context-compiler
  - routing
  - receipt
  - writeback
related:
  - ../router.md
  - ../schema.md
last_reviewed: 2026-05-12
---

The Context Compiler accepts a task, classifies it, scores context files, writes a compact briefing, and emits a receipt.
The first version is deterministic and file-backed.
It should remain compatible with later database, UI, and Obsidian graph integration.

## Acceptance Criteria

- Compilation produces structured JSON and agent-readable Markdown.
- Receipts include loaded, skipped, conflicts, missing context, and writebacks.
- Scoring favors specific, recent, authoritative, low-cost context.
