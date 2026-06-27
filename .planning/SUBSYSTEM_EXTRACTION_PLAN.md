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

## Ownership Classifications

These ownership labels are stricter than maturity states. Maturity says how stable a subsystem is; ownership says whether it belongs in AIOS at all.

| Classification | Meaning | Default Action |
| --- | --- | --- |
| `core_aios` | Product behavior that is part of AIOS as the local-first agent operating layer. | Keep in AIOS; improve module boundaries and tests. |
| `adapter_inside_aios` | Thin integration glue that lets AIOS consume an external package, tool, service, or repo-local workflow. | Keep the adapter in AIOS; keep core logic outside. |
| `contract_package` | Reusable schemas, validators, or protocol definitions with minimal runtime policy. | Prefer separate package or external repo once stable. |
| `standalone_tool` | A tool/product with its own user value, CLI/MCP/plugin surface, or release cadence. | Extract or keep outside AIOS; AIOS should consume through adapter/dependency. |
| `incubator_candidate` | Functionality still being shaped inside AIOS but likely not permanent core if its contract stabilizes. | Keep temporarily; require a next decision point and extraction/consolidation evidence. |

## Strict Ownership Map

This map is the current answer to whether AIOS only contains code in its scope. The answer is **not yet**: AIOS now contains fewer standalone products, but several incubator candidates remain intentionally inside until their contracts are stable enough to split or reject.

| Subsystem | Current Home | Ownership Classification | AIOS-Scope Decision | Boundary Rule | Next Decision Point |
| --- | --- | --- | --- | --- | --- |
| Local runtime, hooks, session lifecycle | `bin/hook-*.py`, `bin/aios.py`, `schema.sql`, session tables, `logs/` projections | `core_aios` | In scope. This is AIOS' operating-layer runtime. | Runtime state, local hooks, and session continuity stay in AIOS. | Define a hook protocol only if non-AIOS runtimes need to emit compatible events. |
| Workflow registry and routing | `services/workflow_orchestration.py`, `services/task_routing.py`, `config/workflows/` | `core_aios` | In scope. AIOS compiles intent into governed workflow routes. | Route policy and active workflow registry remain AIOS-owned. | Extract only route-decision schemas if multiple tools need them without AIOS runtime. |
| Managed invocation and native command execution | `services/invocation_backends.py`, `services/native_commands.py`, `bin/aios-managed-run.py`, `config/commands/` | `core_aios` now, `contract_package` candidate later | Mostly in scope because it executes AIOS workflows. | Runtime execution stays in AIOS; backend handshake schema may become a contract package. | Add versioned backend fixtures before any extraction. |
| TMCP runtime and skill graph governance | `services/tmcp_runtime.py`, `config/tmcp/`, `skills-library/` | `core_aios` now, `incubator_candidate` later | In scope for now because packet compilation and shortcut governance are AIOS behavior. | Skill graph storage, packet receipts, and promotion policy stay in AIOS until portable namespace behavior stabilizes. | Reassess after multi-workflow packet receipts prove stable outside AIOS. |
| Context compiler runtime | `tools/context-compile.mjs`, `aios/context/`, `services/context_compiler.py` | `core_aios` with external `contract_package` dependency | In scope. AIOS owns context-root selection, ranking, receipts, and writebacks. | Runtime stays in AIOS; result/manifest validation lives in `context-compiler-contract`. | Build external fixtures for context roots before considering a runtime split. |
| Context compiler contract | `/Users/jakyeamos/context-compiler-contract` | `contract_package` | Out of AIOS core. AIOS consumes it as a dependency. | AIOS must not reintroduce contract validator logic locally. | Decide when to switch AIOS from local file dependency to `v0.1.0` tag consumption. |
| Success criteria evaluator | `services/success_criteria.py`, `config/success-criteria/`, `spec/success-criteria/` | `core_aios` with external `contract_package` dependency | In scope while it owns registry policy, SQLite writes, and evaluation artifacts. | Evaluator policy/storage stays in AIOS; finding/evidence normalization lives in `quality-evidence-contract`. | Extract evaluator only after registry and artifact writes are fixture-backed without SQLite. |
| Quality evidence contract | `/Users/jakyeamos/quality-evidence-contract` | `contract_package` | Out of AIOS core. AIOS consumes it as a dependency. | AIOS findings should use the package rather than duplicate schema logic. | Decide when to switch AIOS from local path dependency to `v0.1.0` tag consumption, then reuse from repo-quality-certifier outputs. |
| Repo quality certification engine | `/Users/jakyeamos/repo-quality-certifier` | `standalone_tool` | Out of AIOS core. AIOS owns only adoption orchestration and adapter calls. | Certification scan/rubric/doc generation stays external; AIOS adapter injects TMCP and workflow context. | Decide when to switch AIOS from local path dependency to `v0.1.0` tag consumption. |
| Repo gate adoption adapter | `services/repo_gate_adoption.py`, `aios gate adoption-*` CLI surfaces | `adapter_inside_aios` | In scope as adapter only. | No heavy certification logic should move back into AIOS. | Add adapter tests that fail if external package internals are copied back. |
| Linked-repo readiness portfolio ledger | `services/linked_repo_readiness.py`, `config/quality-pipeline.json`, linked-repo evidence docs | `core_aios` now | In scope as AIOS portfolio governance. | Portfolio evidence and AIOS adoption status stay in AIOS; repo-local remediation belongs in target repos. | Reassess after Phase 29 proves whether the ledger is generic enough for a standalone portfolio tool. |
| Quality gates, standards health, and architecture enforcement | `services/quality_gates.py`, `services/standards_health.py`, `services/architecture_enforcement.py`, `config/quality-*`, `config/standards/` | `incubator_candidate` | Partly in scope, but overlap is high. | Keep policy in AIOS until it is consolidated around `quality-evidence-contract`. | Decide whether this becomes part of success criteria, repo-quality-certifier, or a separate standards engine. |
| Commit quality ladder and Pre-CR adapters | `services/commit_quality_ladder.py`, `bin/user-commit-quality-gate.py`, Pre-CR configs | `core_aios` for user gate, `adapter_inside_aios` for Pre-CR | In scope where it protects AIOS/user workflow; adapter only for external Pre-CR behavior. | AIOS may call Pre-CR but should not absorb Pre-CR implementation. | Keep as adapter unless AIOS starts owning changed-line readiness semantics. |
| CTS repository intelligence | `services/cts/**`, `data/cts/`, CTS CLI/MCP entrypoints | `incubator_candidate` leaning `core_aios` sidecar | 2026-06-26 audit rejects a repo split for now. CTS has real graph/index/search/impact code, but repo discovery, graph-store paths, CLI/MCP surfaces, and consumers are still AIOS-local. | Keep inside AIOS; extract only a future contract/fixture package after portable schemas, fixtures, and query benchmarks stabilize. | Add registry adapters, isolated fixture repos, CTS-specific tests, and a stable query-result contract before reconsidering `standalone_tool`. |
| Operator UI | `aios-ui/` | `core_aios` | In scope. It is AIOS' operator surface. | UI stays in AIOS while it mirrors AIOS state and SQLite projections. | Split only reusable UI components if they become product-independent. |
| Operator projections and search | `services/operator_search.py`, `services/next_action.py`, `services/daily_flow.py`, `services/handoff_store.py` | `core_aios` | In scope. These explain and continue AIOS work. | Projection contracts should be shared with UI, but runtime stays in AIOS. | Add JSON contract fixtures shared by Python and UI server. |
| Workflow learning, promotion, and governed writebacks | `services/workflow_learning.py`, `services/workflow_promotion.py`, `services/asset_lifecycle.py`, learning configs | `core_aios` now, `incubator_candidate` for templates | In scope because AIOS learns from runs and governs default behavior. | Approval lifecycle stays in AIOS; reusable proposal schema may become a contract. | Consolidate with asset lifecycle before extracting anything. |
| Prompt, skill, and workflow asset lifecycle | `prompts/`, `skills/`, `config/workflows/skills.json`, lifecycle services | `core_aios` | In scope for AIOS default-layer behavior. | Asset governance stays in AIOS; individual skills can live outside when distributed as skills/plugins. | Add versioned asset metadata before considering packaging. |
| Agent harness and eval run recording | `agent_eval_contract/`, `services/harness*.py`, `services/eval_run_service.py`, `docs/evals/`, `config/agent-eval/` | `core_aios` for runtime/storage; in-repo `contract_package` boundary for schemas/templates | 2026-06-26 audit rejects a standalone runtime split. AIOS now has an in-repo `agent_eval_contract` package for context profiles, status/priority validation, score fields, TypedDict schemas, harness fixture validation, eval template validation, sample record validation, clean-room contract checks, and external result normalization. | Keep runtime, storage, and CLI integration inside AIOS; keep growing the contract package only around portable schemas, fixture formats, template validation, sample records, and external normalization. | Add non-AIOS fixture production and release metadata before physical repo extraction. |
| External benchmark and corpus evaluation | `services/external_benchmark_adapter.py`, `services/tmcp_benchmark.py`, `tmcp-benchmark/`, `config/peer-eval/`, `scripts/aios-corpus-eval.cjs` | `incubator_candidate` leaning `core_aios` proving harness | Useful for AIOS proving, but not a standalone product yet. TMCP benchmark depends on local repo inventory, TMCP graph/shortcut state, and AIOS claim gates; corpus eval is primarily an AIOS regression harness. | Keep inside AIOS until benchmark evidence model stabilizes; extract only external normalization schemas or task/condition manifest validators first. | Repeated passing real benchmark runs, clean-room contract fixture, and separation from AIOS local DB/config assumptions. |
| Personalized humanizer | `services/personalized_humanizer.py`, `config/personalized-humanizer/`, `skills/personalized-humanizer/` | `core_aios` for runtime/state; `contract_package` candidate for schemas | Current audit classifies it as an AIOS memory/persona projection, not an RDW-style standalone product. Runtime, workflow stages, profile governance, SQLite state, and privacy rules stay in AIOS. | Keep inside AIOS; do not extract runtime or personal profile data. | Isolate a portable voice-profile/voice-packet/scorecard contract only after synthetic fixtures and a second consumer justify it. |
| Research Domain Writing | `/Users/jakyeamos/research-domain-writing` | `standalone_tool` | Out of AIOS core. It is a standalone file-based writing pipeline with slash-command/skill distribution. | Extracted. AIOS consumes it as an installed skill/tool and should keep only thin future adapters. | Keep RDW release/test metadata in the external repo; add AIOS adapters only for packet suggestions, guardrails, and reviewable writebacks. |
| NotebookLM synthesis | `services/notebooklm_synthesis.py`, `config/notebooklm/` | `adapter_inside_aios` | In scope only as an adapter to an external research/synthesis tool. | Keep integration thin and avoid making NotebookLM behavior core AIOS logic. | Extract adapter contract only if multiple AIOS workflows share it. |
| Planning governance and GSD/Terrace bridges | planning configs, `.planning/`, planning detection/services | `core_aios` for governance, `adapter_inside_aios` for external workflow packs | In scope where AIOS governs planning quality; adapters should stay thin. | AIOS owns plan quality contracts, not the implementation of every external planning workflow. | Clarify GSD/Terrace boundaries before adding more planning-specific logic. |
| Project inventory and adoption portfolio | `services/project_inventory.py`, `config/project-name-map.json`, linked repo docs | `core_aios` | In scope as AIOS knows which repos it governs. | Inventory stays; per-repo execution belongs in owning repos. | Add source-of-truth rules for stale/missing repos. |
| Portable packet generation | `services/portable_context_packet_generator.py`, packet docs/config | `incubator_candidate` | Useful to AIOS, but portable by design. | Keep until packet schema stabilizes; candidate for contract/package later. | Add clean-room fixture that consumes packets without AIOS runtime. |

## Candidate Subsystems

| Subsystem | Current Home | Current State | Consolidation Posture | Extraction Posture | Main Blockers | Next Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Context compiler core | `tools/context-compile.mjs`, `/Users/jakyeamos/context-compiler-contract`, `aios/context/` | `bounded` | `clarify-boundary` with memory, CTS, and grounded query | Result/receipt contract is repo-extracted and tagged at `github.com/jakyeamos/context-compiler-contract`; compiler runtime should stay in AIOS until routing inputs and context storage assumptions are isolated. | Mixed CLI, file routing, receipts, and AIOS-specific context assumptions. | Standalone compiler package rehearsal only after context-root and routing-manifest inputs are fixture-backed outside AIOS. |
| Success criteria engine | `services/success_criteria.py`, `config/success-criteria/`, `/Users/jakyeamos/quality-evidence-contract` | `bounded` | `share-contract` with standards health, quality gates, and evals | Evidence/finding contract is repo-extracted and tagged at `github.com/jakyeamos/quality-evidence-contract`; evaluator engine stays in AIOS until registry/storage lifecycle stabilizes. | Evaluator execution still writes AIOS SQLite/artifact state and depends on AIOS registry policy. | Fixture-backed evaluator API independent of AIOS SQLite writes, plus downstream consumers using `quality-evidence-contract` directly. |
| Repo quality certifier | `/Users/jakyeamos/repo-quality-certifier`, `services/repo_gate_adoption.py` adapter, `config/workflows/` | `repo-extracted-remote` | `share-contract` with success criteria, TMCP, workflow routing, and linked-repo adoption | Physical repo split is complete and tagged at `github.com/jakyeamos/repo-quality-certifier`; AIOS consumes the package through a local path dependency and keeps only the adapter/orchestration layer. | AIOS still uses a local path dependency. | Decide when to switch AIOS to tagged dependency consumption. |
| Workflow registry and routing | `services/workflow_orchestration.py`, `config/workflows/` | `incubating` | `share-contract` with invocation, command, and strategy surfaces | Keep in AIOS for now. | Product behavior and routing policy are still evolving together. | Stable route decision schema and misroute evaluation history. |
| TMCP runtime and skill graph | `services/tmcp_runtime.py`, `skills-library/skills.tmcp/`, `config/tmcp/` | `bounded` | `share-contract` with workflow routing, invocation, and context receipts | Keep in AIOS until runtime expansion, shortcut, namespace overlay, and receipt contracts stabilize. | TMCP receipts and active-packet handoff are coupled to AIOS SQLite runtime, managed workflow stages, and local skill graph governance. | Multi-run evidence that phase expansion, packet diffs, shortcut lifecycle, adherence events, and portable namespace overlays remain stable across workflows and non-AIOS callers. |
| Invocation backend contracts | `services/invocation_backends.py`, managed runtime code | `bounded` | `share-contract` with workflow routing and native command execution | Possible package later, but only after native workflow command work settles. | Backend capabilities, harness handshakes, and runtime reports are still changing. | Versioned backend contract fixtures and compatibility tests. |
| CTS repository intelligence | `services/cts/**`, CTS graph stores | `incubating` | `clarify-boundary` with context compiler and grounded query | Keep sidecar-style inside AIOS; do not physically extract yet. A future `cts-contract` style package may be justified before any runtime split. | `CTSRegistry` depends on AIOS `projects` and `~/AIOS/data/cts`; MCP/CLI entrypoints require AIOS registration; semantic search and flow layers are not fully implemented; CTS-specific tests are missing from `tests/`. | Portable graph/query contracts, isolated fixture repos, query benchmarks, non-AIOS registry adapter, and regression tests for search/impact/MCP envelopes. |
| Operator UI | `aios-ui/` | `incubating` | `share-contract` with Python operator projections | Keep in-repo as product surface. | UI mirrors AIOS state and is not a reusable product yet. | Clear separation between UI shell, shared components, and AIOS-specific data readers. |
| Workflow learning and promotion | `services/workflow_learning.py`, `services/workflow_promotion.py` | `incubating` | `merge-candidate` with governed writebacks and asset lifecycle proposal flow | Keep in AIOS. | Governance, approval policy, and learning signals are core product behavior. | Stable event taxonomy and promotion proposal contract across multiple workflows. |
| Hook and session lifecycle | `bin/hook-*.py`, session tables, logs | `incubating` | `clarify-boundary` with handoff, closeout, and effectiveness projections | Keep in AIOS. | Hook behavior is deeply tied to local runtime identity. | Documented hook protocol and separate session-effectiveness API. |
| Agent eval framework | `agent_eval_contract/`, `docs/evals/`, `config/agent-eval/`, `services/harness_eval.py`, `services/external_benchmark_adapter.py` | `package-ready-candidate` | `share-contract` with success criteria and quality findings | In-repo `agent_eval_contract` package boundary exists; keep runtime in AIOS and defer physical extraction. | Eval storage, peer traces, shadow worktrees, second-brain lift, and operator projections are AIOS-local. The contract package still needs a non-AIOS producing runner and release metadata before physical split. | Non-AIOS fixture production, explicit vocabulary sharing with `quality-evidence-contract`, and physical split rehearsal. |
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
| 2026-06-24 | Keep durable agent workspaces inside the workflow registry/routing subsystem as an incubating governance contract. | `durable-agent-workspace` is a candidate workflow backed by context packets, docs, and candidate skills; it coordinates existing context, artifact, automation, memory, verifier, and skill-candidacy rules instead of owning an independent runtime or storage API. | Reassess after multiple real durable workspaces produce stable state artifacts, verifier evidence, and repeated TMCP skill-candidacy records. |
| 2026-06-24 | Keep runtime-phase TMCP expansion inside AIOS as a bounded but not package-ready subsystem. | `services.tmcp_runtime.expand_tmcp_packet_for_requirement_change` now persists active expansion receipts, packet diffs, superseded receipt outcomes, and intervention events; `services.workflow_orchestration.execute_workflow` now replaces the active packet at phase-changing stage boundaries. | Reassess after managed-run history shows stable expansion receipts across implementation, testing, closeout, shortcut, and portable namespace routes without AIOS-specific storage assumptions leaking into the packet contract. |
| 2026-06-26 | Split repo quality certification into the `repo_quality_certifier` package boundary and keep AIOS as an adapter/orchestrator. | The adoption engine now lives under `repo_quality_certifier/`; `services/repo_gate_adoption.py` injects AIOS TMCP enrichment while preserving existing workflow imports; focused tests prove standalone import does not load `services.tmcp_runtime` and non-AIOS callers receive valid fallback enrichment. | Create standalone CLI/MCP/package metadata, run the package from an external fixture repo, then move it to a separate repository once AIOS consumes it through the adapter contract. |
| 2026-06-26 | Promote `repo_quality_certifier` from package-ready to repo-ready. | The package now exposes `repo-quality-certifier` and `repo-quality-certifier-mcp` console scripts, dependency-free JSON-RPC tool handlers for plan/doc-quality, a plugin manifest plus skill file, package-data metadata, and external fixture tests for CLI/MCP/plugin contracts. | Rehearse the physical repo split with a local path dependency and prove AIOS can consume the external package without direct internal imports. |
| 2026-06-26 | Physically split repo quality certification into `/Users/jakyeamos/repo-quality-certifier`. | The external repo has committed package source, CLI/MCP/plugin surfaces, tests, Pre-CR config, and an accepted initial oversized-source extraction exception; AIOS removed its in-tree `repo_quality_certifier/` package and now imports the installed package from `file:///Users/jakyeamos/repo-quality-certifier` with focused adapter tests passing. | Create the GitHub remote, push `main`, add version/release governance, and replace the local path dependency with the approved distribution strategy when ready. |
| 2026-06-26 | Created the `jakyeamos/repo-quality-certifier` GitHub remote and pushed `main`. | Local repo `main` now tracks `origin/main` at `git@github.com:jakyeamos/repo-quality-certifier.git`; the private GitHub repo exists at `https://github.com/jakyeamos/repo-quality-certifier`. | Add release/version governance and decide when AIOS should move from local path dependency to a tagged Git/package dependency. |
| 2026-06-26 | Extract the shared quality evidence/finding contract as `quality_evidence_contract`. | The package defines portable evidence and finding schemas, normalization, validation, and count helpers; `services.success_criteria` now adds a nested `quality_contract` payload to stage and evaluation findings without changing legacy fields. | Use the contract from repo quality certification outputs, then reassess whether the success criteria evaluator itself can become package-ready after AIOS storage dependencies are isolated. |
| 2026-06-26 | Physically split quality evidence contracts into `/Users/jakyeamos/quality-evidence-contract`. | The private GitHub repo `jakyeamos/quality-evidence-contract` exists, local `main` tracks `origin/main`, initial commit `5bb3b85` passes Ruff, BasedPyright, pytest, and Pre-CR, and AIOS imports the installed package from `file:///Users/jakyeamos/quality-evidence-contract` with success-criteria integration tests passing. | Add release/version governance and decide when AIOS should move from local path dependency to a tagged Git/package dependency. |
| 2026-06-26 | Extract the context compiler result/receipt contract as `context_compiler_contract`. | The JS contract module validates selected context files, retrieval trace, packet contract, routing manifest, receipt, and briefing output; `tests/context-compiler.test.mjs` now checks live compiler output against that contract. | Use the contract from AIOS CLI/UI consumers, then rehearse a standalone context compiler package only after context-root and routing-manifest inputs are fixture-backed outside AIOS. |
| 2026-06-26 | Physically split context compiler contracts into `/Users/jakyeamos/context-compiler-contract`. | The private GitHub repo `jakyeamos/context-compiler-contract` exists, local `main` tracks `origin/main`, initial commit `e8c6e90` passes package tests, syntax check, and Pre-CR, and AIOS imports `context-compiler-contract` from the installed package with live context compiler regression tests passing. Extraction also hardened malformed routing-manifest validation so non-list skipped sources return issues instead of throwing. | Add release/version governance and defer compiler-runtime extraction until context roots, routing inputs, and storage assumptions have external fixtures. |
| 2026-06-26 | Added a strict ownership map for AIOS subsystem scope. | The map classifies current subsystems as `core_aios`, `adapter_inside_aios`, `contract_package`, `standalone_tool`, or `incubator_candidate`; it records that AIOS is better scoped after extraction candidates move out but still contains incubator candidates such as CTS, agent/eval harness pieces, personalized humanizer, benchmark tooling, and quality/standards consolidation surfaces. | Use the ownership map before any future split; do release governance for extracted repos before extracting another package unless a blocking scope issue appears. |
| 2026-06-26 | Added release governance and `v0.1.0` tags for all three extracted repos. | `repo-quality-certifier` commit `3ff7eb4`, `quality-evidence-contract` commit `36c94bc`, and `context-compiler-contract` commit `de60ba1` now include `CHANGELOG.md`, `RELEASE.md`, Pre-CR doc ignores, passing release validation, and pushed annotated `v0.1.0` tags. | Decide whether AIOS should keep local path dependencies for active development or switch to tagged Git dependencies for stronger release-boundary proof. |
| 2026-06-26 | Audited `research-domain-writing` boundary. | `.planning/RESEARCH_DOMAIN_WRITING_BOUNDARY_AUDIT.md` records that RDW is a standalone file-based writing pipeline with its own skill, prompts, domains, installers, docs, examples, and future-AIOS notes; AIOS references were light and there was no nested repo before extraction. | Extract to `jakyeamos/research-domain-writing` after a narrow hardening pass. |
| 2026-06-26 | Physically split Research Domain Writing into `/Users/jakyeamos/research-domain-writing`. | The private GitHub repo `jakyeamos/research-domain-writing` exists, local `main` tracks `origin/main`, `v0.1.0` is pushed at commit `ba0f608`, standalone Ruff/BasedPyright/pytest checks pass, Pre-CR passes with 89.5% changed-line coverage, and local Claude/Cursor/Codex skill installs point at the external repo. | Keep AIOS integration adapter-only; do not reintroduce RDW prompt/domain/installer source into AIOS. |
| 2026-06-26 | Audited personalized humanizer boundary. | `.planning/PERSONALIZED_HUMANIZER_BOUNDARY_AUDIT.md` records that the subsystem is tightly coupled to AIOS workflow orchestration, SQLite feedback/profile-update state, local privacy rules, and personal profile governance. | Keep runtime/state/profile in AIOS; consider only a future portable voice-profile/voice-packet/scorecard contract after synthetic fixtures and a second consumer exist. |
| 2026-06-26 | Audited CTS repository intelligence boundary. | `.planning/CTS_BOUNDARY_AUDIT.md` records that CTS has real graph/index/search/impact/MCP code, but `CTSRegistry` depends on AIOS `projects` and `~/AIOS/data/cts`, current semantic search is FTS/LIKE with no embeddings, flow discovery is placeholder-only, and CTS-specific tests are not present under `tests/`. | Keep CTS inside AIOS as a sidecar; revisit only after registry adapters, isolated fixture repos, stable query-result contracts, and CTS-specific search/impact/MCP/eval tests exist. |
| 2026-06-26 | Audited agent eval and benchmark harness boundary. | `.planning/EVAL_BENCHMARK_BOUNDARY_AUDIT.md` records that eval run recording, peer traces, shadow branches, second-brain lift, corpus eval, and TMCP benchmarks are tied to AIOS SQLite/runtime/operator state, while schemas, context profiles, failure taxonomy, fixture formats, templates, and external result normalization are portable contract candidates. | Keep eval/benchmark runtime inside AIOS; consider a future `agent-eval-contract` package only after validators, sample records, and a non-AIOS fixture-producing runner exist. |
| 2026-06-26 | Created the in-repo `agent_eval_contract` package boundary. | The package owns context-profile/status/priority validation, score fields, TypedDict schemas, harness fixture validation, and external benchmark normalization; `services.eval_run_service`, `services.harness_eval`, `services.external_benchmark_adapter`, and `config/agent-eval/eval-schemas.py` now consume the shared package, and focused tests prove package import does not import AIOS services. | Keep runtime/storage inside AIOS; add template validators, sample records, and non-AIOS fixture production before considering a physical repo split. |
| 2026-06-26 | Hardened `agent_eval_contract` with template/sample validation and a clean-room runner. | `agent_eval_contract.templates` validates the five checked-in eval templates, `agent_eval_contract.samples` validates bundled eval task/run/score/failure/shadow/external-normalization samples, and `run_clean_room_contract_check` validates both without importing AIOS `services`. | Add non-AIOS fixture production and release metadata before physically splitting `agent-eval-contract`. |
