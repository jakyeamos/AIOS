---
id: global.design
title: Global Design Standard
tier: global
scope:
  - all_projects
priority: high
status: active
summary: AIOS UI should expose system state clearly without decorative or low-density surfaces.
applies_when:
  - task_touches_design
  - task_touches_product_design
tags:
  - design
  - ui
  - command-center
last_reviewed: 2026-05-12
---

AIOS product surfaces are operational tools, not marketing pages.
Prefer dense but readable tables, drilldowns, traces, filters, and explicit state labels.
Do not hide missing or inferred data behind polished summary numbers.

## Applicability

- Load for UI, dashboard, command-center, and drilldown work.
- Pair with observability when the UI explains system health or routing.

## Acceptance Criteria

- Users can inspect why a score, warning, or packet was produced.
- Critical states are not collapsed into vague healthy/unhealthy labels.
- Controls match expected operational workflows.
