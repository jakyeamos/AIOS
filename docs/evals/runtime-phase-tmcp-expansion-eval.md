# Runtime-Phase TMCP Expansion Eval

## Task Summary

- Task ID: runtime-phase-tmcp-expansion
- Date: 2026-06-24
- Evaluator: Codex
- Repository: AIOS

## Original Acceptance Criteria

- TMCP governance is not limited to invocation start.
- Managed/runtime workflow execution can recompile TMCP paths when task requirements change.
- New TMCP packets are persisted with receipt, diff, and intervention evidence.
- The workflow continues against the expanded active packet.

## Context Profile

- Selected profile: `jakye_repo_only`
- Why this profile fits: The implementation used repository source, AGENTS instructions, compiled AIOS context, and local tests. No private second-brain content was required.

## AIOS Condition

- Condition: AIOS-local runtime feature evaluation.

## Starting SHA / Branch

- Starting SHA: `0cf99ffd26d2baf338e63f09662330bc63a10f44`
- Branch: `codex/project-aios-component-scope`

## Files Changed

- `.planning/SUBSYSTEM_EXTRACTION_PLAN.md`
- `PROJECT.md`
- `bin/aios-managed-run.py`
- `services/tmcp_runtime.py`
- `services/workflow_orchestration.py`
- `tests/test_orchestration_runtime.py`
- `tests/test_tmcp_runtime.py`
- `tests/test_workflow_orchestration.py`

## Checks Run

- Lint: `env PYTHONPATH=/Users/jakyeamos/AIOS uv run ruff check ...`
- Typecheck: `env PYTHONPATH=/Users/jakyeamos/AIOS uv run basedpyright ...`
- Tests: `env PYTHONPATH=/Users/jakyeamos/AIOS uv run pytest -q tests/test_tmcp_runtime.py tests/test_workflow_orchestration.py tests/test_orchestration_runtime.py`
- Context: `pnpm context:validate`
- Complexity: `pnpm quality:eval`
- Full suite attempt: `env PYTHONPATH=/Users/jakyeamos/AIOS uv run pytest -q`

## Check Results

- Passed: focused tests `97 passed`; Ruff clean; Basedpyright 0 errors with existing test import warnings; context validation passed; `quality:eval` exited 0.
- Failed: full Python suite had 11 failures unrelated to this change in learning analysis, contract audit expectations, skills harvest CLI output, and workflow experiment temp-repo commits blocked by the local commit quality hook.
- Not run: UI checks, because this change does not touch `aios-ui/`.
- Reason for not-run checks: No frontend or Vercel app surface changed.

## Component-Level Evaluation

- Components inspected: TMCP runtime receipts, workflow execution stage loop, managed runtime artifact syncing, orchestration tests.
- Evidence: new tests assert persisted runtime expansion receipts, packet diffs, intervention events, stage-level expansion records, active packet replacement, and promoted shortcut supersession.
- Risks: Stage-kind to TMCP-phase mapping is intentionally simple and may need registry-driven configuration if workflow kinds diversify.

## End-to-End Evaluation

- Exact path exercised: managed runtime subprocess through `bin/aios-managed-run.py` via `tests/test_orchestration_runtime.py`.
- Inputs used: managed run rows, invocation rows, briefing packet rows, TMCP seed receipts, and workflow registry stages.
- Outputs observed: workflow reports contain `tmcp_packet_expansions`; active packet artifact metadata points to the final active receipt; superseded receipts remain queryable.
- Side effects observed: SQLite TMCP traversal receipts and intervention events are written for phase expansions.

## Complexity/Maintainability Review

- Architecture fit: Expansion logic lives in `services.tmcp_runtime`; workflow execution only decides when stage phase changes require expansion.
- Duplication: Existing packet compile, persist, diff, event, and intervention helpers are reused.
- Naming and typing: New public helper names the requirement-change behavior directly; Basedpyright errors were fixed.
- Future maintenance risk: TMCP phase mapping should move to workflow registry metadata if more stage kinds appear.

## Context Effectiveness

- Context that was necessary: AGENTS workflow contract, TMCP runtime implementation, workflow execution loop, managed runtime integration tests.
- Context that was missing: None blocking.
- Context that was unnecessary or bloated: UI-oriented context from the compiler was not needed for this backend/runtime task.

## Context Portability Notes

- Portable to peer agent: partial.
- Required packet additions: A future TMCP/runtime packet should document stage-kind to phase mapping and expansion lifecycle.
- Private/local dependencies: AIOS SQLite schema and managed runtime artifacts make this AIOS-local for now.

## Regression Risks

- Existing consumers expecting a single managed-run TMCP receipt now need to inspect the active receipt or expansion list.
- Shortcut evidence is no longer necessarily on the final active packet when later phase expansion supersedes it.

## Failure Taxonomy Labels

- full-suite-unrelated-existing-failures
- local-hook-interference
- runtime-contract-change

## Open Questions

- Should workflow registry stages declare their own TMCP phase instead of relying on `_TMCP_STAGE_PHASES`?

## Backfill Items

- Add a future packet or registry field for explicit TMCP phase mapping if a second workflow needs non-default stage-to-phase behavior.

## Final Confidence Level

- Confidence: high
- Reason: The changed runtime path has focused red-green coverage, managed-runtime subprocess coverage, lint/typecheck coverage, context validation, and complexity review evidence. Full-suite failures are outside the touched TMCP/runtime surface.
