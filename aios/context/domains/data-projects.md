---
id: domains.data-projects
title: Data Projects Domain Standard
tier: domain
scope:
  - data_projects
priority: normal
status: active
summary: Routing standard for SQLite, corpus, metrics, and durable data flows.
applies_when:
  - task_touches_data
tags:
  - data
  - sqlite
  - metrics
  - corpus
last_reviewed: 2026-05-12
---

Data work should preserve provenance, schema clarity, and replayable evidence.
Prefer structured records over ambiguous text blobs when data feeds UI or audits.
Do not collapse missing data into successful or healthy states.

## Acceptance Criteria

- Data shape and source are explicit.
- Missing or inferred records remain distinguishable.
