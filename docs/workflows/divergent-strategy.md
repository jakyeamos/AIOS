# Divergent Strategy Workflow

The Divergent Strategy Workflow is an AIOS-native workflow for tasks with multiple plausible answers. It creates structured candidates, evaluates them with reusable judges, selects a portfolio, preserves useful failures, proposes memory writebacks, and tracks convergence risk.

## When To Use

Use it for architecture decisions, repo/workflow audits, prompt and skill design, standards design, product strategy, or high-leverage creative work.

Do not use it for small deterministic fixes, clear acceptance criteria, or speed-first requests.

## Modes

- Lightweight: 3 candidates, 2 judges, approval-gated writeback proposals.
- Standard: 5 to 8 candidates, 3 to 5 judges, portfolio output.
- Gallery: broad exploration, stronger novelty preservation, explicit promotion approval.
- Audit: candidate interpretations plus risk, adoption, implementation, and AIOS-delta judges.

## Workflow Shape

1. Classify task.
2. Select mode.
3. Generate role-based candidates.
4. Run reusable judges.
5. Select a portfolio.
6. Create memory writeback proposals.
7. Track entropy.
8. Expose evidence in UI and logs.

## Portfolio Slots

- Best Overall
- Most Immediately Useful
- Highest Upside
- Safest Implementation
- Best Long-Term Architecture
- Most Interesting Failure
- Should Not Implement
- Rebranch Later

## Status Explanations

- `completed`: candidates, judgments, entropy, and portfolio metadata exist.
- `proposed`: no memory mutation has been applied.
- `approved`: proposal was accepted, but promotion still requires evidence.
- heuristic score: inspect the formula and judge rationale before treating it as a decision.

## Current Implementation

The first implementation is deterministic and local. It stores durable workflow records in SQLite and exposes them through:

- `/runs/divergent`
- `/runs/divergent/:id`
- `/writebacks`
- `/skills/candidates`

Future work can replace deterministic candidate text with actual agent-generated candidate outputs without changing the storage contract.
