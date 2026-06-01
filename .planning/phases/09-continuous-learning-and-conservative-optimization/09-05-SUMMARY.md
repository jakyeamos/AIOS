---
phase: 09-continuous-learning-and-conservative-optimization
plan: "05"
subsystem: learning-surfaces
tags: [cli, hook-stop, trpc, learning-ui, governance]
requires:
  - phase: 09-continuous-learning-and-conservative-optimization
    provides: LEARN-01 signal taxonomy
  - phase: 09-continuous-learning-and-conservative-optimization
    provides: LEARN-02 recurring patterns
  - phase: 09-continuous-learning-and-conservative-optimization
    provides: LEARN-03 conservative optimizer
  - phase: 09-continuous-learning-and-conservative-optimization
    provides: LEARN-04 learning impact projections
provides:
  - CLI commands for learning analysis, proposals, and impact
  - Hook-stop closeout signal_kind heuristic
  - UI server and tRPC learning surfaces
affects: [operator-surfaces, learning-ui, workflow-learning-audit]
tech-stack:
  added: []
  patterns:
    - additive CLI audit payload extensions
    - tRPC router per AIOS learning domain
key-files:
  created:
    - aios-ui/server/routers/learning.ts
    - .planning/phases/09-continuous-learning-and-conservative-optimization/09-05-SUMMARY.md
  modified:
    - services/aios_cli.py
    - bin/hook-stop.py
    - aios-ui/lib/types.ts
    - aios-ui/server/aios/learning.ts
    - aios-ui/server/routers/_app.ts
    - tests/test_aios_cli.py
    - tests/test_hook_stop.py
key-decisions:
  - "CLI learning-propose supports dry-run mode that classifies proposals without writes."
  - "Hook-stop closeout signal_kind is a heuristic; cross-run pattern detection remains authoritative."
  - "UI proposal rows expose both proposal_status and current_lifecycle_state."
patterns-established:
  - "Learning payload additions are backward-compatible and additive."
  - "Learning UI server functions are read-only and exposed through a dedicated learning router."
requirements-completed: [LEARN-01, LEARN-04]
duration: 12min
completed: 2026-06-01
---

# Phase 9 Plan 05 Summary

**Operator-reachable learning analysis, proposal, closeout signal, and UI server surfaces**

## Accomplishments

- Added `aios learning-analyze`, `aios learning-propose`, and `aios learning-impact` CLI commands.
- Extended `_workflow_learning_payload` with `recurring_patterns`, `conservative_proposals`, `recurring_pattern_count`, `conservative_proposal_count`, `signal_kind_counts`, and contract metadata for signal kinds and policy source.
- Added hook-stop closeout signal emission with priority: follow-up or repair -> `repeated_failure`; failed workflow -> `weak_workflow`; open blocker -> `ignored_rule`; otherwise `NULL`.
- Added UI learning types, read-only server functions, a new `learningRouter`, and `appRouter.learning` wiring.

## Files Created/Modified

- `services/aios_cli.py` - New learning CLI payloads, parser wiring, audit payload extensions, and LearningSignal contract row.
- `bin/hook-stop.py` - Closeout signal-kind classifier and emitter.
- `aios-ui/lib/types.ts` - `LearningSignalKind`, `RecurringPattern`, `LearningImpactPerRun`, `LearningImpactRollup`, `ConservativeProposalRow`, and related asset/proposal types.
- `aios-ui/server/aios/learning.ts` - `getLearningImpactForRun`, `getLearningImpactRollup`, `listRecurringPatterns`, `listConservativeProposals`.
- `aios-ui/server/routers/learning.ts` - Four tRPC procedures: `getRunImpact`, `getRollup`, `listPatterns`, `listProposals`.
- `aios-ui/server/routers/_app.ts` - `learning: learningRouter` wiring.

## Pitfall 8

`ConservativeProposalRow` includes both `proposal_status` from `improvement_writebacks.status` and `current_lifecycle_state` from `promotion_lifecycle_items.status` when available. The UI page that renders these fields remains Phase 10 scope.

## Verification

- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_aios_cli.py tests/test_hook_stop.py tests/test_architecture_enforcement.py -x -q` -> 62 passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check bin/hook-stop.py tests/test_hook_stop.py services/aios_cli.py tests/test_aios_cli.py` -> passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format --check bin/hook-stop.py tests/test_hook_stop.py services/aios_cli.py tests/test_aios_cli.py` -> passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run basedpyright services/aios_cli.py bin/hook-stop.py` -> passed
- `cd aios-ui && pnpm lint` -> passed with 83 pre-existing anti-slop warnings
- `cd aios-ui && pnpm exec tsc --noEmit` -> passed

## Next Phase Readiness

Plan 06 can tighten divergent strategy and workflow experiment promotion paths through governed proposal helpers. The rendered React learning surface remains out of scope until Phase 10.

---
*Phase: 09-continuous-learning-and-conservative-optimization*
*Completed: 2026-06-01*
