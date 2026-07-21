---
schemaVersion: 1
projectName: AIOS
summary: Active local-first agent operating system with honest evidence verdicts, evidence-gated verify-run completion, durable eval-run recording, context-loop learning primitives, TMCP expertise compilation, standalone Quality Runner consumption, review-gated session-intelligence tools, and progressive colocated context routing across AIOS and linked repos; root and subsystem agent routers are now explicitly scoped.
healthScore: 85
statusLabel: warning
nextStep: Migrate the next legacy UI write family behind the Python owner with rollback/deletion proof; keep M6 deferred pending promotion-grade effectiveness evidence.
blockers: []
lastUpdated: 2026-07-21
tags: [infra, ai-os, hooks, automation]
areas: [engineering]
goals: []
repoType: infra
sourceOfTruth: mixed
primaryLanguage: Python
activeBranch: dev
lastCommitDate: 2026-07-21
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

Pattern approval and rejection UI mutations now route through the validated
Python-owned `pattern-approval-update` boundary; direct TypeScript updates were
deleted, with rollback to the parent revision and no schema migration.

_(9 older entries trimmed)_

_(11 older entries trimmed)_

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
- 2026-07-21: Added read-only Obsidian skill-package discovery with pinned provenance, host-layout availability, registry-state separation, and three focused tests (`8665ca2`).
- 2026-07-21: Declared Flask for the existing review-app runtime and refreshed the uv lock; `uv lock --check` and Flask import verification pass (`3ffdbee`).
- 2026-07-21: Refreshed the compiled context briefing and receipts after the router/audit changes; JSON validation and context compiler checks pass (`bd09f21`).
- 2026-07-21: Recorded the nested AIOS UI TypeScript 7 audit; the upgrade remains deferred pending toolchain support and a package-level baseline (`0608748`).
- 2026-07-21: Replaced the oversized root agent contract with a thin router and added scoped `aios-ui/` and `services/` agent routers; remaining active-dev slices are staged for separate verification (`e59df2d`).
- 2026-07-19: Added session-intelligence adoption review signals for dormant and underused implemented helpers, with 29 focused tests passing and Ruff clean (`f711e3e`).
- 2026-07-15: Routed pattern approval/rejection through the Python owner, deleted direct TypeScript updates, and passed 5 focused tests, the 97-test CLI regression slice, UI lint, architecture, build, and 3 browser tests (`4cd4183`).
- 2026-07-15: Routed `automations.triggerWorkflow` through the Python owner, launched the managed runtime from the validated `automation-trigger` CLI, deleted the direct TypeScript plan/invocation path, and passed 4 focused tests, 96 CLI regressions, UI lint, architecture, build, and 3 browser tests (`85de909`).
- 2026-07-14: Routed Taski project component toggles through the Python owner, deleted the direct UI SQLite helper, and passed 4 focused tests, 96 CLI regressions, UI build, architecture, and 3 browser tests (`82106f3`).
- 2026-07-14: Routed standards backfill Start/Block/Resolve mutations through the Python owner, deleted the direct UI SQLite helper, and passed 4 focused tests, 96 CLI regressions, UI build, architecture, and 3 browser tests (`fdd1c1d`).
- 2026-07-14: Migrated the Context Compiler page behind an explicit read-only projection contract with three-viewport browser proof; UI lint, architecture, build, and direct validation passed.
- 2026-07-14: Added durable eval-pair supersession metadata, append-only events, and a fail-closed promotion-ready consumer; audit history remains visible; 108 focused tests, Ruff, and BasedPyright passed.
- 2026-07-14: Routed the manual business-memory adapter through `capture.v1` for Markdown, JSON, HTML, and CSV, retaining the SourceRecord/raw-sidecar contract; 11 focused tests, Ruff, and BasedPyright passed (`625056d`).
- 2026-07-14: Added the `capture.v1` source-normalization boundary with pinned schema, deterministic adapters, provenance/removal records, CLI, fixtures, and focused proof; no network, enrichment, or vault writes (`b408ad5`).
- 2026-07-14: Closed the corrected three-task live audit benchmark: six clean runs, three pair-specific contamination records, six score IDs, independent review, and a bounded +0.013 treatment delta; M6 remains deferred (`docs/evals/M6_LIVE_BENCHMARK_REPORT.md`).
- 2026-07-14: Closed the eval-pair report-path contract gap with schema migration compatibility, CLI flags, round-trip tests, and 107 focused tests passing (`10c992a`).
- 2026-07-14: Captured one clean live control/treatment pair at `7797f3e` with passed contamination, independent review, persisted IDs, and a bounded +0.0500 portable-context delta; broader M6 evidence remains open (`docs/evals/M6_LIVE_PAIRED_REPORT.md`).
- 2026-07-14: Implemented the durable M5A `eval_pairs` contract with hash/parity validation, contamination and review gates, append-only pair events, CLI create/finalize/list commands, and 139 focused evaluation tests (`2eec354`).
- 2026-07-14: Recorded M5A deterministic paired harness evidence (AIOS 1.0000 vs control 0.5379, +0.4621) and deferred promotion pending clean live paired runs and independent review (`078f310`, `docs/evals/M5A_EFFECTIVENESS_REPORT.md`).
- 2026-07-14: Resolved M5 gated review/closeout with governed effect events, explicit capability/loopback/egress/redaction/rollback metadata, terminal writeback transitions, closeout downgrade gates, and fail-closed control-plane/remediation UI mutation procedures (`1ea29a0`).
- 2026-07-14: Fixed canonical start-work FK ordering, cross-project session linkage, and verification resume snapshots; added the M4 route → packet → run → invocation → verify/resume integration proof (`tests/test_m4_start_work.py`, `e190ca5`).

## Open Problems

1. The live main-store archive migration now reports zero FK violations with an immutable pre/post backup and ledger entry; older 555/557 audit snapshots and distributed runtime DDL still need reconciliation/cleanup.
2. V2 intentionally excludes remote control. Control-plane and remediation UI mutation endpoints now fail closed behind the Python owner; unrelated legacy UI write surfaces still require later consumer-by-consumer migration.
3. M2 and M3 UI validation is green, M4 Python route/packet/run/verify proof is green, and M5 governed review/closeout proof is green. M5A fixture evidence and the durable pair contract are recorded; the corrected three-task live audit corpus is independently reviewed but explicitly deferred because it is audit-only and provider telemetry is unavailable. The superseded single-task promote row is now excluded by the promotion-ready consumer while remaining in the audit ledger. The Context Compiler read-only, standards backfill owner, and project component owner slices are proven, but remaining write-owner migrations, rollback/deletion, cutover, and broad effectiveness claims remain blocked.
   Milestone 0's fixture/replay contract, storage boundary, copied-store recovery proof, and approved live archive are complete.
## Next Concrete Steps

1. Migrate the next legacy UI write family behind the Python owner with a rollback/deletion ledger and focused proof.
2. Keep M6 promotion and v2 cutover deferred while the corrected three-task evidence packet remains the bounded benchmark record and provider telemetry is unavailable.
3. Migrate remaining legacy UI write surfaces only through the Python owner with focused proofs.

## Risks / Blockers

- Broad persistence changes are unsafe until the remaining UI/schema owners are retired; the ADR-002 live archive, backup, restore, and zero-FK gates now pass.
- Remote deployment is intentionally out of scope for v2; remaining legacy local UI write surfaces still need consumer-by-consumer migration to the governed Python owner before they can be trusted control surfaces.
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
