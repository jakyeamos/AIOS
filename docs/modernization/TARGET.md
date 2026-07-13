# AIOS V2 Target

**Status:** Accepted v2 target contract
**Date:** 2026-07-13
**Scope:** Product shape, operator experience, architecture, contracts, and
acceptance posture. This document does not implement runtime behavior.

## Outcome

AIOS v2 is the local operator control plane for serious AI-assisted work. A
local user can bring an ambiguous task to a trustworthy closeout without
manually stitching together project identity, workflow choice, context,
execution state, evidence, approvals, and follow-up.

The target is a coherent system rather than a collection of dashboards:

```text
intent → route → packet → run → verify → review → closeout → next action
             ↘ evidence, authority, and provenance at every stage ↗
```

The existing runtime remains the compatibility baseline while this target is
built in a protected v2 branch/worktree. V2 may temporarily expose a new
surface beside v1, but it never introduces a second SQLite authority, a second
logical mutation owner, or permanent dual writes.

## Product principles

1. **Local authority is explicit.** The local operator approves privileged
   effects; agents may execute scoped work and propose changes, but cannot
   self-approve durable truth, egress, migration, deployment, or destructive
   actions.
2. **Evidence precedes confidence.** Every important state is paired with its
   source, scope, freshness, actor, and validation result. Unknown, stale, and
   contradictory evidence stay visible.
3. **One fact, one owner.** Python owns logical state mutation and migration;
   the UI is a local client and projection; files and Git remain authoritative
   for repository truth and authored knowledge.
4. **Vertical slices over subsystem theatre.** A milestone must take one
   operator journey from input through durable evidence and verification.
5. **Reversible progress.** Each write-capable slice has an immutable backup,
   a recorded rollback path, and a deletion list for the implementation it
   replaces.
6. **Context is selected, not dumped.** Packets explain both loaded and
   skipped context, with stale or missing inputs treated as an explicit risk.
7. **Satellites serve the loop.** CTS, business memory, session intelligence,
   quality, and eval enrich a run; none silently becomes a competing product
   or state authority.

## Operator experience

### Primary loop

| Mode | Operator question | Required content | Primary action |
| --- | --- | --- | --- |
| Today | What needs attention now? | active runs, blocked gates, approvals, stale truth, next action | open the responsible item |
| Start work | What am I asking AIOS to do? | project candidates, ambiguity, task family, route rationale, prompt/handoff family, execution surface | confirm route or resolve ambiguity |
| Current run | What is happening? | stage, run lineage, packet, actor, scope, live evidence, failure/blocked state | resume, cancel, or inspect evidence |
| Verify | Is the work trustworthy? | criteria, checks, artifacts, source-backed results, warnings, unresolved deltas | rerun or accept verification evidence |
| Gated review | What effect requires my authority? | proposed writeback/egress/migration/deployment, scope, redaction, risk, alternatives | approve, reject, or return |
| Closeout | What became true? | changed artifacts, checks, approvals, follow-up, rollback reference, next action | close, reopen, or create follow-up |

Daily flow and next-action replay return the operator to Today. Contextual
satellites are reached from a task or run; they are not peer-level primary
navigation.

### State language

Every mode supports the same explicit meanings: loading, empty, healthy/passed,
warning/stale, blocked/ambiguous, needs review, failed, and success/closed.
The UI must name the gate owner, source evidence, freshness, and next valid
action. Color, motion, or a toast alone never communicates authority or failure.

### Route contract

The implementation may choose exact URL names, but it must expose stable route
identities equivalent to `today`, `start-work`, `current-run`, `verify`,
`gated-review`, and `closeout`. Route identity, run id, project id, and packet
id are carried in source-backed fixtures so the UI and Python control plane do
not invent separate state vocabularies.

## Authority and data model

```text
Git repos / PROJECT.md / committed docs ───────┐
Vault and immutable raw sources ────────────────┼─> Python control plane
Hooks and local CLI ───────────────────────────┤     ├─ migration ledger
Local Next UI ── read/propose requests ────────┘     ├─ AIOS_DB
                                                       ├─ run/evidence state
                                                       ├─ approval/writeback state
                                                       └─ operator projections
Context source ──> compiler ──> packets/receipts
Repo source ─────> CTS sidecar ──> contextual projections
```

### Source-of-truth matrix

| Fact or artifact | Canonical owner | V2 rule |
| --- | --- | --- |
| Repository code, config, `PROJECT.md`, committed docs | linked Git repository | AIOS records pointers and evidence; it never reconstructs code truth from SQLite |
| Project identity and repo path | Python project registry plus normalized path evidence | ambiguous names block; path is required for deterministic mapping |
| Sessions, prompts, tool events, artifacts, runs, invocations, approvals, and closeout | Python control plane and `AIOS_DB` | hooks, CLI, and UI adapters call one shared connection/mutation layer |
| Migration version and checksums | Python migration ledger | versioned, checksummed, forward-only, backup-linked; no request-time DDL |
| Human-authored knowledge | local vault/Git files | SQLite stores pointers and review state, not canonical prose |
| Raw business sources | immutable local staging plus metadata | never mutate raw payloads; promotion creates a reviewed artifact |
| CTS nodes/edges/search | per-repo `data/cts` sidecar | derived and rebuildable; no business truth migration |
| Context sources, standards, routing rules | `aios/context`, `.agents/context`, committed config | compiled packets and receipts are reproducible outputs |
| Quality/eval evidence | Python runtime/storage with external contract adapters | evidence is inspectable and linked to the run; portable schemas remain package candidates |

### Control-plane contract

- All main-store connections resolve the same absolute `AIOS_DB` path and set
  `foreign_keys=ON`, WAL, a bounded busy timeout, and explicit timeouts.
- Migrations run outside request handlers with writers quiesced and an
  immutable pre-migration backup recorded before `BEGIN IMMEDIATE`.
- Read-only projections cannot issue DDL or mutate state.
- UI actions are local, POST-only requests bound to a launch capability and
  approval policy; loopback is containment, not authorization by itself.
- Orphaned or ambiguous rows are quarantined with source table, primary key,
  original payload, reason, proposed disposition, and reviewer decision.
- `foreign_key_check` must return zero rows before a write-capable cutover;
  `quick_check=ok` alone is never sufficient.

## Architecture and ownership

### Layers

1. **Entrypoints:** `bin/` hooks and CLI adapters preserve local invocation
   contracts.
2. **Python control plane:** `services/` owns routing, orchestration, storage,
   criteria, approvals, migrations, and durable evidence.
3. **Configuration and context:** `config/`, `aios/context/`, and
   `.agents/context/` define registries and deterministic packets.
4. **Operator UI:** `aios-ui/` renders source-backed projections and requests
   governed actions through the Python boundary.
5. **Sidecars:** CTS, business memory, session intelligence, and contextual
   evaluation enrich the loop without owning the core lifecycle.
6. **External contracts/tools:** extracted repositories are consumed through
   thin adapters; their core logic is not copied back into AIOS.

Dependency direction is inward toward the Python control-plane contracts:
entrypoints and UI adapters may call the control plane; the control plane may
emit projections and evidence; no UI module or sidecar may create a competing
database, schema, route, or promotion authority.

### Subsystem posture

| Area | Target posture |
| --- | --- |
| Runtime, hooks, sessions, routing, invocation, run lifecycle | retain as AIOS core |
| Context compiler runtime | retain in AIOS; validate result/receipt shapes through `context-compiler-contract` |
| Success criteria, standards, quality, eval runtime/storage | retain in AIOS; consolidate evidence vocabulary and consume portable contracts |
| Workflow learning, promotion, writebacks, asset lifecycle | retain and converge on one governed proposal lifecycle |
| Operator UI, projections, search, daily flow, next action | retain as core product surface |
| CTS | retain as AIOS sidecar/incubator; consider a contract/fixture package only after independent adapter proof |
| Business memory/connectors | retain as contextual sidecar/incubator; disabled by default, opt-in egress, review-gated promotion |
| Extracted repositories | adapter-only until tagged release and a second consumer prove an independent boundary |

The detailed matrix and extraction evidence live in [ADR-005](ADR-005-subsystem-ownership-and-parallel-v2-strategy.md) and
`.planning/SUBSYSTEM_EXTRACTION_PLAN.md`.

## Contract surfaces

The first shared fixtures and typed envelopes cover:

- route decision: project candidates, task family, workflow, prompt family,
  execution surface, rationale, ambiguity, and required gates;
- packet receipt: loaded/skipped context, freshness, conflicts, packet id,
  source pointers, and acceptance criteria;
- run lifecycle: run, invocation, session, stage, actor, capability, status,
  evidence, approval, and next action linkage;
- verification: criterion id, check command, result, artifact path, scope,
  timestamp, and failure taxonomy;
- proposal/review: proposed effect, target, data classification, redaction,
  approval state, reviewer, decision, and rollback reference;
- closeout: changed artifacts, checks, approvals, unresolved deltas,
  writeback disposition, and next action.

These envelopes are shared as fixtures between Python and TypeScript before
they become a public package. A contract is extracted only when it has stable
ownership, focused tests, a tagged release, and an independent consumer.

## UI and accessibility target

The v2 UI uses one coherent design system: a small spacing and type scale,
semantic landmarks, native controls, explicit focus states, labelled tables,
source/freshness metadata, and state-specific empty/error/approval content.
Interactive components define default, hover, focus, active, disabled, loading,
and error behavior. Motion is limited to state feedback and respects reduced
motion.

Acceptance covers 375×812, 768×1024, and 1440×900; keyboard-only and pointer
paths; landmarks, labels, table semantics, live status, focus order, contrast,
console, network, and screenshot evidence. No redesign milestone starts until
ADR-004's clean-install, local-font, explicit-root, independent quality-gate,
runtime, and browser preconditions are green.

## Security, privacy, and observability

- Raw prompts, tool events, filesystem paths, artifacts, vault pointers, and
  backups are private local data by default.
- Connectors and external LLM egress are disabled by default. Any approved
  egress records provider, purpose, classification, consent, redaction result,
  payload hash, and outcome before transmission.
- Every meaningful run leaves inspectable route, packet, evidence, approval,
  closeout, and next-action traces. Missing or stale receipts are warnings, not
  silently inferred success.
- Recovery is a restore operation from an immutable backup or a route/pointer
  switch; untested destructive down migrations are not part of the target.

## Target quality bar

The audit's provisional scores are the baseline. The target is a measured
acceptance bar, not a promise that every dimension reaches five immediately.

| Dimension | Baseline | Target | Evidence required |
| --- | ---: | ---: | --- |
| Product coherence | 3 | 5 | one loop, contextual satellites, coherent closeout and next action |
| Correctness and data integrity | 1 | 4 | zero FK violations, migration ledger, restore and reconciliation proof |
| Architectural coherence | 2 | 4 | one mutation owner, explicit adapters, no competing bootstrap/route contracts |
| Maintainability | 2 | 4 | bounded modules, deleted duplicate paths, dependency and architecture checks |
| Testability | 2 | 4 | deterministic Python/UI checks plus seeded browser fixtures |
| Security and privacy | 2 | 4 | capability/approval enforcement, egress classification, audit evidence |
| UI quality and accessibility | 1 | 4 | WCAG 2.2 AA-oriented browser, keyboard, semantic, contrast, and responsive proof |
| Operability | 2 | 4 | replayable closeout, recovery drill, inspectable receipts, no hidden blockers |
| Developer experience | 2 | 4 | one package posture, reproducible commands, clear setup and architecture docs |

## Non-goals

- hosted or remotely authoritative AIOS;
- multi-user identity, RBAC, tenants, remote workers, or synchronization;
- a new frontend framework or component library without an evidence-backed
  need;
- a second database, direct UI DDL, permanent dual writes, or silent schema
  repair;
- extracting CTS, business memory, eval runtime, or session intelligence
  solely because the directory is large;
- treating cached dependencies, a one-off browser render, or a green static
  build as reproducible validation;
- automatic promotion of raw business sources, prompts, skills, workflows,
  standards, or vault pages.

## Definition of target acceptance

The target is ready for cutover only when the execution plan's final gates are
green: canonical state is migrated and restore-tested, the v2 vertical loop is
browser-proven across all required states and viewports, approvals and egress
are enforced, every migrated consumer has one owner, stale implementations are
deleted, and the remaining risks are explicit in project truth.
