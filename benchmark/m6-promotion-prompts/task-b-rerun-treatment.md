You are one side of a fresh matched implementation benchmark. Work only in this clean repository at the protected start SHA. Do not use private state, network, production systems, or credentials.

Task: Route eval.approveShadowCandidate through the Python owner. Preserve the existing ShadowCandidate-or-null response contract, fail safely for missing candidates, delete the direct TypeScript update, and retain existing shadow-automation state-transition semantics.

Acceptance criteria:
1. Validated Python service/CLI and typed server adapter own the mutation.
2. Success, missing candidate, invalid payload, and state-transition tests pass.
3. UI lint/typecheck, architecture, build, and relevant browser checks pass or are explicitly recorded as environment-blocked.
4. Source scan proves eval-data/router no longer owns the update.
5. Report exact commands, actual protected parent SHA, and remaining risks.

Treatment-only receipt:
- Read the JSON file at the path in `AIOS_BENCHMARK_RECEIPT` before implementation.
- Include its exact `packet_sha256`, protected SHA, prompt hash, and receipt path in the final report.
- Treat the receipt as context provenance, not implementation proof.

Portable AIOS context packet (treatment-only):
- Read docs/modernization/ADR-002-canonical-state-and-migration-authority.md.
- Read docs/modernization/ADR-005-subsystem-ownership-and-parallel-v2-strategy.md.
- Read docs/modernization/PROGRESS.md, .tracker/PROJECT_TRUTH.md, and resolved owner-migration tickets 019 through 022.
- Treat one Python mutation authority, reversible migration, no dual writes, and deletion proof as hard constraints.

Do not broaden scope into shadow pipeline execution or benchmark redesign. Do not commit generated files or alter project truth outside the bounded task.

Benchmark receipt: the harness will provide `AIOS_BENCHMARK_RECEIPT` and
`AIOS_BENCHMARK_RECEIPT_SHA256`. Before any edit, verify that receipt's digest
and print its receipt id, protected SHA, task hash, prompt hash, packet id, and
context manifest hash. The rollback parent must be exactly
`4d8adbca3b89d6259e252f26aaad0db69a9bf102`.
