# Plan 15-05 Summary: To-Issues Skill And Issues Store

## Outcome

Created the global to-issues skill at `/Users/jakyeamos/.claude/skills/to-issues/SKILL.md` and added `services/issues_store.py` with an idempotent SQLite-backed `issues` table.

The skill decomposes plans, PRDs, specs, and architecture reports into independently verifiable vertical tracer-bullet issues with AFK/HITL labels, dependencies, acceptance criteria, and test expectations.

## Evidence

- `services/issues_store.py` provides `write_issue(...)` and `list_issues(project=None)`.
- The service creates the `issues` table with `CREATE TABLE IF NOT EXISTS` and stores JSON acceptance criteria/dependencies.
- `schema.sql` now includes the `issues` table and indexes as checked-in schema authority.
- The skill defaults to AIOS local storage, falls back to markdown under a user-level issues directory when AIOS/DB access is unavailable, and treats `gh issue create` as explicit opt-in only.

## Verification

- `uv run pytest -q tests/test_issues_store.py` passed: 4 tests.
- `uv run ruff check services/issues_store.py tests/test_issues_store.py` passed.
- `node /Users/jakyeamos/.claude/get-shit-done/bin/gsd-tools.cjs verify artifacts .planning/phases/15-agent-skill-portfolio-audit-and-external-library-integration/15-05-PLAN.md` passed.
- `node /Users/jakyeamos/.claude/get-shit-done/bin/gsd-tools.cjs verify references .planning/phases/15-agent-skill-portfolio-audit-and-external-library-integration/15-05-PLAN.md` passed.
- `node /Users/jakyeamos/.claude/get-shit-done/bin/gsd-tools.cjs verify key-links .planning/phases/15-agent-skill-portfolio-audit-and-external-library-integration/15-05-PLAN.md` passed.
- `rg` confirmed the skill includes vertical tracer-bullet slicing, AFK/HITL labels, dependencies/blockers, acceptance criteria, test expectations, issues-store persistence, and opt-in GitHub publishing.
- `git diff --check` passed.

## Notes

- The global skill file is outside the AIOS git repository; this repo records the service, schema, tests, plan contract, summary, and planning truth updates.
