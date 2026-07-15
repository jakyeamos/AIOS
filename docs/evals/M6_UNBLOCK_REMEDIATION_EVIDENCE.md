# M6 Post-Review Remediation Evidence

**Date:** 2026-07-15  
**Protected start SHA:** `4d8adbca3b89d6259e252f26aaad0db69a9bf102`  
**Scope:** disposable A/B/C treatment worktrees only; protected branch source was not modified

The immutable benchmark receipts retain `4d8adbca…` as the protected start
SHA. Their rollback-parent field points to the actual Git parent
`4cd4183f4cb890197507135579a877ac4ade046c`; these are intentionally recorded
as separate provenance values and are not interchangeable.

## A — atomic workflow skill promotion

Worktree: `/private/tmp/aios-m6-promotion-rerun-a-20260715-v1/a-treatment`

The A treatment owner now updates SQLite inside the transaction before writing
`skills.json`, uses an atomic same-directory replace, and restores the previous
registry bytes if a later database/commit failure occurs. A durable promotion
journal now records the pre/post registry bytes before the transaction starts;
the next owner invocation replays or restores that journal based on the
candidate's committed status, covering a process crash before or after the
database commit. A same-registry interprocess file lock serializes concurrent
promotions so two candidates cannot overwrite one another's registry update.
Missing or malformed registries retain the prior no-file-write behavior.

Remediation proof:

```text
PYTHONPATH=. .venv/bin/ruff check services/workflow_skill_mutations.py tests/test_workflow_skill_mutations.py
All checks passed!
PYTHONPATH=. .venv/bin/basedpyright services/workflow_skill_mutations.py tests/test_workflow_skill_mutations.py
0 errors, 0 warnings, 0 notes
PYTHONPATH=. .venv/bin/pytest -q tests/test_workflow_skill_mutations.py tests/test_workflow_experiments.py tests/test_aios_cli.py
111 passed
```

`test_promote_rolls_back_database_and_registry_on_update_failure` installs a
SQLite abort trigger, invokes promote, and verifies both the candidate row and
registry bytes remain unchanged. The two recovery tests simulate a process
ending before commit and after commit, verifying registry restoration/replay
and journal cleanup. Remediation file hashes:

- `services/workflow_skill_mutations.py` — `4b02713d651962f56f931311aae6fe7b6052f75027624f3a1306f634790d5b87`
- `tests/test_workflow_skill_mutations.py` — `1582e8699a5398c965a9c9f8e40b9ae84be0c947fa7b5a934f6134d0ad24def5`

The A treatment UI gate was then rerun with the disposable dependency mount
available:

```text
CI=true pnpm --dir aios-ui exec eslint .                         passed
CI=true pnpm --dir aios-ui exec tsc --noEmit                    passed
CI=true pnpm --dir aios-ui exec next build --webpack             passed
CI=true pnpm --dir aios-ui exec playwright test --config=/private/tmp/aios-m6-a-browser.config.ts
3 passed (26.9s)
```

Raw receipts:

- webpack build: `/private/tmp/aios-m6-a-build-20260715.log` — `f989bca2e8883e3ad69ba65ac885d6b4348a0e4f3456b558e706def96fc2280b`
- browser suite: `/private/tmp/aios-m6-a-browser-20260715.log` — `b73e779f675907c539cd1d75e102c80f403e8c4ddf54c11eda6daec4fbef4676`

The canonical `next build`/Turbopack path still fails because the external
`node_modules` symlink is outside the filesystem root; the supported webpack
build and browser proof pass without changing the treatment source.

## B — shadow-candidate transition coverage

Worktree: `/private/tmp/aios-m6-promotion-rerun-b-20260715-v3/b-treatment`

The treatment test now asserts a non-null `state_updated_at` after approval,
advances the candidate to `SNAPSHOT_CREATED`, and verifies that the subsequent
transition retains a timestamp.

```text
PYTHONPATH=. <protected-venv>/ruff check services/shadow_candidate_mutations.py services/shadow_automation.py tests/test_shadow_candidate_mutations.py
All checks passed!
PYTHONPATH=. <protected-venv>/basedpyright services/shadow_candidate_mutations.py services/shadow_automation.py tests/test_shadow_candidate_mutations.py
0 errors, 1 warning: pytest could not be resolved in the disposable shared environment
PYTHONPATH=. <protected-venv>/python -m pytest -q tests/test_shadow_candidate_mutations.py tests/test_shadow_automation.py
10 passed
```

The BasedPyright warning is an environment import-resolution warning for the
test dependency; service code has zero errors. Test hash:
`5b210f2036e640d5d7b05ee8a5718172a079cbc4d6d8260208334128b52c2542`.

## C — superseded Review runtime coverage

Worktree: `/private/tmp/aios-m6-promotion-rerun-c-20260715/c-treatment`

The browser fixture now seeds a real `superseded` run, session, packet, and
lifecycle event. The browser contract includes that run, asserts its persisted
status is `superseded`, and expects the active stage to be `Review`. The closeout
assertion selects the Closeout run by explicit ID rather than relying on a
positional index. The known exact local Next font abort is allowlisted only for
`GET /__nextjs_font/*.woff2` with `net::ERR_ABORTED`; all other request failures
remain fatal. The failure parser exercises the allowlist against the raw
method, URL, and error fields rather than a lossy space split, and the receipt
prints all observed bad responses, request failures, console errors, and
mutation requests.

```text
pnpm exec tsc --noEmit
passed
AIOS_UI_TEST_PORT=3224 pnpm exec playwright test tests/browser/m6-verify-review-closeout.spec.ts --workers=1
1 passed
```

The first sandboxed loopback attempt failed with `listen EPERM`; the successful
browser proof ran with explicit loopback permission and its raw stdout/stderr
receipt is retained at
`/private/tmp/aios-m6-remediation-browser-20260715/c-browser.log` with SHA-256
`70b35f70d39b9dedd276a54c8717c75f650da867f71899f24ee15d300d07f506`.
Remediation hashes:

- `tests/browser/global-setup.ts` — `cf95e3f13d3ed85e550de122e9f73ab42ccdb85f409b12478758aff98bd9a07c`
- `tests/browser/m6-verify-review-closeout.spec.ts` — `6560526f1b169429a0b6773487402a82711a7727f136b0a4096137461e5c0781`

The C treatment also contains the product stage-mapping change and the
test-harness configuration required to run the seeded contract. They are
included in the treatment boundary rather than silently omitted:

- `components/v2/V2OperatorShell.tsx` — `8324bab39a5528583a311c42e606d6189f6da75d13f9b72a868e550009ecf15f`
- `playwright.config.ts` — `116a88bf7ee99c874daea46c849fa840f75eb58a3dbab384c0fad3e0e06bfcc1`
- generated `next-env.d.ts` — `7ad303e40d4fddf44f156129e397511953a71481c5cfd86b1862649aaaf240cc`

## Remaining gate

These remediations address the prior A/B/C implementation findings. The fresh
post-fix adversarial review is recorded in
`M6_UNBLOCK_REMEDIATION_ADVERSARIAL_REVIEW.md`. It found no P0 findings and
verified the implementation remediations, but retained the authoritative
provider score/cost gate, the immutable treatment-report provenance mismatch,
the canonical Turbopack symlink limitation, and the disposable A `.venv`
boundary.
M6 promotion remains fail-closed until the promotion evidence gate passes and
the remaining evidence risks are closed or explicitly accepted. The
read-only provider manifest contract is documented in
`M6_PROVIDER_TELEMETRY_CONTRACT.md`; its pending template is intentionally not
promotion evidence.
