---
schemaVersion: 1
projectName: AIOS
summary: Active local-first agent operating system with honest evidence verdicts, evidence-gated verify-run completion, durable eval-run recording, context-loop learning primitives, TMCP expertise compilation, standalone Quality Runner consumption, review-gated session-intelligence tools, and progressive colocated context routing across AIOS and linked repos.
healthScore: 85
statusLabel: warning
nextStep: Start M5's gated review and closeout slice; keep UI mutations gated behind the Python owner.
blockers: []
lastUpdated: 2026-07-14
tags: [infra, ai-os, hooks, automation]
areas: [engineering]
goals: []
repoType: infra
sourceOfTruth: mixed
primaryLanguage: Python
activeBranch: dev
lastCommitDate: 2026-07-14
quality:
  lint: fail
  types: fail
  tests: pass
  deadCode: pass
  structure: partial
canonicalCommands:
  install: uv sync
  dev: unknown
  lint: ruff check .
  typecheck: basedpyright
  test: uv run pytest -q
  deadcode: vulture . --min-confidence 70
agentExpectationsVersion: 1
---

## Current State

AIOS now has a completed v2 modernization baseline, accepted local-first operating model, canonical-state contract, task-centred UI contract, reproducible UI validation contract, subsystem modernization strategy, and dependency-ordered target/vertical plan: [`AUDIT.md`](../docs/modernization/AUDIT.md), [`TARGET.md`](../docs/modernization/TARGET.md), [`EXEC_PLAN.md`](../docs/modernization/EXEC_PLAN.md), [`ADR-001`](../docs/modernization/ADR-001-v2-operating-loop-and-trust-boundary.md), [`ADR-002`](../docs/modernization/ADR-002-canonical-state-and-migration-authority.md), [`ADR-003`](../docs/modernization/ADR-003-task-centred-ia-and-accessible-design-system.md), [`ADR-004`](../docs/modernization/ADR-004-reproducible-ui-validation-contract.md), and [`ADR-005`](../docs/modernization/ADR-005-subsystem-ownership-and-parallel-v2-strategy.md). Wayfinder Ticket 006 is resolved; Milestone 0 has the shared JSON fixture, TypeScript boundary guard, Python cross-reference tests, disposable SQLite projection, and daily-flow replay proof. Milestone 1 now has the executable Python storage boundary, copied-store runner, evidence-backed FK transformer, and broad adapter adoption: one resolved `AIOS_DB`, canonical pragmas, read-only projections, idempotent migration/quarantine ledger, schema checksums, preflight/postflight health/counts, unique-path mappings, source-payload quarantine, and immutable backup/restore helpers; lifecycle hooks, high-traffic prompt/compaction/post-tool/session-stop hooks, the managed runtime, Codex ingestion, session CLI, all four provider canonical upserts, stale-session repair, prompt sync, workflow experiment utilities, metrics/reporting paths, history import, inventory sync, Apple-backed ingestion writes, the CLI doctor probe, daily pipeline pending-rule query, pattern schema migration, pattern extraction, pattern scoring, pattern promotion, pattern confirmation/approval/contradiction lifecycle tools, observation review, noise purging, bug-motif extraction, handoff-learning extraction, personal-pattern extraction and promotion, agent synthesis, domain-file projection, DOCX/PDF document indexers, rule-bundle registration, the business-memory path resolver and five CLI adapters, issues/handoffs, query/statusline utilities, and the UI database path converge on the override/pragmas. The actual current read-only store preflight reports 561 FK violations (older audit documents record 555/557); the disposable transformer copy reaches zero and the restored copy replays the canonical daily flow. UI-owned request-time DDL, remaining lower-traffic adapters, and human retention review are still gated. V2 is a single-user, loopback-only local control plane with one logical mutation authority; no live rows have been migrated. The target and plan now turn those decisions into eight vertical milestones plus a paired-effectiveness gate before satellite promotion and cutover. Divergent schema/bootstrap ownership, unenforced UI mutation boundaries, and blocked UI implementation gates remain. The current `dev` worktree was already dirty when this work started, so its shadow lane remains trace-only.

Current-state amendment (2026-07-14): the approved archive migration is now
applied live with zero FK violations, a version-1 ledger entry, immutable
pre/post backups, and a completed restore/replay check. UI request-time DDL and
ADR-004 validation is complete; the Python-owned UI mutation boundary remains a later modernization gate.

Current-state amendment (2026-07-14): the M2 UI validation slice now vendors
`eslint-plugin-anti-slop` 0.4.0 inside `aios-ui`, removes request-time UI DDL in
favor of a read-only migration-ledger assertion, and passes ESLint, fixture,
TypeScript, architecture, warning-baseline, build, and disposable runtime
smoke gates. Seeded overview/run-detail routes, the three-viewport responsive
matrix, same-origin network capture, and console evidence now pass locally; a
duplicate run-detail key was fixed. Playwright 1.61.1 now proves the same
routes, screenshots, console/network policy, and keyboard traversal. Generated
prompt/workflow catalogs and static managed-runtime spawn arguments remove the
NFT tracing warning. M2 is resolved; UI mutation endpoints still need
Python-owner routing.

Current-state amendment (2026-07-14): M3 now ships the read-only v2 operator
shell at `/` Today, `/start` Start work, and `/runs/:id` Current run, using
canonical tRPC projections and preserving legacy session-detail fallback.
Primary navigation is task-centred with contextual satellites behind
disclosure; provenance, freshness, authority, next action, and
healthy/blocked/stale/empty states are visible without UI writes. The M2 and
M3 Playwright suites pass at all required viewports with zero mutation
requests, console errors, bad same-origin responses, or horizontal overflow.
M4 remains the Python-owned governed mutation boundary.

Current-state amendment (2026-07-14): M4 now proves the Python-owned
route → packet → run → invocation → verification envelope against the
foreign-key-enforced canonical schema. `start-work` persists the run and
packet before creating the invocation, then links `active_invocation_id` only
after its target exists. The integration fixture records zero FK violations,
preserves partial-state resume snapshots with verifier provenance, blocks
cross-project session linkage, and completes `verify_run` with source-backed
evidence and a verifier artifact. Ambiguous and unsupported routes still block
before durable creation; M5 owns approval/capability/egress/writeback/
closeout enforcement.

_(4 older entries trimmed)_

Pipeline and lab schema migrations now also use the shared storage boundary
and `AIOS_DB` override; their schema/data changes remain disposable until the
main-store migration gate is accepted. RTK execution and tuning, GitHub-skill
discovery, workflow synthesis, and workflow experiment control now use the
same boundary while preserving read-only analytics and explicit `--db` paths.
The Flask review surface, vault-lint checks, and lab-trigger runner now use the
same boundary; Flask remains runtime-unverified because it is not installed in
the repository environment. Lifecycle-status migration uses the boundary for
file-backed databases while preserving `:memory:`, and commit-quality evidence
reads use the shared read-only path.
The CTS registry's AIOS project metadata reads also use shared read-only
storage and honor `AIOS_DB`; CTS graph stores remain CTS-owned.
The current recovery gate was rerun read-only: the live store remains
`quick_check=ok` and `integrity_check=ok` with 561 FK violations, while the
disposable transformer/restore path reaches zero FK violations and replays the
eight-step daily-flow preview without changing live rows.
The first ADR-004 UI pass initially had passing TypeScript, architecture,
warning-baseline, native-module, and production-build checks while ESLint and
NFT tracing were still open; the subsequent M2 slice resolved both gates.
The loopback runtime smoke also passed: `/` and the source-backed `projects.list`
tRPC route returned HTTP 200 with no request errors on a disposable dev server.
The approved live archive migration (`m001-archive-live-20260714`) then
reconciled all 561 FK violations, retained 73 unresolved quality payloads in
quarantine, recorded decisions for all 561 repair records, and passed live
restore/replay verification.

AIOS now also has a file-backed and SQLite-backed context-loop learning primitive: `services/context_loops.py`, `schema.sql`, and `python bin/aios.py context-loops ...` record inner-loop context/draft runs, review events, learning candidates, explicit approvals/rejections, approved lesson application, metrics, and a draft-only email pilot. Contract docs and examples live under `aios/context-loops/`.

AIOS now has `expert_rubric_remediation_v1` implemented and smoke-verified through the core artifact service, workflow runtime dispatch, active workflow/skill registry contracts, route scoring, and `aios tmcp review-plan`. The workflow compiles TMCP expertise into an explicit rubric, audits concrete evidence, produces ordered remediation slices, and writes an approval-gated implementation handoff without executing implementation.

AIOS also has `repo_gate_adoption_v1`, a narrow audit-and-plan workflow for repository quality-gate adoption. It scans repo-local scripts, Pre-CR, anti-slop, local AIOS quality contracts, CI, hooks, dead-code, structural-scan, and truth-file evidence; produces a core gate readiness matrix; conditionally records TMCP expert enrichment only when source sufficiency passes; writes broad repo-class and gate-specific rubric packs; writes a staged rollout plan under git-ignored `AIOS-backfill/gate-adoption/{run_id}`; and exposes the flow through `aios gate adoption-plan`.

Quality Runner now lives in `/Users/jakyeamos/quality-runner` as a standalone audit-and-plan package with CLI and MCP surfaces. AIOS should consume it as an external tool and may provide adapters, standards profiles, or workflow shortcuts, but the standalone package owns the core workflow and `.quality-runner/` artifact contract.

AIOS now has a review-gated Codex/Claude Session Intelligence loop. The loop enriches Codex session normalization with tool calls, commands, cwd, approval friction, errors, and terminal outcomes; stores lane candidates in SQLite; emits redacted Markdown/JSON reports; exposes `aios session-intel` commands; runs daily through the Codex automation `daily-codex-session-intelligence`; supports resumable historical backfill across Codex and Claude sources; can implement explicitly approved candidate IDs into helper-family records; and now records helper run/failure/bypass telemetry that drives active, insufficient, or removal-review statuses.

AIOS now has a read-only workflow router preview surface: `aios route "objective"` resolves the registered project, governed workflow, agent, backend, prompt family, candidate alternatives, and a ready-to-run `aios start-work ...` command without creating orchestration runs, packets, invocations, or sessions. `~/AIOS/bin/route` is a convenience wrapper around the same command.

AIOS now has a deterministic repo-state closeout helper integrated into daily-flow replay. `aios repo closeout` exposes the canonical `aios-repo-closeout-v0.1` payload, and `daily-flow --run-id` attaches that payload to the run step as `metadata.repo_closeout` when the run's project has a known repo path. The UI daily-flow mirror renders repo path, branch, short HEAD, dirty-file count, and diff stat on Command Center and run-detail surfaces without changing the canonical eight-step trace.

Quality Runner now supersedes the older repo-quality-certifier and quality-evidence-contract path dependencies for AIOS consumption. AIOS consumes `/Users/jakyeamos/projects/quality-runner` through one local `quality-runner` dependency, while Quality Runner provides the compatibility imports, CLI/MCP tools, plugin metadata, deterministic gate-certification workflow, and evidence-normalization helpers still used by existing `quality_evidence_contract` and `repo_quality_certifier` callers. `services/repo_gate_adoption.py` remains the AIOS adapter that injects AIOS TMCP enrichment and preserves existing workflow/CLI imports.

AIOS now exposes `aios quality rollout`, a thin adapter over Quality Runner's multi-repo `rollout_payload`. The adapter launches the external QR controller workflow, defaults captured artifacts to `~/AIOS/artifacts/quality-rollouts/<run-id-prefix>`, writes `aios-rollout-artifact-index.json` beside the QR ledger/controller reports/validation artifacts, and records an AIOS evidence pointer for operator lookup without taking ownership of QR's rollout protocol.

Context compiler contract validation now lives in the standalone repository `/Users/jakyeamos/context-compiler-contract`, with remote `git@github.com:jakyeamos/context-compiler-contract.git`. AIOS consumes it through a local file dependency, while `tools/context-compile.mjs` remains AIOS-owned until context-root and routing assumptions are external-fixture backed.

AIOS now has a strict subsystem ownership map in `.planning/SUBSYSTEM_EXTRACTION_PLAN.md`. The map classifies major surfaces as `core_aios`, `adapter_inside_aios`, `contract_package`, `standalone_tool`, or `incubator_candidate`. The current scope truth is that AIOS is better scoped after extracting `repo-quality-certifier`, `quality-evidence-contract`, `context-compiler-contract`, Research Domain Writing, and `agent-eval-contract`. CTS, personalized humanizer, and eval/benchmark runtime have now been audited and intentionally remain AIOS-owned for runtime/state reasons. Portable agent eval contracts now live in `/Users/jakyeamos/agent-eval-contract`, with remote `git@github.com:jakyeamos/agent-eval-contract.git` and pushed tag `v0.1.0` at `7489155`; AIOS consumes `agent-eval-contract @ file:///Users/jakyeamos/agent-eval-contract` while keeping eval runtime/storage in AIOS. The agent-eval-contract split remains gated on tagged AIOS dependency consumption and a second consumer before it is release-complete.

The earlier repo-quality-certifier and quality-evidence-contract repos are now historical extraction sources rather than AIOS dependencies. `context-compiler-contract` remains a separate local file dependency with release governance at commit `de60ba1`.

Research Domain Writing now lives in the standalone repository `/Users/jakyeamos/research-domain-writing`, with remote `git@github.com:jakyeamos/research-domain-writing.git` and pushed tag `v0.1.0` at commit `ba0f608`. AIOS no longer owns RDW prompts, domain packs, examples, installers, packet validation, or release process; local slash commands and agent skills point at the external repo.

Personalized humanizer has a boundary audit in `.planning/PERSONALIZED_HUMANIZER_BOUNDARY_AUDIT.md`. The current decision is to keep personalized humanizer runtime, workflow stages, profile governance, SQLite state, and privacy rules inside AIOS. It is an AIOS memory/persona projection, not the next RDW-style standalone product. A future extraction should start with a portable voice-profile/voice-packet/scorecard contract using synthetic fixtures, not with moving runtime or personal profile data.

## Why This Matters / Intended Outcome

AIOS is not an app — it is the operating layer for all AI-assisted development work across every project. Hook correctness and DB integrity are load-bearing. Breakage here silently degrades all Claude Code sessions. The ops database is the canonical store for sessions, prompts, artifacts, patterns, bug logs, and next-action candidates across all projects.

## Recent Progress
- 2026-07-14: Fixed canonical start-work FK ordering, cross-project session linkage, and verification resume snapshots; added the M4 route → packet → run → invocation → verify/resume integration proof (`tests/test_m4_start_work.py`).
- 2026-07-14: Shipped the read-only v2 Today → Start work → Current run shell with canonical projections, task-centred navigation, contextual disclosure, explicit state contracts, and zero-mutation browser proof (`a6adf99`).
- 2026-07-14: Vendored anti-slop 0.4.0, removed UI request-time DDL in favor of the migration-ledger assertion, and passed ESLint/fixtures/TypeScript/architecture/build/runtime gates.
- 2026-07-14: Added the pinned Playwright 1.61.1 browser contract, generated prompt/workflow catalogs, and static managed-runtime spawn arguments; browser and production-build M2 gates now pass without NFT warnings.
- 2026-07-14: Ran the UI loopback smoke after the build fix: `/` and `projects.list` tRPC returned HTTP 200 with source-backed data and clean server logs; the pinned browser/build gates are green without NFT warnings.
- 2026-07-14: Scoped the UI Turbopack root and refreshed native dependencies: TypeScript, architecture, warning-baseline, and production build passed; workspace-root warning resolved.
- 2026-07-14: Reran the live recovery preflight and disposable restore drill: 561 FK violations captured, 561 quarantined in the copy, zero restored FK violations, and eight-step daily-flow replay passed.
- 2026-07-14: Created `docs/modernization/M1_RETENTION_DECISION.md` from a fresh disposable run; it became the approved archive record after live reconciliation.
- 2026-07-14: Added the guarded transactional live migration runner (`eb59adb`): focused migration/storage tests, Ruff, and BasedPyright passed; archive application then completed successfully.
- 2026-07-14: Applied the approved archive migration: live `quick_check`/`integrity_check` pass, FK violations are 0, `user_version=1`, 561 quarantine decisions recorded, and 8-step replay/restore passed.
- 2026-07-14: Routed CTS registry AIOS metadata reads through shared storage (`52d22e5`): passed Ruff/BasedPyright and disposable read-only registry proof.
- 2026-07-14: Routed lifecycle migration and commit-quality evidence reads through shared storage (`6924d0a`): passed Ruff/BasedPyright, 29 focused tests, and disposable migration proof.
- 2026-07-14: Routed review, vault-lint, and lab-trigger adapters through shared storage (`c36cf66`): passed Ruff/BasedPyright and disposable vault/lab proof; Flask runtime remains dependency-blocked.
- 2026-07-14: Routed RTK, discovery, workflow synthesis, and experiment adapters through shared storage (`cfbab64`): passed Ruff/BasedPyright, 14 focused workflow tests, and disposable operational integration.
- 2026-07-14: Routed pipeline and lab schema migrations through shared storage (`217f29c`): honored `AIOS_DB`, passed Ruff/BasedPyright, and passed disposable state/schema/FK migration proof.
- 2026-07-14: Routed rule-bundle registration through shared storage (`7c3d509`): honored `AIOS_DB`, passed Ruff/BasedPyright, and passed disposable FK-enforced registration proof.
- 2026-07-14: Routed DOCX/PDF indexers through shared storage (`4c1374e`): honored `AIOS_DB`, passed Ruff/BasedPyright, and passed disposable dry-run metadata/index proof.
- 2026-07-14: Routed `build-domain-files.py` through shared read-only storage (`21bdd63`): honored `AIOS_DB`, passed Ruff/BasedPyright, and passed disposable domain projection dry-run proof.

## Open Problems

1. The live main-store archive migration now reports zero FK violations with an immutable pre/post backup and ledger entry; older 555/557 audit snapshots and distributed runtime DDL still need reconciliation/cleanup.
2. V2 now intentionally excludes remote control, but current UI mutation endpoints still lack the required loopback, local-capability, approval-enforcement, and single-mutation-owner implementation; M5 owns this boundary.
3. M2 and M3 UI validation is green, and M4 Python route/packet/run/verify proof is green. Approval, capability, egress, writeback, closeout, and paired-effectiveness proof remain.
   Milestone 0's fixture/replay contract, storage boundary, copied-store recovery proof, and approved live archive are complete.
## Next Concrete Steps

1. Start M5's gated review and closeout slice through the Python mutation owner.
2. Add loopback, capability, approval, and egress enforcement before enabling any UI mutation.
3. Preserve paired-effectiveness and cutover gates for later milestones.

## Risks / Blockers

- Broad persistence changes are unsafe until the remaining UI/schema owners are retired; the ADR-002 live archive, backup, restore, and zero-FK gates now pass.
- Remote deployment is intentionally out of scope for v2; current local UI mutation routes still need capability, approval, and egress enforcement before they can be a trusted control surface.
- UI change acceptance is reliable for M2/M3: anti-slop, ESLint, TypeScript, architecture, warning-baseline, build, seeded routes, responsive browser, console, network, and keyboard gates pass. Mutation ownership remains a separate modernization risk.
- The parallel v2 strategy still requires strict no-dual-write ownership, immutable backups, restore proof, and an explicit deletion ledger at every migration wave.
- The current dirty worktree prevents a clean modernization shadow comparison; implementation should begin only from an intentionally clean branch/worktree.

## Quality Ladder Notes

| Step | Status | Notes |
| ------ | -------- | ------- |
| Lint (ruff) | Fail | 2026-07-10 baseline found four diagnostics in `services/business/lint.py` and `services/business/pipeline.py`. |
| Type check (basedpyright) | Fail | 2026-07-10 baseline found three optional `ModuleSpec`/loader diagnostics in `tests/test_purge_noise_patterns.py`. |
| Dead code (vulture) | Pass | `pnpm dead-code` passed on 2026-07-10. |
| Runtime smoke | Pass | `pnpm smoke` and `aios doctor --json` passed on 2026-07-10. |
| Tests | Pass | `uv run pytest -q` passed on 2026-07-10 with 1,158 tests. |
| UI structure | Partial | Architecture lint passed; UI lint/typecheck and production build are currently blocked. |

Focused user commit gate checks on 2026-06-25:
- `uv run pytest tests/test_user_commit_quality_gate.py -q` passed with 28 tests.
- `uv run ruff check bin/user-commit-quality-gate.py tests/test_user_commit_quality_gate.py` passed.
- `uv run ruff format --check bin/user-commit-quality-gate.py tests/test_user_commit_quality_gate.py` passed.
- `uv run basedpyright bin/user-commit-quality-gate.py tests/test_user_commit_quality_gate.py` passed.
- `uv run vulture bin/user-commit-quality-gate.py --min-confidence 70` exited 0.

Focused expert workflow checks on 2026-06-24:
- `uv run pytest tests/test_aios_cli.py::test_tmcp_review_plan_writes_expert_review_artifacts tests/test_aios_cli.py::test_tmcp_review_plan_rejects_malformed_evidence_json -q` passed.
- `uv run pytest tests/test_workflow_orchestration.py::test_expert_review_workflow_registry_contract tests/test_workflow_orchestration.py::test_expert_review_workflow_executes_with_artifacts -q` passed.
- `uv run pytest tests/test_expert_rubric_remediation.py -q` passed.

Focused expert routing alias check on 2026-06-25:
- `uv run pytest tests/test_task_routing.py -k tmcp_expert_rubric -q` passed.

Doc-only update note: the 2026-06-24 expert-rubric-remediation spec, implementation-plan, GSD phase-split, and Phase 26-28 planning commits ran the staged AIOS commit-quality checks and passed the registered standards, context, success-criteria, quality-pipeline, allowlist, and staged handler-race gates. The Phase 26-28 planning pass also ran `verify plan-structure` and `frontmatter validate --schema plan` for all eight plan files plus `git diff --check`; `gap-analysis --phase-dir` exited 0 but warned because global `REQUIREMENTS.md` coverage is not scoped to these TBD-requirement phases. No repo-level Ruff, BasedPyright, Vulture, or pytest run was performed for those design/planning-only commits; existing repo-level failures remain authoritative.

Doc-only update note: the 2026-06-24 TDD Test Value Adoption Gate commit passed the staged AIOS commit-quality checks, `git diff --check`, `uv run pytest -q tests/test_success_criteria.py tests/test_commit_quality_ladder.py`, and `pnpm context:validate`. Full repo-level Ruff, BasedPyright, Vulture, and pytest were not rerun for this policy-only change; the existing repo-level failures remain authoritative.

## Agent Notes

- `bin/` contains both hook scripts (prefix `hook-`) and standalone utility scripts. Treat hook scripts as highest-priority for type-safety review — they run in every Claude Code session.
- `services/cts/` is the Code Topology Service package. The 2026-06-26 boundary audit keeps it inside AIOS as a sidecar/incubator candidate until portable contracts, fixture repos, query benchmarks, and a non-AIOS registry adapter exist.
- `archive/` and `staging/` are excluded from all quality tools per `pyproject.toml`. Do not audit those directories.
- The DB schema is append-only in practice; migration scripts exist in `bin/`. Always check `schema.sql` for current canonical table definitions before querying.
- shellcheck skips `.py` files named like shell scripts — no action needed there.
- zsh scripts (if any) are intentionally skipped by shellcheck; this is expected, not a gap.
- Agents should proactively surface better long-term approaches when they see them, including tradeoffs and a recommended path, while keeping the active task moving.

## QR Remediation Planning

- 2026-07-04: Added GSD Phase 30 for QR remediation from qr-fleet-continue-20260704-aios; 2 plan(s) created from aios.md. Execution has not started.
