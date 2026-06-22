# Quick Task 260622: Commit Hook Quality Ladder

## Result

Added a versioned AIOS pre-commit quality ladder:

- `.githooks/pre-commit` runs `python3 bin/aios-quality-ladder.py`
- `services.commit_quality_ladder` validates global standards inventory, standards-health registry coverage, context standards, success-criteria registry coverage, AIOS quality-pipeline gate coverage, and staged confident-code event-loop ordering
- the confident-code check blocks staged JavaScript/TypeScript message handlers registered before `postMessage()` unless the code documents a real runtime reason with `aios-quality: allow handler-before-send`
- focused tests cover the handler-before-send blocker, waiver path, standards inventory failure, standards-health registry failure, and success-criteria registry failure

## Verification

- Passed: `uv run pytest tests/test_commit_quality_ladder.py -q`
- Passed: `python3 bin/aios-quality-ladder.py`
- Passed: `pnpm context:validate`
- Passed: `uv run ruff check services/commit_quality_ladder.py bin/aios-quality-ladder.py tests/test_commit_quality_ladder.py`
