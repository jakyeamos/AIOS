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
---

Major writebacks should be proposed for review instead of auto-approved.
Examples include new global rules, changed immutable standards, project truth rewrites, and broad reusable packets.
Small stale-date or typo fixes can be treated as normal documentation work.

## Acceptance Criteria

- Writeback candidates include type, severity, target file, and reason.
- Approval needs are visible before promotion to authoritative context.
