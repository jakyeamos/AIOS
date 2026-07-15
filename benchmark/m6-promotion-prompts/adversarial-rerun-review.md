Act as a fresh, hostile principal-engineer reviewer. Do not edit files, commit,
or change project truth.

Review the M6 unblock rerun against the protected start SHA
4d8adbca3b89d6259e252f26aaad0db69a9bf102.

Evidence to inspect:
- B control/treatment worktrees and events under
  /private/tmp/aios-m6-promotion-rerun-b-20260715-v3
- B receipts under that artifact root; verify sidecar digests, protected SHA,
  prompt hashes, task hash, packet hash, and the first pre-run JSONL record.
- C rerun worktrees and events under
  /private/tmp/aios-m6-promotion-rerun-c-20260715
- Final protected branch files under the current repository, especially the
  M6 browser fixture/spec/config and V2OperatorShell stage mapping.
- The previous M6 evidence/review and the M6 promotion ledger.
- `docs/evals/M6_UNBLOCK_RERUN_REPORT.md` and
  `docs/evals/M6_UNBLOCK_RERUN_EVIDENCE.json`, plus the durable ledger at
  `/private/tmp/aios-m6-promotion-rerun-ledger-20260715-v2.db`.
- Protected browser proof command:
  `AIOS_UI_TEST_PORT=3222 pnpm --dir aios-ui test:browser -- m6-verify-review-closeout.spec.ts`

Check:
1. B control/treatment are truly matched and start from the protected SHA;
   treatment packet provenance is receipt-backed and fail-closed.
2. Both B implementations preserve the ShadowCandidate-or-null contract,
   validate payloads, use one Python mutation authority, retain state
   transitions, and delete the direct TypeScript update.
3. C fixtures seed Verify, Review, and Closeout with structured packets,
   lifecycle events, a valid non-null-session closeout artifact, and a narrow
   exact-412 approval path.
4. The Review stage rail maps canceled/superseded runs consistently with the
   Review fact label.
5. Lint, architecture, build, browser discovery, focused browser proof, and
   source scans are represented honestly; known local font abort handling is
   exact and cannot hide other failures.
6. No unrelated generated or production data changes leaked into the branch.

Classify findings P0/P1/P2/P3 with file references and reproduction steps.
Return a concise verdict: pass, revise, or defer, and list any remaining gate
blockers. Treat the post-remediation protected browser proof as current evidence
even if an earlier disposable run was environment-blocked. Do not make fixes.
