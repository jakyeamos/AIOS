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

## Evidence

Backfill records should include:

- File or subsystem.
- Current issue.
- Why it matters.
- Suggested remediation.
- Behavior risk.
- Verification needed.
- Whether the work is agent-safe.

## Shadow Evaluation

In `shadow_eval` mode, record structural delta score, complexity movement, review acceptance, regression rate, speed, and token-efficiency deltas. Do not label a personalized local win as portable unless the run used a portable context profile.
