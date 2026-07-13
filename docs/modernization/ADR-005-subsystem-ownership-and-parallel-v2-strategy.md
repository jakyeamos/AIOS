# ADR-005: Subsystem Ownership and Parallel V2 Migration Strategy

**Status:** Accepted v2 modernization strategy<br>
**Date:** 2026-07-13<br>
**Scope:** AIOS subsystem ownership, consolidation posture, and migration
strategy. This decision does not move code or change runtime behavior.

## Decision

AIOS v2 will use a **parallel v2 implementation with progressive migration**.
“Parallel” means a new, coherent operator/product surface and bounded internal
contracts can be built beside the current surface while it is being proven. It
does **not** mean a second SQLite authority, a second mutation owner, or
permanent dual writes.

The current runtime remains the compatibility baseline while v2 is built in a
protected branch/worktree. V2 starts with read-only projections and vertical
operator slices, then earns write-capable behavior only after the ADR-002
state/migration gates and ADR-004 validation gates pass. Each migrated slice
must have one owner, one source of truth, a rollback path, and a deletion list
for the replaced path.

## Why the other strategies are rejected

| Strategy | Strength | Blocking risk | Decision |
| --- | --- | --- | --- |
| Deep refactor in place | Smallest visible surface change | 557 persisted FK violations, divergent schema/DDL owners, UI validation failures, and overlapping subsystem contracts make rollback and blame ambiguous | Reject for v2 foundation |
| Parallel v2 with progressive migration | Allows a coherent UI/runtime boundary while preserving a runnable baseline and reversible vertical slices | Requires disciplined ownership and temporary compatibility routing | **Select** |
| Clean rewrite with data/contract migration | Maximum freedom to simplify the product | Reimplements valuable domain rules and external contracts while data provenance and migration safety are not yet proven | Reject for now; reconsider only with a tested preservation/migration rehearsal |

The chosen strategy is therefore a **parallel surface, single authority** plan:
the v2 shell may coexist temporarily with v1 routes, but both read through the
canonical state boundary and only the Python control plane owns logical
mutation and migration.

## Retain, adapt, and retire matrix

| Subsystem | V2 posture | Owner and boundary | Consolidation / extraction decision | Required evidence before migration |
| --- | --- | --- | --- | --- |
| Local runtime, hooks, session lifecycle | **Retain as core** | Python `bin/`/`services/` and `AIOS_DB`; local identity, session continuity, and closeout remain AIOS-owned | Do not split; define a hook/event contract only if a real non-AIOS producer appears | ADR-002 connection/migration owner; session/run fixtures; restore and replay proof |
| Workflow routing, orchestration, invocation, native commands | **Retain as core** | Python workflow registry and runtime own route, packet, invocation, stage, and handshake state | Consolidate around one route-decision object; possible future contract package only for stable handshake schemas | Route fixtures consumed by start-work, invocation, packet, eval, and UI projections |
| Context compiler runtime | **Retain in AIOS; adapt to contract package** | AIOS owns context-root selection, ranking, receipts, and writebacks; `context-compiler-contract` validates result/receipt shapes | Keep runtime in AIOS; do not reintroduce validator logic; tagged external dependency after fixture rehearsal | External context-root/routing fixtures and tagged dependency consumption |
| Success criteria, standards health, quality gates | **Retain as core; consolidate contracts** | AIOS owns registry policy, criteria evaluation, SQLite/artifact writes, and governance | Share one evidence/finding vocabulary with extracted quality contracts; do not create another evaluator | Fixture-backed evaluator API and one shared finding/evidence adapter |
| Agent eval, harness, peer traces, shadow branches, corpus/TMCP benchmark | **Retain runtime/storage as core** | AIOS owns eval tables, worktrees, contamination checks, local context profiles, operator projections, and CLI lifecycle | Keep portable schemas/templates/fixtures in `agent-eval-contract`; no runtime repo split yet | Tagged consumption plus a second non-AIOS consumer; clean-room fixture run |
| Workflow learning, promotion, governed writebacks, asset lifecycle | **Retain as core; merge lifecycle concepts** | AIOS owns proposals, approvals, promotion, rollback, and learning signals | One governed proposal lifecycle; reusable proposal schema may become a contract package later | Stable event taxonomy and lifecycle fixtures across prompt/skill/workflow proposals |
| Session intelligence and helper telemetry | **Retain as core satellite** | Python session providers, redaction, candidates, implementations, and helper telemetry remain tied to hooks, sessions, and daily flow | Keep in AIOS; expose contextual projections and a stable event/result contract, not a standalone repo | Provider fixture matrix, redaction-before-writeback proof, and telemetry-backed helper review |
| Operator UI and projections/search/daily-flow/next-action | **Retain as core product** | `aios-ui/` presents AIOS-owned projections; Python remains the domain/state owner | Share JSON fixtures/contracts between Python and TypeScript; do not extract the product UI | ADR-003 IA plus ADR-004 clean install, runtime, browser, and console gates |
| CTS repository intelligence | **Retain as AIOS sidecar / incubator** | `services/cts`, `data/cts`, AIOS project registry, and local MCP/CLI wrappers remain coupled | No physical repo split. Consider a future `cts-contract` fixture/schema package before any runtime extraction | Registry adapter, configurable graph root, isolated fixture repos, query/impact/MCP tests, stable result envelope |
| Business memory/wiki and source connectors | **Retain as contextual sidecar / incubator** | `services/business`, immutable staging, candidate wiki pages, local SQLite metadata, and approval-gated promotion remain AIOS-owned | Keep connectors disabled by default; do not make business memory a v2 primary mode or extract it while privacy/LLM boundaries evolve | Source/consent/redaction fixtures, candidate-to-promotion proof, and explicit connector decisions |
| Extracted contract/tools | **Adapt only** | AIOS adapters consume `context-compiler-contract`, `quality-evidence-contract`, `agent-eval-contract`, `repo-quality-certifier`, and Research Domain Writing | Do not copy their core logic back into AIOS; move local paths to tagged/registry dependencies when release proof allows | Versioned dependency/release checks and adapter compatibility tests |
| Direct UI DDL, divergent bootstrap, duplicate route/state contracts | **Retire after migration** | Replaced by ADR-002 storage owner and ADR-003/004 operator contracts | Delete only after every consumer migrates and restore/replay proof passes | Migration ledger, zero FK violations, consumer inventory, and clean deletion diff |

### Business memory disposition

Business memory remains useful, but it is not part of the v2 critical path. Its
safe role is contextual retrieval and reviewable candidate generation. Raw
sources remain immutable, generated pages remain candidates until promoted,
connectors remain disabled unless explicitly configured, and LLM use remains
opt-in with the privacy/egress rules from the v2 trust boundary. This prevents a
rich but still-evolving business ingestion path from defining the core operator
loop.

### Extracted package disposition

The already-extracted repositories are evidence that contract extraction can
work, not a mandate to split every subsystem. AIOS keeps thin adapters and
integration state. A local path dependency is a development bridge, not the
final release boundary; switching to a tag/registry requires a release,
compatibility, and clean-install proof.

## Progressive migration and cutover posture

### Wave 0 — boundary and fixture foundations

- Freeze the ownership matrix and record one owner for every state/projection.
- Create shared JSON fixtures for route decisions, run stages, evidence,
  approvals, next actions, and operator projections.
- Reconcile package and contract dependencies without changing user behavior.
- Implement the ADR-002 migration/quarantine and ADR-004 validation gates before
  any write-capable v2 slice.

### Wave 1 — read-only v2 shell

- Build the Today/Current Run shell from existing source-backed projections.
- Keep v1 routes available as a compatibility fallback, but do not duplicate
  writes or state stores.
- Exercise the Ticket 004 browser journey with seeded, empty, blocked, and
  approval-required fixtures.

### Wave 2 — governed vertical slice

- Add Start work → Verify → Gated review → Closeout against the canonical
  route/run/evidence records.
- Route all privileged effects through the Python mutation/approval owner.
- Keep rejected/returned work in the same run lineage and make rollback a
  restore/re-route operation, not a hidden inverse mutation.

### Wave 3 — contextual satellite migration

- Move projects, knowledge/search, session intelligence, business memory, CTS,
  eval, learning, and quality views behind the v2 modes as contextual
  drill-downs.
- Migrate one consumer family at a time and delete duplicate projection or
  route logic once its replacement has independent evidence.

### Wave 4 — cutover and deletion

- Make v2 the default entry point after the full quality/browser/data gates are
  green for a sustained acceptance run.
- Retain a read-only v1 fallback only for the documented rollback window.
- Remove compatibility flags, duplicate writes, obsolete routes, stale
  dependencies, old table/bootstrap paths, and superseded documentation.
- Close the migration with a clean diff review, adversarial review, restore
  drill, and updated project truth.

## Rollback rules

- Capture an immutable pre-write or pre-migration backup and record it in the
  ledger before every write-capable cutover.
- Roll back by switching the route/projection pointer or restoring the backup;
  never run an untested destructive “down” migration.
- Keep v1 read-only while a v2 slice is under acceptance; never allow v1 and v2
  to write the same logical fact independently.
- If a slice cannot meet its browser, data, or approval gate, revert that slice
  and preserve its evidence as a blocked run. Do not broaden scope to make the
  failure disappear.

## Deletion ledger

These are expected deletion targets after consumers migrate. None are deleted
by this decision:

| Replace | Eventual deletion |
| --- | --- |
| Fifteen peer-level UI destinations and route-local shells | Old primary-nav entries, compatibility route wrappers, and page-local duplicates after Today/Systems/contextual placement is proven |
| Div/grid table markup and hidden-scroll mobile navigation | Obsolete table/layout CSS and duplicated semantics after the ADR-003 components pass browser/a11y proof |
| Google font fetch and external local-path dependency assumptions | `next/font/google` usage and unresolvable `file:` dependency specs after ADR-004 packaging/font gates pass |
| Distributed runtime DDL and legacy bootstrap authority | Request-time schema helpers and active use of `data/schema.sql` after the migration ledger owns bootstrap/upgrade |
| Hard-coded UI database path and direct UI mutations | Compatibility path/mutation code after the shared Python connection/broker contract is live |
| Temporary v2 route flags and parallel read-model adapters | Flags, shims, and adapter branches after cutover acceptance and rollback expiry |
| Disabled connector skeletons in the v2 primary path | Only if an explicit product decision retires them; retain source history and privacy evidence otherwise |

## Evidence

- [Subsystem consolidation and extraction plan](../../.planning/SUBSYSTEM_EXTRACTION_PLAN.md)
  — current ownership map, maturity states, overlap candidates, and extraction
  gates.
- [CTS boundary audit](../../.planning/CTS_BOUNDARY_AUDIT.md) — AIOS-local
  registry/storage coupling and future contract shape.
- [Eval and benchmark boundary audit](../../.planning/EVAL_BENCHMARK_BOUNDARY_AUDIT.md)
  — runtime/storage coupling and portable contract candidates.
- [Canonical state and migration authority](ADR-002-canonical-state-and-migration-authority.md)
  — one state/mutation owner and quarantine-first migration posture.
- [Task-centred UI contract](ADR-003-task-centred-ia-and-accessible-design-system.md)
  and [reproducible validation contract](ADR-004-reproducible-ui-validation-contract.md)
  — product surface and implementation gates.
- `services/business`, `services/cts`, `services/workflow_orchestration.py`,
  `services/eval_run_service.py`, `services/session_intelligence_loop.py`,
  `services/workflow_learning.py`, `services/success_criteria.py`, and
  `aios-ui/` — current subsystem boundaries and callers.
- Required context compile completed on 2026-07-13 with architecture-boundary
  and workflow-orchestration context selected.
- Required shadow run `shadow-run-3549134b-8392-455d-a7f5-def86890baa5` was
  trace-only because the baseline worktree was dirty; no shadow changes were
  merged or treated as implementation evidence.
