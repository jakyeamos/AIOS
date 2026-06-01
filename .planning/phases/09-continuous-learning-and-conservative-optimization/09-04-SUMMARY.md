---
phase: 09-continuous-learning-and-conservative-optimization
plan: "04"
subsystem: conservative-optimizer
tags: [sqlite, writebacks, governance, learning-proposals]
requires:
  - phase: 09-continuous-learning-and-conservative-optimization
    provides: LEARN-01 signal taxonomy
  - phase: 09-continuous-learning-and-conservative-optimization
    provides: LEARN-02 RecurringPattern detector output
provides:
  - Conservative proposal synthesis from recurring learning patterns
  - Git-tracked conservatism policy thresholds
  - Cooling-period dedupe for repeated pattern proposals
affects: [learning-cli, writeback-governance, operator-surfaces]
tech-stack:
  added: []
  patterns:
    - governed improvement_writebacks insertion from services layer
    - declarative policy loading with strict key validation
key-files:
  created:
    - config/learning/conservatism-policy.json
    - services/conservative_optimizer.py
    - tests/test_conservative_optimizer.py
  modified: []
key-decisions:
  - "Learning proposals always require approval, regardless of policy classification."
  - "Cooling-period dedupe matches pattern_id inside proposed_change_json using quoted LIKE for SQLite portability."
  - "Thresholds are operator-tunable through config/learning/conservatism-policy.json."
patterns-established:
  - "Learning optimizer writes only improvement_writebacks and improvement_writeback_events."
  - "Batch proposal APIs return structured skipped reasons for operator visibility."
requirements-completed: [LEARN-03]
duration: 5min
completed: 2026-06-01
---

# Phase 9 Plan 04 Summary

**Governed conservative proposal synthesis from recurring learning patterns with approval and cooling-period safeguards**

## Performance

- **Duration:** 5 min
- **Started:** 2026-06-01T22:58:50Z
- **Completed:** 2026-06-01T23:03:42Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- Added `config/learning/conservatism-policy.json` with conservative defaults: sample floor 5, recurrence floor 3, confidence floor 0.6, 14-day cooling period, trend sample floor 10.
- Added `services/conservative_optimizer.py` with `load_conservatism_policy`, `propose_from_pattern`, `propose_from_all_patterns`, `_writeback_within_cooling_period`, and approval-forced writeback insertion.
- Added 24 tests covering strict policy loading, threshold gates, per-signal overrides, informational-signal skips, metadata provenance, hard approval, event rows, cooling-period dedupe, and batch skip reasons.

## Governance Invariants

- `propose_from_pattern` skips non-actionable informational signals before any write.
- Every emitted `improvement_writebacks` row has `status='pending_approval'` and `requires_approval=1`.
- Proposed payload metadata includes `source='learning_analysis'`, `pattern_id`, `evidence_run_ids`, `sample_size`, `recurrence_count`, and `confidence`.
- The optimizer writes only `improvement_writebacks` and `improvement_writeback_events`; tests assert registry-like tables do not change.

## Cooling Period

`_writeback_within_cooling_period` checks for the quoted `pattern_id` inside `proposed_change_json` and does not filter by status. Pending, approved, and rejected rows all suppress repeated proposals within `policy.cooling_period_days`.

## Files Created/Modified

- `config/learning/conservatism-policy.json` - Git-tracked operator thresholds for conservative proposal synthesis.
- `services/conservative_optimizer.py` - Policy loading, threshold classification, writeback insertion, cooling-period dedupe, and batch proposal helper.
- `tests/test_conservative_optimizer.py` - Focused behavior coverage for policy, proposal, dedupe, and batch paths.
- `.planning/phases/09-continuous-learning-and-conservative-optimization/09-04-SUMMARY.md` - Plan completion artifact.

## Decisions Made

- Duplicated the services-safe `improvement_writebacks` insert shape locally instead of importing from `bin/`, preserving the architecture boundary.
- Used `proposed_change_json` as the metadata carrier because `schema.sql` does not define a separate `metadata_json` column on `improvement_writebacks`.
- Used quoted `LIKE` matching for `pattern_id` dedupe instead of `json_extract` to avoid coupling this layer to a specific SQLite JSON extension version.

## Deviations from Plan

None in behavior. The implementation did not import the lifecycle shim because the available insert helper is private and lifecycle-specific; the optimizer keeps its own narrow insert helper.

## Verification

- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_conservative_optimizer.py tests/test_architecture_enforcement.py -x -q` -> 26 passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check services/conservative_optimizer.py tests/test_conservative_optimizer.py` -> passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format --check services/conservative_optimizer.py tests/test_conservative_optimizer.py` -> passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run basedpyright services/conservative_optimizer.py` -> passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run python -c "import json; p=json.load(open('config/learning/conservatism-policy.json')); assert {'version','min_sample_size','min_recurrence_count','min_confidence','cooling_period_days','min_sample_size_for_trend','per_signal_overrides'} <= set(p.keys())"` -> passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run python -c "from services.conservative_optimizer import load_conservatism_policy, propose_from_pattern, propose_from_all_patterns, _writeback_within_cooling_period; p=load_conservatism_policy(); assert p.min_sample_size>=5"` -> passed

## Next Phase Readiness

Plan 05 can expose recurring patterns, conservative proposals, and learning impact through CLI and UI surfaces. LEARN-03 now has a governed backend proposal path.

---
*Phase: 09-continuous-learning-and-conservative-optimization*
*Completed: 2026-06-01*
