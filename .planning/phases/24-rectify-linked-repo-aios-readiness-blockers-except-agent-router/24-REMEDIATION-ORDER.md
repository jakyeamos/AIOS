# Phase 24 Remediation Order By Ease

Date: 2026-06-24

Purpose: order the 20 in-scope linked repositories by likely ease of rectification. `ci` is excluded from the ease count because local CI replacement proof is a dependent final gate: it should pass only after the repo's other required gates pass.

Current setup state: every required gate has a configured runnable command. Remaining blockers are failing, blocked, stale, or not-yet-rerun evidence, not missing AIOS setup.

## Recommended Order

| Order | Repository | Non-CI blockers | Why this order |
| ---: | --- | --- | --- |
| 1 | `portfolio` | `pre_cr` | Single non-CI blocker; likely fastest proof refresh. |
| 2 | `pre-cr-suite-lsp` | `architecture`, `dependency_security` | Two bounded checks; architecture is structural and dependency security is likely audit output. |
| 3 | `claude-improvement-lab` | `dependency_security`, `pre_cr` | Two blockers with no app build/runtime surface in the current report. |
| 4 | `R-Project` | `lint`, `pre_cr` | Two blockers; lint is now a parse-style R script check. |
| 5 | `csds391-s26-6` | `lint`, `pre_cr` | Two blockers; lint is a lightweight Java source presence/read check. |
| 6 | `BBDSE` | `pre_cr`, `validation` | Two aggregate/container blockers, but delegated child checks may fan out. |
| 7 | `career-ops` | `pre_cr`, `validation` | Two blockers, both local workflow/content validation style. |
| 8 | `eslint-plugin-anti-slop` | `lint`, `typecheck`, `architecture` | Three lightweight JS/package structure checks; no dependency blocker currently listed. |
| 9 | `tm` | `architecture`, `dependency_security`, `pre_cr` | Three blockers; likely bounded if dependency audit is cleanable. |
| 10 | `LIS` | `lint`, `test`, `dependency_security` | Three blockers; real Python lint/test surface may require code fixes. |
| 11 | `Terrace` | `test`, `architecture`, `dependency_security`, `pre_cr` | Four blockers; developer-tool tests and audit may need repo changes. |
| 12 | `dispatches-from-cyberspace` | `typecheck`, `architecture`, `dependency_security`, `pre_cr` | Four blockers; typecheck can expose real app/package drift. |
| 13 | `Bballedu` | `architecture`, `dependency_security`, `e2e_smoke`, `pre_cr` | Four blockers; e2e smoke makes this less trivial. |
| 14 | `Dsci-proj` | `lint`, `test`, `dependency_security`, `pre_cr` | Four blockers across Python pipeline and dashboard dependency checks. |
| 15 | `Fantasy` | `lint`, `test`, `dependency_security`, `validation` | Four blockers across backend and frontend aggregate commands. |
| 16 | `Vaults` | `architecture`, `secret_scan`, `pre_cr`, `validation` | Four blockers, but content validation and secret scan may require manual review of vault material. |
| 17 | `aios` | `install`, `test`, `architecture`, `pre_cr` | Four blockers in the control-plane repo; higher blast radius than linked apps. |
| 18 | `amos-saas` | `lint`, `typecheck`, `build`, `architecture`, `dependency_security`, `pre_cr` | Six production-app blockers including build/typecheck. |
| 19 | `soundscape-app` | `lint`, `typecheck`, `test`, `secret_scan`, `dependency_security`, `e2e_smoke`, `pre_cr` | Seven blockers in a large production app with smoke/security gates. |
| 20 | `remodelvision` | `lint`, `typecheck`, `test`, `build`, `architecture`, `secret_scan`, `dependency_security`, `e2e_smoke`, `pre_cr` | Nine blockers; largest remaining gate surface. |

## Execution Rule

For each repo:

1. Run and fix the listed non-`ci` gates first.
2. Re-run `python3 scripts/linked-repo-quality-runner.py --project <repo> --gate <gate>` after each fix to record fresh evidence.
3. Run `python3 scripts/linked-repo-quality-runner.py --project <repo> --gate ci` only after all non-`ci` required gates pass.
4. Recompute the portfolio report with `python3 scripts/linked-repo-quality-runner.py --report`.

## Notes

- `video-pipeline`, `manga-sync`, and `agent-router` remain excluded from this remediation order.
- This is an ease order, not a business-priority order.
- If two repos have the same blocker count, the repo with lighter-weight structural checks is listed first.
