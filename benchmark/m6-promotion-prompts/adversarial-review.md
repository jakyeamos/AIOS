# M6 promotion-grade adversarial review

Act as an independent principal engineer reviewing a fresh matched control/treatment
implementation benchmark. Do not modify any worktree or the protected ledger.

Protected start SHA: `4d8adbca3b89d6259e252f26aaad0db69a9bf102`.

Review these six disposable worktrees and their final reports:

- `/private/tmp/aios-m6-promotion/task-a-control`
- `/private/tmp/aios-m6-promotion/task-a-treatment`
- `/private/tmp/aios-m6-promotion/task-b-control`
- `/private/tmp/aios-m6-promotion/task-b-treatment`
- `/private/tmp/aios-m6-promotion/task-c-control`
- `/private/tmp/aios-m6-promotion/task-c-treatment`

The paired tasks are:

1. Workflow skill-candidate promote/dismiss owner migration.
2. `eval.approveShadowCandidate` owner migration.
3. Verify -> Review -> Closeout browser-contract coverage.

Control prompts are repository-only. Treatment prompts additionally name the
portable M6 modernization packet. The model, effort, tools, budget, protected
SHA, and acceptance criteria are otherwise matched.

For every worktree:

1. Verify the actual start SHA and contamination boundary.
2. Inspect the complete diff against the start SHA, not only the agent report.
3. Run or inspect the focused verification results and distinguish source
   failures from environment failures.
4. Check whether the treatment-only packet is the only context difference.
5. Check for direct TypeScript writes, authorization regressions, stale
   consumers, weakened tests, accidental commits, generated-file pollution,
   and browser/build claims unsupported by artifacts.

Classify findings P0/P1/P2/P3. P0/P1 include promotion-critical ledger gaps,
security or authorization regressions, data-loss risk, false test claims, or
material cross-pair contamination. P2 includes environment-blocked proof and
missing non-critical cleanup. Do not mark a pair promotion-ready merely because
implementation tests pass.

Produce a concise independent review with:

- per-pair decision: `promote`, `defer`, or `revise`
- evidence-backed scores from 0.0 to 1.0 for task success, quality adherence,
  workflow speed, cost efficiency, context effectiveness, context portability,
  autonomy, and user trust
- exact P0/P1/P2/P3 findings with worktree/file references
- contamination verdict and its evidence
- whether browser/build proof is actually complete
- a final M6 decision

The correct outcome may be deferred promotion. Do not invent provider cost or
runtime data; mark unavailable fields as null.
