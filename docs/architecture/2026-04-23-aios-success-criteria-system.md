# AIOS Success Criteria System (Phase 0c)

Date: 2026-04-23  
Status: Implemented baseline

## 1) Audit Findings

- `spec/success-criteria/` existed but only `testing-trust.md` was present and not wired into runtime evaluation.
- There was no canonical index for criteria discovery, scope, and severity semantics.
- Agent startup/stop hooks did not resolve or evaluate success criteria.
- There was no durable schema for per-run criteria findings and no artifact trail for downstream analytics.
- Skill-to-criteria postcondition mapping was not explicit.

## 2) Implemented Control-Plane Components

### Criteria catalog + mapping
- `config/success-criteria/registry.json`
- `config/success-criteria/skill-map.json`

### Canonical criteria docs
- `spec/success-criteria/index.md`
- `spec/success-criteria/_template.md`
- normalized starter criteria set:
  - `code-simplicity`
  - `testing-trust`
  - `security-review`
  - `observability`
  - `truth-file-consistency`
  - `repo-boundary-discipline`
  - `workflow-state-integrity`

### Runtime evaluator
- `services/success_criteria.py`
  - context inference (task/domain/skill/project)
  - criteria applicability resolution
  - criterion evaluators with blocker/warning/pass output
  - DB persistence + JSON artifact persistence

## 3) Hook + CLI Integration

- `bin/hook-session-start.py`
  - resolves and surfaces applicable criteria in startup packet before implementation.
- `bin/hook-stop.py`
  - evaluates applicable criteria at session close against changed patch paths.
  - records findings, counts, and tradeoffs.
- `services/aios_cli.py`
  - `aios metadata --json` now includes:
    - criteria catalog summary
    - latest success criteria evaluation

## 4) Durable Storage Contract

Added runtime tables:
- `success_criteria_evaluations`
- `success_criteria_findings`

Added schema snapshots:
- `schema.sql`
- `data/schema.sql`

Durable artifact path:
- `data/success-criteria/evaluations/<evaluation-id>.json`

Each evaluation stores:
- objective/task linkage (`project_id`, `run_id`, `session_id`, `packet_id`, `task_id`)
- `criteria_ids_json`
- `files_changed_json`
- pass/warning/blocker counts
- accepted tradeoffs
- artifact path
- finding-level evidence + metadata

## 5) Validation

- New tests: `tests/test_success_criteria.py`
- Updated tests:
  - `tests/test_orchestration_runtime.py`
  - `tests/test_aios_cli.py`

Validated with:
- `uv run pytest tests/test_success_criteria.py tests/test_aios_cli.py tests/test_orchestration_runtime.py`
- `uv run ruff check services/success_criteria.py bin/hook-stop.py services/aios_cli.py tests/test_success_criteria.py tests/test_aios_cli.py tests/test_orchestration_runtime.py`

## 6) Remaining Ratchet Steps

1. Add explicit human override approval fields for blocker acceptance at evaluation time.
2. Expand evaluator depth from heuristic path signals to richer diff/test/trace evidence.
3. Add criterion-level trend analytics and noise scoring to guide Phase 3b health scoring.
