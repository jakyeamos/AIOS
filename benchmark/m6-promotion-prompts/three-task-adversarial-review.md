Act as a fresh, hostile principal-engineer reviewer. Do not edit files, commit,
or change project truth.

Review the M6 three-task unblock rerun against protected start SHA
4d8adbca3b89d6259e252f26aaad0db69a9bf102.

Evidence to inspect:
- A control/treatment worktrees and artifacts under
  /private/tmp/aios-m6-promotion-rerun-a-20260715-v1
- B artifacts under /private/tmp/aios-m6-promotion-rerun-b-20260715-v3
- C artifacts under /private/tmp/aios-m6-promotion-rerun-c-20260715
- Receipts and sidecar digests for all six runs
- Codex rollout telemetry for A:
  /Users/jakyeamos/.codex/sessions/2026/07/15/rollout-2026-07-15T14-46-14-019f6719-d8a6-7f53-9729-f7ee2dfcf3ab.jsonl
  /Users/jakyeamos/.codex/sessions/2026/07/15/rollout-2026-07-15T14-46-13-019f6719-d1d2-7710-a828-1fba50afcce6.jsonl
- docs/evals/M6_UNBLOCK_THREE_TASK_REPORT.md
- docs/evals/M6_UNBLOCK_THREE_TASK_EVIDENCE_V3.json
- durable ledger /private/tmp/aios-m6-promotion-rerun-ledger-20260715-v5.db
- benchmark/m6-record-unblock-rerun.py and the protected branch diff
- the prior M6 adversarial review and protected browser proof

Check:
1. All three pairs are matched, receipt-backed, and start at the protected
   SHA; treatment packet identity and hashes are verified.
2. A preserves promote/dismiss behavior, validates payloads, routes mutation
   through one Python owner, preserves CLI/tRPC contracts, and removes direct
   TypeScript candidate mutation.
3. B preserves the nullable ShadowCandidate contract, state transitions, and
   one Python mutation owner.
4. C preserves Verify → Review → Closeout fixture provenance, lifecycle events,
   stage mapping, exact approval error behavior, and the protected browser proof.
5. Rollout telemetry is parsed without fabricated duration, token, tool-call,
   or failure values. Confirm the A treatment report's rollback-parent wording
   is a P2 mismatch because git identifies 4cd4183f4cb890197507135579a877ac4ade046c
   as the actual parent of the protected start SHA.
6. The external node_modules/EPERM UI limit is represented honestly and does
   not get mistaken for a product pass.
7. No unrelated generated or production data changes leaked into the protected
   branch; promotion_ready remains empty while score/cost telemetry is absent.

Classify findings P0/P1/P2/P3 with file references and reproduction steps.
Return a concise verdict: pass, revise, or defer. Treat missing provider score
rows and the unresolved A report/UI limits as promotion gates even if no P0/P1
implementation defects remain. Do not make fixes.
