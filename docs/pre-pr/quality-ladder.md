# Pre-PR Quality Ladder

AIOS Pre-PR review uses correctness gates first, then structural gates. There is no value in abstraction review for code that does not run, but passing tests does not prove the change deserves to merge.

## Order

1. Tests pass.
2. Typecheck passes.
3. Lint passes.
4. Security-sensitive changes pass security review.
5. Data, migration, and API safety checks pass when applicable.
6. UI/display thinness passes when applicable.
7. Thermo-Nuclear Simplification passes.
8. Product acceptance criteria pass.
9. Pre-PR summary is generated.
10. Shadow/eval metrics are recorded when the task is part of an experiment.

## Thermo Placement

Run `thermo_nuclear_simplification` after basic correctness checks and before merge recommendation. It answers a different question from tests:

- Tests: does the behavior still work?
- Thermo: did the implementation preserve or improve structural quality?

## Merge Posture

- `PASS`: merge can proceed if other gates pass.
- `PASS_WITH_WARNINGS`: merge can proceed with recorded warnings or follow-ups.
- `BLOCKED`: do not merge until P0 findings are fixed or explicitly accepted by a governed exception.
- `BACKFILL_ONLY`: adoption or shadow-eval output; not a merge verdict by itself.

Waivers are allowed only when decomposition would exceed the task scope, behavior risk is higher than structural risk, the issue is not made worse, and a follow-up artifact exists.
