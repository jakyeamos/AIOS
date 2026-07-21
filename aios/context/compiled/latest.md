# AIOS Context Briefing

## Task Summary

Start M5: make approvals, capabilities, loopback, egress, writebacks, and closeout first-class governed states with negative security tests and truthful next actions.

## Task Classification

- Signals: all_tasks, task_touches_permissions, task_touches_testing, task_touches_web_app
- Domains: web-apps

## Selected Context Files

- `standards/global.security.md` (global.security) — 1 applies_when signal(s) matched; 1 tag(s) matched; 3 title/summary term(s) matched
- `standards/global.testing.md` (global.testing) — 1 applies_when signal(s) matched; 2 title/summary term(s) matched
- `schema.md` (context.schema) — Bootloader context is always loaded.
- `router.md` (context.router) — Bootloader context is always loaded.
- `standards/global.maintainability.md` (global.maintainability) — 1 applies_when signal(s) matched
- `index.md` (context.index) — Bootloader context is always loaded.
- `config/agent-rules.md` (config.agent-rules) — 1 applies_when signal(s) matched
- `domains/web-apps.md` (domains.web-apps) — 1 applies_when signal(s) matched; 1 title/summary term(s) matched
- `projects/aios-ui.md` (projects.aios-ui) — 1 applies_when signal(s) matched; 2 title/summary term(s) matched
- `features/context-compiler.md` (features.context-compiler) — 1 tag(s) matched; 1 title/summary term(s) matched
- `packets/workflow.approval-gates.md` (packets.workflow.approval-gates) — 1 applies_when signal(s) matched; 2 tag(s) matched; 4 title/summary term(s) matched
- `packets/testing.no-mock-echo.md` (packets.testing.no-mock-echo) — 1 applies_when signal(s) matched; 1 title/summary term(s) matched
- `packets/security.oidc-secrets.md` (packets.security.oidc-secrets) — Loaded because global.security matched and requested this packet.
- `handoffs/latest.md` (handoffs.latest) — Bootloader context is always loaded.
- `services/.context/success-criteria.md` (module.services.success-criteria) — 1 applies_when signal(s) matched

## Relevant Rules

- global.security: Baseline security expectations for all AIOS-managed work.
- global.testing: Behavior must be validated with deterministic tests or equivalent execution evidence.
- context.schema: Required schema for AIOS Context Compiler Markdown files.
- context.router: Agent bootloader for AIOS-managed projects and context receipts.
- global.maintainability: Keep AIOS changes simple, bounded, readable, and aligned to existing architecture.
- context.index: Thin entrypoint for AIOS context routing and compiled briefing generation.
- config.agent-rules: Behavioral rules loaded for all AIOS agent sessions and workflow execution.
- domains.web-apps: Routing standard for Next.js, React, dashboard, and deployment work.
- projects.aios-ui: Project truth routing for the local AIOS Next.js command center.
- features.context-compiler: Feature context for tiered Markdown routing, scoring, receipts, and writeback candidates.
- packets.workflow.approval-gates: Packet for approval-gated writebacks, major context changes, and reviewable proposals.
- packets.testing.no-mock-echo: Testing packet for avoiding shallow tests that only mirror mocked behavior.
- packets.security.oidc-secrets: Deep-enough packet for routing deployment secret work toward short-lived OIDC credentials.
- handoffs.latest: Current handoff node for the file-backed AIOS Context Compiler.
- module.services.success-criteria: Service-layer notes for success criteria and evaluation records.

## Project State

- AIOS UI Project Context: Project truth routing for the local AIOS Next.js command center.
- Latest Context Compiler Handoff: Current handoff node for the file-backed AIOS Context Compiler.

## Feature Context

- AIOS Context Compiler Feature: Feature context for tiered Markdown routing, scoring, receipts, and writeback candidates.
- Workflow Approval Gates Packet: Packet for approval-gated writebacks, major context changes, and reviewable proposals.
- No Mock Echo Testing Packet: Testing packet for avoiding shallow tests that only mirror mocked behavior.
- OIDC Secretless Deployment Packet: Deep-enough packet for routing deployment secret work toward short-lived OIDC credentials.

## Known Risks

- No context-selection risks detected by the compiler.

## Acceptance Criteria

- global.security: No new static secret path is introduced.
- global.security: Sensitive context is scoped to the task and receipt.
- global.security: Security tradeoffs are explicit writeback candidates when unresolved.
- global.testing: Schema validation is exercised against real Markdown files.
- global.testing: Routing tests assert selected files and receipt content.
- global.testing: Conflict precedence is covered by executable tests.
- global.testing: New tests protect behavior, public contracts, domain logic, or confirmed regressions; brittle static render/copy assertions are omitted unless their value is documented.
- context.schema: `pnpm context:validate` passes before a context file is treated as authoritative.
- context.schema: `load_if_matched` links point to existing files relative to `aios/context/`.
- context.schema: Thin routing files stay below the deep-packet threshold unless they declare a larger `token_budget`.
- context.router: Every non-trivial run has a loaded/skipped context receipt.
- context.router: Missing, stale, and conflicting context are explicit.
- context.router: Writebacks are proposed for missing rules or reusable patterns.
- global.maintainability: New code has a narrow surface and deterministic behavior.
- global.maintainability: Expanded concepts update the original contract and stale generic names instead of leaving parallel, semantically overlapping APIs.
- global.maintainability: Existing call sites, tests, fixtures, docs, and persisted shapes are checked for implicit-default assumptions when a second variant is added.
- global.maintainability: Message/worker response code reflects the actual event-loop or runtime ordering guarantees instead of guarding against impossible races.
- global.maintainability: If a handler is registered before a send, the code or plan identifies a real reentrancy, synchronous callback, replay buffer, or platform-specific reason.
- global.maintainability: Recurring error surfaces are resolved with durable remediation or captured as explicit follow-up work.
- global.maintainability: Agent-facing files fit a bounded context budget, or document why the larger surface remains coherent.
- global.maintainability: Agent-facing artifacts preserve machine-readable structure before prose or visual presentation.
- global.maintainability: Project truth or handoff files reflect meaningful architecture changes.
- global.maintainability: Context routing remains auditable from receipt output.
- context.index: Agents produce a context receipt before treating context selection as complete.
- context.index: Loaded context is explainable by task classification, score, or explicit linked packet.
- context.index: Skipped context remains visible in the receipt.
- domains.web-apps: User-facing state is source-backed and inspectable.
- domains.web-apps: UI changes follow the existing component and routing patterns.
- projects.aios-ui: Project health and delta UI stays source-backed.
- projects.aios-ui: New UI surfaces can explain missing, inferred, or conflicting signals.
- projects.aios-ui: Meaningful architecture changes update `PROJECT.md`.
- features.context-compiler: Compilation produces structured JSON and agent-readable Markdown.
- features.context-compiler: Receipts include loaded, skipped, conflicts, missing context, and writebacks.
- features.context-compiler: Scoring favors specific, recent, authoritative, low-cost context.
- packets.workflow.approval-gates: Writeback candidates include type, severity, target file, and reason.
- packets.workflow.approval-gates: Approval needs are visible before promotion to authoritative context.
- packets.testing.no-mock-echo: Tests fail before implementation when behavior is absent.
- packets.testing.no-mock-echo: Tests inspect actual output and side effects.
- packets.security.oidc-secrets: No static deployment secret is introduced as the default path.
- packets.security.oidc-secrets: Provider, subject, audience, and permission scope are explicit.
- packets.security.oidc-secrets: Exceptions include owner, reason, review date, and removal path.
- handoffs.latest: Update this handoff when compiler output shape or routing conventions change.
- handoffs.latest: Keep detailed implementation history in docs or project truth, not this routing node.

## Missing Context

- None.

## Writeback Candidates

- None.
