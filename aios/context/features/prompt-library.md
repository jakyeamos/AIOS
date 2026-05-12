---
id: features.prompt-library
title: Prompt Library Feature
tier: feature
scope:
  - aios
priority: high
status: active
summary: Feature context for reusable prompt templates, validation, sync, and evaluation workflows.
applies_when:
  - task_touches_prompt_library
  - task_touches_agent_harness
tags:
  - prompt-library
  - prompts
  - evaluation
  - templates
related:
  - ../../docs/architecture/2026-04-23-aios-prompt-library-phase1.md
last_reviewed: 2026-05-12
---

The prompt library has seed templates, validation, registry generation, and vault/DB sync.
Reusable prompt evaluation should extend that deterministic flow instead of bypassing it with ad hoc prompts.
Evaluation cases live under `prompts/evals/`.

## Acceptance Criteria

- New prompt workflows preserve frontmatter validation and registry generation.
- Evaluation output can be traced to prompt template IDs.
