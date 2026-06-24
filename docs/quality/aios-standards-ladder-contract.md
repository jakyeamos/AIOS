# AIOS Standards Ladder Contract

## Purpose

This contract defines how AIOS quality standards can appear in the user-level commit quality ladder without turning local runtime assumptions into global fail-closed hooks too early.

Phase 14 may introduce warn-only and reporting surfaces. Fail-closed rollout requires later evidence binding from Phase 16 and progressive governance rollout from Phase 22.

## Canonical Criteria

The source of truth is `config/success-criteria/registry.json` plus `spec/success-criteria/`.

Current quality-gate criteria covered by this contract include:

- `complexity-budget`
- `architecture-boundary`
- `simplicity`
- `code-simplicity`
- `test-quality`
- `testing-trust`
- `agent-claim-verification`
- `performance-budget`
- `thin-display`
- `data-integrity`
- `api-contract`
- `supply-chain-review`
- `security-review`
- `truth-file-consistency`
- `repo-boundary-discipline`
- `git-worktree-cleanliness`

Do not invent a second naming scheme for quality gates. New ladder checks must map back to a registered criterion or explicitly propose a registry addition.

## Enforcement Modes

| Mode | Meaning | Allowed Now |
| --- | --- | --- |
| `off` | The check is documented but does not run. | Yes, for standards without a deterministic implementation. |
| `warn` | The check reports findings but does not block commits. | Yes, for deterministic staged-file or documentation checks. |
| `fail-eligible-later` | The check may become blocking after evidence and governance gates pass. | Yes, as a documented future posture. |
| `AIOS-local` | The check requires AIOS runtime state and must not become a portable global hook. | Yes, for SQLite, context, truth, or success-criteria runtime checks. |

## Eligible For Warn-Only Now

Cheap staged-file checks are eligible when they are deterministic, local, fast, and do not require AIOS runtime state:

- Markdown references to known criterion IDs.
- Agent-rule and AGENTS cross-reference checks.
- Simple pattern checks for known anti-patterns.
- File-scope complexity or size reports that produce findings without claiming semantic completeness.
- Documentation completeness checks for required sections.

Warn-only findings must identify file, rule id, severity, blocking mode, evidence source, and remediation.

## AIOS-Local Only

Checks must remain AIOS-local when they depend on:

- SQLite state under `data/`.
- Context compiler receipts.
- Success-criteria evaluation records.
- Project truth writebacks.
- Local second-brain or private operator context.
- Runtime evidence that cannot be reproduced from staged files.
- Semantic test-value judgments that require knowing the intended behavior,
  failing reason, contract boundary, or duplicate coverage across layers.

These checks may block AIOS-managed workflows, but they must not be promoted into a portable user-level hook as if they were repo-independent.

## Fail-Closed Prerequisites

A check can move from `warn` to `fail` only after all of the following are true:

- The check maps to a registered success criterion.
- The implementation is deterministic on staged files or has a documented AIOS-local scope.
- Phase 16 evidence/verifier gates bind findings to durable command evidence.
- Phase 22 progressive governance approves rollout order, owner, waiver policy, and rollback path.
- Existing backfill findings have an accepted remediation or waiver plan.

## Waiver Contract

Every waiver must include:

- Rule or criterion id.
- Concrete runtime reason.
- Owner.
- Expiration date or backfill reference.
- Evidence showing the waiver is scoped to a known finding.

Unowned, permanent, or generic waivers are invalid.

## Output Contract

Every ladder finding must include:

- File path.
- Rule or criterion id.
- Severity.
- Blocking mode: `off`, `warn`, `fail-eligible-later`, or `AIOS-local`.
- Evidence source.
- Suggested remediation.
- Whether the finding was fixed, deferred, or waived.

## Current Phase 14 Posture

The Complexity + Simplification Gate is mandatory for agents after large work, but commit-ladder enforcement is warn-only/reporting in Phase 14. This preserves visibility while avoiding premature fail-closed behavior before evidence binding and governance rollout are complete.

## Phase 22 Rollout Contract

Phase 22 promotes only deterministic portable checks into the user-level commit
hook. Criteria that need AIOS runtime state, SQLite, context receipts, truth
files, verifier artifacts, or workflow evidence remain AIOS-local.

The global hook may fail only on checks that can run from staged files and
produce an actionable message without reading AIOS-private state. All other
criteria may appear as `warn`, `off`, or `AIOS-local`.

## Coverage Matrix

| Rule id | Source | Check summary | Portability | Evidence | Mode | Waiver format | False-positive risk | Promotion blocker |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `global.security.secret-literal` | `aios/context/standards/security.md`, `security-review` | Detect likely committed secrets. | portable | staged-file | fail | `AIOS-WAIVER security-review owner expiry reason` | Medium; test fixtures can contain tokens. | Keep allowlist narrow and require owner/expiry. |
| `global.maintainability.typescript-any` | `aios/context/standards/maintainability.md`, `code-simplicity` | Flag production TypeScript `any`. | portable | staged-file | warn | `AIOS-WAIVER code-simplicity owner expiry reason` | Medium; generated/vendor files need exclusions. | Backfill false positives across first-class projects. |
| `global.maintainability.oversized-source` | `aios/context/standards/maintainability.md`, `complexity-budget` | Report oversized source files. | portable | staged-file | warn | `AIOS-WAIVER complexity-budget owner expiry reason` | High; size is a proxy, not semantic complexity. | Requires backfill and remediation candidates. |
| `global.testing.weak-test` | `aios/context/standards/testing.md`, `test-quality` | Flag test files with no assertions. | portable | staged-file | warn | `AIOS-WAIVER test-quality owner expiry reason` | Medium; snapshot/smoke tests may be valid. | Requires documented smoke-test waiver format. |
| `global.testing.tdd-test-value` | `aios/context/standards/global.testing.md`, `test-quality`, `testing-trust` | In adoption/backfill mode, classify low-signal, duplicate, implementation-coupled, snapshot-heavy, or mock-echo tests as hotspots, backfill candidates, ratchet targets, or do-not-touch-yet. | AIOS-local | backfill-artifact | AIOS-local | Evaluation metadata accepted tradeoff plus backfill reference | High; test intent and behavior value are semantic. | Requires behavior/contract evidence and reviewed backfill artifacts. |
| `global.release.package-manager` | `aios/context/standards/maintainability.md`, `supply-chain-review` | Block npm/yarn drift in pnpm repos. | portable | staged-file | fail | `AIOS-WAIVER supply-chain-review owner expiry reason` | Low when package manager is configured. | None for pnpm-governed repos. |
| `global.maintainability.handler-before-send` | `aios/context/standards/maintainability.md`, `code-simplicity` | Detect handler-before-send event-loop ordering. | portable | staged-file | warn | Inline `aios-quality: allow handler-before-send` plus reason | Medium; some runtimes require early handler registration. | Needs project backfill and runtime-specific waiver examples. |
| `global.testing.pre-cr` | `test-quality`, `agent-claim-verification` | Require changed-line readiness where `.pre-cr.json` exists. | portable | command-evidence | warn | `AIOS-WAIVER pre-cr owner expiry reason` | Medium; Pre-CR may not be installed. | Tool availability and first-class project backfill. |
| `aios.context.validate` | `truth-file-consistency`, `repo-boundary-discipline` | Validate AIOS context compiler receipts and selected context. | AIOS-local | AIOS-state | AIOS-local | Evaluation metadata accepted tradeoff | Low inside AIOS; invalid outside AIOS. | Requires AIOS repo/runtime state. |
| `aios.criteria.registry` | `spec/success-criteria/index.md` | Validate success criteria registry paths and blocking criteria. | AIOS-local | AIOS-state | AIOS-local | Evaluation metadata accepted tradeoff | Low inside AIOS. | Registry is AIOS-specific. |
| `aios.evidence.fresh` | `agent-claim-verification`, `execution-first-verification` | Bind claims to fresh evidence/verifier artifacts. | AIOS-local | verifier-artifact | AIOS-local | Evaluation metadata accepted tradeoff | Medium; evidence can be absent for valid doc-only work. | Requires Phase 16 evidence/verifier artifacts. |
| `aios.truth.writeback` | `truth-file-consistency` | Require project truth updates after substantive changes. | AIOS-local | AIOS-state | AIOS-local | Evaluation metadata accepted tradeoff | Medium outside managed AIOS workflows. | Requires project truth files and workflow context. |

## Promotion Rules

1. `off` to `warn`: allowed when the check has deterministic output and an
   actionable message.
2. `warn` to `fail`: allowed only after a backfill run records acceptable false
   positives, waivers, and remediation candidates.
3. Evidence-dependent checks may block only inside AIOS-local gates when fresh
   Phase 16 evidence/verifier artifacts are cited.
4. The global user-level hook must not require AIOS SQLite, context receipts, or
   project truth files for repos that have not opted into AIOS-managed
   operation.

## Fail-Closed Message Requirements

Every fail-closed finding must include:

- file
- rule id
- reason
- waiver format
- next command or doc reference

Example:

```text
[FAIL] src/config.ts:3 [global.security.secret-literal]
Possible secret literal. Waive with AIOS-WAIVER security-review <owner> <expiry> <reason>, or move the value to environment configuration.
```
