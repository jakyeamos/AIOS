# Success Criteria Index

Last updated: 2026-04-23

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
| `security-review` | Security Review Before Sensitive Change Acceptance | domain-specific | yes | security-sensitive implementation, bugfix, review | `spec/success-criteria/security-review.md` |
| `observability` | Observability Completeness for Operational Changes | domain-specific | no | observability/workflow/reliability-impacting changes | `spec/success-criteria/observability.md` |
| `truth-file-consistency` | Project Truth File Consistency | project-domain-specific | yes | AIOS implementation, bugfix, refactor | `spec/success-criteria/truth-file-consistency.md` |
| `repo-boundary-discipline` | Repository Boundary Discipline | global | yes | implementation, bugfix, refactor | `spec/success-criteria/repo-boundary-discipline.md` |
| `workflow-state-integrity` | Workflow State Integrity | domain-specific | no | orchestration/workflow-affecting work | `spec/success-criteria/workflow-state-integrity.md` |

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
