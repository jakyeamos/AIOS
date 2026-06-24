---
phase: 24-rectify-linked-repo-aios-readiness-blockers-except-agent-router
plan: "03"
subsystem: quality-governance
tags: [linked-repos, production-web, evidence, quality-pipeline]
requires:
  - phase: 24-rectify-linked-repo-aios-readiness-blockers-except-agent-router
    provides: Plan 24-01 evidence runner and Plan 24-02 local evidence pattern
provides:
  - Production web validation scripts for portfolio, dispatches-from-cyberspace, Bballedu, and tm
  - AIOS-owned production web gate registry updates
  - Fresh local evidence rows for all runnable updated gates
affects: [phase24, linked-repo-readiness, quality-pipeline]
tech-stack:
  added: []
  patterns: [Honest local gates, blocked readiness until CI/default proof]
key-files:
  created:
    - .planning/phases/24-rectify-linked-repo-aios-readiness-blockers-except-agent-router/24-03-SUMMARY.md
  modified:
    - config/quality-pipeline.json
    - config/quality-gates.json
    - docs/audits/linked-repo-adoption-readiness-audit.md
    - PROJECT.md
key-decisions:
  - "Added only repo-local scripts that execute real validation logic."
  - "Kept all four production web apps blocked because failed gates and CI/default proof gaps remain."
  - "Recorded workflow-file presence as blocked CI proof until default-branch status is verified."
patterns-established:
  - "AIOS quality-pipeline commands must match committed linked-repo scripts."
  - "Production web app maturation may add local gate surfaces without promoting readiness."
requirements-completed: []
duration: 35 min
completed: 2026-06-24
---

# Phase 24 Plan 03: Standard Production Web App Gate Remediation Summary

**Production web apps now have real local gate surfaces and recorded evidence, with readiness still blocked**

## Performance

- **Duration:** 35 min
- **Started:** 2026-06-24T03:17:00Z
- **Completed:** 2026-06-24T03:31:00Z
- **Tasks:** 3
- **Files modified:** AIOS config/audit/truth files plus four linked repos

## Accomplishments

- Added or normalized production web validation scripts for `portfolio`, `dispatches-from-cyberspace`, `Bballedu`, and `tm`.
- Registered matching AIOS gate commands for test, typecheck, env validation, secret scan, dependency security, and smoke coverage where the repo has an honest local surface.
- Captured local `quality_pipeline_runs` evidence for every attempted configured gate.
- Updated the linked-repo adoption audit with evidence IDs, failed gates, external commits, and remaining blockers.
- Kept all four repos blocked pending failed-gate fixes and Plan 24-09 CI/default-branch proof.

## Task Commits

1. **AIOS production web gate registry** - `63cd9c50` (feat)
2. **portfolio scripts** - `665821a` in `/Users/jakyeamos/projects/portfolio`
3. **dispatches scripts** - `afddf2d` in `/Users/jakyeamos/projects/dispatches-from-cyberspace`
4. **Bballedu scripts** - `7acad4f` in `/Users/jakyeamos/projects/Bballedu`
5. **tm scripts** - `07c1222` in `/Users/jakyeamos/projects/tm`

## Files Created/Modified

- `config/quality-pipeline.json` - Adds production web gate commands and narrowed blockers for the four repos.
- `config/quality-gates.json` - Adds corresponding `test_quality` command coverage.
- `docs/audits/linked-repo-adoption-readiness-audit.md` - Records Plan 24-03 evidence IDs and remaining blockers.
- `PROJECT.md` - Records factual linked-repo readiness state after production web evidence capture.
- Linked repos - Add repo-local validation scripts and package script entries.

## Issues Encountered

- `portfolio` needed a Vite patch update to clear the high-severity dependency-security gate.
- `portfolio` Pre-CR initially included unrelated dirty files, so its adapter was narrowed to staged changes before committing the plan files.
- Several gates still fail honestly:
  - `dispatches-from-cyberspace`: typecheck, dependency security, Pre-CR, and missing architecture/CI/default proof.
  - `Bballedu`: dependency security, smoke, Pre-CR, and missing architecture/CI/default proof.
  - `tm`: dependency security, Pre-CR, and missing architecture/CI/default proof.
  - `portfolio`: Pre-CR plus CI/default, coverage, SEO, and full e2e proof gaps.

## Verification

- Package JSON parse command for all four linked repos - passed.
- `python3 -c 'import json; [json.load(open(p)) for p in ["config/quality-pipeline.json","config/quality-gates.json"]]; print("json ok")'` - passed.
- `uv run pytest -q tests/test_linked_repo_readiness.py tests/test_quality_pipeline.py` - passed.
- Phase 24 readiness report for the four repos - passed, with all four still blocked.

## User Setup Required

None for local evidence. CI/default-branch proof remains assigned to Plan 24-09.

## Next Phase Readiness

Ready for 24-04. Plan 24-03 converted missing production-web gate surfaces into concrete passing, failing, or blocked evidence without marking any repo ready.

---
*Phase: 24-rectify-linked-repo-aios-readiness-blockers-except-agent-router*
*Completed: 2026-06-24*
