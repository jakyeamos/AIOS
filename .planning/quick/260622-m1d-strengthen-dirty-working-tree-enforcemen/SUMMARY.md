# Summary

Strengthened AIOS dirty working tree enforcement at session close.

## Changed

- Added blocking success criterion `git-worktree-cleanliness`.
- Added `spec/success-criteria/git-worktree-cleanliness.md` and indexed it.
- Updated `bin/hook-stop.py` to capture `git status --porcelain` for the active repo and pass entries into success-criteria evaluation.
- Updated `services/success_criteria.py` to emit blocker findings when tracked or untracked changes remain at session close.
- Added focused evaluator and stop-hook tests.
- Updated `PROJECT.md` and `.planning/STATE.md` with the new enforcement behavior.

## Verification

- `uv run pytest -q tests/test_success_criteria.py tests/test_hook_stop.py`
- `uv run ruff check services/success_criteria.py bin/hook-stop.py tests/test_success_criteria.py tests/test_hook_stop.py`
- `uv run ruff format --check services/success_criteria.py bin/hook-stop.py tests/test_success_criteria.py tests/test_hook_stop.py`
- `uv run python -m json.tool config/success-criteria/registry.json`
- `pnpm context:validate`
