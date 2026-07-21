Act as a fresh, independent adversarial reviewer of a three-task live paired
benchmark. Do not modify any repository or benchmark files. Read only the
listed reports and checked-in repository evidence.

Benchmark evidence:
- Existing pair reports: /tmp/aios-m6-control-final.md and
  /tmp/aios-m6-treatment-final.md
- Task 2 reports: /tmp/aios-m6-t2-control-final.md and
  /tmp/aios-m6-t2-treatment-final.md
- Task 3 reports: /tmp/aios-m6-t3-control-final.md and
  /tmp/aios-m6-t3-treatment-final.md
- Durable DB: /tmp/aios-m6-live.db (inspect eval_tasks, eval_runs,
  eval_scores, and eval_pairs)
- Repository at protected SHA: /tmp/aios-m6-review

Use this fixed rubric for every output, scoring each dimension 0.0 to 1.0:
acceptance coverage, evidence accuracy, risk/verification quality,
decision discipline, and portability/limitations. Overall is the arithmetic
mean. Apply the same rubric to control and treatment. Check that each pair
shares a protected SHA and task/prompt/model/effort/tools/budget parity, that
all four disposable benchmark worktrees are clean, and that durable IDs are
present. Treat provider token/cost telemetry as unavailable rather than
estimated. Do not treat the prior pair's self-review as independent.

Return a self-contained Markdown review with:
1. per-task control/treatment scores and concise rationale;
2. aggregate control mean, treatment mean, and delta;
3. contamination, parity, safety, and reproducibility findings;
4. P0/P1/P2/P3 findings with exact output or file references;
5. an explicit promote/revise/defer decision for M6 and the minimum next gate.

The benchmark claim must stay bounded to this three-task audit corpus. Do not
claim general productivity, satellite readiness, or production safety from it.
