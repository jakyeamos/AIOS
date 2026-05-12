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
---

The first Context Compiler version is file-backed, deterministic, and intended to feed future AIOS UI/run-history integration.
Receipts and compiled packets are written under `aios/context/`.
Project truth remains `PROJECT.md`; this handoff only summarizes routing state.

## Acceptance Criteria

- Update this handoff when compiler output shape or routing conventions change.
- Keep detailed implementation history in docs or project truth, not this routing node.
