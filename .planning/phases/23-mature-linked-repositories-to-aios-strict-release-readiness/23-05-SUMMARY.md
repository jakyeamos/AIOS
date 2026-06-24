---
phase: 23-mature-linked-repositories-to-aios-strict-release-readiness
plan: "05"
subsystem: linked-repo-adoption
tags:
  - data-repos
  - research-repos
  - quality-gates
key-files:
  created: []
  modified:
    - config/quality-gates.json
    - config/quality-pipeline.json
key-decisions:
  - "Data/research/course repos use class-specific validation instead of fake app gates."
  - "pre_cr_only repos are moved to class_blocked when no real validation surface exists."
requirements-completed:
  - TBD
completed: 2026-06-24
---

# Phase 23 Plan 05: Python Data Research And Course Repo Maturation Summary

Matured the AIOS-owned configuration surface for Python/data/research/course repos where real local validation exists, and recorded blockers where strict readiness cannot yet be claimed.

## Outcome

- Added quality-pipeline gates for `career-ops`, `Dsci-proj`, `claude-improvement-lab`, `R-Project`, `LIS`, `csds391-s26-6`, `manga-sync`, and `Fantasy`.
- Updated quality-gate `test_quality` adapters where real commands exist:
  - `career-ops`: `npm run verify`, `npm run doctor`, `npm run sync-check`
  - `Dsci-proj`: `make test`, `make check-deps`
  - `claude-improvement-lab`: Python compile floor
  - `R-Project`: `Rscript save_plots.R`
  - `LIS`: `uv run ruff check .`, `uv run pytest -q`, `uv run lis --help`
  - `Fantasy`: backend `uv run pytest -q`
- Moved `pre_cr_only` repos in this class to `class_blocked` where strict validation is still missing.
- Preserved weak/floor validations as blockers instead of calling them mature.

## Readiness Result

| Repo | Result |
| --- | --- |
| career-ops | `blocked`: missing lint/static, architecture/structure, CI, secret scan, dependency security, and fresh evidence |
| Dsci-proj | `blocked`: Makefile still uses npm for dashboard install/test, and architecture/security/dependency/fresh CI proof are missing |
| claude-improvement-lab | `blocked`: py_compile is only a floor; tests/static checks/CI/security are missing |
| R-Project | `blocked`: Rscript validation is only a floor; reproducibility, tests, CI, security are missing |
| LIS | `blocked`: strong Python surfaces exist, but CI, architecture/structure, security, dependency, and fresh proof are missing |
| csds391-s26-6 | `blocked`: no install/test/validation surface beyond pre-cr |
| manga-sync | `blocked`: no install/test/validation surface beyond pre-cr |
| Fantasy | `blocked`: backend pytest exists, but aggregate frontend/backend validation, CI, security, and default-branch proof are missing |

## Verification

| Check | Result |
| --- | --- |
| `validate_commit_quality_gate(..., run=False)` for all eight data/research/course repos | PASS |
| `python3 -m json.tool config/quality-gates.json` | PASS |
| `python3 -m json.tool config/quality-pipeline.json` | PASS |
| `uv run pytest -q tests/test_quality_gates.py tests/test_commit_quality_ladder.py` | PASS, 21 tests |
| `pnpm context:validate` | PASS |
| `git diff --check -- config/quality-gates.json config/quality-pipeline.json .planning/phases/23-mature-linked-repositories-to-aios-strict-release-readiness` | PASS |

## Deviations From Plan

The generated Plan 23-05 file had no GSD `<task>` blocks. I executed its prose scope inline and recorded this summary as the durable closeout artifact.

I did not add project truth files inside external repos in this pass because those paths are outside the AIOS writable root and several repos need repo-local decisions. Missing truth/instruction surfaces are recorded as blockers.

## Issues Encountered

No AIOS config validation blockers.

Strict adoption remains blocked for every repo in this class until missing validation, CI/default-branch proof, security/dependency gates, and fresh AIOS evidence are added.

## Self-Check: PASSED
