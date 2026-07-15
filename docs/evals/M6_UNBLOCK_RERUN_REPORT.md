# M6 Unblock Rerun Report

**Date:** 2026-07-15
**Protected start SHA:** `4d8adbca3b89d6259e252f26aaad0db69a9bf102`
**Decision:** defer promotion; unblock evidence and implementation blockers

## Durable ingestion

`benchmark/m6-record-unblock-rerun.py` recorded two new receipt-backed eval
pairs in `/private/tmp/aios-m6-promotion-rerun-ledger-20260715-v2.db` and
exported `M6_UNBLOCK_RERUN_EVIDENCE.json`. The ledger contains B owner-migration
and C browser-contract rerun pairs. Promotion-ready remains empty because no
provider score/cost telemetry was invented and independent review is still a
separate gate.

Every pair starts at the protected SHA. Receipt sidecars and the first JSONL
record match; treatment receipts include packet IDs and packet hashes.

## B — shadow-candidate approval owner

- Fresh matched worktrees: `/private/tmp/aios-m6-promotion-rerun-b-20260715-v3`
- Treatment packet: `m6-owner-migrations-v1`
- Treatment packet SHA: `dcb106c9050566272972f90d54105f11be37065911bc1ce1c2a73e164390e60e`
- UI lint, architecture lint, production build, Ruff, BasedPyright, and focused
  Python proof passed in the runs.
- The direct TypeScript update was removed in both implementations and the
  Python owner preserved the null response and existing transition authority.
- Browser/pytest limits remain explicit: local font aborts and unavailable
  Python dependencies affect the disposable run; no failure was hidden.

## C — Verify → Review → Closeout browser contract

- Fresh matched worktrees: `/private/tmp/aios-m6-promotion-rerun-c-20260715`
- Treatment packet: `m6-browser-contract-rerun-v1`
- Treatment packet SHA: `78de4073e69532c6410e352b70466e3d71b8a480de6697d5588a51e009ec5c71`
- The fixture now seeds three runs, three lifecycle events, three structured
  packets, three sessions, one closed-session closeout artifact, and one
  governed review writeback.
- The stage rail maps `canceled` and `superseded` runs to Review, matching the
  displayed stage fact.
- The exact focused proof passed after remediation:

  `AIOS_UI_TEST_PORT=3223 pnpm --dir aios-ui test:browser -- m6-verify-review-closeout.spec.ts`

  Result: 4 tests passed (M2, M3, M6 satellite, and Verify → Review → Closeout).

- Protected branch proof passed the same focused command on port 3223 after the
  explicit displayed-stage assertion was added.
- UI lint, architecture lint, and production build passed. The only browser
  request exception is the exact local Next font abort at
  `/__nextjs_font/*.woff2` with `net::ERR_ABORTED`; other request failures,
  console errors, and unexpected responses remain fatal.

## Remaining promotion gates

- Quantitative provider score/cost telemetry is unavailable, so the rerun ledger
  intentionally omits fabricated scores.
- A fresh adversarial review must consume this durable ledger and the protected
  browser proof before any promotion decision.
- The protected worktree is clean apart from the intentional M6 code, fixture,
  receipt harness, and evidence changes; generated `next-env.d.ts` noise was
  not promoted.

## Adversarial review

The fresh read-only review is recorded in
[`M6_UNBLOCK_RERUN_ADVERSARIAL_REVIEW.md`](M6_UNBLOCK_RERUN_ADVERSARIAL_REVIEW.md).
It found no P0/P1 defects and identified one P2 coverage gap in its review
snapshot. The P2 was repaired immediately afterward with an explicit Stage-fact
assertion and `canceled`/`superseded` Review mapping; the protected 4-test proof
then passed. Promotion remains deferred because the durable ledger still has
pending independent review and no provider score/cost rows.
