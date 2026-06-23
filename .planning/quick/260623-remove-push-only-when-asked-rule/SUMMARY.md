# Remove Push-Only-When-Asked Rule

Completed on 2026-06-23.

## Result

Removed the deployment-gate instruction that limited branch pushes to cases where the user explicitly asked or the task explicitly included pushing.

## Changed Files

- `AGENTS.md`
  - Removed the Vercel deployment gate line: "Push the branch only when asked or when the task explicitly includes pushing."
  - Renumbered the remaining deployment completion gate steps.
- `.planning/STATE.md`
  - Recorded the quick policy update.
- `PROJECT.md`
  - Recorded that the Vercel completion gate no longer narrows push behavior.

## Verification

- `pnpm context:validate` passed.
- `git diff --check` passed.
