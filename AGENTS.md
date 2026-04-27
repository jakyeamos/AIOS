# AIOS Agent Workflow Contract

This repository uses AIOS-managed success criteria as a first-class completion gate.

## Required Execution Flow

1. Resolve applicable criteria before implementation.
2. Keep criteria visible during execution (blockers vs warnings).
3. Evaluate final changed files against applicable criteria before completion.
4. Record blockers, warnings, passes, and accepted tradeoffs in durable artifacts.

## Rule: Execution-First Verification

Trigger this rule for:

- non-trivial side effects or state
- cross-system interactions
- core/shared logic modification
- debugging inconsistent behavior
- low trust in tests
- complex domain models

When triggered:

1. Run the exact code path being modified.
2. Call all relevant functions directly.
3. Reproduce real inputs, using mocks only when necessary.
4. Observe outputs, side effects, and state changes.
5. Only then propose or implement changes.

Do not rely solely on static reasoning in these cases.

## Runtime Sources of Truth

- Criteria registry: `config/success-criteria/registry.json`
- Skill mapping: `config/success-criteria/skill-map.json`
- Criteria docs index: `spec/success-criteria/index.md`
- Evaluator: `services/success_criteria.py`

## Hook Integration

- Session start (`bin/hook-session-start.py`) surfaces applicable criteria in startup packet.
- Session close (`bin/hook-stop.py`) evaluates criteria and persists findings.

## Storage Contract

- SQLite tables:
  - `success_criteria_evaluations`
  - `success_criteria_findings`
- JSON artifacts:
  - `data/success-criteria/evaluations/<evaluation-id>.json`

## Completion Requirement

Do not mark implementation complete when blocker-level criteria fail unless accepted tradeoffs are explicitly recorded in evaluation metadata.
