# Success Criteria Index

Last updated: 2026-06-23

This index is the canonical discovery point for all AIOS-managed success criteria.

## How Criteria Work

- Skills define execution tactics.
- Success criteria define quality judgment.
- Hooks and runtime evaluators decide when checks run.
- Evaluation artifacts are persisted in:
  - `success_criteria_evaluations`
  - `success_criteria_findings`
  - `data/success-criteria/evaluations/*.json`

## Criteria Catalog

| ID | Title | Scope | Blocking | Applies When | File |
|---|---|---|---|---|---|
| `code-simplicity` | Protect Simplicity and Comprehension | global | yes | implementation, bugfix, refactor, review | `spec/success-criteria/code-simplicity.md` |
| `testing-trust` | Do Not Treat Test Volume as Trust | task-type | no | implementation, bugfix, refactor, testing, review | `spec/success-criteria/testing-trust.md` |
| `execution-first-verification` | Execution-First Verification | global | yes | implementation, bugfix, refactor, testing, review with runtime-risk triggers | `spec/success-criteria/execution-first-verification.md` |
| `security-review` | Security Review Before Sensitive Change Acceptance | domain-specific | yes | security-sensitive implementation, bugfix, review | `spec/success-criteria/security-review.md` |
| `observability` | Observability Completeness for Operational Changes | domain-specific | no | observability/workflow/reliability-impacting changes | `spec/success-criteria/observability.md` |
| `truth-file-consistency` | Project Truth File Consistency | project-domain-specific | yes | AIOS implementation, bugfix, refactor | `spec/success-criteria/truth-file-consistency.md` |
| `repo-boundary-discipline` | Repository Boundary Discipline | global | yes | implementation, bugfix, refactor | `spec/success-criteria/repo-boundary-discipline.md` |
| `workflow-state-integrity` | Workflow State Integrity | domain-specific | no | orchestration/workflow-affecting work | `spec/success-criteria/workflow-state-integrity.md` |
| `git-worktree-cleanliness` | Git Worktree Cleanliness at Completion | global | yes | session close and completion closeout | `spec/success-criteria/git-worktree-cleanliness.md` |
| `complexity-budget` | Complexity and Big-O Regression Budget | domain-specific | yes | algorithm, query, hot-path, pagination, polling, recursion, performance-risk changes | `spec/success-criteria/complexity-budget.md` |
| `supply-chain-review` | Dependency and Supply Chain Review | domain-specific | yes | dependency, lockfile, package-manager, build/deploy package changes | `spec/success-criteria/supply-chain-review.md` |
| `architecture-boundary` | Architecture Boundary and Modularity Gate | global | yes | implementation, bugfix, refactor, review | `spec/success-criteria/architecture-boundary.md` |
| `thin-display` | Thin Display UI Purity | domain-specific | no | UI/component/display-layer changes | `spec/success-criteria/thin-display.md` |
| `test-quality` | Behavior-Proving Test Quality | task-type | yes | behavior-changing implementation, bugfix, refactor, testing, review | `spec/success-criteria/test-quality.md` |
| `data-integrity` | Data Integrity and Migration Safety | domain-specific | yes | schema, migration, durable data, IDs, timestamps, backfill changes | `spec/success-criteria/data-integrity.md` |
| `api-contract` | API and Caller Contract Compatibility | domain-specific | yes | API, tRPC, server action, CLI JSON, typed contract changes | `spec/success-criteria/api-contract.md` |
| `performance-budget` | Practical Performance Budget | domain-specific | no | UI route, render, bundle, network, hot-path performance changes | `spec/success-criteria/performance-budget.md` |
| `accessibility` | Accessibility Gate | domain-specific | no | user-facing UI, form, navigation, dialog, control changes | `spec/success-criteria/accessibility.md` |
| `resilience` | Failure Mode and Resilience Gate | domain-specific | no | IO, external service, retry, DB write, job, offline/slow-path changes | `spec/success-criteria/resilience.md` |
| `product-alignment` | Product Alignment and Scope Discipline | task-type | no | planning, implementation, review, UI/product work | `spec/success-criteria/product-alignment.md` |
| `simplicity` | Simplicity and De-Slop Gate | global | no | all agent-managed work | `spec/success-criteria/simplicity.md` |
| `agent-claim-verification` | Agent Claim Verification | global | yes | all agent-managed work | `spec/success-criteria/agent-claim-verification.md` |

## Diff-Scoped Gate Routing

AIOS should prefer scoped gate selection over a universal checklist:

- UI diffs route to `thin-display`, `accessibility`, `performance-budget`, and `product-alignment`.
- Database, schema, migration, and durable data diffs route to `data-integrity`, `api-contract` when caller shapes change, and `resilience`.
- Auth, permission, secret, token, validation, and sensitive data diffs route to `security-review` in hard-blocking mode.
- Algorithm, query, pagination, polling, recursion, and hot-path diffs route to `complexity-budget` and may require benchmarks.
- Dependency, lockfile, package-manager, build, and deployment package diffs route to `supply-chain-review`.
- Large or agent-generated PRs route to `simplicity`, `architecture-boundary`, and `agent-claim-verification`.

## Quality Modes

Pre-PR gate mode is diff-scoped and prevents new quality debt. It should block severe regressions in touched paths without requiring unrelated legacy cleanup.

Adoption/backfill mode audits an existing repository, inventories quality debt, ranks remediation by severity and return on investment, and creates backfill tasks instead of blocking every future PR on old debt. Backfill artifacts should distinguish critical backfill, high-ROI backfill, medium-ROI backfill, deferred work, and the current quality ratchet baseline.

## Runtime Resolution Rules

1. Global criteria always apply.
2. Task/domain/project/skill criteria apply when trigger metadata matches registry rules.
3. Skill-specific additions are merged from `config/success-criteria/skill-map.json`.
4. Applicable criteria are surfaced at session start and evaluated at session close.

## Blocking vs Advisory Semantics

- `blocker`: work must not be marked complete without explicit override/tradeoff record.
- `warning`: advisory concern that can proceed with documented tradeoffs.
- `pass`: no active concern detected by current evaluator.

## Related Runtime Files

- `config/success-criteria/registry.json`
- `config/success-criteria/skill-map.json`
- `services/success_criteria.py`
- `bin/hook-session-start.py`
- `bin/hook-stop.py`
