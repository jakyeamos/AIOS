# Phase 18 Plan 18-03 Summary: Confidence Scoring And Target Routing

## Completed Scope

- Added `services/meta_learning_scoring.py` for deterministic weighted scoring of extracted meta-learning signals.
- Added confidence bands:
  - `observe_only` for scores 0-2.
  - `suggest_project_note_or_low_risk_command` for scores 3-4.
  - `propose_project_rule_skill_or_command` for scores 5-7.
  - `strong_review_gated_proposal` for scores 8+.
- Added scoring inputs for explicit corrections, repeated corrections, approvals, repeated commands, tool friction, model mismatch, context misses, recency, explicit remember/from-now-on requests, multi-project evidence, contradictions, high blast radius, security sensitivity, and permission risk.
- Added a four-question quality filter:
  - specific actionable learning
  - future value
  - supported and non-contradictory
  - safe to route
- Added rejection reasons for generic best practices, vague one-off preferences, contradictory weak signals, and unsafe permission changes.
- Added `services/meta_learning_router.py` for accepted scored signal routing to `global`, `project`, `skill`, `command`, `agent`, `second_brain`, `eval`, or `observe_only`.
- Added project-vs-global safeguards so project-specific signals stay out of global rules unless multi-project evidence justifies global review.

## TMCP / Agent-Rule Placement Decision

No always-loaded agent files were edited for this plan. The scoring and routing policy lives in intent-specific service modules and focused tests because it applies only to the meta-learning proposal workflow, not all agent work.

## Requirement Evidence

- `META-03`: Complete. `services/meta_learning_scoring.py` implements weighted confidence scoring, confidence bands, risk flags, manual-review flags, and quality filtering.
- `META-04`: Complete. `services/meta_learning_router.py` routes quality-filtered scored signals with target-layer justification and project-vs-global safeguards.

## Verification

- `uv run pytest -q tests/test_meta_learning_scoring.py tests/test_meta_learning_router.py` -> 13 passed.
- `uv run ruff check services/meta_learning_scoring.py services/meta_learning_router.py tests/test_meta_learning_scoring.py tests/test_meta_learning_router.py` -> passed.
- `pnpm quality:eval` -> exited 0; reported broad existing repository hotspots and the previously recorded `services/meta_learning_signals.py` size hotspot. New 18-03 modules are below the 500-line file threshold.

## Complexity + Simplification Gate

- Gate A: Scoring and routing use single-pass helpers, sets for multi-project evidence, explicit policies, and no database/network calls.
- Gate B: Policy is split between scoring and routing instead of extending the existing 524-line extractor. No additional abstraction was introduced beyond dataclass result objects needed by Plan 18-04 proposal generation.
- Gate C: Focused tests and lint passed; quality eval completed with no new hotspot introduced by this plan.

## Next Plan

Proceed to Phase 18 Plan 18-04: proposal generator and review lifecycle.
