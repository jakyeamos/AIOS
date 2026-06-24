# Context Receipt

## Task

Add durable agent workspaces with goal verifiers, steering, queueing, artifacts, automation, and memory rules

## Loaded Context

- `config/agent-rules.md`
  - Reason: 1 applies_when signal(s) matched; 2 tag(s) matched; 6 title/summary term(s) matched
- `router.md`
  - Reason: Bootloader context is always loaded.
- `standards/global.observability.md`
  - Reason: 1 applies_when signal(s) matched
- `schema.md`
  - Reason: Bootloader context is always loaded.
- `standards/global.maintainability.md`
  - Reason: 1 applies_when signal(s) matched
- `index.md`
  - Reason: Bootloader context is always loaded.
- `domains/agent-harnesses.md`
  - Reason: 1 applies_when signal(s) matched; 3 title/summary term(s) matched
- `features/prompt-library.md`
  - Reason: 1 applies_when signal(s) matched
- `features/context-compiler.md`
  - Reason: 1 applies_when signal(s) matched
- `features/skill-registry.md`
  - Reason: 1 applies_when signal(s) matched; 1 title/summary term(s) matched
- `packets/workflow.durable-agent-workflows.md`
  - Reason: Loaded because domains.agent-harnesses matched and requested this packet.
- `packets/workflow.approval-gates.md`
  - Reason: 1 applies_when signal(s) matched
- `handoffs/latest.md`
  - Reason: Bootloader context is always loaded.

## Skipped Context

- `packets/security.oidc-secrets.md` — Scored below load threshold for this task.
- `packets/knowledge.notebooklm-routing.md` — Scored below load threshold for this task.
- `packets/testing.no-mock-echo.md` — Scored below load threshold for this task.
- `packets/ui.command-center.md` — Scored below load threshold for this task.
- `packets/knowledge.obsidian-routing.md` — Scored below load threshold for this task.
- `features/obsidian-search.md` — Scored below load threshold for this task.
- `features/standards-delta.md` — Scored below load threshold for this task.
- `standards/global.testing.md` — Scored below load threshold for this task.
- `packets/maintainability.architecture-boundaries.md` — Scored below load threshold for this task.
- `standards/global.security.md` — Scored below load threshold for this task.
- `projects/aios-ui.md` — Scored below load threshold for this task.
- `domains/web-apps.md` — Scored below load threshold for this task.
- `projects/index.md` — Scored below load threshold for this task.
- `projects/taski.md` — Scored below load threshold for this task.
- `projects/soundscape.md` — Scored below load threshold for this task.
- `features/index.md` — Scored below load threshold for this task.
- `projects/terrace.md` — Scored below load threshold for this task.
- `domains/knowledge-systems.md` — Scored below load threshold for this task.
- `domains/index.md` — Scored below load threshold for this task.
- `domains/data-projects.md` — Scored below load threshold for this task.

## Context Routing Manifest

- Phase: context_compile
- Loaded sources: 13
- Skipped sources: 20
- Estimated context tokens: 5713
- Second brain available: false
- Second brain used: false
- Fallback used: false

## Conflicts

None detected.

## Missing Context

- None.

## Writeback Candidates

- None.
