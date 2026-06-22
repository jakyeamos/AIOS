# Quick Task Plan

Task: Implement the TMCP benchmark paired-run pipeline from the approved plan.

Scope:
- Extend the benchmark service and CLI beyond scaffold creation.
- Add task import, condition randomization, freeze hashing, preflight, stub isolated runs, and aggregation.
- Generate dry-run artifacts only; do not claim real TMCP performance from dry-run data.

Verification:
- Focused benchmark and eval service tests.
- Ruff on the benchmark service, CLI, and tests.
- Context validation.
- Dry-run artifact presence under `tmcp-benchmark/runs`, `evaluation/automated`, and `analysis/tables`.
