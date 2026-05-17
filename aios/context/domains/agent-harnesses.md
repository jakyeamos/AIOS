---
id: domains.agent-harnesses
title: Agent Harnesses Domain Standard
tier: domain
scope:
  - agent_workflows
priority: high
status: active
summary: Routing standard for agent workflows, prompts, packets, skills, and orchestration.
applies_when:
  - task_touches_agent_harness
  - task_touches_context_compiler
  - task_touches_prompt_library
  - task_touches_skill_registry
tags:
  - agents
  - workflows
  - prompts
  - skills
  - packets
last_reviewed: 2026-05-12
---

Agent harness work should make routing, packet assembly, invocation, and writeback behavior explicit.
Prefer deterministic classification before LLM-based expansion.
Every agent-facing packet should be auditable after execution.
Harness rules should make common failures harder to repeat by turning error patterns into durable checks, standards, or writeback candidates.
Agent-facing files, packets, prompts, and workflows should remain easy to scan under limited context, using responsibility-based splits instead of arbitrary line-count ceilings.
Failures surfaced to agents should be structured enough to parse and specific enough to include next remediation steps.
Human-readable agent guidance may clarify machine-readable data, but must not replace, obscure, or contradict parseable packet fields, stable IDs, explicit states, deterministic labels, or remediation steps.
For most non-trivial work, prefer orchestrated sub-agent development: the orchestrator classifies and supervises while explorer, implementer, reviewer, or specialist agents execute bounded work with the cheapest sufficient model tier and reasoning level.
Direct execution remains appropriate for tiny local tasks where subagent setup costs more than it saves.
Model and reasoning defaults should come from `config/execution-strategies/model-routing-policy.json`, with approved routing changes gated by repeated evidence rather than one-off results.

## Acceptance Criteria

- Routing decisions include reasons and skipped alternatives.
- Prompt or skill changes include validation paths.
- Repeated harness failures are promoted into durable standards, checks, or explicit backlog items.
- Agent-facing files remain small enough for agents to load and reason over without losing local context.
- Error records include parseable remediation steps.
- Packet, prompt, and workflow surfaces preserve stable machine-readable fields when adding human-facing copy.
- Writebacks are proposed for review rather than silently promoted.
- Non-trivial execution records whether direct execution or subagent execution was chosen and why.
- Model or reasoning upgrades track whether extra cost produced meaningful quality improvement.
