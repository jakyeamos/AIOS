# Quick Task 260622: User-Level Commit Quality Gate

## Result

Added a portable user-level commit quality gate for repositories outside AIOS:

- `.githooks-user/pre-commit` invokes `bin/user-commit-quality-gate.py`
- the gate blocks staged merge conflict markers, likely secret literals, npm/yarn package-manager drift, production TypeScript `any`, oversized source files, weak Python tests without assertions, and JavaScript/TypeScript message handlers registered before `postMessage()` without an explicit runtime-reason waiver
- source commits now require `.pre-cr.json` and a `pre-cr` CLI on PATH, then run `pre-cr run --json --workspace <repo>` so the global hook bridges into Pre-CR changed-line readiness
- global Git `core.hooksPath` now points to `/Users/jakyeamos/AIOS/.githooks-user`
- AIOS keeps its repo-local `core.hooksPath=.githooks`, so AIOS still uses the stricter AIOS standards ladder

## Verification

- Passed: `uv run pytest tests/test_user_commit_quality_gate.py -q`
- Passed: `uv run ruff check bin/user-commit-quality-gate.py tests/test_user_commit_quality_gate.py`
- Passed: `.githooks-user/pre-commit`
- Verified global hook path: `/Users/jakyeamos/AIOS/.githooks-user`
- Verified AIOS local hook path remains `.githooks`
