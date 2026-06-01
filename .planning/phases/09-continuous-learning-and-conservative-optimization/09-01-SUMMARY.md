---
phase: 09-continuous-learning-and-conservative-optimization
plan: "01"
subsystem: learning-foundation
tags: [learning-taxonomy, workflow-learning-events, signal-kind, writeback-policy]
requires: []
provides:
  - "LearningSignalKind taxonomy and ConservatismPolicy dataclass"
  - "Nullable workflow_learning_events.signal_kind migration in runtime and CLI bootstrap paths"
  - "route-default and packet-default approval-gated impact scopes"
  - "signal_kind-aware workflow learning event persistence and dedupe"
affects: [phase-09, learning-analysis, conservative-optimizer, learning-impact, workflow-learning-audit]
tech-stack:
  added: []
  patterns:
    - "Learning evidence keeps evidence_type as run-shape bucket and signal_kind as signal-content axis."
    - "Route and packet defaults are approval-gated through the same writeback policy as prompt/skill/workflow defaults."
key-files:
  created:
    - services/learning_taxonomy.py
    - tests/test_learning_taxonomy.py
  modified:
    - bin/aios_orchestration_runtime.py
    - services/aios_cli.py
    - tests/test_orchestration_runtime.py
    - tests/test_aios_cli.py
key-decisions:
  - "Use a nullable signal_kind column on workflow_learning_events rather than a sibling table."
  - "Keep legacy workflow learning rows valid with NULL signal_kind."
  - "Treat route-default and packet-default as high-impact approval scopes."
patterns-established:
  - "Phase 9 modules import shared learning signal literals from services.learning_taxonomy."
  - "Workflow learning event dedupe keys include signal_kind when present and preserve legacy NULL dedupe behavior."
requirements-completed: [LEARN-01]
duration: resumed
completed: 2026-06-01
---

# Phase 9 Plan 01 Summary

**Typed learning signal taxonomy with signal-kind persistence and approval-gated route/packet defaults**

## Performance

- **Duration:** resumed in current session
- **Started:** 2026-06-01T00:00:00Z
- **Completed:** 2026-06-01T00:00:00Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- Added `services/learning_taxonomy.py` with the ten-value `LearningSignalKind` literal, `LEARNING_SIGNAL_KINDS`, `SIGNAL_TO_IMPACT_SCOPE`, `IS_ACTIONABLE_SIGNAL`, `impact_scope_for_signal`, and frozen `ConservatismPolicy`.
- Added idempotent runtime migration support for `workflow_learning_events.signal_kind` and `idx_workflow_learning_events_signal`.
- Extended `writeback_approval_policy` so `route-default`, `packet-default`, and `standards-default` are scope-based approval-gated defaults.
- Extended CLI workflow learning events to accept optional `signal_kind`, persist it, dedupe by it when present, preserve NULL legacy dedupe, and expose it in payload rows.

## Task Commits

Task-level commits were collapsed into one Plan 09-01 implementation commit for this resumed execution.

## Files Created/Modified

- `services/learning_taxonomy.py` - Shared Phase 9 learning signal taxonomy and policy dataclass.
- `tests/test_learning_taxonomy.py` - Taxonomy completeness, mapping, actionable split, helper, and dataclass tests.
- `bin/aios_orchestration_runtime.py` - Runtime signal_kind migration and default-scope approval policy expansion.
- `tests/test_orchestration_runtime.py` - Runtime migration, policy scope, and legacy-row tests.
- `services/aios_cli.py` - CLI signal_kind schema bootstrap, dedupe, insert, and payload passthrough.
- `tests/test_aios_cli.py` - CLI signal_kind persistence, optional legacy path, dedupe, schema, and payload tests.

## Decisions Made

- `signal_kind` remains nullable to preserve old `workflow_learning_events` rows.
- `evidence_type` remains unchanged; `signal_kind` adds a second typed axis rather than replacing the existing run-shape buckets.
- Services do not import from `bin/`; CLI and runtime each own their schema bootstrap path.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Include standards-default in high-impact scope policy**
- **Found during:** Task 2 tests
- **Issue:** The planned regression set included `standards-default` as an existing approval-gated scope, but runtime policy only covered standards via layer-level approval.
- **Fix:** Added `standards-default` to `high_impact_scopes` so policy class is `standards-default_change`.
- **Files modified:** `bin/aios_orchestration_runtime.py`, `tests/test_orchestration_runtime.py`
- **Verification:** Targeted runtime policy tests passed.
- **Committed in:** Plan closeout commit

---

**Total deviations:** 1 auto-fixed (Rule 2)
**Impact on plan:** Additive policy hardening; no behavioral weakening.

## Issues Encountered

- The initial `ensure_runtime_schema` test used a bare in-memory database, but the runtime schema extender expects the base schema's `sessions` table. The test now applies `schema.sql` first.

## User Setup Required

None - no external service configuration required.

## Verification

- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_learning_taxonomy.py tests/test_orchestration_runtime.py tests/test_aios_cli.py tests/test_architecture_enforcement.py -x -q` — 69 passed.
- `uv run ruff check services/learning_taxonomy.py bin/aios_orchestration_runtime.py services/aios_cli.py tests/test_learning_taxonomy.py tests/test_orchestration_runtime.py tests/test_aios_cli.py` — passed.
- `uv run ruff format --check services/learning_taxonomy.py bin/aios_orchestration_runtime.py services/aios_cli.py tests/test_learning_taxonomy.py tests/test_orchestration_runtime.py tests/test_aios_cli.py` — passed.
- `uv run basedpyright services/learning_taxonomy.py bin/aios_orchestration_runtime.py services/aios_cli.py` — passed.
- Explicit grep/import acceptance checks for taxonomy symbols, signal_kind schema, scope policy, test names, and `_record_workflow_learning_event` signature — passed.

## Next Phase Readiness

Phase 9 Plans 02, 03, and 04 can now import the taxonomy and write/reason over `workflow_learning_events.signal_kind`.

---
*Phase: 09-continuous-learning-and-conservative-optimization*
*Completed: 2026-06-01*
