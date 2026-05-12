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

## Acceptance Criteria

- Routing decisions include reasons and skipped alternatives.
- Prompt or skill changes include validation paths.
- Writebacks are proposed for review rather than silently promoted.
