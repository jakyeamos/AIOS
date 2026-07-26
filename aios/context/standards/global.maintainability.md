---
id: global.maintainability
title: Global Maintainability Standard
tier: global
scope:
  - all_projects
priority: immutable
status: active
summary: Keep AIOS changes simple, bounded, readable, and aligned to existing architecture.
applies_when:
  - all_tasks
  - task_changes_core_logic
  - task_extends_existing_concept
  - task_touches_event_loop_or_message_flow
tags:
  - maintainability
  - architecture
  - simplicity
  - confident-code
  - event-loop
conflicts:
  protected_topics:
    - maintainability
    - architecture
last_reviewed: 2026-05-12
---

Prefer boring, inspectable logic over opaque routing or broad abstractions.
Read existing code and relevant context before modifying behavior.
Keep file-backed rules thin and create packets only for repeated needs.
Architectural changes must have executable evidence and reviewable artifacts; durable project context is optional.
Common error surfaces require durable fixes at the source of recurrence, not repeated local workarounds.
When context is limited, keep agent-facing files small enough to load, scan, and reason over in one pass; split by responsibility when a file becomes context-heavy.
Machine readability takes precedence over human-friendly presentation: instructions, packets, errors, logs, schemas, receipts, and status surfaces must preserve parseable structure, stable identifiers, explicit states, deterministic labels, and actionable remediation fields before adding prose or visual polish.
Write confident code when extending a domain concept: update the existing contract, names, call sites, and tests so the new model is explicit. Do not bolt on a parallel service, function, table, or type just because the old name encoded an implicit default. If `Notification` implicitly meant email and SMS is added, prefer an explicit discriminator such as `Notification.type = "email" | "sms"` or an equivalent existing local pattern, and rename stale generic behavior such as `sendNotification()` to `sendEmailNotification()` when it remains email-only.
Do not write defensive code for impossible event-loop interleavings. When a synchronous send/enqueue/call cannot receive an asynchronous response until the current turn yields, keep the code ordered by the real causal model: send the message, then attach the response listener if the platform guarantees the response cannot arrive before listener registration. Adding handlers "just in case" before the cause exists is a sign to verify the runtime contract, not to encode superstition.

## Applicability

- Load for most implementation work and always for compiler/routing changes.
- Pair with relevant project context when it materially improves handoff quality.
- Apply when a feature turns an implicit default into one option among several.
- Apply when code sends work to a worker, subprocess, event emitter, queue, actor, or callback-driven runtime and awaits a response.

## Acceptance Criteria

- New code has a narrow surface and deterministic behavior.
- Expanded concepts update the original contract and stale generic names instead of leaving parallel, semantically overlapping APIs.
- Existing call sites, tests, fixtures, docs, and persisted shapes are checked for implicit-default assumptions when a second variant is added.
- Message/worker response code reflects the actual event-loop or runtime ordering guarantees instead of guarding against impossible races.
- If a handler is registered before a send, the code or plan identifies a real reentrancy, synchronous callback, replay buffer, or platform-specific reason.
- Recurring error surfaces are resolved with durable remediation or captured as explicit follow-up work.
- Agent-facing files fit a bounded context budget, or document why the larger surface remains coherent.
- Agent-facing artifacts preserve machine-readable structure before prose or visual presentation.
- Handoff or optional project-context files reflect meaningful architecture changes when those files are in scope.
- Context routing remains auditable from receipt output.
