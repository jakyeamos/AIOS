---
id: features.index
title: Feature Context Index
tier: feature
scope:
  - all_projects
priority: normal
status: active
summary: Index of feature packets available for task-specific routing.
applies_when:
  - task_touches_context_compiler
tags:
  - features
  - packets
last_reviewed: 2026-05-12
---

Feature context narrows a project or domain into a concrete subsystem.
Feature files should route to implementation docs, packets, or evidence without becoming large design essays.

## Acceptance Criteria

- Feature context loads only when task terms or linked context justify it.
- Missing feature files are proposed as writebacks.
