---
phase: 11-testing-benchmark-evaluation-and-shadow-workflows
plan: "02"
completed_at: "2026-06-13T00:00:00.000Z"
requirements:
  - EVAL-02
key-files:
  created:
    - services/second_brain_eval.py
    - tests/test_second_brain_eval.py
    - tests/test_second_brain_eval_cli.py
    - config/agent-eval/ablation-policies/no-second-brain.json
    - config/agent-eval/ablation-policies/no-personal-corpus.json
    - config/agent-eval/ablation-policies/no-project-truth.json
    - config/agent-eval/ablation-policies/no-prior-task-history.json
  modified:
    - schema.sql
    - services/eval_run_service.py
    - services/aios_cli.py
metrics:
  focused_tests_passed: 7
  production_commit: aeedadb6
---

# Phase 11 Plan 02 Summary

## Result

Created the second-brain evaluation track for Phase 11. AIOS can now record retrievals, compute precision/recall/staleness metrics, register deterministic gold-set context requirements, evaluate a run against that gold set, and compute Second Brain Lift between full-second-brain and repo-only runs.

## Changed Files

- `schema.sql`
  - Added `eval_second_brain_retrievals` and `eval_gold_set_context`.

- `services/eval_run_service.py`
  - Extended eval schema initialization so later services can operate from an empty SQLite connection.

- `services/second_brain_eval.py`
  - Added retrieval logging, retrieval metrics, gold-set registration, gold-set run evaluation, and Second Brain Lift computation.
  - Missing variant runs return `available: false` with a concrete `missing_condition` instead of crashing.

- `config/agent-eval/ablation-policies/`
  - Added `no-second-brain`, `no-personal-corpus`, `no-project-truth`, and `no-prior-task-history` policy files with condition, description, disable source list, and portability impact.

- `services/aios_cli.py`
  - Added `aios eval second-brain-lift`, `aios eval retrieval-metrics`, and `aios eval gold-set-run`.

- `tests/test_second_brain_eval.py`
  - Covers retrieval round-trip, precision/recall/staleness math, missed required sources, positive lift, unavailable missing variant, and policy JSON validity.

- `tests/test_second_brain_eval_cli.py`
  - Covers all three new CLI commands through the real `run_cli` JSON path.

## Verification

- `uv run pytest -q tests/test_second_brain_eval.py tests/test_second_brain_eval_cli.py` passed: 7 tests.
- `uv run ruff check services/second_brain_eval.py services/eval_run_service.py services/aios_cli.py tests/test_second_brain_eval.py tests/test_second_brain_eval_cli.py` passed.

## Broader Check Notes

`uv run pytest -q tests/test_second_brain_eval.py tests/test_aios_cli.py -q` was also run before isolating the new CLI coverage. The new second-brain checks passed, but `tests/test_aios_cli.py` still has unrelated failures in pre-existing contract-status and skills-harvest expectations. Those failures were already outside the Plan 11-02 changed surface and were left unstaged.

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

All Plan 11-02 must-haves are present: schema tables, service exports, ablation policies, CLI subcommands, focused service tests, and CLI execution tests.
