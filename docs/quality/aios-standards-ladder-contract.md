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
