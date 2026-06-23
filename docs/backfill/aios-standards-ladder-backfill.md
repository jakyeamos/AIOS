# AIOS Standards Ladder Backfill

**Date:** 2026-06-23
**Scope:** Phase 22 Plan 22-01 read-only backfill record.

## Summary

The expanded AIOS success criteria are registered as AIOS-local/runtime gates by
default. Only deterministic staged-file checks are candidates for the portable
global user-level hook.

## Candidate Checks

| Check | Candidate mode | Backfill status | Notes |
| --- | --- | --- | --- |
| secret literal | fail | Existing hook coverage | Portable staged-file check with medium false-positive risk. |
| package manager drift | fail | Existing hook coverage | Portable for pnpm-governed repos. |
| TypeScript `any` | warn | Existing hook coverage | Needs generated/vendor exclusions before fail. |
| oversized source | warn | Existing hook coverage | Proxy for complexity; not fail-eligible without remediation plan. |
| weak tests | warn | Existing hook coverage | Needs smoke/snapshot waiver examples. |
| handler-before-send | warn | Existing AIOS ladder coverage | Runtime-specific waiver required. |
| Pre-CR changed-line readiness | warn | Existing hook bridge | Depends on `.pre-cr.json` and CLI availability. |

## Read-Only Project Scan

The Phase 22 scan covered the AIOS repo and the linked portfolio workspace.
Generated/runtime output directories were excluded where practical, including
`node_modules`, `.next`, `dist`, and `build`.

| Project | Package-manager drift | TypeScript `any` candidates | Handler-before-send candidates | Secret literal candidates | Weak-test candidates | Notes |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `AIOS` | mixed historical fixtures; active UI has `pnpm-lock.yaml` and a legacy `package-lock.json` | 0 production hits | 0 production hits | 2 test-fixture hits | 1 staging fixture | Do not promote fixture-sensitive checks beyond current fail/warn posture without narrower exclusions. |
| `portfolio` | active root uses `pnpm-lock.yaml`; no active `package-lock.json`/`yarn.lock` found | 0 production hits | 0 production hits | 1 `.env.example` hit | 0 test files found | Secret-like example files need explicit example/placeholder handling. |

Scan commands used read-only `find`, `rg`, and `uv run python` inventory
checks. No source files were mutated during backfill.

## AIOS-Local Checks

These checks must not block arbitrary repositories through the global hook:

- context compiler validation
- success-criteria registry validation
- standards-health registry validation
- quality-pipeline registry checks
- evidence artifact freshness
- verifier artifact freshness
- project truth/writeback checks
- git worktree cleanliness for AIOS-managed completion

## False Positives And Waivers

- Secret literal fixtures require narrow allowlisting or test-fixture exclusions.
- TypeScript `any` can be valid in generated or third-party files.
- Oversized source can be valid for generated files or external schemas.
- Weak tests can be valid for smoke tests when explicitly labeled.
- Handler-before-send may be required by some runtimes.

Waivers must include rule id, owner, expiry, concrete runtime/governance reason,
and evidence path.

## Remediation Candidates

- Add generated/vendor/test-fixture exclusions to portable staged-file checks.
- Add a machine-readable waiver parser before promoting more checks to `fail`.
- Add first-class project backfill fixtures before fail-closing TypeScript,
  oversized-source, weak-test, handler-ordering, or Pre-CR checks.
- Keep evidence-dependent checks inside `services/commit_quality_ladder.py`.

## Result

No additional checks are promoted to fail in this plan. The safe Phase 22
posture is:

- portable global hook: staged-file fail checks already covered by deterministic
  rules, plus warn checks for candidates needing backfill
- AIOS-local ladder: context, registry, evidence, verifier, truth, and workflow
  gates
