# Session Effectiveness Attribution Debug

## Symptoms
- Recent `logs/session-effectiveness/*.json` receipts show project `.claude`.
- The same receipts have `run_id: null` even when hook closeout resolves a governed run.

## Evidence
- `session_effectiveness_receipts` mirrors `sessions.project_id` and `sessions.run_id`.
- `hook-session-start.py` creates the session project from payload `cwd`.
- `hook-stop.py` resolves `linked_run_id` but did not persist that linkage to `sessions` before writing the effectiveness receipt.

## Hypothesis
The bug has two sources:
- Agent configuration directories such as `/Users/jakyeamos/.claude` are being accepted as project workspaces when the hook runtime is actually executing inside the AIOS repository.
- Stop-time linkage remains local to `hook-stop.py`, so downstream receipt generation sees an empty `sessions.run_id`.

## Fix Plan
- Resolve hook project cwd away from agent config directories when the process cwd points at a registered project.
- Persist resolved run/invocation linkage onto `sessions` before session effectiveness is recorded.
- Add regression coverage for both cases.

## Follow-up Symptom
- Managed session-effectiveness receipts later linked to the correct `AIOS` project and governed run, but still reported `prompt_count: 0`.
- The blocker was `No prompts were captured for the session.`

## Root Cause
- `bin/aios-managed-run.py` fired `SessionStart` and `Stop` hooks for synthesized managed sessions, but never fired `hook-prompt-submit.py` for the governed run objective.
- `hook-stop.py` and `services/session_effectiveness.py` correctly count rows in `prompts_used`; the missing prompt row was upstream of closeout.

## Fix
- `bin/aios-managed-run.py` now emits `hook-prompt-submit.py` after managed session start using the explicit session, run, invocation, backend, cwd, and objective payload.
- The managed path reuses existing prompt classification, reusable-candidate detection, retrieval metadata, and `prompts_used` persistence.

## Verification
- `uv run pytest -q tests/test_orchestration_runtime.py::test_managed_runtime_completes_via_explicit_handshake tests/test_session_effectiveness.py tests/test_hook_prompt_submit.py tests/test_hook_lifecycle.py::test_prompt_submit_recovers_missing_session_before_logging_prompt tests/test_hook_lifecycle.py::test_prompt_submit_reassigns_stale_payload_to_current_session` passed with 11 tests.
- `uv run ruff check bin/aios-managed-run.py tests/test_orchestration_runtime.py` passed.
- `pnpm context:validate` passed.
- Real DB verification against `/Users/jakyeamos/AIOS/data/aios.db` created `run-managed-prompt-capture-260604202353` / `invoke-managed-prompt-capture-260604202353`; session `managed-invoke-managed-prompt-capture-260604202353` recorded one `prompts_used` row and receipt `logs/session-effectiveness/managed-invoke-managed-prompt-capture-260604202353.json` reports `prompt_count: 1` with no blockers.

## Residual Observation
- `tests/test_orchestration_runtime.py::test_managed_runtime_keeps_failed_workflow_report` currently returns success instead of the expected failed workflow in this dirty worktree. This appears tied to existing workflow-runtime changes, not managed prompt capture.
