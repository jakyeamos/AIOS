# Phase 14: Code Quality Gates And Cross-Project Complexity Standards - Context

**Gathered:** 2026-06-23  
**Status:** Ready for execution

<domain>
## Phase Boundary

Phase 14 establishes the Complexity + Simplification Gate as an agent workflow and documentation standard. It creates instruction-layer rules, quality docs, and observation-backed backfill inventories. It does not broadly remediate discovered hotspots and does not replace the existing success-criteria registry or quality-eval script.

</domain>

<decisions>
## Implementation Decisions

### Existing Rule And Ladder Drift

- `config/agent-rules.md` already has Rule 10 for bounded NotebookLM usage. Preserve it and add the Complexity + Simplification Gate as Rule 11.
- `/Users/jakyeamos/.claude/CLAUDE.md` already has Quality Ladder Step 5 for repo truth updates. Preserve it and add the Complexity + Simplification Gate as Step 6.
- Existing Phase 14 plan text that says Rule 10 or Step 5 for the complexity gate is treated as stale numbering, not as permission to overwrite current rules.

### Canonical Vocabulary

- Use `config/success-criteria/registry.json` and `spec/success-criteria/` as the canonical quality vocabulary.
- Reference existing IDs including `complexity-budget`, `architecture-boundary`, `simplicity`, `test-quality`, `agent-claim-verification`, `performance-budget`, `thin-display`, `data-integrity`, `api-contract`, and `supply-chain-review`.
- Do not create a parallel taxonomy for complexity or simplification.

### Standards Ladder

- Phase 14 may document warn-only/reporting eligibility for portable staged-file checks.
- Fail-closed promotion remains deferred until Phase 16 evidence/verifier binding and Phase 22 progressive governance rollout.
- AIOS-local/runtime checks remain local when they require SQLite state, context receipts, success-criteria records, or truth writebacks.

</decisions>

<code_context>
## Existing Surfaces

- `config/agent-rules.md` currently has Rules 1 through 10.
- `AGENTS.md` already contains AIOS context compilation, success criteria, execution-first verification, subsystem governance, eval workflow, runtime sources of truth, and deployment gates.
- `/Users/jakyeamos/.claude/CLAUDE.md` has the user-level quality ladder and project roots. Editing this file is outside the repo and requires elevated filesystem access.
- `.githooks-user/pre-commit` exists and is the portable user-level hook target for the standards-ladder contract.
- `docs/backfill/agent-eval-backfill.md` and `scripts/quality-eval.sh` are existing AIOS quality/backfill surfaces referenced by the phase research.

</code_context>

<specifics>
## Specific Ideas

- Rule 11 should be self-contained enough for an agent to apply without opening the full docs.
- `AGENTS.md` should cross-reference Rule 11 and the future `docs/quality/complexity-simplification-gate.md` document.
- The ladder contract should distinguish `off`, `warn`, `fail-eligible-later`, and `AIOS-local` modes.
- Every hotspot finding should be recorded before fixing, with file, category, severity, confidence, suggested remediation, behavior risk, tests/benchmarks needed, and agent-safe classification.

</specifics>

<deferred>
## Deferred Ideas

- Broad hotspot remediation is deferred to later remediation passes.
- Fail-closed commit-ladder enforcement is deferred until Phase 16 and Phase 22 evidence gates.
- Cross-project backfill docs are later Phase 14 plans and should remain observation-backed rather than speculative.

</deferred>
