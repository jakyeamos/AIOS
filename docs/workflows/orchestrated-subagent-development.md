# Orchestrated Sub-Agent Development

Date: 2026-05-17
Status: Approved operating standard

## Rule

Prefer sub-agent-driven development for most non-trivial tasks. The orchestrator owns task decomposition, routing, context control, supervision, quality gates, and final synthesis. Execution should go to specialized subagents with the lowest-cost model tier and reasoning level likely to complete the task reliably.

This is a default, not a dogma. The orchestrator may execute directly when the task is simple, likely under 5-10 minutes, requires no repo-wide context, affects one small file or doc, is a pure explanation or isolated command, or subagent setup would cost more than it saves.

Prefer subagents when work requires repo inspection, multiple phases, architecture, tests, security, migrations, data models, multi-file changes, parallel research, isolated review, or protection from context bloat and premium-model token waste.

## Roles

- Orchestrator: classifies the task, chooses direct or subagent execution, builds briefing packets, assigns model tier and reasoning, supervises outputs, enforces quality gates, and writes final synthesis.
- Explorer or mapper: read-only context gathering, file discovery, execution-path mapping, test/schema/dependency lookup, and concise packet production.
- Implementer: focused changes, no broad refactors unless requested, assigned verification, and explicit reporting of files changed, commands run, and assumptions.
- Reviewer: usually read-only; checks correctness, maintainability, security, test coverage, AIOS standards, and whether the model choice was overpowered or underpowered.
- Specialist: bounded docs, tests, security, UI, data, dependency, prompt, or performance work.

The machine-readable role defaults live in `config/execution-strategies/model-routing-policy.json`.

## Routing Policy

Routing starts deterministic and configurable:

1. Classify the task category, likely file count, risk, write intensity, security sensitivity, architecture impact, test availability, token budget, and expected cost of mistakes.
2. Check direct-execution exceptions.
3. If non-trivial, choose an agent role, model tier, and reasoning level from the routing policy.
4. Escalate model tier or reasoning only when risk, ambiguity, or prior failure evidence justifies it.
5. Record whether the routing choice was appropriate, overkill, underpowered, or unknown.

Policy statuses are `experimental`, `candidate`, `approved`, and `deprecated`. Approved and deprecated default changes require review and repeated evidence. Experimental rows may be recorded without becoming defaults.

## Telemetry

Each routed run should eventually capture:

- task ID and category
- subagent type
- model and reasoning level used
- input and output tokens
- tool calls
- wall-clock time
- retries
- test and lint/typecheck status
- reviewer defects
- human intervention
- accepted, revised, or rejected outcome
- estimated complexity
- final quality score
- cost estimate
- notes on overkill or underpowered model choice

The learning metric is:

```text
marginal_reasoning_model_value =
  quality_improvement - additional_cost - additional_latency - additional_token_usage
```

AIOS should learn the point where higher model tiers or reasoning levels stop improving outcomes enough to justify cost for each task category.

## Eval Plan

Use representative task classes:

1. Simple docs edit
2. Small bug fix
3. Mechanical refactor
4. Test creation
5. Repo mapping
6. Architecture audit
7. Security-sensitive review
8. Multi-file feature implementation
9. UI polish task
10. Prompt or rule improvement task

Compare these combinations over time rather than running the full matrix every time:

- cheap model plus low reasoning
- cheap model plus medium reasoning
- mid model plus medium reasoning
- strong model plus medium reasoning
- strong model plus high reasoning

Evaluation output should identify the best default, cheapest reliable option, failure-prone combinations, cases where higher reasoning helps, cases where stronger model tier helps, cases with diminishing returns, and cases where orchestration overhead is not worth it.

## Follow-Up Implementation Plan

This pass establishes the durable rule, policy file, validation, and docs. Deeper implementation should:

1. Add a SQLite-backed run table or extend orchestration run metadata for model-routing telemetry.
2. Emit routing-choice events from managed invocation paths.
3. Add harness-eval fixtures for the ten routing benchmark task classes.
4. Build a proposer that aggregates repeated evidence and emits approval-gated policy update candidates.
5. Surface routing efficiency and marginal-value summaries in the operator UI.

