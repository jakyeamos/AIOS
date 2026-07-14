# AIOS V2 Vertical Modernization Plan

**Status:** Accepted execution contract
**Date:** 2026-07-13
**Target:** [TARGET.md](TARGET.md)
**Strategy:** Parallel v2 implementation with progressive migration, as
accepted in [ADR-005](ADR-005-subsystem-ownership-and-parallel-v2-strategy.md).

## How to use this plan

This is the executable modernization sequence: eight vertical milestones plus
one explicit paired-effectiveness gate. It supplements the existing
`.planning/ROADMAP.md`; it does not erase the broader feature roadmap. Each
milestone is a vertical slice with a runnable boundary, named evidence, a
rollback path, and a deletion ledger. The lead agent owns integration and
architecture. Specialist reviews may inspect bounded surfaces, but no parallel
agent may redesign shared foundations independently.

Do not resolve more than one Wayfinder ticket in a session. Do not implement a
later milestone while an earlier hard gate is red. Record progress and command
results in `docs/modernization/PROGRESS.md` once implementation begins.

## Fixed decisions and defaults

These decisions are already resolved and are not implementation-time blockers:

- v2 is single-user, local-first, and loopback-only;
- the Python control plane owns one `AIOS_DB`, one migration ledger, and one
  logical mutation authority;
- the operator loop is Today → Start work → Current run → Verify → Gated review
  → Closeout;
- the UI is a local projection/client, not a remote authority;
- CTS and business memory stay contextual sidecars; extracted tools/contracts
  are adapter-only until independent release evidence exists;
- the UI uses the existing Next.js/React stack unless a measured blocker makes
  replacement necessary; no framework rewrite is assumed;
- the package target is one repository-level pnpm workspace and lockfile;
- fonts are system or committed local assets; build-time network fetches are
  not accepted;
- a pinned Playwright-compatible browser harness may be added when the first
  UI slice needs automated browser proof;
- v1 remains read-only fallback only during the documented rollback window;
  v1 and v2 never write the same logical fact independently;
- modernization acceptance includes a paired AIOS-effectiveness benchmark;
  shadow worktrees provide isolation and trace evidence but are not themselves
  evidence that AIOS outperforms a non-AIOS run.

## Global entry gates

Before Milestone 0 begins:

1. Work from an intentionally clean protected branch/worktree based on the
   current `dev` baseline. Preserve user-owned guidance changes outside the
   modernization commits.
2. Run the baseline command set and record known failures rather than
   attributing them to v2.
3. Compile context with `pnpm context:compile --task ...`; retain the receipt
   and validate it with `pnpm context:validate`.
4. Run the AIOS shadow lane. Dirty-baseline output is trace-only and is never
   treated as implementation proof.
5. Create disposable database, seed, fixture, screenshot, and artifact paths;
   no production credentials or production data are allowed.
6. Freeze the effectiveness benchmark corpus, acceptance criteria, metric
   definitions, and protected baseline SHA before further modernization
   changes. A moving `dev` branch is never used as the benchmark control.

At every milestone boundary, the lead agent reports the exact commands,
results, changed behavior, evidence paths, unresolved risks, and deletion
targets. A blocker-level failure pauses the next milestone.

## Milestone 0 — Freeze boundaries and build shared fixtures

**Objective:** Turn the accepted target into machine-readable route, packet,
run, evidence, approval, and projection fixtures without changing application
behavior.

**Affected systems:** `docs/modernization/`, `docs/evals/`,
`tests/fixtures/`, `services/` contract tests, `aios-ui/` fixture consumers,
`config/` registries, `.planning/ROADMAP.md`, and package/lockfile manifests.

**Dependencies:** ADR-001 through ADR-005; no live migration or UI redesign.

**Preserve / change:** Preserve every current CLI/hook and valid stored shape.
Add explicit envelope schemas and fixture ids; do not add a second runtime
store or mutate the live database.

**Proof:** schema/fixture validation, Python contract tests, TypeScript fixture
type checks, `pnpm context:validate`, architecture checks, and a read-only
daily-flow replay against seeded fixtures.

**Migration / rollback:** No data migration. Delete only fixtures that fail
contract review; source runtime remains untouched.

**Deletion targets:** Duplicate ad hoc route/run/evidence fixture shapes and
temporary names discovered during the inventory, after all consumers point to
the shared envelope.

**Failure modes:** A fixture encodes UI-only state, hides an authority owner,
or diverges from persisted rows. Stop and revise the contract before coding.

**Completion criteria:** Every later milestone has a stable fixture for happy,
empty, blocked, failed, needs-review, and closed states, with an owner and
source pointer for each field.

## Milestone 1 — Establish canonical state and recovery

**Objective:** Make the Python control plane the executable owner of the main
store before any write-capable v2 slice.

**Affected systems:** migration runner/ledger under `bin/` and `services/`,
`schema.sql`, legacy `data/schema.sql`, `bin/init-db.sh`, shared storage
helpers, `aios-ui/server/db.ts` and control-plane adapters, backup/quarantine
artifacts, and migration tests.

**Dependencies:** Milestone 0; ADR-002's quarantine and restore contract.

**Preserve / change:** Preserve valid project, session, prompt, run, artifact,
approval, raw-source, and vault-pointer meaning. Change bootstrap and request
paths so one absolute `AIOS_DB`, one connection policy, and one migration
ledger are authoritative. UI reads through the shared boundary and cannot run
DDL.

**Proof:** sanitized FK fixture; copied-store migration; zero-row
`foreign_key_check`; `quick_check`, `integrity_check`, schema checksum, count
reconciliation, quarantine inventory, backup hash, restore to a disposable
path, and read-only daily-flow replay. Run focused Python migration and
storage tests plus architecture checks.

**Migration / rollback:** Quiesce writers, capture an immutable local backup,
record it in the ledger, transform only deterministic mappings, quarantine
ambiguous rows, and restore the backup on failure. Never invent missing parent
rows or use an untested destructive down migration.

**Deletion targets:** Direct request-time DDL, divergent active bootstrap,
hard-coded UI database path, duplicate connection pragmas, and synthetic
parent repair paths after all consumers pass the new owner.

**Failure modes:** FK violations remain, a path differs between adapters,
quarantine loses original payloads, restore cannot replay, or a hook writes
around the broker. Block all later write-capable work and retain the baseline.

**Completion criteria:** The copied production-shaped store has a versioned
ledger, zero FK violations, a repeatable restore drill, and no active caller
that can mutate or migrate outside the Python owner.

## Milestone 2 — Make UI validation reproducible

**Objective:** Restore ADR-004's deterministic install, compile, runtime, and
browser gates before redesigning the operator surface.

**Affected systems:** root and `aios-ui` package manifests/lockfiles,
workspace config, anti-slop dependency packaging, fonts in `aios-ui/app/`,
`aios-ui/next.config.ts`, tRPC route imports, validation scripts, CI workflow,
and the pinned browser harness.

**Dependencies:** Milestone 0; does not require migrated business rows but
does require a source-backed seeded fixture path.

**Preserve / change:** Preserve existing Next.js/React behavior and valid
TypeScript contracts. Change dependency resolution to one authoritative
workspace/lockfile, remove external sibling-path assumptions, replace network
font fetches with system/local assets, scope Turbopack root/tracing, and make
ESLint, TypeScript, warning baseline, architecture, fixture, build, runtime,
network, and console checks independently visible.

**Proof:** clean offline install; Node 20/pnpm 11.7.0 preflight; independent
ESLint and `tsc`; warning baseline; architecture and anti-slop fixtures;
production build with no forbidden root/font/trace warnings; free-loopback
dev server; valid seeded overview and run-detail requests; browser/keyboard
checks at 375×812, 768×1024, and 1440×900; zero unexplained console errors,
duplicate keys, hydration errors, or same-origin 4xx/5xx responses.

**Migration / rollback:** No main-store migration. Keep the previous nested
install and route as a documented local fallback while the workspace is
proven; revert the packaging change if a clean runner cannot reproduce it.

**Deletion targets:** stale `file:` sibling dependencies, `next/font/google`,
unscoped tracing assumptions, short-circuit lint wrappers, and transitional
lockfile/cache paths after CI proves the new workspace.

**Failure modes:** the clean runner needs a sibling checkout, cached fonts hide
a network fetch, tRPC imports fail, build traces the whole repository, or a
browser path passes with console/network errors. UI implementation remains
blocked; do not weaken a gate.

**Completion criteria:** A clean runner produces a complete, inspectable
quality ladder and seeded browser evidence from the committed repository.

## Milestone 3 — Ship a read-only v2 operator shell

**Objective:** Build the Today → Current run read path and Start work entry
surface from canonical projections, with v1 available only as a read-only
fallback.

**Affected systems:** `aios-ui/app/`, `aios-ui/components/`,
`aios-ui/server/routers/`, `aios-ui/server/aios/`, shared fixtures, design
tokens/styles, route/projection adapters, and browser tests.

**Dependencies:** Milestones 0–2; source-backed projections must be readable
without UI-owned DDL or mutation.

**Preserve / change:** Preserve project/run/evidence provenance and existing
read-only drill-down value. Change primary navigation from peer-level pages to
Today, Start work, and Current run; contextualize search, CTS, knowledge,
quality, and session intelligence; introduce explicit loading, empty, warning,
blocked, and stale states.

**Proof:** seeded happy/empty/blocked fixtures; browser journey through Today,
Start work, and Current run; keyboard and pointer passes; semantic landmarks,
labels, focus, contrast, responsive screenshots, console/network logs, and
architecture/lint/build checks.

**Migration / rollback:** Read-only route/projection pointer switch; no dual
writes. If acceptance fails, route back to v1 read-only and keep v2 artifacts
for diagnosis.

**Deletion targets:** old primary-nav shells, hidden-scroll mobile navigation,
page-local status/table/badge behavior, duplicate route loaders, and stale
read-model adapters after the new shell has independent evidence.

**Failure modes:** UI invents lifecycle state, hides a gate, duplicates source
queries, loses styles at reload, or leaves a console error. Revert the slice;
do not repair by adding a second state store.

**Completion criteria:** An operator can identify current project, stage,
evidence, authority, and next action from the v2 shell at all three viewports,
with no write path enabled.

## Milestone 4 — Complete Start work → Verify as one governed slice

**Objective:** Route a real task into a durable packet/run and verify its work
without breaking provenance or approval boundaries.

**Affected systems:** `services/workflow_orchestration.py`,
`services/execution_strategy.py`, `services/invocation_backends.py`,
`services/success_criteria.py`, `services/aios_cli.py`, context compiler,
packet/run/evidence tables, UI Start work/Current run/Verify routes, and
managed runtime/hook adapters.

**Dependencies:** Milestones 0–3; canonical store and deterministic UI gates
must be green.

**Preserve / change:** Preserve local CLI/hook entrypoints, route rationale,
packet provenance, run lineage, and existing workflow semantics. Change route
selection to a single explicit decision with project ambiguity handling,
prompt/handoff family, execution-surface recommendation, acceptance criteria,
and stage-aware lifecycle states.

**Proof:** route fixtures for clear, ambiguous, unsupported, and high-risk
tasks; packet receipts with loaded/skipped context; managed-run replay;
verification evidence with command/result/artifact; resume after blocked and
partial states; Python tests; UI browser proof through Verify; no unauthorized
mutation or egress side effects.

**Migration / rollback:** New runs use the canonical broker. Existing runs
remain readable and may resume through an adapter. A failed slice is marked
blocked and routed back to the prior run/projection; no state is rewritten to
make a test pass.

**Deletion targets:** heuristic route fallbacks, duplicate prompt/workflow
selection, UI-owned run-state inference, and legacy invocation paths once all
default workflows have the shared route/run envelope.

**Failure modes:** wrong project silently selected, packet omits a required
standard, lifecycle collapses blocked into failed, or verification reports a
green result without a source artifact. Block closeout and retain evidence.

**Completion criteria:** A seeded task can start, execute, verify, block, and
resume with durable route/packet/run/evidence linkage and a truthful next
action.

## Milestone 5 — Add gated review and closeout

**Objective:** Make approvals, writebacks, egress, and closeout first-class
states in the same run rather than hidden side effects.

**Affected systems:** approval/capability services, `improvement_writebacks`,
`memory_writeback_proposals`, workflow learning and promotion, closeout
services, hook-stop/daily-flow/next-action projections, UI review/closeout
routes, and audit/evidence artifacts.

**Dependencies:** Milestone 4; ADR-001 trust gates and ADR-002 broker must be
executable.

**Preserve / change:** Preserve approved local effects, artifact paths,
closeout summaries, and follow-up semantics. Change proposal handling so every
durable truth, policy, asset promotion, egress, migration, deployment, or
destructive effect has target, actor, capability, data classification,
redaction result, evidence, approval state, and rollback reference.

**Proof:** approve, reject, return, stale, and waived fixtures; capability and
loopback negative tests with no side effects; writeback proposal and promotion
tests; egress-block/redaction tests; closeout replay; browser keyboard/dialog
proof; daily-flow and next-action output; security/privacy review.

**Migration / rollback:** Proposal state is append-only. Approved promotion
uses a backup/ledger reference; reject/return changes only proposal state.
Rollback restores the pre-effect backup or switches the projection pointer;
v1 remains read-only during the rollback window.

**Deletion targets:** direct UI mutation routes, approval labels without
enforcement, silent writebacks, duplicated promotion lifecycles, and untracked
follow-up state after the governed flow is proven.

**Failure modes:** UI can self-approve, egress lacks consent/redaction,
closeout claims success without checks, or returned work loses lineage. Stop
the slice and record the failed gate.

**Completion criteria:** A run cannot close as successful without verification,
required approvals, changed artifacts, unresolved deltas, and a next action or
explicit no-follow-up state.

## Milestone 5A — Measure paired AIOS effectiveness

**Objective:** Establish whether the modernized AIOS operating loop produces
measurable lift over a non-AIOS control before satellite promotion or v2
cutover.

**Affected systems:** `docs/evals/`, the benchmark task corpus and acceptance
criteria, `services/eval_run_service.py`, `services/shadow_branch_runner.py`,
benchmark orchestration/CLI, `eval_runs`, `eval_scores`,
`shadow_branch_runs`, and comparison artifacts.

**Dependencies:** Milestones 0–5. The benchmark corpus, metric definitions,
and protected baseline SHA are defined at the global entry gate; paired
execution begins only after the canonical route, packet, run, evidence,
approval, and closeout contracts are executable.

**Preserve / change:** Run the same task from the same starting SHA with the
same model, effort, tools, budget, and acceptance criteria. The control runs
without AIOS routing/context; the treatment runs with the full AIOS loop.
Feature ablations may disable context packets, second brain, success criteria,
subagents, model routing, personal corpus, or project truth. Worktrees are
ephemeral isolation paths; reports and run identifiers are the durable output.

**Proof:** For every selected task, persist paired control/treatment run IDs,
start SHA, prompt and context hashes, model/tool settings, and contamination
checks. Capture task-quality score, acceptance/test/lint/typecheck results,
user corrections, token usage, tool calls, wall-clock time, cost when
available, context loaded, model used, and safety failures. Produce a
per-task and aggregate comparison report, include ablation scorecards for
high-impact claims, and require independent or blinded quality review.

**Migration / rollback:** Evaluation artifacts are append-only and use the
canonical store. Temporary worktrees are deleted after evidence capture.
Failed or incomplete pairs remain explicitly marked as insufficient evidence;
they cannot be converted into a positive result or promotion decision.

**Deletion targets:** Long-lived benchmark worktrees, unpaired shadow-only
comparison paths, and duplicate metric serializers after the paired report
and replay path are proven.

**Failure modes:** Control and treatment start from different SHAs, model or
tool settings drift, the baseline is dirty, only one side completes, quality
scoring is unblinded or missing, contamination is detected, or a result has
no durable evidence. Block the effectiveness gate and record the gap.

**Completion criteria:** The selected benchmark corpus has complete paired
results, no critical safety regression, a reviewable per-task/aggregate report,
and an explicit promote, revise, or defer decision. EVAL-03, EVAL-04, and
EVAL-06 are updated from evidence rather than implementation presence.

## Milestone 6 — Migrate contextual satellites behind the core loop

**Objective:** Move contextual projections one consumer family at a time while
keeping the core run, state, and approval contracts singular.

**Affected systems:** project/truth and grounded query routers, context
compiler/receipts, session intelligence, quality and success-criteria views,
agent eval/harness, CTS, business memory, workflow learning, and their UI
contextual drill-downs.

**Dependencies:** Milestones 5 and 5A; each satellite must satisfy the
ownership and fixture evidence in ADR-005. Satellite work may remain
read-only or adapter-scoped while the effectiveness decision is pending, but
no satellite promotion or v2 cutover may bypass Milestone 5A evidence.

**Preserve / change:** Preserve useful local projections, redaction, raw-source
immutability, CTS rebuildability, eval evidence, helper telemetry, and
review-gated learning. Change navigation and adapters so satellites consume
route/run/evidence contracts instead of inventing lifecycle or mutation state.

**Proof:** one fixture and one consumer migration per satellite; contract
compatibility tests; CTS registry/fixture/query tests; business source/consent/
redaction/promotion tests; eval clean-room fixture; session-intel telemetry
checks; UI contextual browser paths; architecture/dead-code checks.

**Migration / rollback:** Satellite state is derived or append-only wherever
possible. Rebuild CTS from source, restore business/eval backups when needed,
and switch the affected projection adapter back to its prior implementation.
Do not move raw private sources or create synthetic core rows.

**Deletion targets:** duplicate projections, page-local search/quality/status
logic, stale adapter branches, unneeded connector skeletons only after an
explicit product decision, and any copied external package core logic.

**Failure modes:** a satellite becomes a hidden authority, raw data crosses an
egress boundary, an external contract drifts, or telemetry is mistaken for
proof of correctness. Keep the satellite contextual and block the consumer.

**Completion criteria:** Every migrated satellite has a named owner, one
contract boundary, source-backed fixtures, an independent rollback path, and
no duplicate lifecycle or promotion authority.

## Milestone 7 — Cut over, adversarially review, and delete replaced paths

**Objective:** Make v2 the default local operator surface only after full
data, security, UI, performance, and operational evidence passes.

**Affected systems:** route/projection pointers, compatibility flags, old UI
routes/components, dependency manifests, bootstrap/schema paths, CI artifacts,
docs, deployment/runbooks, and project truth.

**Dependencies:** Milestones 0–6 and the Milestone 5A effectiveness decision;
no unresolved P0/P1 findings; all ADR-004 and ADR-002 gates green for a
sustained acceptance run.

**Preserve / change:** Preserve Git history, valid data, CLI/hooks, raw sources,
approvals, run lineage, and a documented read-only rollback window. Change the
default entry point to v2 and remove temporary compatibility code only after
consumer inventory and cutover evidence are complete.

**Proof:** full Python/UI quality ladder; clean install/build; seeded and empty
browser matrix; keyboard/semantics/contrast; same-origin network and console
logs; performance comparison; migration/restore drill; security/privacy,
architecture, maintainability, dead-code, and documentation reviews; fresh
adversarial review from a separate thread or reviewer.

**Migration / rollback:** Capture the final immutable backup and ledger entry.
Switch the default route/pointer, keep v1 read-only for the documented window,
and restore or switch back if a P0/P1 regression appears. Never delete the
rollback source before the window expires and its evidence is recorded.

**Deletion targets:** obsolete flags/shims, duplicate routes and projections,
direct UI DB/mutation paths, divergent bootstrap and runtime DDL, stale
dependencies, superseded docs, and temporary fixtures not used by acceptance.

**Failure modes:** a hidden consumer remains, a migration cannot restore, a
browser error is suppressed, a package is only available from a sibling path,
or adversarial review finds an authorization/data-integrity regression. Keep
v2 non-default and return to the affected slice.

**Completion criteria:** v2 is the default coherent system, the old path is
removed or explicitly retained only for rollback, all remaining risks are
documented, and `.tracker/PROJECT_TRUTH.md` reflects the shipped state.

## Cross-milestone deletion ledger

| Replaced path | Delete after |
| --- | --- |
| Distributed runtime DDL and legacy bootstrap authority | Milestone 1 zero-FK and restore proof |
| External sibling dependency, Google font, unscoped root/tracing | Milestone 2 clean install/build proof |
| Peer-level UI destinations and hidden-scroll mobile nav | Milestone 3 browser/a11y proof |
| Heuristic routing and duplicate packet/run/evidence shapes | Milestone 4 contract and resume proof |
| Direct UI mutation and unenforced approval labels | Milestone 5 negative security tests |
| Unpaired AIOS effectiveness claims and long-lived benchmark worktrees | Milestone 5A paired report and ephemeral-worktree cleanup |
| Duplicate satellite projections and copied external package logic | Milestone 6 consumer-by-consumer proof |
| Flags, shims, old routes, stale dependencies, and superseded docs | Milestone 7 cutover and rollback-window expiry |

## Final review checklist

Before declaring modernization complete, the lead agent must:

1. Re-read `TARGET.md`, all ADRs, and this plan against the final diff.
2. Run the complete quality, migration, browser, security, privacy,
   accessibility, performance, observability, and paired-effectiveness
   checks.
3. Search for stale flags, duplicate route/state contracts, direct UI DDL,
   sibling-path dependencies, disabled checks, skipped tests, TODO migration
   shims, and unused packages.
4. Compare documentation to implementation and update project truth.
5. Run a fresh adversarial review that classifies findings P0–P3 and fixes all
   confirmed P0/P1 findings before cutover.
6. Record the final backup, restore drill, rollback window, deletion ledger,
   verification commands, screenshots, console/network artifacts, the paired
   AIOS comparison report, and known deferred risks.
