# M6 Three-Task Adversarial Review

**Date:** 2026-07-15  
**Reviewer:** fresh read-only GPT-5.6 review  
**Verdict:** **defer** — not promotion-ready

The review consumed the three-task receipts, sidecars, A rollout JSONL,
protected branch diff, exported evidence, durable ledger, prior review, and
protected C browser proof. All six receipt sidecars verified. Task/prompt/
context hashes, protected SHA, worktree heads, and treatment packet identities
matched. No unrelated generated, runtime, database, log, or production-data
leakage was found.

## Findings

- **P1 evidence gate:** the durable ledger has zero `eval_scores` rows, null
  provider score/cost fields, and `promotion_ready=[]`. This is an evidence
  blocker, not an implementation defect.
- **P2 A treatment non-atomic promote:**
  `services/workflow_skill_mutations.py` writes `skills.json` before the SQLite
  candidate update and does not restore the file if that update fails. A
  SQLite trigger that aborts the update reproduces a promoted file with a
  candidate database row. The control implementation has rollback behavior;
  treatment parity is therefore regressed.
- **P2 A report provenance:** the treatment final report called the protected
  start SHA the rollback parent. Git identifies the actual parent as
  `4cd4183f4cb890197507135579a877ac4ade046c`.
- **P2 A UI limit:** UI checks remain blocked by the external
  `aios-ui/node_modules` mount and `EPERM`; this is reported honestly but is
  not a product pass.
- **P2 B transition coverage:** the treatment tests do not assert
  `state_updated_at` or a subsequent transition, leaving the complete
  transition contract under-proven.
- **P3 C runtime coverage:** code maps both `canceled` and `superseded` to
  Review, but the browser fixture exercises `canceled` only.

## Positive checks

- A removes direct TypeScript candidate mutation, validates promote/dismiss
  payloads, and routes through one Python owner.
- B preserves nullable `ShadowCandidate` fields and routes approval through the
  Python owner.
- C preserves Verify → Review → Closeout provenance, lifecycle events, stage
  mapping, and the protected browser proof (`4 passed`).
- A rollout telemetry is receipt-derived without fabricated values:
  control 518,419 ms / 3,317,344 tokens / 37 tool calls / 4 failed commands;
  treatment 467,745 ms / 4,700,740 tokens / 40 tool calls / 4 failed commands.

No P0 or P1 implementation defect was found. Promotion remains blocked by the
P1 evidence gate and the unresolved P2/P3 findings. The next implementation
step is to make A treatment promotion atomic/rollback-safe, then rerun focused
proof and this adversarial review before considering score capture or M6
promotion.

Reviewer artifact:
`/private/tmp/aios-m6-three-task-review-20260715/final.md`
