---
id: packets.workflow.approval-gates
title: Workflow Approval Gates Packet
tier: packet
scope:
  - all_projects
priority: normal
status: active
summary: Packet for approval-gated writebacks, major context changes, and reviewable proposals.
applies_when:
  - task_touches_permissions
  - task_touches_agent_harness
tags:
  - workflow
  - approvals
  - writebacks
last_reviewed: 2026-05-12
wiki_status: current
wiki_confidence: medium
last_validated_at: 2026-05-14
validated_by: agent
source_coverage: partial
source_refs:
  - code:tools/context-compile.mjs|Writeback candidate generation|2026-05-14
  - code:aios-ui/server/aios/topic-graph.ts|Improvement writeback surfaces|2026-05-14
  - code:aios-ui/server/aios/schema.ts|Improvement writeback tables|2026-05-14
  - doc:PROJECT.md|Project truth and approval posture|2026-05-14
known_stale_areas:
  - Approval policy is enforced by workflow conventions and UI surfaces, not a single centralized gate for every writeback path.
related_pages:
  - context.router
  - features.context-compiler
---

Major writebacks should be proposed for review instead of auto-approved.
Examples include new global rules, changed immutable standards, project truth rewrites, and broad reusable packets.
Small stale-date or typo fixes can be treated as normal documentation work.

## Acceptance Criteria

- Writeback candidates include type, severity, target file, and reason.
- Approval needs are visible before promotion to authoritative context.
