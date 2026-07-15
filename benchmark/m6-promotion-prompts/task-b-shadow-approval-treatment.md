You are one side of a frozen live paired benchmark. Work in this clean repository
at the protected start SHA. You may edit only this worktree; do not use private
state, network, production systems, or credentials. Implement and verify the
following bounded task, then return a concise evidence-backed report.

Task: Route eval.approveShadowCandidate through the Python owner. Preserve the
existing ShadowCandidate-or-null response contract, fail safely for missing
candidates, delete the direct TypeScript update, and retain the existing
shadow-automation state transition semantics.

Acceptance criteria:
1. Validated Python service/CLI and typed server adapter own the mutation.
2. Success, missing candidate, invalid payload, and state-transition tests pass.
3. UI lint/typecheck, architecture, build, and relevant browser checks pass.
4. Source scan proves eval-data/router no longer owns the update.
5. Report exact commands, rollback parent SHA, and remaining risks.

Portable AIOS context packet (treatment-only):
- Read docs/modernization/ADR-002-canonical-state-and-migration-authority.md.
- Read docs/modernization/ADR-005-subsystem-ownership-and-parallel-v2-strategy.md.
- Read docs/modernization/PROGRESS.md, .tracker/PROJECT_TRUTH.md, and the
  resolved owner-migration tickets 019 through 022.
- Treat one Python mutation authority, reversible migration, no dual writes,
  and deletion proof as hard constraints. The packet is context, not proof.

Do not broaden scope into shadow pipeline execution or benchmark redesign.
