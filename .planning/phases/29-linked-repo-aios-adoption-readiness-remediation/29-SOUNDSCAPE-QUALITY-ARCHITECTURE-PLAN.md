# Soundscape Quality And Architecture Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move `soundscape-app` from Phase 29 blocked status to a focused quality-and-architecture green path, then record fresh AIOS gate evidence.

**Architecture:** Execute from the Soundscape checkout and treat AIOS as the evidence recorder. Start with the current architecture handoff/build blocker, then clear architecture, typecheck/lint, tests, security, smoke, Pre-CR, and finally local CI proof in that order. Keep every slice small enough to stage and commit independently without disturbing the existing dirty Soundscape worktree.

**Tech Stack:** pnpm 8, TypeScript, Next.js 14, tRPC, Prisma, Vitest, Playwright, AIOS `scripts/linked-repo-quality-runner.py`, `pre-cr`.

---

## Baseline

Current AIOS readiness report, checked from `/Users/jakyeamos/AIOS` on 2026-06-25:

- `soundscape-app` verdict: `blocked`
- Required missing gates: `lint`, `typecheck`, `test`, `ci`, `secret_scan`, `dependency_security`, `e2e_smoke`, `pre_cr`
- Existing passing evidence: `install`, `build`, `architecture`, `repo_truth`
- Warning-level/non-blocking evidence: `env_validation`
- Soundscape working tree is dirty before this plan starts. Preserve unrelated edits.

Authoritative commands come from `config/quality-pipeline.json` in AIOS:

```bash
python3 /Users/jakyeamos/AIOS/scripts/linked-repo-quality-runner.py --project soundscape-app --report
python3 /Users/jakyeamos/AIOS/scripts/linked-repo-quality-runner.py --project soundscape-app --gate lint
python3 /Users/jakyeamos/AIOS/scripts/linked-repo-quality-runner.py --project soundscape-app --gate typecheck
python3 /Users/jakyeamos/AIOS/scripts/linked-repo-quality-runner.py --project soundscape-app --gate test
python3 /Users/jakyeamos/AIOS/scripts/linked-repo-quality-runner.py --project soundscape-app --gate secret_scan
python3 /Users/jakyeamos/AIOS/scripts/linked-repo-quality-runner.py --project soundscape-app --gate dependency_security
python3 /Users/jakyeamos/AIOS/scripts/linked-repo-quality-runner.py --project soundscape-app --gate e2e_smoke
python3 /Users/jakyeamos/AIOS/scripts/linked-repo-quality-runner.py --project soundscape-app --gate pre_cr
python3 /Users/jakyeamos/AIOS/scripts/linked-repo-quality-runner.py --project soundscape-app --gate ci
```

## Files

- Modify as needed: `/Users/jakyeamos/projects/soundscape-app/docs/architecture-cleanup-handoff.md`
- Modify as needed: `/Users/jakyeamos/projects/soundscape-app/packages/web/src/app/[locale]/(main)/compare/[userId]/page.tsx`
- Modify as needed: `/Users/jakyeamos/projects/soundscape-app/packages/platform-web/src/trpc/webClient.ts`
- Modify as needed: `/Users/jakyeamos/projects/soundscape-app/packages/api/package.json`
- Modify as needed: `/Users/jakyeamos/projects/soundscape-app/packages/api/src/index.ts`
- Modify as needed: `/Users/jakyeamos/projects/soundscape-app/packages/api/src/contracts/*`
- Modify as needed: `/Users/jakyeamos/projects/soundscape-app/packages/api/src/server/*`
- Modify as needed: `/Users/jakyeamos/projects/soundscape-app/packages/shared/package.json`
- Modify as needed: `/Users/jakyeamos/projects/soundscape-app/packages/shared/src/*`
- Modify as needed: `/Users/jakyeamos/projects/soundscape-app/packages/web/src/**/*`
- Modify as needed: `/Users/jakyeamos/projects/soundscape-app/packages/api/src/**/*`
- Modify as needed after gate proof: `/Users/jakyeamos/AIOS/docs/audits/linked-repo-adoption-readiness-audit.md`
- Create after completion: `/Users/jakyeamos/AIOS/.planning/phases/29-linked-repo-aios-adoption-readiness-remediation/29-SOUNDSCAPE-SUMMARY.md`

## Execution Rules

- Work from `/Users/jakyeamos/projects/soundscape-app` unless a command explicitly starts with `/Users/jakyeamos/AIOS`.
- Do not revert existing dirty files. Stage only files touched for the current slice.
- Use `pnpm`, never `npm` or `yarn`, except do not change existing `apps/soundscape-landing-page/package-lock.json` unless the task is specifically that app's package-manager migration.
- Keep `packages/shared` breakup out of this remediation unless a gate failure directly requires it.
- Do not add broad `any`, blanket `eslint-disable`, or package-internal `/src` imports to make gates pass.
- Update `docs/architecture-cleanup-handoff.md` before stopping any slice that leaves a gate failing.

## Task 1: Establish The Current Failing Frontier

**Files:**
- Modify: `/Users/jakyeamos/projects/soundscape-app/docs/architecture-cleanup-handoff.md`

- [ ] **Step 1: Capture the starting worktree**

Run:

```bash
cd /Users/jakyeamos/projects/soundscape-app
git status --short
```

Expected: a dirty tree is allowed. Save the visible state mentally or in the handoff before changing files.

- [ ] **Step 2: Record the AIOS baseline report**

Run:

```bash
cd /Users/jakyeamos/AIOS
python3 scripts/linked-repo-quality-runner.py --project soundscape-app --report
```

Expected: `missing_gate_keys` includes `lint`, `typecheck`, `test`, `ci`, `secret_scan`, `dependency_security`, `e2e_smoke`, and `pre_cr`.

- [ ] **Step 3: Run the direct architecture/build frontier**

Run:

```bash
cd /Users/jakyeamos/projects/soundscape-app
node scripts/aios-architecture-check.mjs
pnpm --filter @soundscape/api build
pnpm --filter @soundscape/web typecheck
pnpm --filter @soundscape/web build
```

Expected: fix the first concrete failure surfaced by these commands before branching into broader cleanup. If all pass, move to Task 3.

- [ ] **Step 4: Update the handoff with the exact frontier**

Add a short entry to `/Users/jakyeamos/projects/soundscape-app/docs/architecture-cleanup-handoff.md` using the actual first failing command from Step 3. If the current known web build blocker is still the first failure, use this exact entry:

```markdown
## Current Target Slice
**Pass 3: Phase 29 quality and architecture remediation**

Current first failing command:
- `pnpm --filter @soundscape/web build`

Current first failing symptom:
- Next.js App Router rejects a named export from `packages/web/src/app/[locale]/(main)/compare/[userId]/page.tsx`.

Next action:
- Fix the first failing command before broad cleanup.
```

If Step 3 surfaces a different first failure, write the actual command and one-line error summary from that run instead of the known web build blocker above.

## Task 2: Close The Current Web Build Blocker

**Files:**
- Modify if needed: `/Users/jakyeamos/projects/soundscape-app/packages/web/src/app/[locale]/(main)/compare/[userId]/page.tsx`
- Modify: `/Users/jakyeamos/projects/soundscape-app/docs/architecture-cleanup-handoff.md`

- [ ] **Step 1: Check whether the compare helper is still exported**

Run:

```bash
cd /Users/jakyeamos/projects/soundscape-app
rg -n "export function OverlapResultsSection|function OverlapResultsSection" 'packages/web/src/app/[locale]/(main)/compare/[userId]/page.tsx'
```

Expected: the valid form is `function OverlapResultsSection(...)`, not `export function OverlapResultsSection(...)`.

- [ ] **Step 2: Remove the invalid page export if it exists**

Change this:

```tsx
export function OverlapResultsSection({
  isLoading,
  overlapData,
  albumsToRender,
  suggestions,
  strictOverlapCount,
  rankingEnabled,
  targetUserId,
  targetUsername,
}: OverlapResultsSectionProps) {
```

To this:

```tsx
function OverlapResultsSection({
  isLoading,
  overlapData,
  albumsToRender,
  suggestions,
  strictOverlapCount,
  rankingEnabled,
  targetUserId,
  targetUsername,
}: OverlapResultsSectionProps) {
```

If the file is already in the second form, make no edit.

- [ ] **Step 3: Verify the web build advances**

Run:

```bash
cd /Users/jakyeamos/projects/soundscape-app
pnpm --filter @soundscape/web build
```

Expected: the build no longer fails on `invalid page export field: OverlapResultsSection`. If a new failure appears, record that exact failure in the handoff and continue with the next concrete blocker.

- [ ] **Step 4: Verify web typecheck**

Run:

```bash
cd /Users/jakyeamos/projects/soundscape-app
pnpm --filter @soundscape/web typecheck
```

Expected: pass, or a specific type failure that points at the next file to fix.

- [ ] **Step 5: Commit the slice if files changed**

Run:

```bash
cd /Users/jakyeamos/projects/soundscape-app
git diff -- 'packages/web/src/app/[locale]/(main)/compare/[userId]/page.tsx' docs/architecture-cleanup-handoff.md
git add 'packages/web/src/app/[locale]/(main)/compare/[userId]/page.tsx' docs/architecture-cleanup-handoff.md
git commit -m "fix(web): keep compare route helpers private"
```

Expected: commit only the files changed in this task. If only the handoff changed, use `docs(architecture): refresh cleanup handoff`.

## Task 3: Make The Architecture Boundary Gate Durable

**Files:**
- Modify as needed: `/Users/jakyeamos/projects/soundscape-app/scripts/aios-architecture-check.mjs`
- Modify as needed: `/Users/jakyeamos/projects/soundscape-app/packages/api/package.json`
- Modify as needed: `/Users/jakyeamos/projects/soundscape-app/packages/api/src/contracts/*`
- Modify as needed: `/Users/jakyeamos/projects/soundscape-app/packages/api/src/server/*`
- Modify as needed: `/Users/jakyeamos/projects/soundscape-app/packages/shared/package.json`
- Modify as needed: `/Users/jakyeamos/projects/soundscape-app/packages/platform-web/src/trpc/webClient.ts`
- Modify as needed: `/Users/jakyeamos/projects/soundscape-app/packages/web/src/**/*`

- [ ] **Step 1: Run the current architecture gate directly**

Run:

```bash
cd /Users/jakyeamos/projects/soundscape-app
node scripts/aios-architecture-check.mjs
```

Expected: `AIOS architecture check passed.` If it fails, fix the first import-boundary violation before running broad commands.

- [ ] **Step 2: Audit for package-internal imports**

Run:

```bash
cd /Users/jakyeamos/projects/soundscape-app
rg -n "@soundscape/[^'\"]+/src/|packages/[^'\"]+/src/" apps packages --glob '*.{ts,tsx}'
```

Expected: no runtime consumers should import another package's internal `src` path.

- [ ] **Step 3: Repair any API reach-through by adding a public entrypoint**

If a consumer imports from `@soundscape/api/src/services/example`, create or reuse a focused public module like:

```ts
// packages/api/src/server/example.ts
export { exampleFunction } from '../services/example';
export type { ExampleInput, ExampleOutput } from '../services/example';
```

Then add the subpath to `/Users/jakyeamos/projects/soundscape-app/packages/api/package.json`:

```json
"./example": {
  "types": "./dist/src/server/example.d.ts",
  "default": "./dist/src/server/example.js"
}
```

Then update the consumer:

```ts
import { exampleFunction } from '@soundscape/api/example';
import type { ExampleInput } from '@soundscape/api/example';
```

Expected: the consumer depends on a public package export, not `src`.

- [ ] **Step 4: Repair shared reach-through by exporting the owned public subpath**

If a consumer imports from `@soundscape/shared/src/constants/example`, create or expose a public subpath in `/Users/jakyeamos/projects/soundscape-app/packages/shared/package.json` and keep the consumer import focused:

```ts
import { EXAMPLE_CONSTANT } from '@soundscape/shared/constants/example';
```

Expected: `packages/shared` remains a compatibility surface, but consumers do not reach into `src`.

- [ ] **Step 5: Verify architecture through AIOS**

Run:

```bash
cd /Users/jakyeamos/AIOS
python3 scripts/linked-repo-quality-runner.py --project soundscape-app --gate architecture
```

Expected: gate records a passing `quality_pipeline_runs` row for `architecture`.

- [ ] **Step 6: Commit the architecture slice**

Run:

```bash
cd /Users/jakyeamos/projects/soundscape-app
git diff
git add packages/api packages/shared packages/platform-web packages/web scripts/aios-architecture-check.mjs docs/architecture-cleanup-handoff.md
git commit -m "refactor(architecture): close public package boundary gaps"
```

Expected: stage only files actually changed in this task.

## Task 4: Clear Typecheck And Lint

**Files:**
- Modify as needed: `/Users/jakyeamos/projects/soundscape-app/tsconfig*.json`
- Modify as needed: `/Users/jakyeamos/projects/soundscape-app/packages/**/*.ts`
- Modify as needed: `/Users/jakyeamos/projects/soundscape-app/packages/**/*.tsx`
- Modify as needed: `/Users/jakyeamos/projects/soundscape-app/apps/**/*.ts`
- Modify as needed: `/Users/jakyeamos/projects/soundscape-app/apps/**/*.tsx`

- [ ] **Step 1: Run package-focused typechecks before root typecheck**

Run:

```bash
cd /Users/jakyeamos/projects/soundscape-app
pnpm --filter @soundscape/api build
pnpm --filter @soundscape/platform-web typecheck
pnpm --filter @soundscape/web typecheck
pnpm typecheck
```

Expected: fix package-local failures first. Do not paper over declaration/config mismatches with `any`.

- [ ] **Step 2: Fix type errors by ownership**

Use these default patterns:

```ts
// Prefer type-only imports for contracts.
import type { AppRouter } from '@soundscape/api';

// Prefer public package subpaths for runtime code.
import { createDefaultWebClient } from '@soundscape/platform-web';

// Avoid this.
import type { AppRouter } from '@soundscape/api/src/routers';
```

Expected: each fixed error improves package ownership instead of hiding it.

- [ ] **Step 3: Run lint directly**

Run:

```bash
cd /Users/jakyeamos/projects/soundscape-app
pnpm lint
```

Expected: pass. If Node/ESLint exhausts memory, keep the root gate as the final requirement but triage locally with package-scoped commands:

```bash
pnpm --filter @soundscape/api lint
pnpm --filter @soundscape/web lint
pnpm --filter @soundscape/platform-web lint
```

- [ ] **Step 4: Record AIOS lint and typecheck evidence**

Run:

```bash
cd /Users/jakyeamos/AIOS
python3 scripts/linked-repo-quality-runner.py --project soundscape-app --gate typecheck
python3 scripts/linked-repo-quality-runner.py --project soundscape-app --gate lint
```

Expected: both gates pass and produce fresh evidence IDs.

- [ ] **Step 5: Commit the type/lint slice**

Run:

```bash
cd /Users/jakyeamos/projects/soundscape-app
git diff
git add .
git commit -m "fix(quality): clear typecheck and lint gates"
```

Expected: inspect `git diff --cached` before committing and unstage unrelated dirty files.

## Task 5: Clear Test Quality And Workspace Tests

**Files:**
- Modify as needed: `/Users/jakyeamos/projects/soundscape-app/scripts/testing/test-quality-audit.ts`
- Modify as needed: `/Users/jakyeamos/projects/soundscape-app/scripts/testing/inventory-tests.ts`
- Modify as needed: `/Users/jakyeamos/projects/soundscape-app/docs/testing/test-inventory.md`
- Modify as needed: `/Users/jakyeamos/projects/soundscape-app/packages/**/__tests__/*`
- Modify as needed: `/Users/jakyeamos/projects/soundscape-app/packages/**/*.test.ts`
- Modify as needed: `/Users/jakyeamos/projects/soundscape-app/packages/**/*.test.tsx`

- [ ] **Step 1: Run the hardened test-quality checks**

Run:

```bash
cd /Users/jakyeamos/projects/soundscape-app
pnpm exec node --import tsx scripts/testing/test-quality-audit.ts
pnpm exec node --import tsx scripts/testing/inventory-tests.ts
pnpm test:scripts
```

Expected: no skipped/focused default tests, vacuous assertions, stochastic default tests, raw console output, or missing inventory failures.

- [ ] **Step 2: Run the stable workspace test baseline**

Run:

```bash
cd /Users/jakyeamos/projects/soundscape-app
pnpm test
```

Expected: pass. If a test fails, classify it as product bug, stale/broken test, environment/setup problem, or infra flake in `docs/operations/TESTING-BASELINE-HEALTH.md` before changing assertions.

- [ ] **Step 3: Fix weak or stale tests with behavior-backed assertions**

Use this pattern when replacing a weak render-only assertion:

```ts
it('persists the changed privacy setting', async () => {
  const user = userEvent.setup();
  render(<PrivacySettingsForm initialVisibility="friends" onSave={onSave} />);

  await user.click(screen.getByRole('radio', { name: /private/i }));
  await user.click(screen.getByRole('button', { name: /save/i }));

  expect(onSave).toHaveBeenCalledWith({ visibility: 'private' });
});
```

Expected: tests protect behavior, contracts, domain logic, or confirmed regressions.

- [ ] **Step 4: Record AIOS test evidence**

Run:

```bash
cd /Users/jakyeamos/AIOS
python3 scripts/linked-repo-quality-runner.py --project soundscape-app --gate test
```

Expected: the `test` gate passes and records fresh evidence.

- [ ] **Step 5: Commit the test slice**

Run:

```bash
cd /Users/jakyeamos/projects/soundscape-app
git diff
git add scripts/testing docs/testing docs/operations packages apps
git commit -m "test: harden Soundscape quality baseline"
```

Expected: staged files are only test, source, and docs changes needed for this gate.

## Task 6: Clear Security And Dependency Gates

**Files:**
- Modify as needed: `/Users/jakyeamos/projects/soundscape-app/package.json`
- Modify as needed: `/Users/jakyeamos/projects/soundscape-app/pnpm-lock.yaml`
- Modify as needed: `/Users/jakyeamos/projects/soundscape-app/.env.example`
- Modify as needed: `/Users/jakyeamos/projects/soundscape-app/docs/platform/secrets/*`

- [ ] **Step 1: Run the AIOS secret scan**

Run:

```bash
cd /Users/jakyeamos/AIOS
python3 scripts/linked-repo-quality-runner.py --project soundscape-app --gate secret_scan
```

Expected: pass. If it reports a credential-looking string, remove the secret from source, rotate the credential if real, and replace docs/examples with inert placeholders.

- [ ] **Step 2: Run dependency audit**

Run:

```bash
cd /Users/jakyeamos/projects/soundscape-app
pnpm audit --audit-level high
```

Expected: no high-severity production dependency advisories. This command may need network access.

- [ ] **Step 3: Remediate dependency advisories minimally**

Prefer direct safe upgrades or root `pnpm.overrides` when transitive packages are the issue:

```json
"pnpm": {
  "overrides": {
    "hono": ">=4.11.4",
    "@modelcontextprotocol/sdk": ">=1.25.2",
    "diff": ">=8.0.3",
    "cookie": ">=0.7.0",
    "tar": ">=7.5.7"
  }
}
```

Expected: do not introduce a second lockfile. Keep `pnpm-lock.yaml` authoritative for the workspace.

- [ ] **Step 4: Record AIOS dependency evidence**

Run:

```bash
cd /Users/jakyeamos/AIOS
python3 scripts/linked-repo-quality-runner.py --project soundscape-app --gate dependency_security
```

Expected: the dependency security gate passes.

- [ ] **Step 5: Commit the security slice**

Run:

```bash
cd /Users/jakyeamos/projects/soundscape-app
git diff
git add package.json pnpm-lock.yaml .env.example docs/platform/secrets
git commit -m "fix(security): clear audit and secret scan gates"
```

Expected: commit only files changed for security/dependency remediation.

## Task 7: Clear E2E Smoke

**Files:**
- Modify as needed: `/Users/jakyeamos/projects/soundscape-app/playwright.config.ts`
- Modify as needed: `/Users/jakyeamos/projects/soundscape-app/e2e/**/*`
- Modify as needed: `/Users/jakyeamos/projects/soundscape-app/packages/web/e2e/**/*`
- Modify as needed: `/Users/jakyeamos/projects/soundscape-app/packages/web/src/**/*`

- [ ] **Step 1: Verify local E2E prerequisites**

Run:

```bash
cd /Users/jakyeamos/projects/soundscape-app
pnpm e2e:preview:preflight
pnpm e2e:seeded:verify
```

Expected: pass, or a specific missing local service/env variable. Do not mark E2E as green if the app path was skipped.

- [ ] **Step 2: Run the required smoke gate directly**

Run:

```bash
cd /Users/jakyeamos/projects/soundscape-app
pnpm e2e:smoke
```

Expected: Playwright smoke passes against the configured target.

- [ ] **Step 3: Fix deterministic smoke failures**

Use seeded data and stable selectors. Prefer this style:

```ts
await page.getByRole('link', { name: /feed/i }).click();
await expect(page.getByRole('heading', { name: /feed/i })).toBeVisible();
```

Avoid arbitrary timeouts and text assertions that duplicate implementation copy without proving behavior.

- [ ] **Step 4: Record AIOS E2E evidence**

Run:

```bash
cd /Users/jakyeamos/AIOS
python3 scripts/linked-repo-quality-runner.py --project soundscape-app --gate e2e_smoke
```

Expected: the E2E smoke gate passes and records fresh evidence.

- [ ] **Step 5: Commit the E2E slice**

Run:

```bash
cd /Users/jakyeamos/projects/soundscape-app
git diff
git add playwright.config.ts e2e packages/web/e2e packages/web/src
git commit -m "test(e2e): stabilize Soundscape smoke gate"
```

Expected: commit only E2E and directly required product fixes.

## Task 8: Run Pre-CR And Local CI Proof

**Files:**
- Modify after proof: `/Users/jakyeamos/projects/soundscape-app/docs/architecture-cleanup-handoff.md`
- Create after proof: `/Users/jakyeamos/AIOS/.planning/phases/29-linked-repo-aios-adoption-readiness-remediation/29-SOUNDSCAPE-SUMMARY.md`
- Modify after proof: `/Users/jakyeamos/AIOS/docs/audits/linked-repo-adoption-readiness-audit.md`

- [ ] **Step 1: Run the Soundscape pre-commit quality profile directly**

Run:

```bash
cd /Users/jakyeamos/projects/soundscape-app
pnpm exec node --import tsx scripts/testing/test-quality-audit.ts
pnpm exec node --import tsx scripts/testing/inventory-tests.ts
pnpm test:scripts
pre-cr run --json --workspace /Users/jakyeamos/projects/soundscape-app
```

Expected: all commands pass. If `pre-cr` reports policy failures, fix the named files rather than bypassing hooks.

- [ ] **Step 2: Record AIOS Pre-CR evidence**

Run:

```bash
cd /Users/jakyeamos/AIOS
python3 scripts/linked-repo-quality-runner.py --project soundscape-app --gate pre_cr
```

Expected: `pre_cr` passes.

- [ ] **Step 3: Run local CI replacement proof**

Run:

```bash
cd /Users/jakyeamos/AIOS
python3 scripts/linked-repo-quality-runner.py --project soundscape-app --gate ci
```

Expected: the local CI proof passes only after all non-`ci` required gates pass.

- [ ] **Step 4: Confirm Soundscape readiness**

Run:

```bash
cd /Users/jakyeamos/AIOS
python3 scripts/linked-repo-quality-runner.py --project soundscape-app --report
```

Expected:

```json
{
  "project_id": "soundscape-app",
  "missing_gate_keys": [],
  "verdict": "ready"
}
```

- [ ] **Step 5: Write the Phase 29 Soundscape summary**

Create `/Users/jakyeamos/AIOS/.planning/phases/29-linked-repo-aios-adoption-readiness-remediation/29-SOUNDSCAPE-SUMMARY.md`:

```markdown
# Phase 29 Soundscape Quality And Architecture Summary

Date: 2026-06-25
Project: soundscape-app

## Result

- Final verdict: ready
- Missing gates: []

## Evidence Commands

- `python3 scripts/linked-repo-quality-runner.py --project soundscape-app --gate lint`
- `python3 scripts/linked-repo-quality-runner.py --project soundscape-app --gate typecheck`
- `python3 scripts/linked-repo-quality-runner.py --project soundscape-app --gate test`
- `python3 scripts/linked-repo-quality-runner.py --project soundscape-app --gate secret_scan`
- `python3 scripts/linked-repo-quality-runner.py --project soundscape-app --gate dependency_security`
- `python3 scripts/linked-repo-quality-runner.py --project soundscape-app --gate e2e_smoke`
- `python3 scripts/linked-repo-quality-runner.py --project soundscape-app --gate pre_cr`
- `python3 scripts/linked-repo-quality-runner.py --project soundscape-app --gate ci`
- `python3 scripts/linked-repo-quality-runner.py --project soundscape-app --report`

## Residual Risks

- Document any remaining warning-level environment, remote workflow, or dirty-tree hygiene risk here.
```

- [ ] **Step 6: Commit the evidence summary**

Run:

```bash
cd /Users/jakyeamos/AIOS
git add .planning/phases/29-linked-repo-aios-adoption-readiness-remediation/29-SOUNDSCAPE-SUMMARY.md docs/audits/linked-repo-adoption-readiness-audit.md
git commit -m "docs(phase29): record Soundscape readiness evidence"
```

Expected: commit only the summary/audit evidence files.

## Task 9: Optional Next Quality Debt After Gates Are Green

Do not start this task until Task 8 reports `missing_gate_keys: []`.

**Files:**
- Modify later: `/Users/jakyeamos/projects/soundscape-app/packages/api/src/cron/batchPriceUpdate.ts`
- Modify later: `/Users/jakyeamos/projects/soundscape-app/packages/api/src/cron/distributionSnapshots.ts`
- Modify later: `/Users/jakyeamos/projects/soundscape-app/packages/core/src/composite-tiers.ts`
- Modify later: `/Users/jakyeamos/projects/soundscape-app/packages/shared/src/composite-tiers.ts`
- Modify later: `/Users/jakyeamos/projects/soundscape-app/packages/web/src/components/overlap/OverlapTable.tsx`

- [ ] **Step 1: Pick one complexity hotspot**

Choose exactly one:

```text
batchPriceUpdate N+1 cleanup
distributionSnapshots N+1 cleanup
composite tier source-of-truth consolidation
OverlapTable pagination/windowing
```

- [ ] **Step 2: Add behavior coverage before refactoring**

For cron paths, test grouped input behavior and query count expectations. For composite tiers, test representative album, artist, and track scoring inputs through the public package API. For overlap UI, test large-list rendering behavior without snapshotting implementation copy.

- [ ] **Step 3: Run the focused command and the full affected gate**

Run the focused package test first, then:

```bash
cd /Users/jakyeamos/projects/soundscape-app
pnpm typecheck
pnpm test
```

Expected: no Phase 29 readiness regression.
