# Backfill Quality Ratchet

AIOS adoption mode must not block every future PR on legacy debt. It should prevent new structural debt while turning existing debt into a ranked remediation queue.

## Thermo Adoption Classes

| Class | Meaning | Action |
| --- | --- | --- |
| hotspot | Current debt has high change risk or recurring failure evidence. | Create a high-priority backfill item. |
| backfill candidate | Debt is real but not currently blocking active work. | Track with owner and suggested remediation. |
| ratchet target | Debt should not get worse in touched paths. | Enforce non-regression during Pre-PR. |
| do-not-touch-yet | Fixing now has unclear value or high behavior risk. | Record rationale and next decision point. |

## Ratchet Rules

- Existing unrelated debt does not block unrelated changes.
- Touched debt must not get worse.
- Hotspot files must improve or remain neutral unless the change is part of a recorded decomposition.
- Waived P1 issues require a follow-up artifact.
- Backfill items must state scope, priority, behavior risk, and tests or characterization checks needed before remediation.

## TDD Test Value Adoption Gate

TDD adoption must not become a test-volume incentive. In adoption/backfill mode,
AIOS evaluates whether a test suite protects behavior and contracts without
adding brittle maintenance load.

For every TDD-heavy repository or test-suite backfill, classify test debt with
the same adoption classes:

| Class | Test-suite meaning | Action |
| --- | --- | --- |
| hotspot | Brittle, duplicated, implementation-coupled, or mock-echo tests block safe change or create recurring false confidence. | Create a high-priority backfill item tied to the affected behavior or contract. |
| backfill candidate | Low-signal tests exist, but they are not currently blocking active work. | Track removal, consolidation, or replacement with owner and risk notes. |
| ratchet target | Touched tests must improve or preserve behavioral signal and must not add duplicate coverage, opaque snapshots, or implementation coupling. | Enforce non-regression during Pre-PR and closeout. |
| do-not-touch-yet | Legacy test intent is unclear and deletion risk is higher than maintenance cost. | Record rationale and require characterization before deletion. |

Gate checks:

- New or changed tests should have failed for the intended reason before the
  implementation, unless they characterize legacy behavior.
- Each retained test should protect user-visible behavior, a public API or
  cross-module contract, a confirmed bug, or meaningful domain branching.
- Tests should assert behavior rather than private implementation shape.
- Duplicate unit, integration, and e2e coverage is acceptable only when each
  layer catches a different failure class.
- Prefer one clear integration or contract test over many brittle unit tests
  when behavior spans modules.
- Snapshots must be reviewed for signal; large opaque snapshots are backfill
  candidates.
- Mocks must not recreate the implementation under test.
- When refactoring removes behavior or duplicates coverage, obsolete tests
  should be deleted or explicitly preserved with rationale.
- Coverage is a floor, not a goal; do not add low-value tests only to raise a
  percentage.

## Evidence

Backfill records should include:

- File or subsystem.
- Current issue.
- Why it matters.
- Suggested remediation.
- Behavior risk.
- Verification needed.
- Whether the work is agent-safe.

Test-value backfill records should also include:

- Behavior or contract the test claims to protect.
- The intended failing reason, or why the test is legacy characterization.
- Redundant layers, mock echoes, snapshots, or implementation-coupled assertions.
- Recommendation: retain, rewrite, consolidate, delete, or characterize first.

## Shadow Evaluation

In `shadow_eval` mode, record structural delta score, complexity movement, review acceptance, regression rate, speed, and token-efficiency deltas. Do not label a personalized local win as portable unless the run used a portable context profile.
