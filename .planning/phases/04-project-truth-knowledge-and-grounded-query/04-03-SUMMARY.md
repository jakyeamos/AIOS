# 04-03 Summary: Truth-First Grounded Query

## Result

Grounded query now uses the truth boundary as a first-class retrieval source for operator questions.

## Shipped

- Added truth/operator question detection for truth, unresolved work, prior knowledge, default-layer status, and remaining-work questions.
- Added a truth-first answer path that separates accepted truth, recent proposal evidence, recent runtime changes, and inferred prior knowledge.
- Added truth-boundary citations and retrieval traces to what-changed, project-state, agent-brief, and system-state answers.
- Added explicit unresolved-review language when proposal evidence exists but has not been promoted into accepted truth.

## Verification

- `pnpm lint` from `aios-ui/`

The lint command passed with the existing warning-only anti-slop baseline.

## Follow-Up

- Add UI rendering for authority lanes in grounded query results.
- Add deterministic query fixtures once the UI/server test harness can import TypeScript modules directly.
