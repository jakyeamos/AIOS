# Native Workflow Command Contracts

Date: 2026-06-23

## Scope

These contracts define the Phase 19 native workflow command pack before implementation. They cover command names, input and output shape, safety class, write behavior, second-brain behavior, reviewer/sub-agent representation, validation gates, logging metadata, rollback expectations, and implementation order.

## Safety Classes

- `read_only`: inspects files, diffs, metadata, or context and writes nothing.
- `artifact_write`: may write an explicit report or handoff artifact, but does not modify source code.
- `guarded_modify`: may modify source code only after explicit confirmation, scoped plan, checks, and rollback instructions.
- `sandbox_write`: writes only under explicit prototype/sandbox paths.
- `shadow_branch_only`: broad or behavior-risk changes must run in an isolated branch/worktree before promotion.

## Common Logging Metadata

Every command record should eventually include:

- `command_id`
- `invoked_as`
- `safety_class`
- `input_scope`
- `repo_root`
- `second_brain_mode`
- `subagent_or_lane_mode`
- `files_inspected`
- `files_written`
- `checks_run`
- `model_used`
- `started_at`
- `completed_at`
- `outcome`
- `artifact_paths`

## Command Contracts

### `aios zoom-out`

- Safety class: `read_only`
- Input schema: `target`, optional `depth`, optional `format=json|markdown`
- Output schema: purpose, system position, inbound dependencies, outbound dependencies, sibling modules, conventions, domain vocabulary, risks, and next context to inspect
- Write behavior: none
- Second-brain usage: disabled by default; optional labeled context later
- Sub-agent/reviewer lanes: none in MVP
- Validation gates: target exists; output includes every required section
- Rollback: not applicable

### `aios handoff`

- Safety class: `artifact_write`
- Input schema: objective, optional target project, optional output path, optional include git status, optional include checks
- Output schema: goal, current state, branch/workspace status, files touched, decisions, tests run, failed approaches, blockers, references, and next actions
- Write behavior: preview by default; explicit output path required for file write
- Second-brain usage: disabled by default; may reference approved local context when explicitly requested
- Sub-agent/reviewer lanes: suggested next-agent skill list, not active delegation
- Validation gates: no secrets; branch status captured when available; artifact path under allowed workspace or planning directory
- Rollback: delete generated artifact or mark superseded

### `aios review squad`

- Safety class: `read_only`
- Input schema: scope type `diff|files|branch`, target refs/files, optional lanes, optional strictness
- Output schema: findings grouped by severity, lane, file, line when available, issue, evidence, recommended fix, confidence, and non-issues checked
- Write behavior: none
- Second-brain usage: disabled by default; repo-local evidence first
- Reviewer lanes: security, correctness, testing, architecture, maintainability, project alignment
- Validation gates: findings must separate confirmed issues from speculation; empty result must list non-issues checked
- Rollback: not applicable

### `aios audit security`

- Safety class: `read_only`
- Input schema: mode `strict|practical`, scope type `diff|files|branch`, target refs/files
- Output schema: contextual findings, severity, affected files, exploit or failure scenario, recommended fix, confidence, non-issues checked, and verification suggestions
- Write behavior: none
- Second-brain usage: disabled by default; repo-local security standards first
- Reviewer lanes: security only, with strict/practical mode
- Validation gates: must include non-issues checked and confidence for each finding
- Rollback: not applicable

### `aios cleanup de-slopify`

- Safety class: `guarded_modify`
- Input schema: scope, cleanup goals, max risk, apply flag, checks to run
- Output schema: cleanup plan, proposed changes, applied changes, skipped risky changes, checks run, rollback instructions
- Write behavior: plan-only by default; `--apply` plus confirmation required for modifications
- Second-brain usage: disabled by default
- Sub-agent/reviewer lanes: maintainability and test-quality lanes
- Validation gates: behavior/public API preservation, scoped diff, checks before/after, no broad rewrites
- Rollback: reverse patch or commit revert instructions

### `aios prototype`

- Safety class: `sandbox_write`
- Input schema: question, prototype type, sandbox path, cleanup mode
- Output schema: created files, run command, answer learned, limitations, cleanup or promotion guidance
- Write behavior: writes only to explicit prototype/sandbox locations
- Second-brain usage: disabled by default
- Sub-agent/reviewer lanes: none in MVP
- Validation gates: refuse production paths unless explicitly overridden by future governed workflow
- Rollback: delete sandbox directory or leave artifact marked disposable

## Deferred Commands

- `codebase-rehab`: workflow candidate, not MVP command.
- `codebase-sweep`: deferred and not default. Any future version must be read-only by default and shadow-branch-only before broad changes.

## Implementation Order

1. `aios zoom-out`
2. `aios handoff`
3. `aios review squad`
4. `aios audit security`
5. `aios cleanup de-slopify`
6. `aios prototype`

This order preserves the read-only core first and delays modifying commands until safety/logging behavior exists.
