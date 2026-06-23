# Behavioral Spec Verification Loop

`behavioral-spec-verification-loop` is an optional mature-repo rehabilitation workflow. It is for projects with enough feature surface that exhaustive behavioral verification is worth the cost. It is intentionally too heavy for small prototypes, early experiments, or low-surface-area repos.

## When To Use

Use this workflow when a repo needs a known-good, evidence-backed state rather than a narrow QA pass. Good candidates have multiple routes or screens, API or server-action surface, auth or permission logic, persisted data, existing tests or runnable app workflows, meaningful user-facing flows, background jobs or notifications, admin/settings/search/import/export/payment flows, or a large source footprint.

Do not use it by default. If the maturity gate fails, prefer a basic smoke test loop, route/API inventory, pre-PR quality gate, targeted bugfix loop, or test backfill plan.

## Eligibility

AIOS considers the workflow eligible when the user explicitly opts in or at least four maturity signals pass:

- 8+ routes/pages/screens
- 5+ API endpoints or server actions
- Auth/session/role/permission logic
- Persistent database/schema/models
- Existing test infrastructure
- 10+ discoverable user-facing features
- Background jobs, queues, emails, or notifications
- 5,000+ non-generated source lines
- Admin/settings/search/filter/sort/import/export/payment flows
- Web app or product platform surface

If maturity is unclear, AIOS should return an eligibility report instead of running the loop.

## Canonical Artifact

The workflow uses exactly one canonical `.xlsx`, updated in place across all phases and iterations. The default artifact is `.planning/runs/{run_id}/behavioral-spec.xlsx`.

The main thread is the single spreadsheet writer. Subagents may inspect, test, and report, but they must not mutate the spreadsheet unless a future AIOS artifact pattern provides safe single-writer coordination.

## Spreadsheet Schema

`Feature ID | Area | Surface | User story | Persona / role | Auth state | Data precondition | Viewport | Expected behavior from code | User-acceptable behavior | Source files/functions | Test method | Test command/actions | Observed behavior | Status | Defect ID | Defect type | Root cause | Fix summary | Regression test added | Complexity review | Evidence | Iteration | Last tested commit | Open question / notes`

Status flow:

`Discovered -> Spec'd -> Test-Blocked / Tested-Pass / Tested-Fail -> Fixing -> Fixed -> Verified -> Regression-Covered`

Additional statuses:

`Needs-Product-Decision`, `Needs-Environment`, `Won't-Fix-With-Reason`

Defect types:

`Functional`, `Logistical`, `UX`, `Accessibility`, `Security`, `Performance`, `Data integrity`, `Permission/auth`, `Regression`, `Test infra`

## Verification Rules

No row may be marked `Verified` unless it has source file/function citation, test method, exact command or browser action, observed result, evidence path or concise output, iteration number, last tested commit, and no open functional, UX, permission, security, data-integrity, or logistical defect for that story.

No row may be marked `Regression-Covered` unless the verified behavior is covered by an automated regression test, or automation is genuinely not feasible and a manual verification note explains why.

## Phases

1. Plan
2. Catalog and spec
3. Coverage audit
4. Test
5. Fix
6. Re-test
7. Regression-cover
8. Boundary audit
9. Final report

The test/fix/re-test/regression-cover loop continues until every row is `Verified`, `Regression-Covered`, `Needs-Product-Decision`, `Needs-Environment`, or `Won't-Fix-With-Reason`.

## Complexity Gate

Every fix must pass the existing `thermo-nuclear-simplification` gate. Fixes should be rejected or revised when they add thin wrappers, move complexity instead of deleting it, duplicate business logic, leak business logic into display components, push files over 1,000 lines without justification, add unnecessary global state, add unnecessary abstractions, create needless dependency chains, make code harder to test, or expand beyond the logged defect.

Record `Complexity review` as `Pass`, `Fail`, or `N/A`.

## Safety Cap

If a story still fails after three full fix/re-test iterations, stop working that story, leave it `Tested-Fail`, record root-cause notes, attempted fixes, evidence, and recommended next action, then continue other stories if safe.

## Relationship To Other Gates

This workflow complements the pre-PR quality ladder and shadow-branch workflow. For large or risky repo rehabilitation, run it on an AIOS shadow branch before promotion. It reuses the Thermo simplification gate for complexity control and should still finish through normal quality-ladder checks before merge.
