---
id: features.standards-delta
title: Standards Delta Health Feature
tier: feature
scope:
  - aios-ui
priority: high
status: active
summary: Feature context for project health scores, standards deltas, and critical-delta drilldowns.
applies_when:
  - task_touches_standards_delta
  - task_touches_aios_ui
  - task_touches_observability
load_if_matched:
  - packets/ui.command-center.md
tags:
  - standards-delta
  - health-score
  - critical-delta
  - project-health
related:
  - ../../docs/architecture/2026-04-23-aios-standards-delta-health-phase3b.md
last_reviewed: 2026-05-12
---

Standards delta health evaluates projects against structured standards and preserves unknowns as first-class states.
Critical delta, unknown coverage, migration delta, and domain scores should be inspectable rather than collapsed into a single opaque health number.
The UI already has project health surfaces; new work should improve explanation and drilldown clarity.

## Acceptance Criteria

- Health score explanations point to source-backed delta records.
- Unknown and missing states remain visible.
- Critical deltas can be inspected by domain, severity, and remediation path.
