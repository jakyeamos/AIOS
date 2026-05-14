---
id: projects.aios-ui
title: AIOS UI Project Context
tier: project
scope:
  - aios
  - aios-ui
priority: high
status: active
summary: Project truth routing for the local AIOS Next.js command center.
applies_when:
  - task_touches_aios_ui
  - task_touches_web_app
  - task_touches_design
  - task_touches_observability
tags:
  - aios-ui
  - dashboard
  - command-center
  - health-score
related:
  - ../../PROJECT.md
  - ../../docs/architecture/2026-04-23-aios-standards-delta-health-phase3b.md
last_reviewed: 2026-05-12
wiki_status: current
wiki_confidence: medium
last_validated_at: 2026-05-14
validated_by: agent
source_coverage: partial
source_refs:
  - doc:PROJECT.md|AIOS project truth and UI summary|2026-05-14
  - code:aios-ui/package.json|UI scripts and dependencies|2026-05-14
  - code:aios-ui/app/knowledge/page.tsx|Knowledge UI route|2026-05-14
  - code:aios-ui/server/aios/knowledge.ts|Knowledge UI backend assembly|2026-05-14
  - doc:docs/architecture/2026-04-23-aios-standards-delta-health-phase3b.md|Standards delta UI architecture note|2026-05-14
known_stale_areas:
  - UI build currently depends on local native `better-sqlite3` bindings and may fail if pnpm build scripts are not approved.
related_pages:
  - packets.ui.command-center
  - features.context-compiler
---

AIOS UI is a local Next.js dashboard over `~/AIOS/data/aios.db`.
It is strongest at run observability, project health, grounded query, and control-plane packet generation.
Current truth lives in `PROJECT.md`, while standards-delta design history lives under `docs/architecture/`.
UI additions should favor inspectable state and existing dashboard patterns.

## Acceptance Criteria

- Project health and delta UI stays source-backed.
- New UI surfaces can explain missing, inferred, or conflicting signals.
- Meaningful architecture changes update `PROJECT.md`.
