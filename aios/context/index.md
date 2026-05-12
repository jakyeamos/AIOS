---
id: context.index
title: AIOS Context Compiler Index
tier: global
scope:
  - all_projects
priority: high
status: active
summary: Thin entrypoint for AIOS context routing and compiled briefing generation.
applies_when:
  - all_tasks
tags:
  - context
  - routing
  - bootloader
related:
  - router.md
  - schema.md
last_reviewed: 2026-05-12
---

AIOS context is routed through small Markdown manifests, not broad document dumps.
Agents should classify the task, load the project truth file, then add only matching standards, domains, features, packets, and handoffs.
This directory is the authoritative file-backed source for the first Context Compiler version.
Compiled packets are written to `compiled/latest.md` and receipts to `receipts/latest.md`.

## Applicability

- Use this file before implementation, debugging, design, or research inside AIOS-managed work.
- Prefer compiler output over manual Markdown browsing when a task has a concrete objective.
- Load deeper packets only when selected by frontmatter or explicit receipt rationale.

## Acceptance Criteria

- Agents produce a context receipt before treating context selection as complete.
- Loaded context is explainable by task classification, score, or explicit linked packet.
- Skipped context remains visible in the receipt.

## Priority Notes

Global immutable standards cannot be weakened by project, feature, packet, or task-local convenience.
