# ADR-004: Reproducible UI Validation Contract

**Status:** Accepted v2 validation contract<br>
**Date:** 2026-07-13<br>
**Scope:** Dependency installation, lint/typecheck, build, local runtime,
browser, and console evidence for `aios-ui`. This decision defines gates; it
does not repair the current toolchain or change application code.

## Decision

AIOS UI validation uses one explicit Node toolchain and a staged quality ladder.
Every stage produces a command result and, for browser stages, a screenshot or
console/network artifact linked to the run. A green result is not inferred from
the existence of a lockfile, a cached font, a successful static build, or a
page that happened to render once.

The authoritative target is:

- pnpm `11.7.0`, invoked from the repository root or with `--dir aios-ui`;
- Node `20.x`, matching the existing GitHub Actions workflow and the supported
  Next.js 16 runtime range;
- a single repository-level workspace and lockfile after the workspace
  consolidation milestone;
- no dependency resolved from an uncommitted path outside the repository;
- no build-time network fetches;
- `aios-ui` as the explicit Next/Turbopack root;
- independent ESLint and TypeScript commands so a lint bootstrap failure cannot
  hide the type result; and
- a browser journey that fails on console errors, same-origin 4xx/5xx
  responses, hydration failures, missing styles, or duplicate React keys.

Until the workspace consolidation, dependency packaging, local-font, and
runtime repairs land, the current local and CI setup is a baseline with known
red gates. It must not be reported as v2 validation-ready.

## Current evidence

| Check | 2026-07-13 result | Interpretation |
| --- | --- | --- |
| `pnpm install --frozen-lockfile --offline` from `aios-ui/` | Exited 0, “Already up to date” | Only proves the existing `node_modules` state is accepted; it did not repair the stale file dependency package |
| `pnpm lint` from `aios-ui/` | **Fail** before TypeScript | Installed `eslint-plugin-anti-slop@0.2.0` imports missing `no-arbitrary-z-index.mjs`; the source package at the external path is `0.4.0` and has that rule |
| `pnpm exec tsc --noEmit` | Pass | TypeScript is independently green when ESLint does not short-circuit it |
| `pnpm lint:warning-baseline` | Pass, `0/71` | Warning ratchet is meaningful once ESLint can load |
| `pnpm lint:architecture` | Pass, 121 modules / 255 dependencies | Dependency boundaries are currently clean |
| `pnpm lint:anti-slop:fixtures` | **Fail** with the same missing rule module | Fixture coverage cannot be trusted until the plugin artifact is deterministic |
| `pnpm build` | Pass locally, with warnings | Current cache allows the build, but Turbopack warns about inferred root, multiple lockfile/workspace signals, and whole-project file tracing |
| Prior clean-ish audit build | **Fail** on Google-hosted Geist and JetBrains Mono fetch | A cached local pass is not an offline/reproducible proof |
| `pnpm dev` on free loopback port | `/` returned 200; `controlPlane.overview` returned 500 | Dev server log reproduced `Cannot find module '@trpc/server/adapters/fetch'` |
| `controlPlane.runDetail` without input | Returned a typed 400 | The route handler can execute far enough to validate input; a seeded valid-input request is still required for the browser gate |
| Existing browser audit | Desktop and 375px rendered; duplicate React keys observed | Tablet was inconclusive after the runtime/style failure; duplicate keys remain a hard console failure |

The baseline also records these browser/runtime findings in
[AUDIT.md](AUDIT.md): duplicate keys for
`workflow_agent_control.explicit_handshake`, `testing.trust_signal`, and
`architecture.boundary_enforcement`; an intermittent `runDetail` 500; lost
stylesheet after reload; and no passing tablet proof.

## Package, lockfile, and workspace contract

### Target posture

The repository will converge on one pnpm workspace and one root
`pnpm-lock.yaml`. The root package keeps context-compiler scripts; `aios-ui`
becomes a workspace package. The current root lockfile and nested
`aios-ui/pnpm-lock.yaml` remain historical inputs until that consolidation is
implemented, but no check may silently choose between them.

The UI's anti-slop dependency must be one of:

1. a versioned package available to CI from a registry, with its version and
   integrity locked; or
2. a committed workspace package inside this repository, included in the same
   lockfile.

The current `file:../../eslint-plugin-anti-slop` dependency is not an
authoritative CI contract. It resolves to `/Users/jakyeamos/projects/` on this
machine, points outside the checkout, and allowed `node_modules` to retain a
0.2.0 package while the source directory is 0.4.0. A clean runner does not have
that sibling path. The validation gate must fail with a remediation message if
the dependency is not present; it must not copy a developer's `node_modules`
or disable the rule.

### Install preflight

The authoritative clean-install sequence is:

```sh
node --version                 # must be 20.x in CI and release evidence
pnpm --version                 # must be 11.7.0
pnpm install --frozen-lockfile # from the chosen workspace root
pnpm --dir aios-ui install --frozen-lockfile # transitional nested-scope check
```

The preflight records the resolved package path and version for every local
file dependency. It fails when a dependency path is outside the checkout,
when the installed package differs from the lockfile source, or when a clean
install requires network access not declared by the contract.

CI must cache the lockfile that actually governs the install. The existing
workflow caches `aios-ui/pnpm-lock.yaml` and installs with
`pnpm --dir aios-ui install --frozen-lockfile`; that is valid only while the
nested scope remains intentional and the anti-slop dependency is packaged for
clean runners.

## Fonts and build determinism

`next/font/google` is not allowed in the validation target. It makes a build
depend on Google availability and allowed the audit build to fail before the
application was compiled. The implementation must choose one deterministic
path:

- use a system font stack for interface text and monospace values; or
- use `next/font/local` with committed, license-approved font files and a
  checksum recorded in the repository.

The build gate runs with network access unavailable or explicitly denied. A
font cache is not evidence of an offline build. Any external font request,
missing local asset, or fallback-font warning fails the gate.

`aios-ui/next.config.ts` must set the Turbopack root to the app root and keep
the production trace scoped to the files the app actually reads. The current
build warning about the root inferred from the repository lockfile and the
whole-project NFT trace is a failure until it is either removed or documented
with a narrow, reviewed tracing exception. Dynamic filesystem reads must be
scoped to the configured `AIOS_ROOT`; they must not make the entire repository
an accidental deployment input.

## Required quality ladder

Run these commands from a clean checkout, in this order:

```sh
pnpm --dir aios-ui exec eslint .
pnpm --dir aios-ui exec tsc --noEmit
pnpm --dir aios-ui lint:warning-baseline
pnpm --dir aios-ui lint:architecture
pnpm --dir aios-ui lint:anti-slop:fixtures
pnpm --dir aios-ui build
```

The combined `pnpm --dir aios-ui lint` remains a convenience command, not the
only proof: it currently short-circuits before `tsc` when the plugin import
fails. The first two commands must remain independently visible in CI.

### Failure policy

- ESLint errors, TypeScript errors, architecture violations, and anti-slop
  fixture failures are hard failures.
- Warning-baseline drift is a hard failure; an intentional change requires a
  scoped baseline update in the same review.
- Build warnings are hard failures when they indicate a wrong root, a network
  fetch, a whole-project trace, a missing asset, or a hidden fallback. Cosmetic
  compiler notices require a written allowlist entry with an owner and expiry.
- No gate may be weakened with skipped tests, `|| true`, disabled rules,
  `--no-verify`, or a production-only fallback.

## Local runtime contract

The dev server is started on an explicitly selected free loopback port and its
PID is owned by the validation process:

```sh
PORT=3002
pnpm --dir aios-ui dev -- --hostname 127.0.0.1 --port "$PORT"
```

The harness records the selected port, server output, commit, Node/pnpm
versions, and `AIOS_ROOT`/`AIOS_DB` values. It stops only the process it
started. A port already in use is reported and a different free port is chosen;
the check never kills an unrelated developer server.

Before browser interaction, the harness must prove:

1. `GET /` returns 200 and contains the app shell and stylesheet links.
2. A valid seeded `controlPlane.overview` request returns a source-backed
   response, not an HTML error page.
3. A valid seeded `controlPlane.runDetail` request returns its typed response.
4. Every same-origin request made by the first route has a 2xx/3xx result;
   4xx/5xx responses are captured with URL and body excerpt.

The route handler import error for `@trpc/server/adapters/fetch` is a hard
failure even when the home page itself returns 200. A typed 400 caused by a
deliberately missing input is not a pass for a valid-input route check.

## Browser and console contract

The first automated browser slice follows the Ticket 004 contract:

```text
Today → Start work → Current run → Verify → Gated review → Closeout
```

For each slice, use a seeded happy path plus empty, blocked, failed, and
approval-required fixtures. The browser proof records:

| Dimension | Required matrix | Failure examples |
| --- | --- | --- |
| Viewport | 375×812, 768×1024, 1440×900 | clipped primary action, hidden required content, accidental horizontal nav |
| Input | keyboard-only pass and pointer pass | unreachable stage, invisible focus, native control bypassed by a div |
| Semantics | landmarks, labels, table headers, `aria-current`, live status, error association | unnamed controls, incorrect state, status communicated only by color |
| Visual | screenshot of each stage and each viewport | stylesheet lost after reload, overflow, unreadable contrast, layout shift |
| Network | capture all same-origin requests and failed resources | tRPC 4xx/5xx, missing chunks, font fetch, unexpected remote egress |
| Console | fail on `error`, hydration error, duplicate key, uncaught exception | current three duplicate-key messages or adapter import error |
| State | loading, empty, warning/stale, blocked, needs-review, failed, success | spinner without explanation, silent ambiguity, approval hidden in a toast |

Playwright or an equivalent pinned browser harness may be added as a dev
dependency when implementation begins. Until a checked-in harness exists,
manual browser evidence is labelled **local exploratory**, not CI validation.
Screenshots must include the commit, viewport, route, fixture, and timestamp;
console/network artifacts must include the same run identifier.

## CI contract

The existing `.github/workflows/aios-ui-quality.yml` is the starting point. It
must run on Node 20 with the governing lockfile, then run the quality ladder,
the deterministic build, and the browser slice once the harness is checked in.
The workflow must expose separate step names and preserve raw logs. A green
workflow is required for any UI milestone; a local-only pass is not enough.

The minimum CI artifact set is:

- dependency and runtime versions;
- resolved lockfile and local-package manifest;
- ESLint, TypeScript, warning-baseline, architecture, and fixture logs;
- build log with root/trace/font warnings;
- browser screenshots for all three viewports;
- browser console and network logs; and
- a machine-readable validation summary linked from the modernization run.

## Completion gate for future UI milestones

Ticket 004's IA/design contract and any later UI implementation remain blocked
until all of the following are true:

1. A clean install resolves every dependency from the governing lockfile and
   does not require a sibling checkout.
2. Fonts are local/system-only and an offline production build completes.
3. Turbopack root and file-tracing warnings are removed or narrowly justified.
4. ESLint, TypeScript, warning baseline, architecture, and fixture gates pass
   independently.
5. The tRPC route handler imports successfully and valid seeded overview and
   run-detail requests return typed responses.
6. The browser slice passes all viewports, keyboard/semantic checks,
   screenshot checks, network checks, and console policy.
7. Any remaining warning has an owner, evidence, expiry, and documented
   remediation path; no blocker is hidden in an allowlist.

## Evidence

- [Modernization baseline audit](AUDIT.md) — initial UI, browser, font, and
  toolchain failures.
- [Task-centred UI contract](ADR-003-task-centred-ia-and-accessible-design-system.md)
  — the slice and accessibility acceptance target.
- `.github/workflows/aios-ui-quality.yml` — current Node 20, pnpm, lockfile,
  and UI quality workflow.
- `aios-ui/package.json`, `aios-ui/pnpm-lock.yaml`,
  `aios-ui/pnpm-workspace.yaml`, and root `pnpm-lock.yaml` — current package
  scopes and lockfile divergence.
- `aios-ui/app/layout.tsx` — current Google font fetch path.
- `aios-ui/next.config.ts` — current absence of an explicit Turbopack root.
- `aios-ui/app/api/trpc/[trpc]/route.ts` and
  `aios-ui/server/routers/prompts.ts` — current runtime import and broad
  filesystem-trace surfaces.
- Required context compile completed on 2026-07-13 with UI, testing,
  architecture, and no-mock-echo packets selected.
- Required shadow run `shadow-run-e20f222c-4bff-4d8c-8d84-91f66bfe11b4` was
  trace-only because the baseline worktree was dirty; no shadow output was
  merged or treated as validation evidence.
