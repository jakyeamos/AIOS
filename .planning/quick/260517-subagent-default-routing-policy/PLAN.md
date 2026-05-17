# Quick Task Plan: Subagent Default Routing Policy

Date: 2026-05-17
Status: complete

## Objective

Make sub-agent-driven development a durable AIOS default for non-trivial work while preserving direct execution for tiny tasks.

## Context Loaded

- `pnpm context:compile --task "Add durable subagent default routing policy, workflow docs, telemetry and eval plan"`
- `config/agent-rules.md`
- `config/execution-strategies/*.json`
- `services/execution_strategy.py`
- `tests/test_execution_strategy.py`
- `aios/context/domains/agent-harnesses.md`
- `docs/evals/aios-harness-eval-v0.md`

## Steps

1. [x] Audit existing agent rules, execution strategies, harness eval, telemetry, and docs surfaces.
2. [x] Add a configurable model/subagent routing policy under the existing execution-strategy config.
3. [x] Extend validation/tests so the policy is machine-checkable.
4. [x] Update durable agent/context/docs guidance.
5. [x] Run targeted validation.
6. [ ] Commit implementation, then update project truth in a follow-up commit.
