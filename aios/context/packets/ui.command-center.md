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
wiki_status: current
wiki_confidence: medium
last_validated_at: 2026-05-14
validated_by: agent
source_coverage: partial
source_refs:
  - code:aios-ui/app/context/page.tsx|Context compiler UI surface|2026-05-14
  - code:aios-ui/app/knowledge/page.tsx|Knowledge index UI surface|2026-05-14
  - code:aios-ui/components/knowledge/KnowledgePageView.tsx|Knowledge page detail UI|2026-05-14
  - code:aios-ui/server/aios/knowledge.ts|Knowledge data source assembly|2026-05-14
  - doc:PROJECT.md|UI project truth summary|2026-05-14
known_stale_areas:
  - UI screenshots and visual verification are not captured in this packet; run browser verification for layout-sensitive changes.
related_pages:
  - projects.aios-ui
  - features.context-compiler
---

Command-center surfaces should show what happened, why it happened, and what needs attention.
For context compilation, likely UI surfaces include loaded packets per run, receipts, missing context warnings, stale context warnings, conflicts, and writeback candidates.
Do not hide uncertainty behind a summary score.

## Acceptance Criteria

- Operators can drill into source-backed evidence.
- Missing and conflicting state appears as actionable warnings.
- Receipts can later be attached to run history.
