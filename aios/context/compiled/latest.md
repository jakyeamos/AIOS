# AIOS Context Briefing

## Task Summary

Add likely missing AIOS quality-pipeline gates to repo gate adoption workflow

## Task Classification

- Signals: all_tasks, task_changes_core_logic, task_touches_agent_harness, task_touches_permissions
- Domains: agent-harnesses

## Selected Context Files

- `standards/global.observability.md` (global.observability) — 2 applies_when signal(s) matched; 1 title/summary term(s) matched
- `standards/global.maintainability.md` (global.maintainability) — 2 applies_when signal(s) matched; 1 title/summary term(s) matched
- `config/agent-rules.md` (config.agent-rules) — 1 applies_when signal(s) matched; 1 tag(s) matched; 3 title/summary term(s) matched
- `standards/global.security.md` (global.security) — 1 applies_when signal(s) matched; 2 title/summary term(s) matched
- `index.md` (context.index) — Bootloader context is always loaded.
- `schema.md` (context.schema) — Bootloader context is always loaded.
- `router.md` (context.router) — Bootloader context is always loaded.
- `standards/global.testing.md` (global.testing) — 1 applies_when signal(s) matched
- `domains/agent-harnesses.md` (domains.agent-harnesses) — 1 applies_when signal(s) matched
- `features/context-compiler.md` (features.context-compiler) — 1 applies_when signal(s) matched; 1 title/summary term(s) matched
- `features/prompt-library.md` (features.prompt-library) — 1 applies_when signal(s) matched
- `features/skill-registry.md` (features.skill-registry) — 1 applies_when signal(s) matched; 1 title/summary term(s) matched
- `packets/workflow.approval-gates.md` (packets.workflow.approval-gates) — 2 applies_when signal(s) matched; 1 tag(s) matched; 4 title/summary term(s) matched
- `packets/workflow.durable-agent-workflows.md` (packets.workflow.durable-agent-workflows) — Loaded because domains.agent-harnesses matched and requested this packet.
- `packets/maintainability.architecture-boundaries.md` (packets.maintainability.architecture-boundaries) — 1 applies_when signal(s) matched; 1 title/summary term(s) matched
- `packets/security.oidc-secrets.md` (packets.security.oidc-secrets) — Loaded because global.security matched and requested this packet.
- `handoffs/latest.md` (handoffs.latest) — Bootloader context is always loaded.

## Relevant Rules

- global.observability: AIOS behavior should leave inspectable traces, receipts, and failure evidence.
- global.maintainability: Keep AIOS changes simple, bounded, readable, and aligned to existing architecture.
- config.agent-rules: Behavioral rules loaded for all AIOS agent sessions and workflow execution.
- global.security: Baseline security expectations for all AIOS-managed work.
- context.index: Thin entrypoint for AIOS context routing and compiled briefing generation.
- context.schema: Required schema for AIOS Context Compiler Markdown files.
- context.router: Agent bootloader for AIOS-managed projects and context receipts.
- global.testing: Behavior must be validated with deterministic tests or equivalent execution evidence.
- domains.agent-harnesses: Routing standard for agent workflows, prompts, packets, skills, and orchestration.
- features.context-compiler: Feature context for tiered Markdown routing, scoring, receipts, and writeback candidates.
- features.prompt-library: Feature context for reusable prompt templates, validation, sync, and evaluation workflows.
- features.skill-registry: Feature context for installed skill discovery, sync, and agent workflow routing.
- packets.workflow.approval-gates: Packet for approval-gated writebacks, major context changes, and reviewable proposals.
- packets.workflow.durable-agent-workflows: Packet for long-running durable agent workspaces, goal verifiers, steering, queueing, artifacts, automation, memory, and skill candidacy.
- packets.maintainability.architecture-boundaries: Packet for preserving AIOS module and ownership boundaries during implementation.
- packets.security.oidc-secrets: Deep-enough packet for routing deployment secret work toward short-lived OIDC credentials.
- handoffs.latest: Current handoff node for the file-backed AIOS Context Compiler.

## Project State

- Latest Context Compiler Handoff: Current handoff node for the file-backed AIOS Context Compiler.

## Feature Context

- AIOS Context Compiler Feature: Feature context for tiered Markdown routing, scoring, receipts, and writeback candidates.
- Prompt Library Feature: Feature context for reusable prompt templates, validation, sync, and evaluation workflows.
- Skill Registry Feature: Feature context for installed skill discovery, sync, and agent workflow routing.
- Workflow Approval Gates Packet: Packet for approval-gated writebacks, major context changes, and reviewable proposals.
- Durable Agent Workflows Packet: Packet for long-running durable agent workspaces, goal verifiers, steering, queueing, artifacts, automation, memory, and skill candidacy.
- Architecture Boundaries Packet: Packet for preserving AIOS module and ownership boundaries during implementation.
- OIDC Secretless Deployment Packet: Deep-enough packet for routing deployment secret work toward short-lived OIDC credentials.

## Known Risks

- No context-selection risks detected by the compiler.

## Acceptance Criteria

- global.observability: Generated receipts include loaded and skipped context.
- global.observability: Missing and stale context are visible as warnings.
- global.observability: Scoring decisions are preserved in structured output.
- global.observability: Error output includes remediation guidance that an agent can execute or propose as a follow-up.
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
- global.security: No new static secret path is introduced.
- global.security: Sensitive context is scoped to the task and receipt.
- global.security: Security tradeoffs are explicit writeback candidates when unresolved.
- context.index: Agents produce a context receipt before treating context selection as complete.
- context.index: Loaded context is explainable by task classification, score, or explicit linked packet.
- context.index: Skipped context remains visible in the receipt.
- context.schema: `pnpm context:validate` passes before a context file is treated as authoritative.
- context.schema: `load_if_matched` links point to existing files relative to `aios/context/`.
- context.schema: Thin routing files stay below the deep-packet threshold unless they declare a larger `token_budget`.
- context.router: Every non-trivial run has a loaded/skipped context receipt.
- context.router: Missing, stale, and conflicting context are explicit.
- context.router: Writebacks are proposed for missing rules or reusable patterns.
- global.testing: Schema validation is exercised against real Markdown files.
- global.testing: Routing tests assert selected files and receipt content.
- global.testing: Conflict precedence is covered by executable tests.
- global.testing: New tests protect behavior, public contracts, domain logic, or confirmed regressions; brittle static render/copy assertions are omitted unless their value is documented.
- domains.agent-harnesses: Routing decisions include reasons and skipped alternatives.
- domains.agent-harnesses: Prompt or skill changes include validation paths.
- domains.agent-harnesses: Repeated harness failures are promoted into durable standards, checks, or explicit backlog items.
- domains.agent-harnesses: Agent-facing files remain small enough for agents to load and reason over without losing local context.
- domains.agent-harnesses: Error records include parseable remediation steps.
- domains.agent-harnesses: Packet, prompt, and workflow surfaces preserve stable machine-readable fields when adding human-facing copy.
- domains.agent-harnesses: Writebacks are proposed for review rather than silently promoted.
- domains.agent-harnesses: Non-trivial execution records whether direct execution or subagent execution was chosen and why.
- domains.agent-harnesses: Model or reasoning upgrades track whether extra cost produced meaningful quality improvement.
- domains.agent-harnesses: Durable work records the active goal, verifier, declared surfaces, steering events, queued work, artifacts, memory updates, and next action outside the chat transcript.
- features.context-compiler: Compilation produces structured JSON and agent-readable Markdown.
- features.context-compiler: Receipts include loaded, skipped, conflicts, missing context, and writebacks.
- features.context-compiler: Scoring favors specific, recent, authoritative, low-cost context.
- features.prompt-library: New prompt workflows preserve frontmatter validation and registry generation.
- features.prompt-library: Evaluation output can be traced to prompt template IDs.
- features.skill-registry: Skill routing remains inspectable and deterministic where possible.
- features.skill-registry: Missing skill metadata becomes a writeback candidate.
- packets.workflow.approval-gates: Writeback candidates include type, severity, target file, and reason.
- packets.workflow.approval-gates: Approval needs are visible before promotion to authoritative context.
- packets.workflow.durable-agent-workflows: Durable workspace state records decisions, blockers, owners, dates, useful links, verification status, known pitfalls, and next actions.
- packets.workflow.durable-agent-workflows: Goals include verifiers and explicit stopping conditions.
- packets.workflow.durable-agent-workflows: Steering preserves the active goal unless explicitly changed.
- packets.workflow.durable-agent-workflows: Queued work waits for the current checkpoint and is visible in durable state.
- packets.workflow.durable-agent-workflows: Allowed and out-of-scope work surfaces are declared.
- packets.workflow.durable-agent-workflows: Substantial work has a reviewable artifact when a transcript would be insufficient.
- packets.workflow.durable-agent-workflows: Automation mode is labeled as scheduled fresh work or context-preserving workspace wakeup.
- packets.workflow.durable-agent-workflows: Skill candidacy is based on repeated evidence, not generic preference language.
- packets.maintainability.architecture-boundaries: New modules have a clear owner and caller.
- packets.maintainability.architecture-boundaries: Cross-layer changes are deliberate and documented.
- packets.security.oidc-secrets: No static deployment secret is introduced as the default path.
- packets.security.oidc-secrets: Provider, subject, audience, and permission scope are explicit.
- packets.security.oidc-secrets: Exceptions include owner, reason, review date, and removal path.
- handoffs.latest: Update this handoff when compiler output shape or routing conventions change.
- handoffs.latest: Keep detailed implementation history in docs or project truth, not this routing node.

## Missing Context

- None.

## Writeback Candidates

- None.
