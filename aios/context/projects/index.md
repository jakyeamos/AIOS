---
id: projects.index
title: Project Context Index
tier: project
scope:
  - all_projects
priority: normal
status: active
summary: Index of optional project-context routing files for AIOS-managed work.
applies_when:
  - task_touches_context_compiler
tags:
  - projects
  - truth
last_reviewed: 2026-05-12
---

Project files route task context into the correct product or repository truth.
They should summarize current state and point to authoritative docs instead of copying them.

## Acceptance Criteria

- Project context links to the durable truth source.
- Missing optional project context is not a blocker; add a writeback only when it would prevent a real recurring failure.
