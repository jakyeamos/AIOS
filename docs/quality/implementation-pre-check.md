# Implementation Pre-Check

Use this quick checklist during non-trivial implementation, before a commit or a full Complexity + Simplification Gate pass.

1. Am I creating nested loops over data that can grow?
2. Am I repeatedly scanning the same collection (find/filter/map applied multiple times on the same list)?
3. Should this data be indexed by ID/key rather than found by linear scan?
4. Am I adding unnecessary abstraction (helper that obscures rather than clarifies)?
5. Is this function doing too many things?
6. Is this code easy for a future agent or human to modify?
7. Did I add tests around the behavior I changed?
8. Did I preserve existing public contracts (function signatures, return types, exported interfaces)?

## When To Apply

Run this during any non-trivial implementation: new functions, service extensions, data access changes, workflow wiring, or code that may trigger the large-work gate.

## Relationship To The Full Gate

This pre-check is a short in-loop review. Rule 12 in `config/agent-rules.md` remains the mandatory post-large-work gate, and `docs/quality/complexity-simplification-gate.md` is the full intent-specific checklist.

## Pass/Fail

If a question reveals a real problem, address it before completing the current unit of work. Do not defer known problems just because the full gate will run later.

## Criteria Mapping

- Questions 1-3: `complexity-budget`
- Questions 4-6: `simplicity`
- Question 7: `test-quality`
- Question 8: `api-contract`
