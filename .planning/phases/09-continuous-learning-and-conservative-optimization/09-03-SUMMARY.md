---
phase: 09-continuous-learning-and-conservative-optimization
plan: "03"
subsystem: learning-impact
tags: [sqlite, learning-impact, compounding-visibility, trend-rollups]
requires:
  - phase: 09-continuous-learning-and-conservative-optimization
    provides: LEARN-01 signal taxonomy and workflow learning signal persistence
provides:
  - Pure-read per-run learning impact projection
  - Pure-read workflow, prompt, and skill trend rollups
  - Trend rationale that always cites sample size
affects: [learning-cli, operator-surfaces, conservative-optimization]
tech-stack:
  added: []
  patterns:
    - schema-aware read projections
    - conservative trend labeling with insufficient-data guard
key-files:
  created:
    - services/learning_impact.py
    - tests/test_learning_impact.py
  modified: []
key-decisions:
  - "Per-run impact returns None when the run id is unknown."
  - "Prompt and skill rollups use outcome quality as a rework proxy until explicit rework events exist."
  - "Trend labels are blocked behind the ConservatismPolicy min_sample_size_for_trend default of 10."
patterns-established:
  - "Pure projection modules are verified by snapshotting table row counts before and after calls."
  - "Rollup rationale strings include sample_size for every trend branch."
requirements-completed: [LEARN-04]
duration: 6min
completed: 2026-06-01
---

# Phase 9 Plan 03 Summary

**Compounding-visibility projections for per-run learning impact and per-asset trend rollups**

## Performance

- **Duration:** 6 min
- **Started:** 2026-06-01T22:52:30Z
- **Completed:** 2026-06-01T22:58:41Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added `LearningImpactPerRun`, `LearningImpactRollup`, `AssetEvidenceDelta`, and `ProposalCreated` frozen dataclasses.
- Added `build_per_run_impact` to project workflow learning events, asset evidence, linked writebacks, and no-learning reasons for a single run.
- Added `build_rollup` and `_trend_from_rates` for workflow, prompt, and skill trend projections with an `insufficient_data` guard below the trend sample floor.

## Files Created/Modified

- `services/learning_impact.py` - Pure-read learning impact projections, schema-aware asset loaders, rollup window readers, and trend math.
- `tests/test_learning_impact.py` - 21 behavior tests for per-run payloads, rollup trend branches, project filters, and pure-read guarantees.
- `.planning/phases/09-continuous-learning-and-conservative-optimization/09-03-SUMMARY.md` - Plan completion artifact.

## Decisions Made

- Returned `None` for missing runs rather than manufacturing an empty `LearningImpactPerRun`; this keeps callers from confusing absent runs with runs that produced no learning.
- Imported the existing `_no_learning_reason` classifier from `services.aios_cli` because it is already the persisted workflow-learning closeout taxonomy.
- Supported current root schemas defensively: run-linked prompt/evaluation evidence is used when available; otherwise projections return empty asset evidence instead of failing.

## Trend Semantics

`_trend_from_rates` returns:

- `insufficient_data` when `sample_size < min_sample_size_for_trend`.
- `improving` when recent rework rate drops below prior rate by more than `_TREND_EPSILON`.
- `regressing` when recent rework rate rises above prior rate by more than `_TREND_EPSILON`.
- `flat` otherwise.

Every rationale branch includes `sample_size=...`, closing Pitfall 9 for misleading tiny-sample trend labels.

## Pure-Read Proof

The module contains no `INSERT`, `UPDATE`, or `DELETE` statements. Tests snapshot all table row counts before and after `build_per_run_impact` and `build_rollup` calls and assert no changes.

## Deviations from Plan

The checked-in root schema still has some session-linked rather than run-linked evidence tables. The implementation handles that through table/column checks and uses focused run-linked fixtures for the intended Phase 9 projection behavior.

## Verification

- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_learning_impact.py tests/test_architecture_enforcement.py -x -q` -> 23 passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check services/learning_impact.py tests/test_learning_impact.py` -> passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format --check services/learning_impact.py tests/test_learning_impact.py` -> passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run basedpyright services/learning_impact.py` -> passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run python -c "from services.learning_impact import LearningImpactPerRun, LearningImpactRollup, AssetEvidenceDelta, ProposalCreated, build_per_run_impact, build_rollup, _trend_from_rates"` -> passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run python -c "import sqlite3; from pathlib import Path; from services.learning_impact import build_per_run_impact, build_rollup; conn=sqlite3.connect(':memory:'); conn.executescript(Path('schema.sql').read_text()); assert build_per_run_impact(conn, run_id='missing') is None; rollup=build_rollup(conn, scope='workflow', key='missing', since='2026-06-01T00:00:00Z'); assert rollup.sample_size == 0"` -> passed

## Next Phase Readiness

Plan 05 can expose these projections through CLI and UI surfaces. Plan 04 can remain focused on proposal generation because per-run and rollup visibility now has a separate pure-read module.

---
*Phase: 09-continuous-learning-and-conservative-optimization*
*Completed: 2026-06-01*
