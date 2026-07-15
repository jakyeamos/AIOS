# M6 Post-Remediation Adversarial Review

**Date:** 2026-07-15  
**Protected start SHA:** `4d8adbca3b89d6259e252f26aaad0db69a9bf102`  
**Decision:** defer promotion; retain fail-closed gates

The fresh read-only review was run after the A/B/C remediation pass with
`gpt-5.6-luna` at high reasoning effort. Its raw event stream and final verdict
are retained at `/private/tmp/aios-m6-remediation-review-20260715-v4/`.

## Verified remediation

- A updates SQLite before the registry replacement, serializes concurrent
  promotions with a same-registry lock, journals pre/post registry bytes, and
  has rollback plus pre- and post-commit recovery tests. The focused suite is
  `111 passed`; Ruff and BasedPyright pass.
- B preserves the nullable `ShadowCandidate` contract and proves timestamps for
  approval and the subsequent `SNAPSHOT_CREATED` transition. The focused suite
  is `10 passed`; Ruff passes and BasedPyright has only the disposable-environment
  `pytest` import-resolution warning.
- C seeds and browser-exercises a persisted `superseded` run, asserts its status
  and `Review` mapping, and logs the exact observed request/response failure
  sets. TypeScript passes; the focused browser proof is `1 passed (24.0s)` with
  the raw receipt at `/private/tmp/aios-m6-remediation-browser-20260715/c-browser.log`.

## Residual gates

1. **P1 — Provider telemetry:** the v6 ledger still has three deferred pairs,
   zero `eval_scores` rows, null score/cost telemetry, and
   `promotion_ready=[]`. No score may be invented; promotion remains blocked.
2. **P2 — Immutable treatment provenance:** the A treatment final artifact
   incorrectly labels the protected start SHA as its rollback parent. The
   actual Git parent is `4cd4183f4cb890197507135579a877ac4ade046c`; the durable
   report now records both values separately.
3. **P2 — A UI proof:** UI checks remain environment-blocked by the external
   `node_modules` mount returning `EPERM`. This is not counted as a product pass.
4. **P3 — Disposable boundary:** the A treatment has an untracked `.venv`; it
   is environmental and outside the protected branch, but remains classified.

The reviewer found no P0 findings and no new product defect requiring a change
on the protected branch. M6 must not be promoted until authoritative provider
score/cost telemetry exists and the remaining evidence gates are either closed
or explicitly accepted.
