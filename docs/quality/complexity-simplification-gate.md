# Complexity + Simplification Gate

## Why This Gate Exists

Complexity and simplification are standard quality gates, not optional cleanup. Algorithmic complexity compounds quickly, and unclear code makes future agents and humans more likely to misread, duplicate, or patch the wrong behavior.

This document is intent-specific. Always-loaded agent files should only carry the trigger and pointer to this checklist.

## When The Gate Runs

Run this gate after work completes and before it is considered done when any large-work trigger applies:

1. Changes touch 5 or more files.
2. Changes add or remove 300 or more lines.
3. A new feature is implemented.
4. A change crosses package or layer boundaries.
5. A database, schema, query, or durable data path changes.
6. Data pipeline, analytics, scoring, or model logic changes.
7. UI state or meaningful rendering logic changes.
8. Agent, workflow, or orchestration behavior changes.
9. A performance-sensitive path changes.
10. Code is likely to be reused as infrastructure.

Rule 12 in `config/agent-rules.md` is the always-loaded trigger. This file is the full checklist.

## What Agents Must Check

Gate A: complexity/performance review:

- Nested loops over growing collections.
- Repeated `find`, `filter`, or `map` scans inside loops.
- Repeated object construction in hot paths.
- Sort-inside-loop patterns.
- Avoidable O(n^2) joins that should use maps, sets, or indexes.
- N+1 database or API calls.
- Render recomputation, missing memoization, unstable props, or expensive client-side derived data.
- Unbounded loops, repeated parsing/serialization, or unnecessary deep cloning.
- Arrays that should be `Map` or `Set`.

Gate B: simplification/maintainability review:

- Reduce nesting and branch complexity.
- Remove duplicated logic.
- Extract helpers only when clarity improves.
- Improve names where intent is unclear.
- Consolidate scattered logic into the appropriate module.
- Delete dead code and unnecessary abstractions.
- Prefer direct code over clever code.
- Preserve behavior and public APIs unless explicitly approved.
- Follow local conventions and add or update tests when simplifying logic.

Gate C: verification:

- Run relevant tests, lint, typecheck, format, build, or runtime checks.
- Document concrete limitations for commands that cannot run.
- Keep verification scoped to the changed surface unless the change affects shared behavior.

## How To Run The Gate

1. Start with `docs/quality/implementation-pre-check.md` if you are still coding.
2. Walk Gate A and Gate B for each changed file or subsystem.
3. Use `pnpm quality:eval` when available; it calls `scripts/quality-eval.sh` for file-level size, dead-code, and import-violation metrics.
4. Use `docs/quality/complexity-checklist.md` for the algorithmic pattern checklist once Plan 14-04 creates it.
5. Record every real finding before fixing.

## How To Write Backfill Findings

Use this template:

```markdown
### Hotspot: <short name>
- File(s):
- Category: complexity | simplification | test gap | architecture | render performance | query/data access
- Severity: low | medium | high
- Confidence: low | medium | high
- Current issue:
- Why it matters:
- Suggested remediation:
- Behavior risk:
- Tests/benchmarks needed:
- Agent-safe?: yes / no / partial
```

Severity reflects likely impact. Confidence reflects evidence quality, not how serious the issue would be if true.

## Fix Now Vs. Defer

Fix immediately only when all of these are true:

- The fix is under 5 lines.
- The fix carries no behavior risk.
- The fix requires no test changes.

Defer everything else to a dedicated remediation pass. A recorded deferred finding is evidence that the gate ran honestly; it is not a failure by itself.

## Commit Ladder Integration

This gate follows `docs/quality/aios-standards-ladder-contract.md`:

- Phase 14: portable checks are warn-only/reporting.
- Phase 16: AIOS-managed repositories may opt into evidence-backed blocking checks.
- Phase 22: eligible AIOS standards may be promoted to fail-closed through progressive governance.
- Checks requiring SQLite state, context receipts, success-criteria evaluation records, or project truth writebacks stay AIOS-local until portability is proven.

## Connection To AIOS Quality Standards

Use `spec/success-criteria/index.md` as the canonical quality-mode and criterion index. It defines diff-scoped Pre-PR gate mode, Adoption/backfill mode, and the criterion IDs this gate maps to.

For strict Pre-PR structural review, use `docs/quality-gates/thermo-nuclear-simplification.md`. The Complexity + Simplification gate is the general post-work checklist; the Thermo-Nuclear gate is the named blocking ratchet for working-but-messy code.

Primary criteria:

- `complexity-budget`
- `simplicity`
- `thermo-nuclear-simplification`
- `code-simplicity`
- `test-quality`
- `architecture-boundary`
- `performance-budget`
- `thin-display`
- `data-integrity`
- `api-contract`
- `supply-chain-review`
- `agent-claim-verification`

The user-level Quality Ladder in `../.claude/CLAUDE.md` lists the Complexity + Simplification Gate as Step 6.

## Definition Of Done

The gate is complete when:

- Every relevant Gate A and Gate B item was considered for changed files.
- All findings are recorded in a backfill doc, inline review comment, or task artifact.
- Each finding has a fix-now, defer, or waiver decision.
- Relevant verification commands ran, or concrete limitations were documented.
- Commit-ladder posture is recorded as `off`, `warn`, `fail-eligible-later`, or `AIOS-local`.
