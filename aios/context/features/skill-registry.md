---
id: features.skill-registry
title: Skill Registry Feature
tier: feature
scope:
  - aios
priority: normal
status: candidate
summary: Feature context for installed skill discovery, sync, and agent workflow routing.
applies_when:
  - task_touches_skill_registry
  - task_touches_agent_harness
tags:
  - skills
  - registry
  - agents
related:
  - ../../bin/sync-installed-skills.py
last_reviewed: 2026-05-12
---

Skill registry work should connect installed skills to agent routing and workflow evidence.
The existing `bin/sync-installed-skills.py` is a likely integration point.
Keep this as candidate context until the durable registry contract is clarified.

## Acceptance Criteria

- Skill routing remains inspectable and deterministic where possible.
- Missing skill metadata becomes a writeback candidate.
