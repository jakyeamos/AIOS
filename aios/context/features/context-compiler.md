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
wiki_status: current
wiki_confidence: high
last_validated_at: 2026-05-14
validated_by: agent
source_coverage: strong
source_refs:
  - code:tools/context-compile.mjs|Context compiler implementation|2026-05-14
  - test:tests/context-compiler.test.mjs|Compiler tests and selection cases|2026-05-14
  - doc:docs/context/context-compiler.md|Context compiler design notes|2026-05-14
  - doc:package.json|Context compile and validation scripts|2026-05-14
known_stale_areas:
  - Runtime packet assembly in `aios-ui/server/aios/packet-assembly.ts` is adjacent but not the same path as file-backed context compilation.
related_pages:
  - context.index
  - context.router
  - context.schema
---

The Context Compiler accepts a task, classifies it, scores context files, writes a compact briefing, and emits a receipt.
The first version is deterministic and file-backed.
It should remain compatible with later database, UI, and Obsidian graph integration.

## Acceptance Criteria

- Compilation produces structured JSON and agent-readable Markdown.
- Receipts include loaded, skipped, conflicts, missing context, and writebacks.
- Scoring favors specific, recent, authoritative, low-cost context.
