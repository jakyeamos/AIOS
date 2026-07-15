# M6 Unblock Rerun Adversarial Review

**Date:** 2026-07-15
**Review:** fresh read-only adversarial rerun review
**Verdict:** revise; promotion remains deferred

The review consumed the durable B/C rerun ledger, receipt-backed evidence, the
protected-start SHA, and the protected browser proof. It found no P0 or P1
defects. The review snapshot identified one P2 coverage gap: the fixture used a
canceled Review run but did not also exercise a superseded run, and the browser
spec did not explicitly assert that the displayed Stage fact matched the
active stage rail.

That P2 was repaired immediately after the review snapshot. The stage fact
assertion now runs for every viewport, and the stage mapping covers both
`canceled` and `superseded` as Review. The protected proof then passed:

`AIOS_UI_TEST_PORT=3223 pnpm --dir aios-ui test:browser -- m6-verify-review-closeout.spec.ts`

Result: 4 tests passed. The exact local Next font abort remains the only
allowlisted browser exception; unexpected responses, request failures, and
console errors remain fatal.

The review confirmed that:

- B control/treatment runs start at the protected SHA and carry matching
  receipt sidecars, prompt/context hashes, and treatment packet identity.
- The B implementations remove the direct TypeScript update and route through
  the Python mutation owner while preserving the nullable response contract.
- C seeds Verify, Review, and Closeout lifecycle state, structured packets,
  sessions, a non-null closeout artifact with metadata, and governed writeback.
- The durable ledger remains fail-closed: independent review is pending, score
  rows are absent, and `eval pair-list --promotion-ready` is `[]`.

The review artifact therefore closes the implementation/proof blockers but not
the promotion gate. A clean 3–5-task effectiveness benchmark with provider
score/cost telemetry and completed independent review is still required before
M6 promotion.
