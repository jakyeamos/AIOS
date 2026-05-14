---
id: handoffs.latest
title: Latest Context Compiler Handoff
tier: handoff
scope:
  - aios
priority: normal
status: active
summary: Current handoff node for the file-backed AIOS Context Compiler.
applies_when:
  - all_tasks
tags:
  - handoff
  - context-compiler
  - continuity
last_reviewed: 2026-05-12
wiki_status: current
wiki_confidence: medium
last_validated_at: 2026-05-14
validated_by: agent
source_coverage: partial
source_refs:
  - doc:PROJECT.md|Durable project truth|2026-05-14
  - doc:docs/wiki-maintenance.md|Wiki maintenance workflow|2026-05-14
  - code:tools/context-compile.mjs|Compiled packet writer|2026-05-14
known_stale_areas:
  - This file is intentionally a routing handoff and should not accumulate detailed implementation history.
related_pages:
  - features.context-compiler
  - context.index
---

The first Context Compiler version is file-backed, deterministic, and intended to feed future AIOS UI/run-history integration.
Receipts and compiled packets are written under `aios/context/`.
Project truth remains `PROJECT.md`; this handoff only summarizes routing state.

## Acceptance Criteria

- Update this handoff when compiler output shape or routing conventions change.
- Keep detailed implementation history in docs or project truth, not this routing node.
