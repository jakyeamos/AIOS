---
phase: 09-continuous-learning-and-conservative-optimization
plan: "02"
subsystem: learning-analysis
tags: [sqlite, recurring-patterns, success-criteria, workflow-routing]
requires:
  - phase: 09-continuous-learning-and-conservative-optimization
    provides: LEARN-01 signal taxonomy and LearningSignalKind literals
provides:
  - RecurringPattern dataclass and stable pattern id helper
  - Read-only recurring pattern detector dispatch for seven actionable learning signals
  - Detector tests covering bounds, stability, scope fallback, and content-safe summaries
affects: [learning-impact, conservative-optimization, workflow-learning]
tech-stack:
  added: []
  patterns:
    - schema-aware SQLite detector reads
    - stable pattern identifiers over signal, scope, key, and window bucket
key-files:
  created:
    - services/learning_analysis.py
    - tests/test_learning_analysis.py
  modified: []
key-decisions:
  - "Detectors are read-only and return empty lists for missing evidence tables."
  - "Current and focused-test success criteria schemas are both supported through a source-shape helper."
  - "Packet summaries use numeric section buckets only, never raw selection trace content."
patterns-established:
  - "Learning detectors use bounded created_at windows and conservative sample floors."
  - "Project-scoped detectors fall back to cross-project evidence only when scoped evidence emits no pattern."
requirements-completed: [LEARN-02]
duration: 45min
completed: 2026-06-01
---

# Phase 9 Plan 02 Summary

**Read-only recurring-pattern analysis over persisted workflow, routing, packet, prompt, and standards evidence**

## Performance

- **Duration:** 45 min
- **Started:** 2026-06-01T22:07:00Z
- **Completed:** 2026-06-01T22:52:15Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Added `RecurringPattern` and `detect_recurring_patterns(conn, *, since, project_id, signal_kinds)` with seven actionable detectors keyed by `LearningSignalKind`.
- Implemented bounded SQLite detectors for repeated failures, ignored rules, bloated packets, weak prompts, weak workflows, route misroutes, and standards regressions.
- Added 26 focused tests covering empty schemas, informational signal skips, all detector outputs, since-window filtering, project scoping, cross-project fallback tagging, and stable pattern ids.

## Detector Signatures

- `_detect_repeated_failures(conn, *, since, project_id) -> list[RecurringPattern]`
- `_detect_ignored_rules(conn, *, since, project_id) -> list[RecurringPattern]`
- `_detect_bloated_packets(conn, *, since, project_id) -> list[RecurringPattern]`
- `_detect_weak_prompts(conn, *, since, project_id) -> list[RecurringPattern]`
- `_detect_weak_workflows(conn, *, since, project_id) -> list[RecurringPattern]`
- `_detect_route_misroutes(conn, *, since, project_id) -> list[RecurringPattern]`
- `_detect_standards_regression(conn, *, since, project_id) -> list[RecurringPattern]`

## Threshold Constants

- `_REPEATED_FAILURE_RECURRENCE_THRESHOLD = 3`: avoids one-off blocker noise.
- `_IGNORED_RULE_RECURRENCE_THRESHOLD = 2`: repeated open blockers are enough to flag ignored criteria.
- `_WEAK_PROMPT_SAMPLE_FLOOR = 5`, `_WEAK_PROMPT_MEAN_THRESHOLD = 0.5`: weak prompt signals require a minimum sample and low mean outcome.
- `_WEAK_WORKFLOW_SAMPLE_FLOOR = 5`, `_WEAK_WORKFLOW_FAILURE_RATE_THRESHOLD = 0.4`: workflow weakness requires enough runs and a material failure rate.
- `_BLOATED_PACKET_SAMPLE_FLOOR = 5`, `_BLOATED_PACKET_STDEV_MULTIPLIER = 2.0`: bloated packet detection uses per-workflow median plus standard deviation.
- `_ROUTE_MISROUTE_RECURRENCE_FLOOR = 3`, `_ROUTE_MISROUTE_RATE_THRESHOLD = 0.4`: route signals require multiple blocker-bearing runs.
- `_STANDARDS_REGRESSION_RECURRENCE_FLOOR = 2`: standards regressions require repeated snapshots.

## Pattern Stability

`_stable_pattern_id` hashes only `signal_kind`, `scope_kind`, `scope_key`, and `_bucket_window(since)`. Tests assert repeated calls to each core detector over identical seeded evidence return identical `pattern_id` values.

## Pitfall 6 Enforcement

`_detect_bloated_packets` summaries include only bucketed numeric descriptors such as median section count and current section count. Tests assert raw `selection_trace_json` content is not present in emitted summaries. `_detect_route_misroutes` stores concrete failing run ids in `evidence_run_ids`.

## Scope Fallback

Each detector defaults to the requested `project_id`. If no scoped pattern is emitted, the detector re-runs cross-project and tags fallback patterns with `metadata["scope_fallback"] = "cross-project"` plus `requested_project_id`.

## Files Created/Modified

- `services/learning_analysis.py` - RecurringPattern model, dispatch entrypoint, bounded detector SQL, schema compatibility helpers, stable id/window helpers.
- `tests/test_learning_analysis.py` - In-memory SQLite coverage for dispatcher behavior and all seven detector families.
- `.planning/phases/09-continuous-learning-and-conservative-optimization/09-02-SUMMARY.md` - Plan completion artifact.

## Decisions Made

- Used a sibling `detect_recurring_patterns_partial` helper for partial schema reporting while keeping the primary API a plain list return.
- Supported both current checked-in `success_criteria_findings -> success_criteria_evaluations -> orchestration_runs` shape and focused test schemas with direct `run_id`.
- Left informational signals out of detector dispatch; Plan 03 can reuse the same `IS_ACTIONABLE_SIGNAL` filter pattern for impact rollups.

## Deviations from Plan

One implementation detail changed: the checked-in schema does not match every interface listed in the plan. `prompts_used` is session-oriented in `schema.sql`, and `success_criteria_findings` links through `success_criteria_evaluations`. The module now detects available columns and returns empty when a source cannot support a detector.

## Verification

- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_learning_analysis.py tests/test_architecture_enforcement.py -x -q` -> 28 passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check services/learning_analysis.py tests/test_learning_analysis.py` -> passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format --check services/learning_analysis.py tests/test_learning_analysis.py` -> passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run basedpyright services/learning_analysis.py` -> passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run python -c "from services.learning_analysis import RecurringPattern, detect_recurring_patterns, DETECTORS, _stable_pattern_id, _bucket_window; assert len(DETECTORS) == 7"` -> passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run python -c "import sqlite3; from pathlib import Path; from services.learning_analysis import detect_recurring_patterns; conn=sqlite3.connect(':memory:'); conn.executescript(Path('schema.sql').read_text()); patterns=detect_recurring_patterns(conn, since='2026-01-01T00:00:00Z', project_id=None); assert isinstance(patterns, list)"` -> passed

## Next Phase Readiness

Plan 03 can import `RecurringPattern` and `detect_recurring_patterns` to project impact and handle informational learning signals. Plan 04 can use stable `pattern_id` values as cooling-period dedupe keys.

---
*Phase: 09-continuous-learning-and-conservative-optimization*
*Completed: 2026-06-01*
