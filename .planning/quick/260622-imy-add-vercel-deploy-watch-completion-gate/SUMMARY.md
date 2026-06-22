# Summary

Added a Vercel deployment completion gate for AIOS agent workflows.

## Changed

- Added `scripts/vercel-deploy-watch.sh` for preview and production deployments.
- Added root `pnpm deploy:preview:watch` and `pnpm deploy:prod:watch` scripts.
- Updated `AGENTS.md` so agents must wait for a successful Vercel deployment before completing Vercel-affecting shipping work.
- Updated `PROJECT.md` and `.planning/STATE.md` to record the new workflow behavior.

## Verification

- `bash -n scripts/vercel-deploy-watch.sh`
- `pnpm context:validate`

No real Vercel deployment was run because this task added the workflow gate itself rather than shipping Vercel app changes.
