---
id: packets.workflow.durable-agent-workflows
title: Durable Agent Workflows Packet
tier: packet
scope:
  - all_projects
priority: high
status: active
summary: Packet for long-running durable agent workspaces, goal verifiers, steering, queueing, artifacts, automation, memory, and skill candidacy.
applies_when:
  - task_touches_agent_harness
  - task_touches_skill_registry
  - task_touches_prompt_library
tags:
  - workflow
  - durable
  - agent
  - goals
  - automation
last_reviewed: 2026-06-24
related:
  - ../../docs/workflows/durable-agent-workflows.md
---

Use a durable workspace when work recurs, spans sessions, waits on external state, or must preserve decisions, blockers, owners, dates, useful links, verification status, known pitfalls, and next actions. Examples include release, quality gate, TMCP skill audit, repo adoption, documentation review, and external monitoring threads.

Durable work must avoid context sprawl. Update durable memory only when facts, decisions, blockers, owners, verification results, known pitfalls, reusable workflow patterns, useful links, or unresolved questions meaningfully change. Do not copy noisy transcripts or speculation into durable files.

Every durable goal needs a verifier and a stopping condition. Reject or refine vague goals such as "implement the plan" until the verifier is observable: typecheck passes, lint passes, tests pass, build passes, validation matrix passes, repro is fixed, benchmark improves, deployment succeeds, artifact audit is complete, or an explicit blocker is accepted.

Steering and queueing are distinct. `/steer` changes the current execution direction immediately and preserves the active goal unless the operator explicitly changes it. `/queue` records work that should run after the current checkpoint and must not silently interrupt in-flight verification. Both should be visible in the run log or durable workspace state.

Declare work surfaces before expanding tool reach:

- Repo work: code, tests, migrations, configs, docs.
- Artifact work: PDFs, decks, spreadsheets, reports, generated specs, HTML outputs.
- Surface work: browser UI, Storybook, deployed previews, static pages, data apps.
- Communication work: Slack, Gmail, PR comments, review comments, issue threads.
- Monitoring work: deployment checks, failing gates, review responses, regressions, external state changes.
- Memory work: decisions, blockers, TODOs, owners, dates, known pitfalls, reusable workflows.

For substantial work, the chat transcript is not the source of truth. Prefer a reviewable artifact such as a validation matrix, implementation checklist, audit log, canonical spreadsheet, generated behavioral spec, PR review summary, decision ledger, failing-gate report, static HTML dashboard, or deployment verification report.

Automation must distinguish fresh scheduled jobs from context-preserving workspace wakeups. Automations may check PR comments, deployment status, gates, reports, review feedback, repeated failures, or blockers. They must not silently send external communications or perform destructive actions unless project rules explicitly allow it; prefer draft or review flows.

Skill extraction requires repeated evidence. Promote a workflow toward TMCP skill candidacy only when it repeats across runs or repos, the same failure mode appears more than once, the workflow has a reusable decision tree and verifier, packaging would reduce tokens, variance, or repeated mistakes, scope and non-scope are clear, and the skill can be evaluated objectively.

## Acceptance Criteria

- Durable workspace state records decisions, blockers, owners, dates, useful links, verification status, known pitfalls, and next actions.
- Goals include verifiers and explicit stopping conditions.
- Steering preserves the active goal unless explicitly changed.
- Queued work waits for the current checkpoint and is visible in durable state.
- Allowed and out-of-scope work surfaces are declared.
- Substantial work has a reviewable artifact when a transcript would be insufficient.
- Automation mode is labeled as scheduled fresh work or context-preserving workspace wakeup.
- Skill candidacy is based on repeated evidence, not generic preference language.
