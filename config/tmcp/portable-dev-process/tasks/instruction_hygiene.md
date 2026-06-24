# Task: Instruction Hygiene

Task ID: `@task:instruction_hygiene`

Use when the request involves creating, revising, auditing, consolidating,
shortening, or evaluating agent-facing instructions.

## Load

- `@module:instruction_hygiene`
- `@module:diff_review`
- `@module:quality_gate`

## Procedure

1. Discover editable instruction surfaces and generated or external exclusions.
2. Build an inventory with scope, affected agents, provenance, canonical source,
   and validation hooks.
3. Detect candidate no-op, vague, duplicated, obsolete, or conflicting clauses.
4. Score each candidate for behavioral specificity, redundancy, and removal
   risk.
5. Prove the disposition through static evidence or representative ablation.
6. Apply removals, rewrites, or consolidations only after evidence is recorded.
7. Update routing, provenance, dependency, conflict, and validation records.
8. Run the advisory no-op scan plus relevant prompt, skill, routing, and context
   checks.

## Output

Return:

- inspected and skipped surfaces
- candidates and dispositions
- removed, rewritten, consolidated, retained, and unverified clauses
- TMCP artifacts changed
- validation commands and observed results
- before/after size measurements
- unresolved decisions
