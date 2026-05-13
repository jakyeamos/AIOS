---
id: global.observability
title: Global Observability Standard
tier: global
scope:
  - all_projects
priority: immutable
status: active
summary: AIOS behavior should leave inspectable traces, receipts, and failure evidence.
applies_when:
  - task_touches_observability
  - task_touches_agent_harness
  - task_changes_core_logic
tags:
  - observability
  - receipts
  - audit
  - trace
  - errors
conflicts:
  protected_topics:
    - observability
last_reviewed: 2026-05-12
---

Routing, retrieval, scoring, and writeback proposals must be inspectable after the run.
Receipts should explain loaded context, skipped context, conflicts, stale files, and missing context.
UI surfaces should distinguish confirmed data from inferred or missing signals.
Errors should be emitted in machine-readable structures that include severity, source, affected target, and remediation steps.

## Applicability

- Load for health scores, standards deltas, run history, dashboards, and compiler traces.
- Pair with design context for user-facing inspectability work.

## Acceptance Criteria

- Generated receipts include loaded and skipped context.
- Missing and stale context are visible as warnings.
- Scoring decisions are preserved in structured output.
- Error output includes remediation guidance that an agent can execute or propose as a follow-up.
