# AIOS Context Briefing

## Task Summary

Add durable agent workspaces with goal verifiers, steering, queueing, artifacts, automation, and memory rules

## Task Classification

- Signals: all_tasks, task_touches_agent_harness
- Domains: agent-harnesses

## Selected Context Files

- `config/agent-rules.md` (config.agent-rules) — 1 applies_when signal(s) matched; 2 tag(s) matched; 6 title/summary term(s) matched
- `router.md` (context.router) — Bootloader context is always loaded.
- `standards/global.observability.md` (global.observability) — 1 applies_when signal(s) matched
- `schema.md` (context.schema) — Bootloader context is always loaded.
- `standards/global.maintainability.md` (global.maintainability) — 1 applies_when signal(s) matched
- `index.md` (context.index) — Bootloader context is always loaded.
- `domains/agent-harnesses.md` (domains.agent-harnesses) — 1 applies_when signal(s) matched; 3 title/summary term(s) matched
- `features/prompt-library.md` (features.prompt-library) — 1 applies_when signal(s) matched
- `features/context-compiler.md` (features.context-compiler) — 1 applies_when signal(s) matched
- `features/skill-registry.md` (features.skill-registry) — 1 applies_when signal(s) matched; 1 title/summary term(s) matched
- `packets/workflow.durable-agent-workflows.md` (packets.workflow.durable-agent-workflows) — Loaded because domains.agent-harnesses matched and requested this packet.
- `packets/workflow.approval-gates.md` (packets.workflow.approval-gates) — 1 applies_when signal(s) matched
- `handoffs/latest.md` (handoffs.latest) — Bootloader context is always loaded.

## Relevant Rules

- config.agent-rules: Behavioral rules loaded for all AIOS agent sessions and workflow execution.
- context.router: Agent bootloader for AIOS-managed projects and context receipts.
- global.observability: AIOS behavior should leave inspectable traces, receipts, and failure evidence.
- context.schema: Required schema for AIOS Context Compiler Markdown files.
- global.maintainability: Keep AIOS changes simple, bounded, readable, and aligned to existing architecture.
- context.index: Thin entrypoint for AIOS context routing and compiled briefing generation.
- domains.agent-harnesses: Routing standard for agent workflows, prompts, packets, skills, and orchestration.
- features.prompt-library: Feature context for reusable prompt templates, validation, sync, and evaluation workflows.
- features.context-compiler: Feature context for tiered Markdown routing, scoring, receipts, and writeback candidates.
- features.skill-registry: Feature context for installed skill discovery, sync, and agent workflow routing.
- packets.workflow.durable-agent-workflows: Packet for long-running durable agent workspaces, goal verifiers, steering, queueing, artifacts, automation, memory, and skill candidacy.
- packets.workflow.approval-gates: Packet for approval-gated writebacks, major context changes, and reviewable proposals.
- handoffs.latest: Current handoff node for the file-backed AIOS Context Compiler.

## Project State

- Latest Context Compiler Handoff: Current handoff node for the file-backed AIOS Context Compiler.

## Feature Context

- Prompt Library Feature: Feature context for reusable prompt templates, validation, sync, and evaluation workflows.
- AIOS Context Compiler Feature: Feature context for tiered Markdown routing, scoring, receipts, and writeback candidates.
- Skill Registry Feature: Feature context for installed skill discovery, sync, and agent workflow routing.
- Durable Agent Workflows Packet: Packet for long-running durable agent workspaces, goal verifiers, steering, queueing, artifacts, automation, memory, and skill candidacy.
- Workflow Approval Gates Packet: Packet for approval-gated writebacks, major context changes, and reviewable proposals.

## Known Risks

- No context-selection risks detected by the compiler.

## Acceptance Criteria

- context.router: Every non-trivial run has a loaded/skipped context receipt.
- context.router: Missing, stale, and conflicting context are explicit.
- context.router: Writebacks are proposed for missing rules or reusable patterns.
- global.observability: Generated receipts include loaded and skipped context.
- global.observability: Missing and stale context are visible as warnings.
- global.observability: Scoring decisions are preserved in structured output.
- global.observability: Error output includes remediation guidance that an agent can execute or propose as a follow-up.
- context.schema: `pnpm context:validate` passes before a context file is treated as authoritative.
- context.schema: `load_if_matched` links point to existing files relative to `aios/context/`.
- context.schema: Thin routing files stay below the deep-packet threshold unless they declare a larger `token_budget`.
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
- features.prompt-library: New prompt workflows preserve frontmatter validation and registry generation.
- features.prompt-library: Evaluation output can be traced to prompt template IDs.
- features.context-compiler: Compilation produces structured JSON and agent-readable Markdown.
- features.context-compiler: Receipts include loaded, skipped, conflicts, missing context, and writebacks.
- features.context-compiler: Scoring favors specific, recent, authoritative, low-cost context.
- features.skill-registry: Skill routing remains inspectable and deterministic where possible.
- features.skill-registry: Missing skill metadata becomes a writeback candidate.
- packets.workflow.durable-agent-workflows: Durable workspace state records decisions, blockers, owners, dates, useful links, verification status, known pitfalls, and next actions.
- packets.workflow.durable-agent-workflows: Goals include verifiers and explicit stopping conditions.
- packets.workflow.durable-agent-workflows: Steering preserves the active goal unless explicitly changed.
- packets.workflow.durable-agent-workflows: Queued work waits for the current checkpoint and is visible in durable state.
- packets.workflow.durable-agent-workflows: Allowed and out-of-scope work surfaces are declared.
- packets.workflow.durable-agent-workflows: Substantial work has a reviewable artifact when a transcript would be insufficient.
- packets.workflow.durable-agent-workflows: Automation mode is labeled as scheduled fresh work or context-preserving workspace wakeup.
- packets.workflow.durable-agent-workflows: Skill candidacy is based on repeated evidence, not generic preference language.
- packets.workflow.approval-gates: Writeback candidates include type, severity, target file, and reason.
- packets.workflow.approval-gates: Approval needs are visible before promotion to authoritative context.
- handoffs.latest: Update this handoff when compiler output shape or routing conventions change.
- handoffs.latest: Keep detailed implementation history in docs or project truth, not this routing node.

## Missing Context

- None.

## Writeback Candidates

- None.
