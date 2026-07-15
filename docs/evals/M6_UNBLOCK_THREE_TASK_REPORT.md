# M6 Three-Task Unblock Rerun Report

**Date:** 2026-07-15  
**Protected start SHA:** `4d8adbca3b89d6259e252f26aaad0db69a9bf102`  
**Decision:** defer promotion; retain fail-closed gates

## Durable ingestion

The fresh ledger at `/private/tmp/aios-m6-promotion-rerun-ledger-20260715-v6.db`
contains three receipt-backed matched pairs. The exported evidence is
`M6_UNBLOCK_THREE_TASK_EVIDENCE_V4.json`. All pairs start at the protected SHA,
and `eval pair-list --promotion-ready` returns `[]`. The independent review is
recorded as `failed` for each pair because it found unresolved findings.

No provider score or cost values were invented. Every pair remains `defer`
with no score rows.

| Pair | Treatment packet | Treatment packet SHA | Verification evidence |
| --- | --- | --- | --- |
| A — workflow skill-candidate owner | `m6-workflow-skill-owner-v1` | `220285e0e66d572b67ed7ff1eb586d71f5def05555bdc5c0df1172075b5a02f1` | Python owner, CLI, typed adapter, source scan |
| B — shadow-candidate approval owner | `m6-owner-migrations-v1` | `dcb106c9050566272972f90d54105f11be37065911bc1ce1c2a73e164390e60e` | Prior focused owner and UI proof |
| C — Verify → Review → Closeout | `m6-browser-contract-rerun-v1` | `78de4073e69532c6410e352b70466e3d71b8a480de6697d5588a51e009ec5c71` | Protected browser proof: 4 passed |

## A — workflow skill-candidate owner

Fresh matched worktrees are under
`/private/tmp/aios-m6-promotion-rerun-a-20260715-v1`. Receipt sidecars verify
the task hash, prompt hashes, context manifest, protected start SHA, and
treatment packet. Rollback ancestry is recorded explicitly as
`4cd4183f4cb890197507135579a877ac4ade046c`, the actual parent of the protected
start SHA.

- Control: 110 focused/workflow/CLI tests passed; Ruff and diff check passed.
- Treatment: 16 focused owner/workflow tests and 92 CLI regression tests passed;
  Ruff and BasedPyright passed; the workflow router has no direct candidate
  mutation.
- Control rollout: session `019f6719-d8a6-7f53-9729-f7ee2dfcf3ab`,
  3,317,344 total tokens, 37 tool calls, 518,419 ms, 4 failed commands.
- Treatment rollout: session `019f6719-d1d2-7710-a828-1fba50afcce6`,
  4,700,740 total tokens, 40 tool calls, 467,745 ms, 4 failed commands.
- UI lint/typecheck/build/browser checks were blocked when pnpm attempted to
  recreate the external `aios-ui/node_modules` mount and hit `EPERM`.

The treatment final report incorrectly labels the protected start SHA as the
rollback parent. This is recorded as a P2 report-quality mismatch; the durable
ledger carries the actual git parent and the mismatch flag rather than silently
accepting the incorrect wording.

## B and C

B and C are the previously verified receipt-backed rerun pairs. B preserves the
nullable `ShadowCandidate` contract, routes mutation through one Python owner,
and removes direct TypeScript updates. C seeds Verify, Review, and Closeout
state, keeps lifecycle/stage mapping consistent, and passed the protected
focused browser proof:

```text
AIOS_UI_TEST_PORT=3223 pnpm --dir aios-ui test:browser -- m6-verify-review-closeout.spec.ts
4 passed
```

Their earlier adversarial review found no P0/P1 defects; its P2 coverage gap was
fixed before the protected browser proof. The fresh three-task review
re-consumed the durable ledger and found no P0/P1 implementation defect, but it
recorded a P1 evidence gate plus P2/P3 findings: the A treatment promote path
is not rollback-safe on DB failure, the A report uses the wrong rollback-parent
wording, A UI checks remain environment-blocked, B transition timestamp
coverage is incomplete, and C does not browser-exercise the superseded
mapping. See `M6_UNBLOCK_THREE_TASK_ADVERSARIAL_REVIEW.md` for reproduction
details.

## Remaining promotion gates

1. Fix A treatment atomicity/rollback behavior and rerun the affected proof and
   adversarial review.
2. Close the B/C coverage findings or explicitly accept them after evidence.
3. Capture authoritative provider score/cost telemetry; do not fill missing
   values with estimates.
4. Resolve or explicitly accept the A report-quality mismatch and UI proof
   environment limitation.

Until those gates are complete, M6 promotion remains blocked by design.
