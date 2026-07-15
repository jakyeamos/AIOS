Act as a fresh, hostile principal-engineer reviewer. Do not edit files, commit,
or change project truth.

Review the M6 post-review remediation against protected start SHA
4d8adbca3b89d6259e252f26aaad0db69a9bf102.

Read:
- docs/evals/M6_UNBLOCK_REMEDIATION_EVIDENCE.md
- docs/evals/M6_UNBLOCK_THREE_TASK_REPORT.md
- docs/evals/M6_UNBLOCK_THREE_TASK_ADVERSARIAL_REVIEW.md
- the original A/B/C receipts and durable v6 ledger
- A treatment worktree /private/tmp/aios-m6-promotion-rerun-a-20260715-v1/a-treatment
- B treatment worktree /private/tmp/aios-m6-promotion-rerun-b-20260715-v3/b-treatment
- C treatment worktree /private/tmp/aios-m6-promotion-rerun-c-20260715/c-treatment

Verify:
1. A promote is transactionally safe: a database update failure cannot leave a
   promoted skills.json, and successful promote still preserves the existing
   response and registry contract.
2. B approval returns the nullable ShadowCandidate contract and records
   state_updated_at for approval and a subsequent state transition.
3. C browser fixture and focused proof exercise a real superseded run and map
   it to Review, while the exact local Next font abort remains the only allowed
   request failure.
4. Remediation tests, type checks, browser proof, file hashes, protected SHA,
   and worktree boundaries are represented honestly. Do not convert an
   environment permission failure into a product pass.
5. Provider score/cost telemetry remains absent and promotion_ready remains
   empty; do not invent scores.

Classify any residual findings P0/P1/P2/P3 with file references and reproduction
steps. Return pass, revise, or defer. Do not make fixes.
