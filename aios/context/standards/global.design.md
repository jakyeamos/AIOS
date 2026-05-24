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

When a UI task needs visual direction, agents may use Refero Styles
(`https://styles.refero.design/`) as a design-reference source before implementation.
Treat Refero output as inspiration and extracted design vocabulary, not as binding
project truth. Any adopted colors, typography, spacing, or component patterns must be
named in the task plan or design notes and reconciled with AIOS operational UI rules.

## Applicability

- Load for UI, dashboard, command-center, and drilldown work.
- Pair with observability when the UI explains system health or routing.

## Acceptance Criteria

- Users can inspect why a score, warning, or packet was produced.
- Critical states are not collapsed into vague healthy/unhealthy labels.
- Controls match expected operational workflows.
- UI work that uses Refero or another external design source cites the source and
  records which patterns were adopted or rejected.
