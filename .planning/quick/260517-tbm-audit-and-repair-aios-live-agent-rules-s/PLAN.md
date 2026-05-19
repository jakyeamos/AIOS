# Quick Task 260517-tbm: Audit and repair AIOS live agent-rules smoke session runtime path

## Context Receipt

- Loaded `PROJECT.md` through `pnpm context:compile`.
- Loaded agent-harness, observability, testing, prompt-library, workflow approval gate, and context-compiler packets through the compiled receipt.
- Inspected `logs/session_packet_codex-agent-rules-live-check-260516.md`, `logs/hooks.log`, session/runtime rows in `data/aios.db`, and control-plane workflow report artifacts.

## Findings

- `codex-agent-rules-live-check-260516` opened successfully and wrote a session packet.
- Prompt and tool events after the smoke start continued attaching to stale session `9506d49a-acfe-46dd-b864-03df1cb6e0c7`.
- The smoke session remains open with no prompt rows, no closeout, and no runtime link.
- Existing recovery can create missing sessions but does not repair stale `logs/current_session` selection when a valid AIOS session was opened later.

## Plan

1. [x] Add deterministic current-session resolution for hook payloads that can prefer the current open session in the same cwd when the payload is stale.
2. [x] Use that resolver for prompt-submit, post-tool-use, and stop fallback paths.
3. [x] Add a safe repair/backfill command for stale open sessions and the live smoke session.
4. [x] Add focused regression tests for stale pointer repair and closeout.
5. [x] Verify with pytest and an exact hook-path smoke using a temporary DB/log dir.

## Verification

- `uv run pytest tests/test_hook_lifecycle.py tests/test_orchestration_runtime.py -q`
- `uv run ruff check bin/hook_lifecycle.py bin/hook-prompt-submit.py bin/hook-stop.py bin/hook-post-tool-use.py bin/repair-stale-open-sessions.py tests/test_hook_lifecycle.py`
- `python3 -m py_compile bin/hook_lifecycle.py bin/hook-prompt-submit.py bin/hook-stop.py bin/hook-post-tool-use.py bin/repair-stale-open-sessions.py`
- `pnpm context:validate`
- Exact temp hook path: stale prompt-submit and stop payloads reassigned to the current AIOS session and closed that session.
- Live path: `codex-agent-rules-live-check-260516` captured one prompt and closed with success-criteria and standards-health evaluations.
- Backfill: `bin/repair-stale-open-sessions.py --older-than-days 2 --apply` abandoned two inactive, unlinked sessions; follow-up dry run returned zero candidates.
