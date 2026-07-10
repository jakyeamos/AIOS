---
schemaVersion: 1
projectName: AIOS
summary: Active local-first agent operating system with honest evidence verdicts, evidence-gated verify-run completion, durable eval-run recording, context-loop learning primitives, TMCP expertise compilation, standalone Quality Runner consumption, review-gated session-intelligence tools, and progressive colocated context routing across AIOS and linked repos.
healthScore: 85
statusLabel: healthy
nextStep: Use the new colocated context convention in future repo work while continuing to wire verify-run into hook-stop closeout and the pipeline reaper cadence.
blockers: []
lastUpdated: 2026-07-10
tags: [infra, ai-os, hooks, automation]
areas: [engineering]
goals: []
repoType: infra
sourceOfTruth: mixed
primaryLanguage: Python
activeBranch: dev
lastCommitDate: 2026-07-10
quality:
  lint: pass
  types: pass
  tests: pass
  deadCode: pass
  structure: pass
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

AIOS now uses progressive colocated context routing (2026-07-07). Root and repo `AGENTS.md` files are slim routers, deeper project knowledge lives in `.agents/context/`, module-specific context lives in `.context/`, and `tools/context-compile.mjs` can select repo-local and module-local context with receipt-visible reasons. The rollout also added a warning-only context validator at `/Users/jakyeamos/.agents/bin/validate-context.sh` and migrated linked repo prompt seeds out of the global playbook.

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
- 2026-07-10: Promoted all current pending-review session-intel candidates into telemetry-tracked helper families: 75 candidates across 6 touched implementation records; all 8 helper families remain active/monitor.
- 2026-07-10: Added repeatable `session-intel implement --candidate-id` targeting and used it to implement four latest Codex friction-tool candidates into `artifact_probe`, `bespoke_review`, `doc_excerpt`, and `package_check` with telemetry/removal monitoring.
- 2026-07-10: Added first-class session-intel helper telemetry, automatic run/failure recording, explicit helper bypass recording, decision-report telemetry rollups, and live `doc_excerpt` active status from a recorded helper invocation.
- 2026-07-10: Added the session-intel helper telemetry standard to local governance context and `docs/workflows/session-intel-helper-telemetry-standard.md`: prefer helper runs over equivalent ad hoc probes, record real bypasses, and avoid artificial live adverse telemetry.
- 2026-07-07: Added the progressive context convention, slimmed AIOS/Soundscape/GitNexus and GSD-injected repo routers, created `.agents/context/` indexes and command files across active repos, moved market/printing-press prompt seeds into repo-local context, and extended the AIOS context compiler to discover colocated repo/module context with deterministic receipt evidence.
- 2026-07-04: Stopped tracked runtime control-plane and session-effectiveness receipts from dirtying the worktree by removing generated `logs/control-plane/` and `logs/session-effectiveness/` artifacts from the index while preserving the ignored local operator paths; added a regression test that future receipts remain ignored and untracked.
- 2026-07-02: Integrated the repo closeout helper into daily-flow replay and UI operator surfaces: replay run steps now carry `metadata.repo_closeout`, CLI JSON exposes dirty files and diff stat through the trace, and the Command Center/run-detail trace renders repo path, branch, short HEAD, dirty-file count, and diff summary.
- 2026-07-04: Added the `aios quality rollout` Quality Runner adapter, AIOS rollout artifact index, durable evidence pointer recording, operator-flow docs, and lazy CLI imports so unrelated eval/shadow contract drift no longer prevents quality commands from starting.
- 2026-07-04: Replaced AIOS's direct `quality-evidence-contract` and `repo-quality-certifier` path dependencies with one local `quality-runner` dependency after Quality Runner absorbed those compatibility imports, CLI/MCP surfaces, and plugin metadata. Focused AIOS compatibility tests passed.
- 2026-07-02: Exposed the existing Vulture dead-code check through root `pnpm dead-code` and `pnpm audit:dead-code` scripts so Quality Runner detects the `dead_code` capability; final QR run `qr-clean-audit-20260702T200935Z-AIOS-final-2` has no missing repo-owned capabilities while inherited structural findings remain in generated/shadow worktree paths.
- 2026-07-02: Added repo-local Quality Runner scan exclusions for ignored operational worktrees plus root `pnpm smoke`; final QR run `qr-clean-audit-20260702T200935Z-AIOS-final-4` detects no missing capabilities but remains blocked because QR structural scanning still scans excluded ignored paths (`.aios/shadow-worktrees`, `.worktrees`, `.superpowers`, and `tmcp-benchmark/runs/worktrees`) unless whole structural rule groups are disabled.
- 2026-07-01: Tightened AIOS shadow-run recording so empty shadow lanes must carry an explicit no-evidence reason, persist `parity_checklist_status=no_evidence`, and cannot masquerade as measured shadow output before implementation, verification, or comparison evidence exists.
- 2026-06-30: Removed stale code-intelligence integration references from AIOS active/default project lists, prompt-submit retrieval hints, benchmark manifests, and linked-project planning docs; targeted Ruff, BasedPyright, JSON parse, and tier-one regression checks pass.
- 2026-06-25: Added an AIOS quality-pipeline `anti_slop` adoption/backfill gate for platform, production public web app, and developer-tool package repos, with audit-mode linked-repo commands and readiness regression coverage.
- 2026-06-26: Linked-repo adoption reports now require quality certification through `repo_gate_adoption_v1`, separating `aios_wired`, `quality_standard_compliant`, and `release_ready` stages from final `adoption_ready`, `adopted_but_blocked`, or `not_adopted` status.
- 2026-06-26: Completed Phase 29 pre-execution prep by refreshing the linked-repo adoption baseline, documenting first-wave repo branch/dirty state, and updating Phase 29 acceptance criteria to require `adoption_ready` plus passing certification stages.
- 2026-06-26: Added `BidCamp`, `tenure`, and `EliHealth` to the linked-repo adoption list, expanding Phase 29 to 23 in-scope repos; first evidence rows are recorded and the new repos are AIOS-wired but blocked until failing required gates pass.
- 2026-06-26: Upgraded `repo_gate_adoption_v1` to generate broad and gate-specific rubric packs before rollout planning, preventing sizable repo adoption from being scoped only by failed command gates.
- 2026-06-26: Wired conditional TMCP expert enrichment into `repo_gate_adoption_v1`; adoption artifacts now record `enriched` only when relevant TMCP source sufficiency passes, otherwise `insufficient_source` with AIOS standard rubric fallback.

## Open Problems

1. (none — the full repo quality ladder went green on 2026-07-06; see Quality Ladder Notes)
## Next Concrete Steps

1. Run a real shadow-lane implementation through the generated prompt and verify it transitions from `no_evidence` to `evidence_recorded` only after comparison evidence exists.
2. Decide whether AIOS should add a thin shortcut or adapter for invoking external Quality Runner runs.
3. Resume linked-repo adoption execution with BidCamp repo-local Phase 151, then continue BidCamp 152-155, EliHealth 09-13, and pre-cr-suite-lsp 04-06.

## Risks / Blockers

- Hook regressions are silent — no test safety net catches a broken stop hook until a session closes without writing its record
- The large number of scripts in `bin/` (60+) means drift and dead code accumulation are likely without regular Vulture runs
- Quality tooling is explicit but failing at repo level, so completion claims must distinguish targeted eval-run checks from full-repo health.

## Quality Ladder Notes

| Step | Status | Notes |
| ------ | -------- | ------- |
| Lint (ruff) | Pass | `uv run ruff check .` passed on 2026-07-06 after fixing the 24-issue baseline in four atomic commits (imports, dead code, strict zip, simplifications). |
| Type check (basedpyright) | Pass | `uv run basedpyright` passed on 2026-07-06 with 0 errors and 0 warnings after burning down the 107-error/78-warning baseline: extraPaths for sys.path-loaded bin modules, dict[str, Any] payload typing, single-assignment… |
| Dead code (vulture) | Pass | `uv run vulture bin services --min-confidence 70`, `pnpm dead-code`, and `pnpm audit:dead-code` passed on 2026-07-02; Quality Runner final run `qr-clean-audit-20260702T200935Z-AIOS-final-4` detects `dead_code` from… |
| Runtime smoke | Pass | `pnpm smoke` passed on 2026-07-02 and Quality Runner final run `qr-clean-audit-20260702T200935Z-AIOS-final-4` detects `runtime_smoke` from `package.json:scripts.smoke`. |
| Tests | Pass | `uv run pytest -q` passed on 2026-07-06 with 1122 tests, after both the lint-fix and format-only commits. |
| Structure | Pass | `uv run ruff format --check .` passed on 2026-07-06 after a single format-only commit reformatting 151 files (no logic changes). |

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
