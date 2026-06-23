# Quick Task Summary: First Real Portable TMCP Paired Benchmark

Date: 2026-06-23

## Task

Run the first real paired benchmark for the portable dev-process TMCP graph on one non-AIOS local repo from the benchmark inventory.

## Context

- Graph: `config/tmcp/portable-dev-process/`
- Service: `services/tmcp_benchmark.py`
- Prior graph summary: `.planning/quick/260622-bf4-create-portable-tmcp-dev-process-skill-g/SUMMARY.md`
- Benchmark root: `tmcp-benchmark/`

## Run

- Repository: `BidCamp`
- Commit: `72148b19e4823e9ecd9751e7ec67754b79287c8d`
- Task source: `tmcp-benchmark/tasks/approved/first-real-paired-bidcamp-quality-debug.json`
- Held-out task: `bidcamp-quality-debug-heldout`
- Seed: `260623`
- Paired conditions:
  - `baseline`: `realpair-bidcamp-baseline-260623`
  - `tmcp_cold_start`: `realpair-bidcamp-tmcp-cold-260623`

## Evidence

- Raw run records:
  - `tmcp-benchmark/runs/raw/realpair-bidcamp-baseline-260623.json`
  - `tmcp-benchmark/runs/raw/realpair-bidcamp-tmcp-cold-260623.json`
- Route receipts:
  - `tmcp-benchmark/runs/routes/realpair-bidcamp-baseline-260623.json`
  - `tmcp-benchmark/runs/routes/realpair-bidcamp-tmcp-cold-260623.json`
- Automated evaluations:
  - `tmcp-benchmark/evaluation/automated/realpair-bidcamp-baseline-260623.json`
  - `tmcp-benchmark/evaluation/automated/realpair-bidcamp-tmcp-cold-260623.json`
- Failure log:
  - `tmcp-benchmark/runs/artifacts/realpair-bidcamp-tmcp-cold-260623/public-1.log`

## Outcome

- Both runs reached evaluation and artifact capture.
- Both runs failed the public quality command after `test -f package.json` passed.
- The TMCP cold-start route selected the expected portable nodes with precision and recall of `1.0`.
- The benchmark is failure evidence only, not performance evidence.

## First Failure Patched

The first portability failure was command-discovery mismatch: the inventory emitted `pnpm` script commands for Node repos even when the repo only had `package-lock.json`.

Patch:

- `services.tmcp_benchmark` now records `package_manager`.
- Script commands now use `packageManager` or lockfiles to choose `pnpm`, `npm`, or `yarn`.
- Preflight now accepts clean repos with any quality command (`test`, `lint`, or `typecheck`) instead of requiring only `test`.
- `tests/test_tmcp_benchmark.py` covers lint-only eligibility and npm-lockfile command discovery.

## Verification

- `uv run pytest -q tests/test_tmcp_benchmark.py`
