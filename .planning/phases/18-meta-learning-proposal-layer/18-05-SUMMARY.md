# Phase 18 Plan 18-05 Summary: Auto-Allow Safety Gate

## Completed Scope

- Added `services/meta_learning_auto_allow.py` for separated auto-allow risk assessment.
- Added `AUTO_ALLOW_CHANNEL = meta_learning_auto_allow_recommendations` so permission recommendations remain separate from ordinary meta-learning proposals.
- Added assessment fields for frequency, read-only behavior, write capability, filesystem writes, network access, credential exposure risk, destructive potential, reversibility, repo sensitivity, sandboxability, dry-run support, risk score, and reasons.
- Classified deterministic read-only inspection plus local test/lint/format checks as `safe_to_suggest`.
- Classified write commands, Git operations, package installation, network calls, credential-adjacent commands, shell expansion, and dynamic arguments as `manual_review_required`.
- Classified destructive commands, secret access, deploy/publish/release/production commands, external network writes, and credential modification as `never_auto_allow`.
- Added `docs/meta-learning/auto-allow-safety.md` documenting the policy and review contract.

## TMCP / Agent-Rule Placement Decision

No always-loaded agent rule files were edited. The detailed permission policy is intent-specific documentation under `docs/meta-learning/` plus executable policy in `services/meta_learning_auto_allow.py`; always-loaded surfaces should only point to this policy when the auto-allow intent is active.

## Requirement Evidence

- `META-06`: Complete. Auto-allow candidates are scored separately from ordinary proposals and dangerous actions are never auto-allowed by default.

## Verification

- `uv run pytest -q tests/test_meta_learning_auto_allow.py` -> 6 passed.
- `uv run ruff check services/meta_learning_auto_allow.py tests/test_meta_learning_auto_allow.py` -> passed.
- `pnpm context:validate` -> passed.
- `git diff --check` -> passed.
- `pnpm quality:eval` -> exited 0; reported broad existing repository hotspots and no new >500-line hotspot from this plan.

## Complexity + Simplification Gate

- Gate A: Classification is local, deterministic, and uses token/set checks with no DB, network, or subprocess calls.
- Gate B: Permission recommendations are isolated from proposal generation to prevent frequency-based permission creep.
- Gate C: Focused tests, lint, context validation, whitespace check, and quality eval completed.

## Next Plan

Proceed to Phase 18 Plan 18-06: shadow eval plans and minimal meta CLI surface.
