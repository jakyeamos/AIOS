# Add Vercel Deploy-Watch Completion Gate

## Scope

- Add a local script that deploys preview or production through the Vercel CLI and waits for completion logs.
- Expose root `pnpm` scripts for the preview and production paths.
- Add an AGENTS completion gate for Vercel-affecting shipping work.
- Update project truth and planning state with the new agent workflow behavior.

## Verification

- Run `bash -n scripts/vercel-deploy-watch.sh`.
- Run `pnpm context:validate`.
- Do not run a real Vercel deployment for this task because the change is a workflow/script addition, not a Vercel app change being shipped.
