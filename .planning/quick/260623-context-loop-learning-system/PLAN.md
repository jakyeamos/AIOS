# Quick Task: Context Loop Learning System

## Scope

Implement a minimal AIOS outer/inner loop primitive for context-aware drafting and approval-gated learning.

## Tasks

1. Add audit and context-loop contract artifacts under `aios/context-loops/`.
2. Add `services/context_loops.py` with inner-loop runs, review events, learning candidates, approval/application, email draft pilot, and metrics.
3. Wire `python bin/aios.py context-loops ...` commands and focused tests.

## Verification

- `uv run pytest tests/test_context_loops.py`
- focused CLI smoke with `python bin/aios.py context-loops ... --json`
- `pnpm context:validate`

## Notes

`gsd-sdk` was unavailable in this runtime, so this directory records the required quick-task plan manually.
