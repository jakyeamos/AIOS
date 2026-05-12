---
id: packets.ui.command-center
title: AIOS Command Center UI Packet
tier: packet
scope:
  - aios-ui
priority: high
status: active
summary: UI packet for exposing AIOS operational state, drilldowns, receipts, and warnings.
applies_when:
  - task_touches_design
  - task_touches_aios_ui
  - task_touches_observability
tags:
  - ui
  - command-center
  - drilldowns
  - receipts
last_reviewed: 2026-05-12
---

Command-center surfaces should show what happened, why it happened, and what needs attention.
For context compilation, likely UI surfaces include loaded packets per run, receipts, missing context warnings, stale context warnings, conflicts, and writeback candidates.
Do not hide uncertainty behind a summary score.

## Acceptance Criteria

- Operators can drill into source-backed evidence.
- Missing and conflicting state appears as actionable warnings.
- Receipts can later be attached to run history.
