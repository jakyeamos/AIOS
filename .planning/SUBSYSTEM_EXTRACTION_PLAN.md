# AIOS Subsystem Consolidation And Extraction Plan

**Created:** 2026-06-05
**Owner:** AIOS architecture governance
**Status:** Living consolidation and extraction artifact
**Related:** [FUNCTIONALITY_MAP.md](/Users/jakyeamos/AIOS/.planning/FUNCTIONALITY_MAP.md), [FUNCTIONALITY_PLAN.md](/Users/jakyeamos/AIOS/.planning/FUNCTIONALITY_PLAN.md), [PROJECT.md](/Users/jakyeamos/AIOS/PROJECT.md)

## Purpose

AIOS is intentionally broad: it is the local operating layer for agent workflows, context, memory, quality gates, learning, and operator visibility. That breadth is useful while the product is still discovering the right contracts, but it can become a drag if reusable capabilities remain buried inside one repo after they stabilize.

This plan defines how to decide when AIOS functionality should be consolidated, stay inside this repository, become a stricter internal module, become a reusable package, or move into an independent repository used by AIOS and other projects.

The default posture is **monorepo incubator first, extraction after contract maturity**.

Consolidation comes before extraction. When two subsystems overlap, the first decision is whether to merge, share a lower-level contract, or clarify ownership boundaries. Repo splitting should not preserve accidental duplication.

## Guiding Principles

1. AIOS remains the orchestrating product.
2. Split by runtime boundary, data ownership, and reuse pressure, not by vague feature labels.
3. Do not extract a subsystem while its core contracts still change in lockstep with AIOS workflows.
4. Prefer internal boundaries before repository boundaries.
5. Every extracted subsystem needs explicit APIs, tests, versioning, ownership, and migration evidence.
6. Local-first behavior and reviewable governance remain non-negotiable across any split.

## Maturity States

| State | Meaning | Expected Action |
| --- | --- | --- |
| `incubating` | The subsystem is still product-shaped and changes with AIOS workflows. | Keep in AIOS; improve local module boundaries. |
| `bounded` | Inputs, outputs, storage ownership, and caller expectations are identifiable. | Add stronger interfaces, fixtures, and architecture checks. |
| `package-ready` | The subsystem has stable contracts, focused tests, and at least one plausible non-AIOS caller. | Consider an internal package or workspace package. |
| `repo-ready` | Independent versioning, release notes, issue ownership, and downstream upgrade flow are justified. | Consider separate repo extraction. |
| `externalized` | The subsystem lives outside AIOS and AIOS consumes it through a versioned dependency. | Maintain compatibility notes and migration docs here. |

## Consolidation Posture States

| State | Meaning | Expected Action |
| --- | --- | --- |
| `none-known` | No meaningful overlap is currently identified. | Keep monitoring as nearby work evolves. |
| `watch` | Some adjacent overlap exists, but the boundary may be acceptable. | Record the overlap and avoid premature abstractions. |
| `clarify-boundary` | Two or more subsystems share concepts, data, or responsibilities without a crisp owner. | Define ownership, adapters, and source-of-truth rules. |
| `share-contract` | Subsystems should remain separate but consume one shared schema, event model, or route/evidence contract. | Create or nominate the shared contract before extraction. |
| `merge-candidate` | Overlap appears high enough that separate subsystem identity may be accidental. | Plan consolidation before packaging or repo extraction. |
| `consolidated` | The overlap has been resolved by merging or by a durable shared contract. | Keep compatibility notes and update downstream phase goals. |

## Extraction Decision Gates

A subsystem should not leave the AIOS repo until most of these are true:

- It has a narrow public contract that can be described without AIOS internals.
- It has tests that exercise the contract without requiring a full AIOS runtime.
- It has stable storage boundaries or a migration layer if it owns data.
- It can fail independently with actionable diagnostics.
- It has clear consumers beyond one incidental AIOS call path.
- Its release cadence can differ from AIOS without blocking daily work.
- Its configuration and secrets model remains local-first and reviewable.
- The extraction reduces complexity more than it adds dependency coordination.

## Candidate Subsystems

| Subsystem | Current Home | Current State | Consolidation Posture | Extraction Posture | Main Blockers | Next Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Context compiler core | `tools/context-compile.mjs`, `aios/context/` | `bounded` | `clarify-boundary` with memory, CTS, and grounded query | Good first package candidate after contract cleanup. | Mixed CLI, file routing, receipts, and AIOS-specific context assumptions. | Contract tests for task input, selected packets, skipped context, and receipt output. |
| Success criteria engine | `services/success_criteria.py`, `config/success-criteria/` | `bounded` | `share-contract` with standards health, quality gates, and evals | Strong candidate for reusable package once registry contracts stabilize. | Tight coupling to AIOS evaluation storage and hook lifecycle. | Fixture-backed evaluator API independent of AIOS SQLite writes. |
| Workflow registry and routing | `services/workflow_orchestration.py`, `config/workflows/` | `incubating` | `share-contract` with invocation, command, and strategy surfaces | Keep in AIOS for now. | Product behavior and routing policy are still evolving together. | Stable route decision schema and misroute evaluation history. |
| Invocation backend contracts | `services/invocation_backends.py`, managed runtime code | `bounded` | `share-contract` with workflow routing and native command execution | Possible package later, but only after native workflow command work settles. | Backend capabilities, harness handshakes, and runtime reports are still changing. | Versioned backend contract fixtures and compatibility tests. |
| CTS repository intelligence | `services/cts/**`, CTS graph stores | `incubating` | `clarify-boundary` with context compiler and grounded query | Keep sidecar-style inside AIOS until data model proves stable. | Store lifecycle, query API, and context integration are not yet mature. | Portable graph-store API with isolated index fixtures and query benchmarks. |
| Operator UI | `aios-ui/` | `incubating` | `share-contract` with Python operator projections | Keep in-repo as product surface. | UI mirrors AIOS state and is not a reusable product yet. | Clear separation between UI shell, shared components, and AIOS-specific data readers. |
| Workflow learning and promotion | `services/workflow_learning.py`, `services/workflow_promotion.py` | `incubating` | `merge-candidate` with governed writebacks and asset lifecycle proposal flow | Keep in AIOS. | Governance, approval policy, and learning signals are core product behavior. | Stable event taxonomy and promotion proposal contract across multiple workflows. |
| Hook and session lifecycle | `bin/hook-*.py`, session tables, logs | `incubating` | `clarify-boundary` with handoff, closeout, and effectiveness projections | Keep in AIOS. | Hook behavior is deeply tied to local runtime identity. | Documented hook protocol and separate session-effectiveness API. |
| Agent eval framework | `docs/evals/`, `config/agent-eval/`, quality scripts | `bounded` | `share-contract` with success criteria and quality findings | Candidate for template/package extraction later. | Still partly documentation and local quality policy. | Reusable schemas, sample eval records, and non-AIOS benchmark fixture run. |
| Prompt, skill, and workflow asset lifecycle | `prompts/`, `config/workflows/skills.json`, lifecycle services | `incubating` | `merge-candidate` with learning, promotion, and governed writebacks | Keep in AIOS until promotion governance settles. | Asset governance is still core to AIOS default-layer behavior. | Versioned asset metadata schema and lifecycle transition tests. |

## Consolidation Candidates

These are not extraction targets yet. They are overlap zones where AIOS should decide whether to merge concepts, introduce one shared contract, or make the boundary explicit before packaging anything.

| Overlap Area | Candidate Subsystems | Consolidation Posture | Concern | Next Evidence |
| --- | --- | --- | --- | --- |
| Context, memory, and grounded query | Context compiler core, CTS repository intelligence, project truth, grounded query | Needs boundary clarification | Multiple systems select or explain knowledge, but they may own different layers: packet assembly, graph indexing, truth authority, and operator answers. | A shared source/selection/provenance contract that shows which layer owns retrieval, ranking, citation, and receipt generation. |
| Standards, success criteria, quality gates, and evals | Success criteria engine, standards health, architecture enforcement, agent eval framework, quality hotspot scripts | Strong consolidation candidate | Several systems judge quality or completion with overlapping labels, evidence, and pass/fail semantics. | One evidence and finding schema with adapters for criteria checks, eval runs, architecture rules, and quality scans. |
| Workflow routing, invocation, and native commands | Workflow registry/routing, invocation backend contracts, native workflow command pack, execution strategies | Needs shared route contract | Routing, backend selection, command execution, and strategy choice can drift if each owns its own task model. | A single route-decision object consumed by invocation, command, packet, and eval surfaces. |
| Learning, promotion, and writebacks | Workflow learning, workflow promotion, governed writebacks, prompt/skill/workflow asset lifecycle | Strong consolidation candidate | Proposal, approval, promotion, and learning loops can duplicate lifecycle state and policy checks. | One governed proposal lifecycle with typed proposal kinds, promotion targets, approval status, and evidence links. |
| Session lifecycle, handoff, and effectiveness | Hook/session lifecycle, briefing packets, handoff stores, session effectiveness, run closeout | Needs boundary clarification | Multiple flows capture continuity and completion evidence from the same session/run stream. | A unified run/session event model with separate projections for handoff, effectiveness, closeout, and operator replay. |
| Operator projections and Python backends | Operator UI server mirrors, Python CLI services, drill-down paths, control-plane projections | Consolidate contracts, not runtimes | Python and TypeScript mirrors can diverge while serving the same operator concepts. | Shared JSON contracts or generated fixtures that both runtimes validate against. |

## Recommended Sequence

### Phase A: Internal Boundaries First

- Add clearer public entry points for the context compiler, success criteria evaluator, invocation backend contract, and CTS query API.
- Add architecture checks that prevent UI, hooks, and runtime services from reaching across subsystem internals.
- Create fixture sets that describe inputs and outputs without requiring full operator state.
- Resolve high-risk consolidation candidates before extracting any package that would freeze duplicated concepts.

### Phase B: Package Candidates

- Promote the context compiler core and success criteria engine to package-ready status first if their contracts stabilize.
- Keep AIOS-owned adapters in this repo, even if the core package moves.
- Use local path dependencies during the first extraction rehearsal before publishing or remote repo consumption.

### Phase C: Repository Extraction

- Extract only when a subsystem has independent consumers, independent release needs, and stable maintenance ownership.
- Preserve AIOS integration through a thin adapter with compatibility tests.
- Keep migration notes in this file until the extraction is no longer operationally relevant.

## Resulting Repo Shape Target

The likely end state is not many equal apps. It is an AIOS orchestrator plus a few stable libraries:

- `aios`: orchestrator, local runtime, governance, hooks, adapters, operator UI, product docs.
- `aios-context`: reusable context compiler core, routing manifests, receipt contract.
- `aios-criteria`: reusable success criteria and evidence evaluation engine.
- `aios-invocation-contracts`: optional later home for backend capability and handshake contracts.
- `aios-cts`: optional later home for repository graph/indexing if it becomes broadly useful.

This target is provisional. It should change only when evidence shows that a subsystem is more reusable and maintainable outside the main repo.

## Maintenance Rules

Update this file whenever any of these happen:

- A subsystem crosses a maturity state.
- A new subsystem becomes a serious extraction candidate.
- A subsystem becomes a consolidation candidate or an overlap is intentionally rejected as acceptable.
- A subsystem gains a stable public contract or loses one.
- AIOS starts consuming an extracted subsystem as a dependency.
- A roadmap phase changes the runtime boundary, storage ownership, or governance policy of a listed subsystem.
- A new roadmap phase is added; its phase definition must include a `Subsystem extraction posture goal`.
- A split is rejected after analysis; record the reason so it is not relitigated without new evidence.

Every update should include the date, changed subsystem, evidence, and next decision point.

## Phase Planning Requirement

Every newly added roadmap phase must declare:

```md
**Subsystem consolidation goal:** <none | overlap area> -> <none-known | watch | clarify-boundary | share-contract | merge-candidate | consolidated>
**Subsystem extraction posture goal:** <none | subsystem name> -> <incubating | bounded | package-ready | repo-ready | externalized>
```

The entry must explain the target posture for the affected subsystem by the end of the phase. If the phase is not intended to move any subsystem toward consolidation or extraction, use `none` and state why the work should remain product-integrated. If the phase touches overlapping concepts, name the consolidation candidate and the shared contract or boundary decision the phase should produce.

Phase plans should treat this as a goal, not a promise. Completion evidence can confirm the goal, revise it, consolidate overlapping pieces, or reject extraction, but the decision must be recorded in this file when the phase materially changes subsystem boundaries.

## Decision Log

| Date | Decision | Evidence | Next Decision Point |
| --- | --- | --- | --- |
| 2026-06-05 | Treat AIOS as a monorepo incubator and defer repo splits until contracts mature. | Current subsystems are still coupled through local runtime, workflow governance, SQLite state, and operator surfaces. | Reassess after context compiler and success criteria contracts have independent fixture-backed APIs. |
| 2026-06-05 | Track consolidation candidates before extraction candidates. | Several AIOS areas share concepts such as evidence, routing, knowledge selection, lifecycle proposals, and operator projections. | Before extracting context, criteria, invocation, learning, or CTS packages, decide whether their overlapping contracts should merge or stay separate. |
| 2026-06-23 | Keep mature-repo behavioral verification inside the workflow registry/routing subsystem as an incubating quality workflow. | `behavioral-spec-verification-loop` now depends on AIOS route selection, maturity eligibility reports, prompt/skill registries, canonical artifact rules, Thermo simplification, and pre-PR/shadow-branch quality conventions. | Reassess only after the loop has multiple real run artifacts proving a stable spreadsheet schema, evidence contract, and non-AIOS caller need. |
