# AIOS Context Briefing

## Task Summary

Implement repository-side quality evidence for Pronto taxonomy: canonical Tests and Secrets scan, conditional Dependency audit, and preserve existing Build, Smoke, Lint, Formatter, Typecheck, and Dead-code evidence in AIOS workflows without fabricating gates.

## Task Classification

- Signals: all_tasks, task_changes_core_logic, task_touches_agent_harness, task_touches_api_keys, task_touches_auth, task_touches_design, task_touches_observability, task_touches_permissions, task_touches_testing, task_touches_web_app
- Domains: web-apps, agent-harnesses

## Selected Context Files

- `standards/global.security.md` (global.security) — 3 applies_when signal(s) matched; 1 tag(s) matched; 2 title/summary term(s) matched
- `standards/global.observability.md` (global.observability) — 3 applies_when signal(s) matched; 1 tag(s) matched; 2 title/summary term(s) matched
- `standards/global.testing.md` (global.testing) — 2 applies_when signal(s) matched; 3 title/summary term(s) matched
- `standards/global.maintainability.md` (global.maintainability) — 2 applies_when signal(s) matched; 2 title/summary term(s) matched
- `standards/global.design.md` (global.design) — 1 applies_when signal(s) matched; 1 tag(s) matched; 2 title/summary term(s) matched
- `config/agent-rules.md` (config.agent-rules) — 1 applies_when signal(s) matched; 1 tag(s) matched; 3 title/summary term(s) matched
- `index.md` (context.index) — Bootloader context is always loaded.
- `schema.md` (context.schema) — Bootloader context is always loaded.
- `router.md` (context.router) — Bootloader context is always loaded.
- `domains/web-apps.md` (domains.web-apps) — 2 applies_when signal(s) matched; 1 title/summary term(s) matched
- `domains/agent-harnesses.md` (domains.agent-harnesses) — 1 applies_when signal(s) matched; 1 tag(s) matched; 1 title/summary term(s) matched
- `domains/product-design.md` (domains.product-design) — 1 applies_when signal(s) matched; 1 title/summary term(s) matched
- `projects/aios-ui.md` (projects.aios-ui) — 3 applies_when signal(s) matched; 3 title/summary term(s) matched
- `.agents/context/README.md` (aios.repo-context) — 1 tag(s) matched; 6 title/summary term(s) matched
- `.agents/context/ui.md` (aios.ui-context) — 1 tag(s) matched; 3 title/summary term(s) matched
- `.agents/context/architecture.md` (aios.architecture) — 1 tag(s) matched; 3 title/summary term(s) matched
- `projects/terrace.md` (projects.terrace) — 1 tag(s) matched; 1 title/summary term(s) matched
- `features/prompt-library.md` (features.prompt-library) — 1 applies_when signal(s) matched; 1 title/summary term(s) matched
- `features/context-compiler.md` (features.context-compiler) — 1 applies_when signal(s) matched; 1 title/summary term(s) matched
- `features/standards-delta.md` (features.standards-delta) — 1 applies_when signal(s) matched
- `features/skill-registry.md` (features.skill-registry) — 1 applies_when signal(s) matched; 1 title/summary term(s) matched
- `packets/security.oidc-secrets.md` (packets.security.oidc-secrets) — Loaded because global.security matched and requested this packet.
- `packets/ui.command-center.md` (packets.ui.command-center) — Loaded because features.standards-delta matched and requested this packet.
- `packets/workflow.approval-gates.md` (packets.workflow.approval-gates) — 2 applies_when signal(s) matched; 1 tag(s) matched; 4 title/summary term(s) matched
- `packets/workflow.durable-agent-workflows.md` (packets.workflow.durable-agent-workflows) — Loaded because domains.agent-harnesses matched and requested this packet.
- `packets/testing.no-mock-echo.md` (packets.testing.no-mock-echo) — 1 applies_when signal(s) matched; 1 title/summary term(s) matched
- `packets/maintainability.architecture-boundaries.md` (packets.maintainability.architecture-boundaries) — 1 applies_when signal(s) matched; 1 title/summary term(s) matched
- `handoffs/latest.md` (handoffs.latest) — Bootloader context is always loaded.
- `services/.context/workflow-orchestration.md` (module.services.workflow-orchestration) — 1 applies_when signal(s) matched; 1 tag(s) matched; 3 title/summary term(s) matched; colocated path matched task text
- `services/.context/README.md` (module.services.index) — 1 applies_when signal(s) matched; 1 title/summary term(s) matched; colocated path matched task text
- `aios/context/.context/frontmatter.md` (module.context-compiler.frontmatter) — 1 title/summary term(s) matched; colocated path matched task text
- `services/.context/success-criteria.md` (module.services.success-criteria) — 1 applies_when signal(s) matched; colocated path matched task text
- `aios/context/.context/selection-and-receipts.md` (module.context-compiler.selection) — colocated path matched task text

## Relevant Rules

- global.security: Baseline security expectations for all AIOS-managed work.
- global.observability: AIOS behavior should leave inspectable traces, receipts, and failure evidence.
- global.testing: Behavior must be validated with deterministic tests or equivalent execution evidence.
- global.maintainability: Keep AIOS changes simple, bounded, readable, and aligned to existing architecture.
- global.design: AIOS UI should expose system state clearly without decorative or low-density surfaces.
- config.agent-rules: Behavioral rules loaded for all AIOS agent sessions and workflow execution.
- context.index: Thin entrypoint for AIOS context routing and compiled briefing generation.
- context.schema: Required schema for AIOS Context Compiler Markdown files.
- context.router: Agent bootloader for AIOS-managed projects and context receipts.
- domains.web-apps: Routing standard for Next.js, React, dashboard, and deployment work.
- domains.agent-harnesses: Routing standard for agent workflows, prompts, packets, skills, and orchestration.
- domains.product-design: Routing standard for product UX, operational workflows, and explainable surfaces.
- projects.aios-ui: Project context routing for the local AIOS Next.js command center.
- aios.repo-context: Colocated context for AIOS Repo Context.
- aios.ui-context: Colocated context for AIOS UI Context.
- aios.architecture: Colocated context for AIOS Architecture Context.
- projects.terrace: Candidate context for Terrace workflow and planning integrations.
- features.prompt-library: Feature context for reusable prompt templates, validation, sync, and evaluation workflows.
- features.context-compiler: Feature context for tiered Markdown routing, scoring, receipts, and writeback candidates.
- features.standards-delta: Feature context for project health scores, standards deltas, and critical-delta drilldowns.
- features.skill-registry: Feature context for installed skill discovery, sync, and agent workflow routing.
- packets.security.oidc-secrets: Deep-enough packet for routing deployment secret work toward short-lived OIDC credentials.
- packets.ui.command-center: UI packet for exposing AIOS operational state, drilldowns, receipts, and warnings.
- packets.workflow.approval-gates: Packet for approval-gated writebacks, major context changes, and reviewable proposals.
- packets.workflow.durable-agent-workflows: Packet for long-running durable agent workspaces, goal verifiers, steering, queueing, artifacts, automation, memory, and skill candidacy.
- packets.testing.no-mock-echo: Testing packet for avoiding shallow tests that only mirror mocked behavior.
- packets.maintainability.architecture-boundaries: Packet for preserving AIOS module and ownership boundaries during implementation.
- handoffs.latest: Current handoff node for the file-backed AIOS Context Compiler.
- module.services.workflow-orchestration: Service-layer notes for workflow orchestration and agent run governance.
- module.services.index: Module context index for AIOS Python services.
- module.context-compiler.frontmatter: Frontmatter rules for AIOS context files and colocated context.
- module.services.success-criteria: Service-layer notes for success criteria and evaluation records.
- module.context-compiler.selection: Selection and receipt rules for context compiler changes.

## Project State

- AIOS UI Project Context: Project context routing for the local AIOS Next.js command center.
- AIOS Repo Context: Colocated context for AIOS Repo Context.
- AIOS UI Context: Colocated context for AIOS UI Context.
- AIOS Architecture Context: Colocated context for AIOS Architecture Context.
- Terrace Project Context: Candidate context for Terrace workflow and planning integrations.
- Latest Context Compiler Handoff: Current handoff node for the file-backed AIOS Context Compiler.

## Feature Context

- Prompt Library Feature: Feature context for reusable prompt templates, validation, sync, and evaluation workflows.
- AIOS Context Compiler Feature: Feature context for tiered Markdown routing, scoring, receipts, and writeback candidates.
- Standards Delta Health Feature: Feature context for project health scores, standards deltas, and critical-delta drilldowns.
- Skill Registry Feature: Feature context for installed skill discovery, sync, and agent workflow routing.
- OIDC Secretless Deployment Packet: Deep-enough packet for routing deployment secret work toward short-lived OIDC credentials.
- AIOS Command Center UI Packet: UI packet for exposing AIOS operational state, drilldowns, receipts, and warnings.
- Workflow Approval Gates Packet: Packet for approval-gated writebacks, major context changes, and reviewable proposals.
- Durable Agent Workflows Packet: Packet for long-running durable agent workspaces, goal verifiers, steering, queueing, artifacts, automation, memory, and skill candidacy.
- No Mock Echo Testing Packet: Testing packet for avoiding shallow tests that only mirror mocked behavior.
- Architecture Boundaries Packet: Packet for preserving AIOS module and ownership boundaries during implementation.

## Known Risks

- No context-selection risks detected by the compiler.

## Acceptance Criteria

- global.security: No new static secret path is introduced.
- global.security: Sensitive context is scoped to the task and receipt.
- global.security: Security tradeoffs are explicit writeback candidates when unresolved.
- global.observability: Generated receipts include loaded and skipped context.
- global.observability: Missing and stale context are visible as warnings.
- global.observability: Scoring decisions are preserved in structured output.
- global.observability: Error output includes remediation guidance that an agent can execute or propose as a follow-up.
- global.testing: Schema validation is exercised against real Markdown files.
- global.testing: Routing tests assert selected files and receipt content.
- global.testing: Conflict precedence is covered by executable tests.
- global.testing: New tests protect behavior, public contracts, domain logic, or confirmed regressions; brittle static render/copy assertions are omitted unless their value is documented.
- global.maintainability: New code has a narrow surface and deterministic behavior.
- global.maintainability: Expanded concepts update the original contract and stale generic names instead of leaving parallel, semantically overlapping APIs.
- global.maintainability: Existing call sites, tests, fixtures, docs, and persisted shapes are checked for implicit-default assumptions when a second variant is added.
- global.maintainability: Message/worker response code reflects the actual event-loop or runtime ordering guarantees instead of guarding against impossible races.
- global.maintainability: If a handler is registered before a send, the code or plan identifies a real reentrancy, synchronous callback, replay buffer, or platform-specific reason.
- global.maintainability: Recurring error surfaces are resolved with durable remediation or captured as explicit follow-up work.
- global.maintainability: Agent-facing files fit a bounded context budget, or document why the larger surface remains coherent.
- global.maintainability: Agent-facing artifacts preserve machine-readable structure before prose or visual presentation.
- global.maintainability: Handoff or optional project-context files reflect meaningful architecture changes when those files are in scope.
- global.maintainability: Context routing remains auditable from receipt output.
- global.design: Users can inspect why a score, warning, or packet was produced.
- global.design: Critical states are not collapsed into vague healthy/unhealthy labels.
- global.design: Controls match expected operational workflows.
- global.design: UI work that uses Refero or another external design source cites the source and
- context.index: Agents produce a context receipt before treating context selection as complete.
- context.index: Loaded context is explainable by task classification, score, or explicit linked packet.
- context.index: Skipped context remains visible in the receipt.
- context.schema: `pnpm context:validate` passes before a context file is treated as authoritative.
- context.schema: `load_if_matched` links point to existing files relative to `aios/context/`.
- context.schema: Thin routing files stay below the deep-packet threshold unless they declare a larger `token_budget`.
- context.router: Every non-trivial run has a loaded/skipped context receipt.
- context.router: Missing, stale, and conflicting context are explicit.
- context.router: Writebacks are proposed for missing rules or reusable patterns.
- domains.web-apps: User-facing state is source-backed and inspectable.
- domains.web-apps: UI changes follow the existing component and routing patterns.
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
- domains.product-design: Important system state can be inspected without reading logs.
- domains.product-design: Warnings and blockers are visually distinct and textually precise.
- projects.aios-ui: Project health and delta UI stays source-backed.
- projects.aios-ui: New UI surfaces can explain missing, inferred, or conflicting signals.
- projects.aios-ui: Meaningful architecture changes update `PROJECT.md`.
- projects.terrace: Use only when the task names Terrace or workflow planning integration.
- projects.terrace: Record missing Terrace truth as a writeback candidate when needed.
- features.prompt-library: New prompt workflows preserve frontmatter validation and registry generation.
- features.prompt-library: Evaluation output can be traced to prompt template IDs.
- features.context-compiler: Compilation produces structured JSON and agent-readable Markdown.
- features.context-compiler: Receipts include loaded, skipped, conflicts, missing context, and writebacks.
- features.context-compiler: Scoring favors specific, recent, authoritative, low-cost context.
- features.standards-delta: Health score explanations point to source-backed delta records.
- features.standards-delta: Unknown and missing states remain visible.
- features.standards-delta: Critical deltas can be inspected by domain, severity, and remediation path.
- features.skill-registry: Skill routing remains inspectable and deterministic where possible.
- features.skill-registry: Missing skill metadata becomes a writeback candidate.
- packets.security.oidc-secrets: No static deployment secret is introduced as the default path.
- packets.security.oidc-secrets: Provider, subject, audience, and permission scope are explicit.
- packets.security.oidc-secrets: Exceptions include owner, reason, review date, and removal path.
- packets.ui.command-center: Operators can drill into source-backed evidence.
- packets.ui.command-center: Missing and conflicting state appears as actionable warnings.
- packets.ui.command-center: Receipts can later be attached to run history.
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
- packets.testing.no-mock-echo: Tests fail before implementation when behavior is absent.
- packets.testing.no-mock-echo: Tests inspect actual output and side effects.
- packets.maintainability.architecture-boundaries: New modules have a clear owner and caller.
- packets.maintainability.architecture-boundaries: Cross-layer changes are deliberate and documented.
- handoffs.latest: Update this handoff when compiler output shape or routing conventions change.
- handoffs.latest: Keep detailed implementation history in docs or optional project context, not this routing node.

## Missing Context

- None.

## Writeback Candidates

- None.
