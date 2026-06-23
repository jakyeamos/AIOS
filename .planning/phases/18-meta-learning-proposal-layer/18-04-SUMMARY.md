# Phase 18 Plan 18-04 Summary: Proposal Generator And Review Lifecycle

## Completed Scope

- Added `services/meta_learning_proposals.py` for reviewable meta-learning proposal generation.
- Added `MetaLearningProposal` fields required by META-05:
  - `proposal_id`
  - `title`
  - `summary`
  - `target_layer`
  - `target_file`
  - `confidence_score`
  - `risk_level`
  - `evidence`
  - `why_this_layer`
  - `proposed_patch`
  - `rollback`
  - `requires_manual_approval`
- Added stable proposal IDs based on source signal, target layer, and target file.
- Added file-backed JSONL persistence helpers under `data/meta-learning/proposals/`.
- Added conflict records with older rule, newer signal, recommended action, and rationale.
- Preserved the no-auto-apply contract: proposals are review artifacts only, and applying requires a future explicit approval path.

## TMCP / Agent-Rule Placement Decision

No always-loaded agent rules were edited. Generated proposal target files are hints, not direct writes. For global or agent-rule targets, the generated patch explicitly asks reviewers to decide whether the learning belongs in a narrow intent-specific pointer instead of an always-loaded rule.

## Requirement Evidence

- `META-05`: Complete. `services/meta_learning_proposals.py` generates stable reviewable proposals with required fields, manual approval, rollback text, file-backed persistence, and conflict formatting.

## Verification

- `uv run pytest -q tests/test_meta_learning_scoring.py tests/test_meta_learning_router.py tests/test_meta_learning_proposals.py` -> 19 passed.
- `uv run ruff check services/meta_learning_scoring.py services/meta_learning_router.py services/meta_learning_proposals.py tests/test_meta_learning_scoring.py tests/test_meta_learning_router.py tests/test_meta_learning_proposals.py` -> passed.
- `pnpm context:validate` -> passed.
- `pnpm quality:eval` -> exited 0; reported broad existing repository hotspots and the previously recorded `services/meta_learning_signals.py` size hotspot. New 18-04 module is below the 500-line file threshold.

## Complexity + Simplification Gate

- Gate A: Proposal generation is deterministic, file-backed, and uses no database or network calls.
- Gate B: Proposal formatting and persistence are isolated from extraction, scoring, and routing modules. No target rule, skill, command, or second-brain file is modified.
- Gate C: Focused tests, lint, context validation, and quality eval completed.

## Next Plan

Proceed to Phase 18 Plan 18-05: auto-allow safety scoring and separation from ordinary learning proposals.
