---
phase: 24-rectify-linked-repo-aios-readiness-blockers-except-agent-router
plan: "04"
subsystem: quality-governance
tags: [linked-repos, production-web, remodelvision, amos-saas, evidence]
requires:
  - phase: 24-rectify-linked-repo-aios-readiness-blockers-except-agent-router
    provides: Plan 24-03 production web gate pattern
provides:
  - Targeted remodelvision validation gate surface and evidence
  - Targeted amos-saas validation gate surface and evidence
  - Resolved pnpm package-manager contract for both repos
affects: [phase24, linked-repo-readiness, quality-pipeline]
tech-stack:
  added: []
  patterns: [Package-manager authority before gate proof, evidence rows for failures]
key-files:
  created:
    - .planning/phases/24-rectify-linked-repo-aios-readiness-blockers-except-agent-router/24-04-SUMMARY.md
  modified:
    - config/quality-pipeline.json
    - config/quality-gates.json
    - docs/audits/linked-repo-adoption-readiness-audit.md
    - PROJECT.md
key-decisions:
  - "Made pnpm the explicit package-manager contract for remodelvision and amos-saas."
  - "Removed false amos-saas architecture command coverage and left architecture as an explicit blocker."
  - "Kept both repos blocked because local gate failures and CI/default proof gaps remain."
patterns-established:
  - "Workflow-file presence is blocked CI proof until default-branch status is verified."
  - "Generated or copied worktree directories should not dominate primary repo lint evidence."
requirements-completed: []
duration: 45 min
completed: 2026-06-24
---

# Phase 24 Plan 04: Remodelvision And Amos-SaaS Targeted Production Cleanup Summary

**Targeted production apps now have concrete pnpm gate surfaces and recorded blocker evidence**

## Performance

- **Duration:** 45 min
- **Started:** 2026-06-24T03:31:00Z
- **Completed:** 2026-06-24T03:43:00Z
- **Tasks:** 3
- **Files modified:** AIOS config/audit/truth files plus two linked repos

## Accomplishments

- Added `packageManager: pnpm@10.26.0` and removed npm lockfile ambiguity in both repos.
- Added local env validation, secret scan, dependency security, and workflow-file surfaces for both repos.
- Added `typecheck` for `remodelvision`; added `typecheck`, `test`, and static smoke target checks for `amos-saas`.
- Removed the false `amos-saas` architecture command from AIOS config and kept architecture as a blocker.
- Recorded local evidence rows for every runnable configured gate.

## Task Commits

1. **AIOS targeted production gate registry** - `12954888` (feat)
2. **remodelvision targeted gates** - `64e1618` in `/Users/jakyeamos/projects/remodelvision`
3. **amos-saas targeted gates** - `1b92195` in `/Users/jakyeamos/Projects/amos-saas`

## Files Created/Modified

- `config/quality-pipeline.json` - Registers concrete remodelvision and amos-saas gate commands and remaining blockers.
- `config/quality-gates.json` - Expands the quality-gate command ladder for both repos.
- `docs/audits/linked-repo-adoption-readiness-audit.md` - Records evidence IDs and remaining blockers.
- `PROJECT.md` - Records factual readiness state after Plan 24-04.
- Linked repos - Add pnpm package contracts, local validation scripts, and AIOS workflow files.

## Issues Encountered

- `remodelvision` lint originally scanned copied `.worktrees` and generated `coverage`; those are now ignored so lint evidence reflects the primary repo.
- `remodelvision` still fails lint, typecheck, tests, build, secret scan, env validation, dependency security, coverage, e2e smoke, and Pre-CR.
- `amos-saas` passes install, tests, secret scan, and static smoke, but fails lint, typecheck, build, env validation, and dependency security.
- Both repos still lack substantive architecture proof and verified CI/default-branch proof.

## Verification

- `python3 -c 'import json; [json.load(open(p)) for p in ["config/quality-pipeline.json","config/quality-gates.json"]]; print("json ok")'` - passed.
- `uv run pytest -q tests/test_linked_repo_readiness.py tests/test_quality_pipeline.py` - passed.
- Phase 24 readiness report for `remodelvision` and `amos-saas` - passed, with both repos still blocked.

## User Setup Required

None for local evidence. CI/default-branch proof remains assigned to Plan 24-09.

## Next Phase Readiness

Ready for 24-05. The targeted production app blockers are now factual evidence rows rather than package-manager ambiguity.

---
*Phase: 24-rectify-linked-repo-aios-readiness-blockers-except-agent-router*
*Completed: 2026-06-24*
