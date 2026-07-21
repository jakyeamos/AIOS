You are one side of a frozen live paired benchmark. Work in this clean repository
at the protected start SHA. Do not edit files, use private state, access the
network, or touch production systems. Return a concise evidence-backed report.

Task: Audit whether AIOS's canonical-state and migration-authority contracts are
ready for the first contextual satellite migration in M6.

Acceptance criteria:
1. Identify the current canonical state owner and the proposed satellite
   ownership boundary with file references.
2. State the exact migration gates that are proven, unproven, or blocked.
3. Identify at least three concrete data-integrity, rollback, or authority risks
   and the verification needed for each.
4. Recommend proceed, defer, or revise for the first satellite migration and
   justify it without claiming evidence that is not present.
5. Distinguish checked-in fixture evidence from live or production evidence.

Portable AIOS context packet (the only extra context available to treatment):
- Read `docs/modernization/ADR-002-canonical-state-and-migration-authority.md`
  and `docs/modernization/ADR-005-subsystem-ownership-and-parallel-v2-strategy.md`.
- Read Wayfinder tickets 003, 005, 013, 014 and `.tracker/PROJECT_TRUTH.md`.
- Treat Python-owned SQLite mutation, raw-source immutability, redaction,
  review-gated learning, reversible migration, and fail-closed promotion as
  acceptance constraints. Do not treat the packet as proof that any gate passed.

Use only repository files and ordinary local read-only commands. Do not infer
private memory or hidden runtime state. End with a clearly labeled decision,
evidence gaps, and exact next action.
