---
phase: 12-graph-native-memory-architecture
plan: "05"
completed_at: "2026-06-23T00:00:00.000Z"
requirements:
  - MEM-04
key-files:
  created:
    - docs/specs/memory-packet-contract.md
  modified:
    - schema.sql
    - services/memory_layers.py
    - tests/test_memory_layers.py
metrics:
  focused_tests_passed: 8
---

# Phase 12 Plan 05 Summary

## Result

Defined the formal AIOS memory packet contract for model-facing output. The contract now gives Plan 12-03 a concrete compiler target and Plan 12-06 a validation target for required sections, optional sections, ordering, internal schema shape, Markdown rendering, provenance, stale/superseded facts, contradictions, confidence, token budgeting, and good/bad examples.

## Changed Files

- `docs/specs/memory-packet-contract.md`
  - Defines required sections: `Current Truth` and `Sources/Provenance`.
  - Defines optional sections: `Relevant Prior Decisions`, `Constraints`, `Causal/Dependency Chain`, `Contradictions or Stale Information`, and `Open Questions`.
  - Defines section ordering and token budget priority.
  - Defines internal schema representation for compiler internals and the model-facing Markdown format.
  - Defines provenance, stale/superseded fact, contradiction, confidence, and validity-status rules.
  - States the immutable rule that raw JSON may not appear in model-facing output.
  - Includes two good packet examples and two bad packet examples with named rule violations.

- `schema.sql`
  - Added a `memory_facts.validity_status` `CHECK` constraint for the contract values: `active`, `superseded`, `contradicted`, `uncertain`, and `archived`.

- `services/memory_layers.py`
  - Added `VALIDITY_STATUSES: frozenset[str]`.
  - Added insert-time `FactMemory` validation so the contract matches service behavior.

- `tests/test_memory_layers.py`
  - Added coverage for unknown validity-status rejection.

## Verification

- `uv run pytest -q tests/test_memory_layers.py` passed: 8 tests.
- `uv run ruff check services/memory_layers.py tests/test_memory_layers.py bin/aios_orchestration_runtime.py` passed.
- `uv run ruff format --check services/memory_layers.py tests/test_memory_layers.py bin/aios_orchestration_runtime.py` passed.
- `uv run basedpyright services/memory_layers.py tests/test_memory_layers.py bin/aios_orchestration_runtime.py` passed with 0 errors and 2 existing import-resolution warnings for the test harness.
- `pnpm context:validate` passed.
- Contract grep checks passed for all required sections, examples, validity-status semantics, token budget priority, and the raw-JSON prohibition.

## Deviations from Plan

- **[Rule 2 - Missing critical functionality] Validity-status enforcement** — Found during contract writing. The contract required `validity_status` semantics to match `FactMemory`, but `FactMemory` only defaulted the value and did not reject unknown statuses. Added `VALIDITY_STATUSES`, a SQLite `CHECK`, insert-time validation, and focused test coverage.

**Total deviations:** 1 auto-fixed. **Impact:** The contract now reflects executable behavior instead of documenting an unenforced rule.

## Self-Check: PASSED

All Plan 12-05 must-haves are present: the contract file exists, required and optional sections are specified, ordering and token budgeting are explicit, validity statuses are defined, raw JSON is forbidden from model-facing output, provenance/staleness/contradiction/confidence rules are documented, and the required good/bad examples are included.
