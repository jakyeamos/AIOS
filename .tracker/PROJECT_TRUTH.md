---
schemaVersion: 1
projectName: AIOS
summary: Active local-first agent operating system with honest evidence verdicts, evidence-gated verify-run completion, durable eval-run recording, context-loop learning primitives, TMCP expertise compilation, standalone Quality Runner consumption, review-gated session-intelligence tools, and progressive colocated context routing across AIOS and linked repos.
healthScore: 85
statusLabel: warning
nextStep: Migrate remaining Python direct-connection adapters and close the restored-copy retention review, then freeze the paired effectiveness corpus before later execution.
blockers: []
lastUpdated: 2026-07-13
tags: [infra, ai-os, hooks, automation]
areas: [engineering]
goals: []
repoType: infra
sourceOfTruth: mixed
primaryLanguage: Python
activeBranch: dev
lastCommitDate: 2026-07-13
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

AIOS now has a completed v2 modernization baseline, accepted local-first operating model, canonical-state contract, task-centred UI contract, reproducible UI validation contract, subsystem modernization strategy, and dependency-ordered target/vertical plan: [`AUDIT.md`](../docs/modernization/AUDIT.md), [`TARGET.md`](../docs/modernization/TARGET.md), [`EXEC_PLAN.md`](../docs/modernization/EXEC_PLAN.md), [`ADR-001`](../docs/modernization/ADR-001-v2-operating-loop-and-trust-boundary.md), [`ADR-002`](../docs/modernization/ADR-002-canonical-state-and-migration-authority.md), [`ADR-003`](../docs/modernization/ADR-003-task-centred-ia-and-accessible-design-system.md), [`ADR-004`](../docs/modernization/ADR-004-reproducible-ui-validation-contract.md), and [`ADR-005`](../docs/modernization/ADR-005-subsystem-ownership-and-parallel-v2-strategy.md). Wayfinder Ticket 006 is resolved; Milestone 0 has the shared JSON fixture, TypeScript boundary guard, Python cross-reference tests, disposable SQLite projection, and daily-flow replay proof. Milestone 1 now has the executable Python storage boundary, copied-store runner, evidence-backed FK transformer, and adapter adoption: one resolved `AIOS_DB`, canonical pragmas, read-only projections, idempotent migration/quarantine ledger, schema checksums, preflight/postflight health/counts, unique-path mappings, source-payload quarantine, and immutable backup/restore helpers; the three lifecycle hooks and UI database path now converge on the override/pragmas. The actual current read-only store preflight reports 561 FK violations (older audit documents record 555/557); the disposable transformer copy reaches zero and the restored copy replays the canonical daily flow. UI-owned request-time DDL, remaining Python direct connections, and human retention review are still gated. V2 is a single-user, loopback-only local control plane with one logical mutation authority; no live rows have been migrated. The target and plan now turn those decisions into eight vertical milestones plus a paired-effectiveness gate before satellite promotion and cutover. Divergent schema/bootstrap ownership, unenforced UI mutation boundaries, and blocked UI implementation gates remain. The current `dev` worktree was already dirty when this work started, so its shadow lane remains trace-only.

_(4 older entries trimmed)_

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
- 2026-07-13: Adopted the storage contract in lifecycle hooks and the UI database adapter (`5588b05`): shared `AIOS_DB` override, foreign-key/WAL/busy-timeout pragmas, and read-only inspection behavior without changing live rows.
- 2026-07-13: Added the evidence-backed known-FK transformer (`990a6d9`): 561 copied-store violations reached zero without synthetic parents; 255 quality rows mapped, 73 archived unresolved, 180 session references nulled after quarantine, and 53 shadow-task references nulled after quarantine.
- 2026-07-13: Added the copied-store migration/recovery proof (`5a3e2c1`): preflight health/counts, explicit orphan quarantine transformer, zero-FK validation before ledger recording, post-migration backup, and source-immutability/failure tests.
- 2026-07-13: Started Milestone 1 with the Python storage contract (`2453c42`): canonical `AIOS_DB` connection pragmas, read-only mode, idempotent migration ledger, quarantine inventory, schema health/checksum, immutable backup/restore helpers, CLI adoption, and 95 focused tests.
- 2026-07-13: Added Milestone 5A paired AIOS-effectiveness evidence to the modernization plan (`0b088ab`): freeze the control baseline, compare matched control/treatment runs, require ablation/report evidence, and block cutover on an explicit decision.
- 2026-07-13: Completed Milestone 0 persisted-row replay proof (`66eb586`): the closed fixture maps route, packet, run, evidence, writeback, and canonical daily-flow steps in disposable SQLite with zero live-state writes.
- 2026-07-13: Started Milestone 0 with the shared v2 vertical fixture contract (`563bc66`): six required operator states, route/packet/run/evidence/approval/projection linkage, TypeScript shape guard, Python consistency tests, and recorded complexity-gate evidence.
- 2026-07-13: Resolved Wayfinder Ticket 006 and recorded the target/vertical-plan decision in the modernization map (`aa86ece`); implementation frontier is now Milestone 0 shared contracts and Milestone 1 canonical recovery.
- 2026-07-13: Accepted the AIOS v2 target and vertical modernization plan (`709474f`): eight gated slices from shared fixtures and canonical recovery through UI validation, governed execution, satellites, cutover, adversarial review, and deletion.
- 2026-07-13: Accepted the AIOS v2 subsystem ownership and modernization strategy (`7600d83`): parallel v2 progressive migration with one state/mutation owner, core/sidecar/adapter boundaries, and rollback/deletion posture.
- 2026-07-13: Accepted the reproducible AIOS UI validation contract (`878b03e`): explicit pnpm/Node and workspace posture, packaged dependencies, local/system fonts, independent quality gates, runtime smoke, browser matrix, and console/network failure policy.
- 2026-07-13: Accepted the task-centred AIOS v2 UI contract (`6e7d002`): Today → Start work → Current run → Verify → Gated review → Closeout IA, route disposition, representative slice prototypes, accessible design tokens, and executable browser/keyboard/console proof gates.
- 2026-07-13: Accepted the AIOS v2 canonical-state and migration contract (`04f02e3`): one Python-owned versioned ledger, shared connection policy, quarantine-first FK repair, backup/restore gates, and explicit privacy invariants.
- 2026-07-10: Accepted the AIOS v2 local-first operating model (`7a217e1`): loopback-only local control plane, human approval for privileged effects, and no remote/split/shared product in v2.
- 2026-07-10: Charted and committed the AIOS v2 modernization decision map (`ea8d464`): baseline/invariants first, then operating-loop/trust, state/migrations, task-centred UI, subsystem strategy, and a vertical implementation plan.

## Open Problems

1. The current main-store preflight reports 561 persisted foreign-key violations (older audit documents record 555/557); divergent SQL snapshots, distributed runtime DDL, and live restore ownership remain unresolved.
2. V2 now intentionally excludes remote control, but current UI mutation endpoints still lack the required loopback, local-capability, approval-enforcement, and single-mutation-owner implementation.
3. UI implementation remains blocked by the deterministic validation gates: the external anti-slop file dependency is stale/out-of-repo, fonts are network-sensitive, Turbopack root/tracing warnings remain, and the dev tRPC adapter import still fails.
   Milestone 0's fixture/replay contract, storage boundary, and copied-store recovery proof are complete; adapter adoption, human review of the 73 archived quality rows, and ADR-004 UI preconditions remain before later write-capable/UI work.
## Next Concrete Steps

1. Migrate remaining Python direct-connection adapters and remove UI request-time DDL only after deterministic migration/UI gates pass.
2. Complete the restored-copy review and explicit retention/deletion decision for archived quality payloads.
3. Freeze the paired effectiveness corpus/control baseline and resolve ADR-004 UI preconditions before the v2 read-only shell.

## Risks / Blockers

- Broad persistence changes are unsafe until the ADR-002 migration owner is adopted by all adapters, the current 561 violations are reviewed against the copied proof, and live backup/restore ownership passes.
- Remote deployment is intentionally out of scope for v2; current local UI mutation routes still need capability, approval, and egress enforcement before redesign work can use them as a trusted control surface.
- UI change acceptance is currently unreliable because the anti-slop package, font path, Turbopack root/tracing, tRPC adapter, duplicate keys, and browser harness gates remain unresolved; ADR-004 defines the evidence contract but does not claim those repairs are complete.
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
