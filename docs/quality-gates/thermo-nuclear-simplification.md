# Thermo-Nuclear Simplification Gate

## Purpose

The Thermo-Nuclear Simplification gate prevents AIOS from accepting working code that makes the repository harder to change. It is stricter than the general Complexity + Simplification gate: it is a structural review and quality ratchet, not a style checklist.

Core rule:

> A change is not done when tests pass. A change is done when behavior is preserved, the implementation is simpler than the obvious alternative, and no avoidable structural debt is introduced.

## Gate Identity

- Gate id: `thermo_nuclear_simplification`
- Success criterion: `thermo-nuclear-simplification`
- Aliases: `/thermo`, `/tn-review`, `/complexity-kill`, `/code-judo-review`, `/pre-pr-thermo`

## Modes

| Mode | Posture | Use |
| --- | --- | --- |
| `planning` | advisory | Challenge a plan before implementation adds wrappers, flags, one-off modules, or wrong-layer logic. |
| `pre_pr` | blocking | Block P0 structural regressions; require explicit waiver for P1 issues. |
| `adoption_scan` | report-only | Rank existing debt as hotspots, backfill candidates, ratchet targets, or do-not-touch-yet. |
| `shadow_eval` | report-only metrics | Compare baseline, AIOS, and gated branches for structural quality and regression risk. |

## Severity

P0 blocks merge:

- Working code makes architecture clearly worse.
- A source file crosses 1,000 lines without structural justification.
- Domain or business logic leaks into UI/display code.
- New modes, flags, nullable states, or special cases spread branching through unrelated flows.
- Thin wrappers add indirection without clarity, safety, reuse, testability, or boundary enforcement.
- Type escapes hide unclear invariants through `any`, `unknown`, casts, optionality churn, or silent fallback logic.
- The change duplicates or bypasses an existing canonical helper or layer.

P1 must be fixed or waived:

- Moderate file-size growth.
- Repeated conditionals.
- Unclear module boundary.
- New abstraction with unclear payoff.
- Avoidable sequential orchestration.

P2 is a warning:

- Minor naming drift.
- Localized duplication.
- Slightly awkward helper placement.
- Test readability issue.

Backfill means pre-existing debt that this diff does not worsen.

## Non-Negotiable Review Rules

1. Delete complexity instead of moving it.
2. Do not allow file sprawl.
3. Reject spaghetti growth.
4. Reject thin wrappers.
5. Keep logic in the canonical layer.
6. Protect type boundaries.
7. Prefer boring, direct code.
8. Treat non-atomic orchestration as a design smell.
9. Preserve behavior.
10. Treat working code as necessary but insufficient.

## Scorecard

Every run should produce:

```txt
Thermo Verdict: PASS | PASS WITH WARNINGS | BLOCKED | BACKFILL ONLY
Structural Delta Score: -5 to +5
Complexity Movement: deleted | reduced | moved | increased
File Sprawl Risk: none | watch | blocker
Boundary Hygiene: clean | questionable | leaked
Abstraction Quality: earned | neutral | thin | harmful
Type Boundary Quality: explicit | loose | cast-heavy | unsafe
Display Thinness: thin | mixed | logic-leaking
Canonical Reuse: reused | duplicated | bypassed
Atomicity / Orchestration: clean | sequential smell | unsafe
Backfill Items Created: N
```

Score meaning:

| Score | Meaning |
| --- | --- |
| `+5` | Behavior preserved and implementation became dramatically simpler. |
| `+3` | Meaningfully cleaner than baseline. |
| `+1` | Slightly cleaner. |
| `0` | Neutral; can pass only without P0/P1 findings. |
| `-1` | Mild structural regression. |
| `-3` | Meaningful maintainability regression; hard block unless explicitly waived by policy. |
| `-5` | Working code that should not merge. |

## Output Template

```md
# Thermo-Nuclear Review

## Verdict
PASS / PASS WITH WARNINGS / BLOCKED / BACKFILL ONLY

## One-sentence judgment
This change [improves / preserves / worsens] the codebase because...

## Blockers
1. [P0/P1] Finding
   - Evidence:
   - Why it matters:
   - Required fix:
   - Better shape:

## Code Judo Opportunities
1. Current shape:
   Better reframing:
   Complexity deleted:
   Behavior preserved by:

## File / Boundary Risks
- Files crossing size limits:
- Logic in wrong layer:
- Thin wrappers:
- Type boundary issues:
- Canonical helper duplication:

## Backfill Items
- Issue:
- Scope:
- Suggested ticket:
- Priority:

## Waivers
- Owner:
- Reason:
- Follow-up:
- Evidence this does not worsen the issue:

## Final Score
Structural Delta Score:
Merge Recommendation:
```

## Blocking Policy

In Pre-PR mode, P0 findings block. P1 findings pass only with a waiver that names an owner, reason, follow-up artifact, and behavior-risk tradeoff. Adoption and shadow-eval modes do not block; they record backfill and comparison evidence.

## Implementation Status

AIOS currently registers this as an allowlisted quality gate and success criterion. The first executable adapter is the commit-quality registry contract check; deeper semantic detectors should be added incrementally without weakening the documented review contract.
