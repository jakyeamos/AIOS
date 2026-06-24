# Quick Task Summary: Durable Agent Workflows

## Objective

Add a durable-agent-workflow layer to AIOS without weakening existing AIOS standards, quality gates, TMCP behavior, pre-CR checks, anti-slop checks, or repository rules.

## Changed Surfaces

- `aios/context/packets/workflow.durable-agent-workflows.md`
- `docs/workflows/durable-agent-workflows.md`
- `aios/context/domains/agent-harnesses.md`
- `config/workflows/registry.json`
- `config/workflows/skills.json`
- `README.md`
- `OPERATING_LANGUAGE.md`
- `PROJECT.md`
- `.planning/SUBSYSTEM_EXTRACTION_PLAN.md`
- `tests/context-compiler.test.mjs`
- `tests/test_planned_workflows.py`

## Durable Workflow Contract Added

- Durable workspaces preserve decisions, blockers, owners, dates, useful links, verification status, known pitfalls, and next actions.
- Goals require verifiers and stopping conditions.
- `/steer` is an immediate direction correction that preserves the active goal unless explicitly changed.
- `/queue` records post-checkpoint work and must not interrupt in-flight verification.
- Workflows declare allowed and out-of-scope repo, artifact, surface, communication, monitoring, and memory surfaces.
- Substantial work should use a reviewable artifact instead of treating chat as the source of truth.
- Automation distinguishes fresh scheduled work from context-preserving workspace wakeups.
- TMCP skill candidacy requires repeated evidence, reusable decision trees, reusable verifiers, clear scope, and objective evaluation.

## Verification Planned

- Context compiler packet selection test.
- Workflow registry durable route and skill contract tests.
- Context validation.
- Targeted workflow registry tests.
