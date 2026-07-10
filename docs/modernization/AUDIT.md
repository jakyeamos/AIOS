# AIOS V2 Modernization — Baseline Audit

**Date:** 2026-07-10

**Scope:** Read-only baseline for the AIOS modernization. No application code,
live database records, or user-owned worktree changes were altered.

**Baseline:** `dev` at `94df9e0` before this audit's documentation commit. The
working tree was already dirty, so AIOS shadow evidence is route-only rather
than a clean branch comparison.

## Executive verdict

AIOS has a real, valuable operating loop and a substantial executable test
suite. It is not ready for a broad rewrite or UI redesign to begin in place.
The v2 must first decide its operating and trust boundary, then establish
canonical state/migration ownership and a reproducible verification contract.

The immediate risks are durable-data integrity, conflicting schema authority,
implicit local-only trust for state-changing UI APIs, and a UI toolchain that
cannot currently complete lint/type validation or an offline production build.

## Current product and principal journeys

The clearest current value is the daily-use loop:

```text
doctor → start-work → daily-flow → next-action → closeout evidence
```

The UI exposes this through the Command Center, task router/control plane, run
inspector, projects, query/search, workflows, automations, settings, prompts,
and supporting operator surfaces. The browser successfully loaded the Command
Center, Control Plane, and Run Inspector during this audit.

The product is presently both a personal local control plane and a broad
governance console. That ambiguity is material: navigation exposes fifteen
peer destinations, while the daily loop is not consistently the primary
interaction path.

## Verification baseline

| Surface | Result | Evidence |
| --- | --- | --- |
| Context compiler | Pass | `pnpm context:validate`; context tests 16/16; no-op scan 3/3; wiki tests 8/8. |
| Python tests | Pass | `uv run pytest -q`: 1,158 passed in 66.25s. |
| Smoke and dead-code | Pass | `pnpm smoke` and `pnpm dead-code` passed after using a temporary dependency cache; the initial failures were sandbox-cache access only. |
| Python lint | Fail | Four current diagnostics in `services/business/lint.py` and `services/business/pipeline.py`. |
| Python type check | Fail | Three current optional `ModuleSpec`/loader diagnostics in `tests/test_purge_noise_patterns.py:19-21`. |
| UI architecture lint | Pass | `pnpm lint:architecture`: 121 modules / 255 dependencies, no violations. |
| UI lint and TypeScript | Blocked | `pnpm lint` cannot start ESLint or `tsc` because the installed local `eslint-plugin-anti-slop` lacks `src/rules/no-arbitrary-z-index.mjs`. |
| UI production build | Blocked | `pnpm build` fails while fetching Google-hosted Geist and JetBrains Mono fonts. It also warns that Next/Turbopack inferred the wrong root from multiple lockfiles and traces the whole project through `next.config.ts`. |
| Doctor | Pass | `aios doctor --json`: 10/10 checks passed. It proves reachability, not database integrity or recovery. |
| Daily loop on copied DB | Pass | `scripts/aios-readiness-check.py` against a temporary copy passed all nine routing, ambiguity, daily-flow, search, and next-action checks. |

The audit used a copied database for the daily-loop suite. It did not create
runs or mutate the live database beyond the AIOS routing trace required by the
repository's shadow workflow.

## Browser evidence

The initial desktop and 375px mobile Command Center both rendered. The mobile
navigation changed into the expected abbreviated horizontal strip, which makes
the large navigation set harder to scan rather than clarifying priority.

The Control Plane rendered a task router, workflow/agent registries, approval
queue, findings, run history, and packet ledger. The Run Inspector rendered,
but the browser console emitted duplicate React key errors for
`workflow_agent_control.explicit_handshake`, `testing.trust_signal`, and
`architecture.boundary_enforcement`.

A later local development request to
`/api/trpc/controlPlane.runDetail` returned `500` because
`@trpc/server/adapters/fetch` could not be resolved; a retry returned `200`.
After that development-runtime error, the local app lost its stylesheet on
reload. Therefore tablet layout is **inconclusive**, not a passing responsive
check. The production build could not supply a second validation path because
it requires external font downloads.

## Data, schema, and recovery evidence

### Confirmed state

- The live `data/aios.db` is 51 MiB, uses WAL mode, and passed `quick_check`.
  A disposable copy contains 106 tables, 93 indexes, and 3 views.
- `PRAGMA foreign_key_check` on that copy returned **555 persisted
  violations**: 328 `quality_pipeline_runs → projects`, 180 orchestration
  records → `sessions`, and 47 `shadow_branch_runs → eval_tasks`. The source
  of those orphaned records is not yet established.
- Main schema ownership is fragmented. Root `schema.sql` has 86 tables;
  `data/schema.sql` has 43. They differ materially: 44 tables are root-only
  and `patterns` exists only in `data/schema.sql`.
- `bin/init-db.sh` bootstraps from the divergent `data/schema.sql`, while the
  actual live database has 12 root-schema tables absent and 32 live-only
  tables. Python orchestration, business memory, session import, and UI startup
  also issue runtime DDL.
- Hook processes honor `AIOS_DB`, while the UI directly opens
  `~/AIOS/data/aios.db`; their configuration contract is not unified.
- No tracked backup/restore/PITR workflow or restore drill was found. The
  documented `init-db --force` deletes the existing database before recreation.

### Required preservation boundary

Preserve the semantics and provenance of projects, sessions, prompts,
artifacts, tool events, patterns, orchestration/evaluation records, raw
business sources, and consent/sensitivity metadata. V2 migration must use the
actual live schema and filesystem references, reconcile orphaned foreign keys,
and explicitly choose a single schema/migration and SQLite-connection owner.

## Trust, privacy, and external-contract evidence

- The UI tRPC context has only a database handle; all procedures are
  `publicProcedure`, and the GET/POST API handler adds no identity or origin
  check. It exposes state-changing mutations. Unauthorized remote access is an
  **inferred deployment risk**, not a confirmed incident, because external
  exposure was not tested.
- Prompt hooks retain full prompt text; the current store has 1,673 prompt
  records. Session import persists normalized messages, tool calls, and
  commands before later summary-time redaction.
- Business LLM use is opt-in. The API provider can send metadata and up to
  6,000 source-text characters without calling the available redactor. Current
  evidence shows three compile runs with `llm_enabled=0`; no actual external
  egress was observed.
- Gmail, Discord, and X connectors are disabled and remain skeletons. Manual
  business ingestion is active with four raw-source records. Treat connector
  activation as an explicit product choice, not a presumed modernization task.

## UX and accessibility evidence

- Current contrast tokens fall below AA: `--text-secondary` is 3.60:1 and
  `--text-muted` is 1.76:1 on the primary surface; both appear in small
  labels, table headers, and body copy.
- Table-like UI is commonly div/grid markup without table/row/cell semantics;
  settings inputs also lack programmatic labels.
- Workflow canvas stages are mouse-only clickable `div` elements. Search,
  tab-like controls, workflow skill toggles, and active navigation lack key
  programmatic states.
- At narrower widths, navigation becomes scrollbar-hidden horizontal scrolling
  and several data surfaces require 480–1080px horizontal scrolling without an
  alternate compact view.

## Provisional baseline score

| Dimension | Score / 5 | Basis |
| --- | ---: | --- |
| Product coherence | 3 | Daily loop is clear; console IA is not task-centred. |
| Correctness and data integrity | 1 | 555 persisted FK violations and no canonical migration path. |
| Architectural coherence | 2 | Broad, functional surface but competing schema/configuration ownership. |
| Maintainability | 2 | Rich codebase and clean UI boundaries; broken lint/type baseline and duplicated ownership. |
| Testability | 2 | Strong Python suite, but UI lint/type and production build cannot verify. |
| Security and privacy | 2 | Local-first intent is valuable; trust boundary and sensitive-data egress remain implicit. |
| UI quality and accessibility | 1 | Material contrast, semantics, keyboard, responsive, and console-error gaps. |
| Operability | 2 | Doctor and copied daily loop pass; recovery and state integrity are not proven. |
| Developer experience | 2 | Core tests pass, but toolchain reproducibility is currently broken. |

## Prioritized writeback candidates

| Severity | Candidate | Reason |
| --- | --- | --- |
| P1 | Canonical data/migration authority | Schema divergence, runtime DDL, FK violations, and no recovery proof make broad persistence changes unsafe. |
| P1 | Operator trust/deployment decision | Public mutation procedures need an explicit local-only or authenticated remote contract before UI expansion. |
| P1 | Reproducible UI validation contract | Lint/type validation and production build are currently blocked; a redesign cannot rely on them. |
| P1 | Accessible task-centred UI target | Current contrast, semantics, keyboard support, and mobile navigation do not meet the v2 bar. |
| P2 | Client/runtime error cleanup | Duplicate React keys and intermittent missing tRPC module require root-cause investigation before UI acceptance claims. |
| P2 | Private-data/LLM egress policy | Redaction and consent enforcement must be explicit before connector or LLM expansion. |

## Preserve, migrate, and retire posture

**Preserve:** local-first provenance, the daily loop, deterministic routing,
governed approvals/writebacks, durable agent-run evidence, and the useful
operator drill-down model.

**Explicitly migrate:** live SQLite state and cross-store pointers; orphaned
foreign-key records; path/configuration behavior; retained CLI and hook
contracts; raw-source retention and consent handling.

**Retire only after all consumers migrate:** divergent SQL bootstrap files,
versionless distributed runtime DDL, accidental duplicate state paths, stale
operator surfaces, and disabled connector skeletons that do not support the
chosen v2 operating loop.

## Next decision

Resolve [Choose the V2 Operating Loop and Trust Boundary](../../.wayfinder/aios-modernization/tickets/002-choose-v2-operating-loop-and-trust-boundary.md). The recommended default to assess is a single-user, local-first control plane with explicit loopback-only mutation access; this is an inference from the present product, not yet an approved v2 decision.
