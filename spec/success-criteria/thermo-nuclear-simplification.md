# Thermo-Nuclear Simplification Gate

## Purpose

This criterion blocks changes that technically work but make AIOS structurally worse. Passing tests is necessary evidence, not completion.

## Applies When

- Planning implementation work that could add abstractions, flags, wrappers, or new module boundaries.
- Reviewing a diff before PR.
- Running adoption/backfill scans against existing repositories.
- Comparing AIOS shadow branches for quality, speed, token efficiency, and regression rate.

## Required Judgment

The reviewer must decide whether the diff deletes, reduces, moves, or increases complexity. A change passes only when behavior is preserved and no avoidable structural debt is introduced in touched paths.

## Blocking Findings

Block completion for any P0 issue:

- A working change makes architecture clearly worse.
- A source file crosses 1,000 lines without structural justification.
- Business or domain logic leaks into UI/display code.
- New modes, flags, nullable states, or special cases create branching complexity across unrelated flows.
- Wrappers, adapters, or helpers add indirection without clarity, safety, reuse, testability, or boundary enforcement.
- `any`, `unknown`, casts, optionality churn, or silent fallbacks hide unclear invariants.
- The change duplicates an existing canonical helper or bypasses a canonical layer.

P1 issues require an explicit waiver with owner, reason, follow-up, and proof that the change does not worsen the issue.

## Modes

- `planning`: advisory lens before implementation; prefer plans that delete concepts and reuse canonical abstractions.
- `pre_pr`: blocking review for touched paths; P0 blocks, P1 needs waiver.
- `adoption_scan`: report-only backfill mode; classify legacy debt as hotspot, backfill candidate, ratchet target, or do-not-touch-yet.
- `shadow_eval`: report-only metrics mode for branch comparison.

## Output Contract

Every run must emit:

- Verdict: `PASS`, `PASS_WITH_WARNINGS`, `BLOCKED`, or `BACKFILL_ONLY`.
- One-sentence judgment.
- Blockers with evidence, impact, required fix, and better shape.
- Code-judo opportunities that identify complexity deleted and behavior-preservation evidence.
- File and boundary risks.
- Backfill items.
- Waivers.
- Final structural delta score from `-5` to `+5`.

## Acceptance Criteria

- Pre-PR mode blocks P0 structural regressions in touched paths.
- Existing unrelated debt is recorded as backfill and does not block unrelated work.
- Touched hotspot files do not get materially worse unless the change is part of a recorded decomposition.
- Waived P1 issues create a follow-up artifact.
- The review distinguishes complexity deletion from complexity movement.
- Output is available as structured Markdown and machine-readable JSON when implemented as an executable gate.
