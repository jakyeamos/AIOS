# AIOS Project Truth

Last updated: 2026-07-14

## What AIOS Is

AIOS is the local operating system for work context, agent workflows, and durable project memory.
It is the orchestration layer for agents across all linked development projects, not just a dashboard or standards system for this repository. It is intended to unify:

- structured knowledge pages
- grounded retrieval and query surfaces
- workflow and orchestration state
- task-specific delegation packets
- durable continuity across long-running sessions

## Current Reality

The repository currently contains five meaningful subsystems:

1. `aios-ui/`
   A Next.js local dashboard over `~/AIOS/data/aios.db`. It is strongest at session/run observability.

2. `bin/` and `services/`
   Python hooks, importers, storage maintenance tools, and the CTS prototype.

3. `docs/`
   Design intent for storage, knowledge, CTS, and the current UI, but not yet a single implemented architecture.

4. `aios/context/`
   The file-backed AIOS Context Compiler: tiered Markdown routing manifests, deterministic task compilation, generated briefings, and context receipts.

5. `aios/context-loops/`
   The file-backed contract layer for inner/outer context learning loops: approved/rejected lessons, review taxonomy, retrieval policy, examples, and email pilot guidance.

Root operator documentation now lives in `README.md`, including local UI launch commands, key UI routes, store paths, workflow proposal backfill, and verification commands.

## V2 Modernization (2026-07-14)

The read-only v2 operator shell is shipped behind the canonical projections:
Today (`/`), Start work (`/start`), and Current run (`/runs/:id`). It uses one
task-centred primary navigation with contextual satellites, preserves legacy
session detail fallback, and exposes provenance, freshness, authority, next
action, and explicit healthy/blocked/stale/empty states without emitting
mutations. M2 and M3 browser, accessibility, network, console, architecture,
lint, typecheck, anti-slop, context, and production-build gates pass. M4 now
proves the Python-owned route → packet → run → invocation → verification
envelope against foreign-key enforcement, including partial-state resume
snapshots and source-backed verifier evidence. M5 is the next gated slice for
approval, capability, egress, writeback, and closeout enforcement. M5 now adds
Python-owned governed effect events and closeout reviews, blocks non-loopback
or unredacted effects, requires explicit approval/rollback/evidence metadata,
and downgrades incomplete closeout to follow-up instead of claiming success.
The v2 UI mutation procedures remain read-only guards until they are routed
through this owner. M5A records deterministic paired fixture evidence (AIOS
1.0000 versus control 0.5379, +0.4621 mean delta), but defers promotion because
the baseline is dirty and the fixture path lacks live model/tool/budget
metadata, persisted paired eval ids, contamination proof, and blinded
independent review. M6 remains blocked until clean real paired runs are
captured and reviewed.
The follow-up `eval_pairs` contract now durably links control/treatment runs,
protected start SHA, task/prompt/context hashes, parity metadata, scores,
contamination and independent-review state, decisions, and append-only pair
events. Its CLI create/finalize/list surface fails closed on promotion without
complete evidence. A corrected three-task live audit corpus now has six clean
runs, three pair-specific contamination records, six durable score IDs, and a
fresh independent review; the bounded mean is `0.963` control versus `0.977`
treatment (`+0.013`). Pair decisions remain deferred because the tasks are
audit-only and provider usage telemetry is unavailable. The earlier single-task
promote row is superseded because its treatment artifact was missing and is
excluded from the corrected packet. M6 remains blocked pending the first named
satellite's adapter, mutation-owner migration, rollback/deletion evidence, and
full browser proof.

The first adapter-scoped satellite slice now routes manual business-memory
Markdown, JSON, HTML, and CSV sources through the deterministic `capture.v1`
boundary. Existing `SourceRecord` ingestion remains the contract, while the
immutable raw sidecar retains capture validation and provenance/removal
metadata. No network, enrichment, vault write, schema migration, or promotion
was added; focused adapter proof is recorded in
`tests/test_business_capture_adapter.py`.

Superseded eval-pair evidence is now excluded at the promotion consumer
boundary without deleting audit history. The canonical eval schema records
durable supersession metadata and an append-only event; `eval pair-list
--promotion-ready` requires complete score, contamination, independent-review,
report, and unsuperseded gates, while the ordinary pair list remains the full
ledger. Focused service/CLI proof passed 108 tests, Ruff, and BasedPyright.
M6 remains blocked by the audit-only corpus, unavailable provider telemetry,
incomplete browser coverage, and remaining satellite mutation/rollback gates.

The Context Compiler is now the first browser-proven read-only satellite slice.
Its server projection names the file-backed compiler source, compiler
authority, CLI mutation owner, freshness state, and next action; `/context`
renders that contract without adding a second context store or write path.
The three-viewport browser contract, UI lint, architecture lint, production
build, and direct context validation pass. The root `pnpm context:validate`
wrapper remains blocked by the existing external `context-compiler-contract`
file dependency, with no dependency or lockfile changes made. M6 is advanced
but remains deferred on promotion-grade effectiveness and write-owner/
rollback gates.

## Implemented On 2026-07-10

Codex session-intelligence implementation can now target explicit candidate ids:

- `python bin/aios.py session-intel implement --candidate-id <id>` limits adoption to named candidates, and the flag can be repeated for review batches
- targeted implementation still groups adopted candidates into existing helper-family implementation records with `telemetry_status=awaiting_telemetry`, `removal_status=monitor`, removal reasons, artifact refs, and review events
- this prevents a human approval for the latest daily-review candidates from accidentally implementing the full historical pending backlog
- the four latest approved Codex friction-tool candidates were implemented into the existing `artifact_probe`, `bespoke_review`, `doc_excerpt`, and `package_check` helper-family records with removal monitoring left active
- focused tests cover parser support, explicit candidate filtering, untouched unrelated pending candidates, and incremental helper-family candidate-id merging

Codex session-intelligence helper-family telemetry is now first-class:

- `session-intelligence_helper_telemetry` records helper family, implementation id, covered candidate ids, invocation status, latency, redacted input shape, error metadata, caller surface, and optional run/session/task ids
- `python bin/aios.py session-intel helper run ...` records success telemetry and failure telemetry automatically; `python bin/aios.py session-intel helper bypass --family <family> --reason <reason>` records manual bypasses
- helper-family implementation records now move from `awaiting_telemetry` to `active`, `insufficient_telemetry`, or `removal_review_ready` based on usage evidence; repeated adverse evidence marks the helper as a `removal_candidate`
- the canonical daily decision report now summarizes helper invocations, successes, failures, bypasses, median latency, last-used timestamp, and telemetry candidate coverage inside Removal Candidates
- live verification recorded one successful `doc_excerpt` invocation, so `session-intel helper list` now reports `doc_excerpt` as `active` while the other helper families remain awaiting telemetry
- `.agents/context/governance.md` and `docs/workflows/session-intel-helper-telemetry-standard.md` now make helper telemetry the standard: use `session-intel helper run` instead of equivalent ad hoc probes when a helper family applies, record real bypasses with `session-intel helper bypass`, and avoid artificial live failure/bypass telemetry

## Implemented On 2026-07-03

Codex daily session intelligence now has a first-class review-only wrapper:

- `python bin/aios.py session-intel daily-codex --json` encapsulates `.venv/bin/python /Users/jakyeamos/AIOS/bin/aios.py session-intel run --provider codex --since last --write-report --json`
- the wrapper always runs Codex `since=last` with report writing enabled, returns a clean `report_paths` object for Markdown, JSON, and canonical daily decision reports, and preserves the underlying per-run report fields for compatibility
- behavior remains review-only: the wrapper creates or updates pending-review candidates and report artifacts without approving, rejecting, implementing, installing, generating, or applying candidate artifacts
- tests cover parser support, wrapped-command metadata, report path materialization, persisted `provider=codex` / `scanned_range=last`, pending-review candidate state, and absence of implementation or review-event side effects

## Implemented On 2026-07-02

Codex session-intelligence helper-family adoption now creates real deterministic helper command surfaces:

- `python bin/aios.py session-intel helper list` lists adopted helper-family presets from `session_intelligence_implementations`, including candidate coverage, telemetry state, removal state, and artifact reference
- `python bin/aios.py session-intel helper run --family doc_excerpt --path <file> --start-line <n> --end-line <n>` performs bounded line-oriented file excerpts with stable line numbers and a 500-line cap
- `artifact_probe` summarizes JSON and CSV artifacts with deterministic metadata such as SHA-256, size, top-level JSON keys, array lengths, CSV headers, and row count
- `repo_state` and `git_history` run fixed read-only Git probes for branch/status/diff evidence and recent history evidence without executing arbitrary candidate commands
- `package_check` reads package-manager authority from `package.json` and committed lockfiles, surfaces scripts and likely quality scripts, and does not infer capability from `node_modules`
- `deployment_flow`, `bespoke_review`, and `workflow_skill` now have deterministic inspection surfaces for deployment evidence, low-shape review triage, and workflow-skill candidate review instead of remaining database-only adoption records
- behavior is split by helper-family responsibility with no intentional behavior changes to existing session-intel run/candidates/clusters/mark/implement flows
- tests cover parser support, adopted-family listing, bounded excerpts, JSON/CSV artifact probing, and package-check lockfile/script reporting

Codex repo-state closeout now has a narrow deterministic helper:

- `python bin/aios.py repo closeout --repo <path>` prints one stable closeout report with branch, full HEAD SHA, dirty flag, dirty files in Git porcelain format, diff stat, and recent commit titles
- `python bin/aios.py --json repo closeout --repo <path>` exposes the same state as `aios-repo-closeout-v0.1` JSON for agent workflows and future automation
- the helper is read-only and lives under the existing `repo` command family beside `repo inspect`, based on session-intelligence evidence that repeated `git status` and `git diff --stat` inspection created closeout friction
- `daily-flow --run-id` now attaches the helper payload to the canonical run step as `metadata.repo_closeout` when the run's project has a known `projects.repo_path`, preserving the eight-step daily-flow order while surfacing repo state in closeout traces
- `aios-ui/server/aios/daily-flow.ts` mirrors the same `aios-repo-closeout-v0.1` shape, and `DailyFlowTrace` renders repo path, branch, short HEAD, dirty-file count, and diff stat on Command Center and run-detail surfaces
- tests cover the helper payload, CLI renderer, daily-flow service replay payload, and daily-flow CLI JSON replay against a real temporary Git repository, including preserved porcelain status spacing and normalized diff-stat lines

AIOS Vaults validation is now trust-tier aware:

- `scripts/content-container-validator.py --project Vaults` reports category-specific findings for unsafe content, missing trusted-note metadata, stale trusted notes, raw notes in trusted areas, broken trusted wikilinks, and quarantine candidates
- validator output redacts secret-like and phone-like path segments before printing findings, so path-based reports do not leak likely secrets
- archive, quarantine, raw personal corpus, and generated session handoffs no longer create trusted-wikilink noise unless explicitly promoted through trust metadata
- Obsidian path-style wikilinks now resolve against stem, vault-relative path, and repo-relative path targets, commented template examples are ignored, and generated `.aios/audit` Markdown is treated as raw hook output instead of trusted-note metadata debt
- `tests/test_content_container_validator.py` covers trusted metadata findings, trusted-only wikilink checks, path-style wikilink resolution, commented wikilink suppression, generated audit Markdown classification, archive noise suppression, and redacted secret-like quarantine candidates
- verification: `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_content_container_validator.py` and `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check scripts/content-container-validator.py tests/test_content_container_validator.py`

## Implemented On 2026-07-01

AIOS daily-use release readiness is now the primary near-term product target:

- `bin/aios.py` can fall back to `uv run` when direct `python3 bin/aios.py ...` invocation cannot import extracted local path dependencies, preserving the documented direct help/smoke contract
- `uv run python bin/aios.py --json doctor` now reports a local release-readiness preflight covering extracted Python package imports, SQLite reachability, local store directories, pnpm-only package-manager state, context compiler package access, and the required daily-use command surface
- behavior tests cover direct CLI help, health JSON, doctor pass/fail output, and the integrated daily loop: `start-work` creates route/packet/run/invocation ids, `daily-flow --run-id` replays the eight canonical evidence steps, and `next-action --project` returns project-scoped follow-up work
- the AIOS UI quality workflow now uses pnpm/corepack with `aios-ui/pnpm-lock.yaml`; root and UI package manifests declare `packageManager: pnpm@11.7.0`; the stale `aios-ui/package-lock.json` npm lockfile has been removed
- `README.md` now leads with the daily-use loop and a "When Not To Use AIOS" boundary so tiny edits and direct answers do not route through the operating layer by default
- `docs/case-study.md` records the daily-use release proof story, architecture loop, safety boundary, release evidence, and known limits
- linked-repo Phase 29 certification remains valuable, but it is no longer the release centerpiece until AIOS itself passes the daily-use readiness path consistently

AIOS shadow setup now separates clean worktree creation from missing implementation evidence:

- `codex-aios-shadow` and `aios shadow create-worktree` verify the new shadow branch against the captured start SHA before recording the initial shadow row
- a newly created shadow lane can report `contamination_check_passed: true` while still reporting `parity_checklist_status: no_evidence` until the shadow prompt has actually run
- this removes the misleading initial contamination warning that made automatic shadow procedures look untrustworthy even when the worktree was clean

## Implemented On 2026-06-30

Codex session intelligence scans now write a canonical daily decision report:

- `session-intel run --write-report` still emits the per-run Markdown and JSON artifacts, and now also returns `decision_report_path`
- the canonical report is provider-specific at `data/session-intelligence/reports/{provider}-daily-candidate-decisions.md`, so the daily Codex automation updates `codex-daily-candidate-decisions.md` in place
- the decision report separates `New in latest scan` from `All pending candidates`, so small `--since last` runs do not hide the cumulative pending backlog
- both decision sections are grouped by `friction_tool`, `workflow_skill`, and `impact_idea`, with pending-review counts, candidate ids, impact/confidence, proposed artifact type, next decision, summaries, and redacted evidence excerpts
- each pending candidate now includes an anecdotal setting narrative that explains what the candidate would help with in a concrete future work scenario
- friction-tool candidates are rolled up by reusable helper family, such as `repo_state`, `git_history`, `artifact_probe`, `doc_excerpt`, `package_check`, and `deployment_flow`, before individual candidate details; each family carries candidate count, impact/confidence summary, and a shared-preset recommendation before any one-off helper is considered
- the daily decision report now includes an implementation telemetry contract and a `Removal Candidates` section, so approved future helpers/skills/workflows should be measured for benefit and later surfaced for removal when telemetry shows neutral or negative value
- operators can now run `session-intel implement` to adopt pending or approved candidates into telemetry-tracked helper-family implementation records; the current Codex backlog is covered by seven monitored families (`doc_excerpt`, `bespoke_review`, `artifact_probe`, `package_check`, `deployment_flow`, `git_history`, and `repo_state`) with removal monitoring and no remaining pending-review candidates at the time of adoption
- behavior is intentionally review-only: the report surfaces candidate decisions without approving, rejecting, installing, generating, or applying candidate artifacts

## Implemented On 2026-06-25

AIOS planning is now a governed first-class `start-work` route for tested GSD planning objectives:

- `config/planning/gsd-workflow-phases.json` recognizes GSD phase-add, new-phase, blocker-to-phase, roadmap-phase, and phase-planning language as configured GSD planning aliases without turning unrelated implementation objectives into planning work
- `config/workflows/registry.json` registers active `planning-governance`, and `config/workflows/skills.json` defines registry-only planning compiler and contract validator skills with standards-before-execution and verification-handoff invariants
- `services.workflow_orchestration.recommend_route_primitives()` consumes structured GSD planning detection and selects `planning-governance` for the tested phase-add objective while existing ambiguous/unsupported route blocking remains covered by regression tests
- `services.aios_cli` appends planning-governance packet sections for Planning Quality Contract, Required Planning Artifacts, Standards Before Execution, and Verification Handoff, and the route recommends creating planning artifacts before implementation
- known GSD execution command evidence is covered for `gsd-execute-phase 24` and `Execute GSD phase 24`; both route to the existing governed `implementation-delivery` lane because AIOS does not yet have a separate active GSD execution workflow
- regression evidence covers planning detection, workflow routing, task routing, start-work packets, Codex route helper output, Codex shadow helper `--no-worktree` output, and copied-DB shadow smokes for the original planning objective plus `gsd-execute-phase 24`

## Implemented On 2026-06-24

AIOS automatic Codex shadow routing now has an explicit nonblocking diagnostic contract:

- `bin/codex-aios-shadow` is the narrow Codex-facing entrypoint for shadow setup, so agents can request or approve that specific Git-writing capability instead of running the Python helper as an arbitrary `python3` command
- `scripts/codex-aios-shadow.py` marks automatic route failures with machine-readable `baseline.approval_required: false` and `baseline.can_continue_without_shadow: true`
- `AGENTS.md`, `README.md`, and `docs/diagnostics/route-blocked-failures.md` distinguish automatic route misses from shadow setup failures, so `ok: true`, non-governed `route_failed` payloads no longer require explicit user approval before baseline work continues
- governed `/aios` route failures remain blocking, while automatic shadow route misses continue to be appended to `data/aios-route-failures.jsonl` as diagnostic evidence

AIOS now has an explicit durable-agent-workflow layer:

- `aios/context/packets/workflow.durable-agent-workflows.md` defines the concise agent-facing contract for durable workspaces, goal verifiers, steering, queueing, declared work surfaces, reviewable artifacts, automation modes, durable memory, and TMCP skill candidacy
- `docs/workflows/durable-agent-workflows.md` is the reviewable workflow reference with `/steer` and `/queue` patterns, artifact/source-of-truth guidance, scheduled-vs-workspace automation guidance, durable memory rules, and evidence-backed skill extraction criteria
- `aios/context/domains/agent-harnesses.md` now loads the durable workflow packet for agent-harness work so long-running workloop guidance is selected through the normal context compiler path rather than copied into broad always-loaded prose
- `config/workflows/registry.json` registers `durable-agent-workspace` as a candidate workflow, preserving existing active routing while making durable work loops discoverable in the workflow registry
- `config/workflows/skills.json` registers candidate `durable_workspace_state_keeper` and `durable_goal_verifier` skills with explicit invariants for verifier-backed goals, distinct steering and queueing, declared tool surfaces, meaningful memory updates, and no transcript-sprawl
- `OPERATING_LANGUAGE.md` now includes Durable Workspace, Goal Verifier, Steering Event, Queued Work, Work Surface, and Reviewable Artifact as canonical AIOS terms

AIOS now has instruction-hygiene support for behaviorally inert agent prose:

- `config/tmcp/portable-dev-process/modules/instruction_hygiene.md` defines no-op criteria, candidate categories, scoring, evidence requirements, safety exclusions, dispositions, required audit records, and validation procedure
- `config/tmcp/portable-dev-process/tasks/instruction_hygiene.md` routes future skill, prompt, router, workflow, and agent-facing instruction cleanup through the new module plus diff review and quality gates
- `tools/no-op-instruction-scan.mjs` and `pnpm tmcp:no-op-scan` provide an advisory scan for generic instruction candidates with line-level allowlist support in `config/tmcp/no-op-scan-allowlist.json`
- `config/tmcp/audits/no-op-cleanup/` records the discovery inventory, candidate ledger, static proof, provenance, dependency, conflict, merge, validation, and improvement reports for the initial cleanup

AIOS linked-project adoption contracts now cover the active source inventory:

- AIOS-owned `config/quality-gates.json` registers allowlisted quality-gate adapters for 21 linked repositories beyond AIOS and soundscape-app, using existing repo-local quality surfaces such as package scripts, `.pre-cr.json`, or existing architecture scripts, with a minimal `git diff --check` floor for the BBDSE container repo that has no stronger local quality surface yet
- floor-only and `pre_cr`-only adoption contracts have been replaced with `class_blocked` maturity where the repo is not yet strict-ready, so baseline hook coverage cannot be mistaken for mature AIOS quality-standard compliance
- matching `.aios-quality-gate.json` contracts were added to those linked repositories so the portable user-level commit hook can validate gate IDs without executing repo-local shell from untrusted config
- live project inventory hygiene marked missing-source rows, broad container rows, non-git config folders, and duplicate `Projects`/`projects` casing rows inactive instead of deleting historical records
- `schema.sql` now includes `project_inventory_hygiene_events` so inventory status changes have a durable event trail aligned with the SQLite schema authority
- `prove-project-health --all-inventory` now targets active inventory rows only, so inactive duplicates and bad paths do not reappear in adoption proof runs
- active project inventory is now limited to actual source repos plus existing first-class source projects; known inactive rows include `.claude`, `Downloads`, `jakyeamos`, `projects`, missing repos such as `Bball`, and duplicate uppercase path rows for `Dsci-proj` and `Fantasy`
- Phase 23 now owns linked-repository strict release-readiness maturation after Phase 22 as eight GSD-standard plans covering audit, class-based contracts, class-specific repo maturation, evidence reporting, final verification, CI/default-branch proof, and explicit treatment of dirty trees as lower-priority closeout hygiene rather than the main adoption blocker
- Phase 23 execution produced `.planning/phases/23-mature-linked-repositories-to-aios-strict-release-readiness/23-VERIFICATION.md`: 23 active repo contracts validate, copied and live all-inventory standards-health proof record 23 snapshots with no missing-source contamination, but strict adoption readiness remains blocked with 0 ready repos, 2 evidence-required repos (`soundscape-app`, AIOS), and 21 blocked repos
- BBDSE is no longer represented as mature by `git diff --check`; it is a blocked container repo with delegated subproject Pre-CR gates across all child repos, including LIS, and still needs aggregate evidence plus local CI proof before readiness
- Phase 24 Plan 24-02 recorded fresh local evidence rows for `soundscape-app` and AIOS through `scripts/linked-repo-quality-runner.py`; both repos remain blocked rather than ready because several gates failed or remain blocked, and local replacement CI proof has not passed
- 2026-06-26 linked-repo readiness reports now carry a hard quality-certification object using `repo_gate_adoption_v1` as the required subworkflow, so adoption output distinguishes AIOS wiring, quality-standard compliance, release readiness, and final `adoption_ready` / `adopted_but_blocked` / `not_adopted` classification.
- `repo_gate_adoption_v1` now writes a broad and gate-specific rubric pack before rollout planning. The pack covers complexity/simplification, anti-slop/product quality, architecture boundaries, test quality/value, UI visual/runtime verification, dead code, security/secret handling, dependency risk, truth/docs accuracy, and CI/local proof integrity, so sizable repos are not remediated only from failed command names.
- `repo_gate_adoption_v1` now materializes each broad and gate-specific rubric into Markdown and JSON audit/implementation docs, with `rubric-detail-manifest.json` as the agent-readable index for later GSD phase generation.
- `repo_gate_adoption_v1` now carries repo classification evidence, selected AIOS quality-pipeline profile context, required profile gates, configured command metadata, strict-readiness blockers, and UI visual-proof routing into the rubric pack and per-rubric docs.
- `aios gate adoption-doc-quality` now generates the adoption pack and writes `adoption-doc-quality.json` / `.md`, failing missing or structurally invalid generated docs and carrying explicit readiness fields. Per-rubric docs now include scan-derived evidence, missing-proof blockers, root causes, affected files/scripts, accepted-exception status, and validation commands before those docs become GSD phase inputs.
- UI-bearing repo adoption now requires visual/runtime confirmation through local launch plus browser/device automation, screenshots, computer use, Xcode simulator, or equivalent proof; UI lint/typecheck/component tests and TMCP UI rubric review are supporting evidence, not sufficient proof by themselves.
- `repo_gate_adoption_v1` conditionally enriches rubric packs with TMCP expert context only when the compiled packet has enough relevant source evidence. When source sufficiency fails, adoption artifacts record `insufficient_source` and fall back to AIOS standard rubrics instead of claiming unsupported TMCP expertise.
- `repo_gate_adoption_v1` writes generated adoption documents under `AIOS-backfill/gate-adoption/{run_id}` and adds `AIOS-backfill/` to the target repo's local `.git/info/exclude` when possible, so adoption audits do not flood tracked repo docs.
- `repo_gate_adoption_v1` now includes core adoption rows for `complexity_budget`, `install`, `secret_scan`, `dependency_security`, `package`, `validation`, `mobile_release`, `e2e_smoke`, `pre_pr_readiness`, and `thermo_nuclear_simplification`, so linked-repo adoption plans surface Big-O/performance-regression and quality-pipeline readiness alongside lint, typecheck, tests, build, Pre-CR, anti-slop, CI, and local hook enforcement.
- Phase 29 pre-execution prerequisites are captured in `.planning/phases/29-linked-repo-aios-adoption-readiness-remediation/29-PREREQUISITES.md`, with fresh baseline artifacts in `29-BASELINE.json` and `29-BASELINE.md`; current counts are `target_count: 23`, `ready_count: 0`, `blocked_count: 23`, `evidence_required_count: 0`, `adoption_ready_count: 0`, `adopted_but_blocked_count: 23`, and `excluded_count: 3`.
- Phase 29 scope now includes newly added adoption targets `BidCamp`, `tenure`, and `EliHealth`; all three have first quality-pipeline evidence rows recorded, `BidCamp` and `tenure` use the production public web app profile, and `EliHealth` uses the mobile app profile.
- Phase 29 workflow quality-testing will pilot `repo_gate_adoption_v1` on new target-repo branches for `BidCamp`, `EliHealth`, and `pre-cr-suite-lsp`, covering dense production web, mobile/native, and non-UI developer-tool adoption before portfolio-wide execution.
- The BidCamp Phase 29 workflow-quality pilot now passes `aios gate adoption-doc-quality` as `phase29-bidcamp-pilot-008` with `status=pass`, `warning_count=0`, `ready_for_phase_planning=true`, and `ready_for_execution=true`; the gate matrix distinguishes `present=14`, `enforceable=13`, `absent=7`, and `skipped=2`, with `local_quality_contract` treated as required setup rather than a skip. The generated artifacts remain under git-ignored `AIOS-backfill/gate-adoption/`.
- Phase 29 pilot repos now have local adoption gate setup committed and pushed on their target branches: `BidCamp` (`145b6bd0`, `phase29-bidcamp-pilot-setup-002`), `EliHealth` (`30b9d4d`, `phase29-elihealth-pilot-setup-002`), and `pre-cr-suite-lsp` (`cfc8afd`, `phase29-pre-cr-suite-lsp-pilot-setup-002`). All three latest adoption-doc-quality runs pass with `warning_count=0`, `absent=0`, and `local_quality_contract` present; `mobile_release` is skipped only for non-mobile repo classes and `local_hook` remains an optional skip when CI/local replacement proof is sufficient.
- Phase 29 pilot remediation planning now lives inside the owning repos: `BidCamp` phases `151`-`155`, `EliHealth` phases `09`-`13`, and `pre-cr-suite-lsp` phases `04`-`06`, all sourced from the final `*-pilot-final-doc-pass-001` artifact packs. AIOS remains the portfolio coordinator and readiness evidence ledger rather than owning per-repo gate execution phases.
- `repo_gate_adoption_v1` now enforces that model in generated artifacts: rollout plans use `repo_local_gate_scoped` scope, `target_repo` phase ownership, per-gate repo-local phase templates by default, an explicit final certification phase, and validation that rejects AIOS-owned phases or multi-gate clusters without a concrete shared-root-cause rationale.
- `repo_gate_adoption_v1` now treats full lint and full test failures as strict clearance work. Generated lint/test phases require clearing inherited baseline failures across the repo, focused checks are only interim debugging proof, and final certification cannot classify a repo as `adoption_ready` while full lint or full tests still fail from an inherited baseline.
- `repo_gate_adoption_v1` now models tier-one quality with fifteen broad certification rubrics and corresponding first-class gate rows where commands/proof are actionable: build/package integrity, runtime smoke, complexity/simplification, anti-slop/product quality, architecture boundaries, test value, UI visual/runtime verification, dead code, security/secret handling, dependency risk, truth/docs accuracy, CI/local proof, release/rollback readiness, data/state integrity, and observability/debuggability.
- The complexity/simplification rubric now treats thermo/simplifier skills as the expert audit engine, not the whole gate: final proof requires concrete hotspots, implementation phases for blockers, runtime/product/architecture/over-abstraction review, lint/typecheck/test/build/runtime verification, and accepted exceptions only with rationale and expiry.
- Quality Runner supersedes the older repo-quality-certifier and quality-evidence-contract path dependencies for AIOS consumption. AIOS now consumes `/Users/jakyeamos/projects/quality-runner` through one `quality-runner` path dependency, while Quality Runner carries the compatibility imports, CLI/MCP tools, and plugin metadata required by existing `quality_evidence_contract` and `repo_quality_certifier` callers.
- `services/repo_gate_adoption.py` remains the AIOS adapter that injects TMCP enrichment while preserving existing workflow and CLI callers. The underlying deterministic scan, gate matrix, rubric, rollout, doc-quality, evidence-normalization, and old certifier/evidence compatibility surfaces are now provided by the Quality Runner installable package.
- `bin/aios.py` now re-enters the project virtualenv before loading service modules, so `python3 bin/aios.py ...` command paths can resolve the newly externalized local path dependencies.
- Context compiler contract validation now lives in the standalone repository `/Users/jakyeamos/context-compiler-contract`, with remote `git@github.com:jakyeamos/context-compiler-contract.git`. AIOS consumes it through a `context-compiler-contract` local file dependency while keeping `tools/context-compile.mjs`, context source selection, ranking, receipt writing, and context-root assumptions inside AIOS.
- The context compiler contract validator now treats malformed routing-manifest source lists as validation issues instead of throwing, based on the standalone extraction test suite.
- `.planning/SUBSYSTEM_EXTRACTION_PLAN.md` now includes a strict ownership map that classifies major AIOS surfaces as `core_aios`, `adapter_inside_aios`, `contract_package`, `standalone_tool`, or `incubator_candidate`. The current truth is that AIOS is better scoped after extracting three packages plus the Research Domain Writing standalone tool, but still intentionally contains incubator candidates such as CTS, agent/eval harness pieces, personalized humanizer, benchmark tooling, and quality/standards consolidation surfaces pending stronger boundary evidence.
- The three extracted repos now have release governance and pushed `v0.1.0` tags: `repo-quality-certifier` at `3ff7eb4`, `quality-evidence-contract` at `36c94bc`, and `context-compiler-contract` at `de60ba1`. AIOS still uses local path/file dependencies for active development; the remaining release-boundary decision is whether to switch to tagged Git dependencies.
- Research Domain Writing now lives in the standalone repository `/Users/jakyeamos/research-domain-writing`, with remote `git@github.com:jakyeamos/research-domain-writing.git` and pushed tag `v0.1.0` at commit `ba0f608`. AIOS no longer owns the RDW prompt/domain/installer source tree; local slash commands and agent skills now point at the external repo, while AIOS retains only the boundary audit and future adapter posture.
- `.planning/PERSONALIZED_HUMANIZER_BOUNDARY_AUDIT.md` classifies personalized humanizer as AIOS-owned runtime/state rather than the next standalone extraction. The subsystem remains inside AIOS because it is tied to workflow orchestration, SQLite run/feedback/profile-update tables, local privacy rules, and personal profile governance. The only future extraction candidate is a small portable voice-profile/voice-packet/scorecard contract after synthetic fixtures and a second consumer justify it.
- `.planning/CTS_BOUNDARY_AUDIT.md` classifies CTS repository intelligence as an AIOS-owned sidecar/incubator candidate rather than the next standalone extraction. CTS has real graph storage, parsing, search, impact, eval, CLI, and MCP surfaces, but `CTSRegistry` still depends on the AIOS `projects` table and `~/AIOS/data/cts`; semantic search is currently FTS/LIKE without embeddings, flow discovery is placeholder-only, and CTS-specific regression tests are not yet present. Future extraction should start with portable CTS contracts, isolated fixture repos, query benchmarks, and a non-AIOS registry adapter.
- `.planning/EVAL_BENCHMARK_BOUNDARY_AUDIT.md` classifies agent eval and benchmark runtime as AIOS-owned while marking schemas/templates/fixtures as a future contract-package candidate. Eval run recording, peer traces, shadow branches, second-brain lift, corpus eval, and TMCP benchmark execution stay inside AIOS because they depend on local SQLite/runtime/operator state. A future `agent-eval-contract` should start with context profiles, score/failure schemas, harness fixture formats, template validators, external benchmark normalization, sample records, and a non-AIOS fixture-producing runner.
- Agent eval contracts now live in the standalone repository `/Users/jakyeamos/agent-eval-contract`, with remote `git@github.com:jakyeamos/agent-eval-contract.git` and pushed tag `v0.1.0` at commit `7489155`. AIOS consumes them through `agent-eval-contract @ file:///Users/jakyeamos/agent-eval-contract` while keeping eval storage, peer traces, shadow worktrees, second-brain lift, operator projections, and workflow integration inside AIOS. The extracted package owns context-profile/status/priority validation, score fields, TypedDict schemas, harness fixture validation, eval template validation, bundled sample record validation, a clean-room contract runner, non-AIOS fixture bundle production, checked-in release metadata, and external benchmark normalization. Remaining release-boundary work is to prove tagged AIOS dependency consumption and establish a second real consumer.

## Implemented On 2026-06-23

AIOS now has a canonical operating-language artifact and skill:

- `OPERATING_LANGUAGE.md` defines AIOS domain language, architecture language, agent-control leading words, relationships, ambiguities, rejected terms, migration notes, and example usage
- `skills/operating-language/SKILL.md` captures the reusable process for extracting and maintaining operating language as a behavioral control surface rather than a passive glossary
- `config/workflows/skills.json` registers `operating_language_curator` as a candidate skill with source metadata for workflow routing and inspection
- the operating-language vocabulary introduces compact leading words such as Context Compile, Truth First, Tracer Bullet, Red Gate, Thin Display, Execution-First, Approval-First, Clean Closeout, Complexity Gate, and Portable Boundary
- local TMCP remains the default way to use skills: `services.tmcp_runtime` starts from the canonical `skills-library/skills.tmcp` graph, while `config/tmcp/portable-dev-process` is a traversable namespace overlay rather than a competing default graph
- `config/tmcp/canonical-graph.json` now defines the tracked canonical build profile for the local graph, including source roots, excludes, output path, graph-drop protection, and the `portable_dev_process` overlay namespace
- `aios skills harvest` now persists graph-profile metadata, source hashes, graph diffs, stale-source signals, and structured `skills.tmcp/graph.json` metadata for tasks, modules, branches, source skills, triggers, source tiers, and generated paths
- `services.tmcp_runtime.compile_tmcp_packet()` now prefers `skills.tmcp/graph.json` traversal, scores task/module/source-skill candidates, emits selected and skipped packet evidence, includes precise source-skill excerpts when useful, and falls back to the older heuristic path with an explicit warning when graph metadata is absent
- promoted TMCP shortcuts now materialize as Markdown under `skills.tmcp/shortcuts/` when receipt fingerprints show repeated validation success and positive token ROI, while stale or uncertain shortcuts fall back to normal graph traversal
- Phase 20 Plan 20-07 now owns the remaining tier-one blocker: non-trivial managed runs must compile, persist, and evaluate a TMCP packet by default unless a structured bypass reason is recorded
- `aios skills graph-verify` now verifies or repairs structured graph metadata for an existing generated skills library; the local ignored `skills-library/skills.tmcp/graph.json` has been refreshed and verifies as 99 source-skill nodes, 99 manifest skills, and 2,848 source hashes
- TMCP runtime freshness now includes `graph.json`, `skills.lock`, and selected source-skill content hashes, so promoted shortcuts are bypassed when source skill material changes
- overlay traversal now records matched trigger terms and behavior added, and skips namespace packs when they do not add behavior beyond canonical graph nodes
- TMCP-internal routing, manifest, packet-selection, and skill-graph prompts now stay on the canonical local graph instead of attaching generic portable-dev-process overlays, while explicit instruction-hygiene requests can still cross into that overlay
- ADR 0003 now defines TMCP as a tier-one candidate, states the remaining managed-run adoption gate, and blocks quality/speed/token superiority claims until paired benchmark evidence shows quality non-inferiority plus positive ROI
- TMCP graph metadata now models behavior atoms, token cost, behavior added, redundancy hints, and omission risk for tasks, modules, branches, and source skills so packet compilation can optimize for behavior instead of file matching
- `compile_tmcp_packet()` now runs a behavior-diff optimizer, prunes redundant low-risk modules when selected source skills already cover the same behavior atoms, records negative selections in `skipped_nodes`, and emits `behavior_atoms`, `packet_optimization`, `node_usefulness`, and `omitted_requirements`
- source-skill loading now uses relevant section excerpts before whole-file payloads, reducing token load while preserving provenance
- `tmcp_traversal_receipts` now has additive `node_usefulness_json` and `omitted_requirements_json` fields for future routing/eval learning
- promoted shortcuts now carry compiled-packet metadata, behavior atoms, token estimates, source hashes, and known-failure-case placeholders
- operating-language requests now select the canonical local `@module:operating_language` TMCP module, which points back to `skills/operating-language/SKILL.md` and `OPERATING_LANGUAGE.md`

AIOS now has a general outer/inner context learning primitive:

- `services.context_loops` records inner-loop runs, approved lessons read before drafting, retrieved context/source refs, generated outputs, unsupported commitments, assumptions, human review events, diffs, learning candidates, approvals, rejections, application to durable lessons, and metrics
- `schema.sql` defines `context_loop_runs`, `context_loop_review_events`, and `context_loop_learning_candidates`
- `python bin/aios.py context-loops ...` exposes `inner-run`, `email-draft`, `record-review`, `review`, `approve`, `reject`, `apply-approved`, and `metrics`
- `aios/context-loops/` documents the audit, schema, retrieval policy, review taxonomy, approved/rejected lesson files, example JSON records, and draft-only email pilot
- `tests/test_context_loops.py` covers draft-only email safety, approved-lesson retrieval, unsupported commitment flags, evidence-backed candidates, no automatic memory promotion, rejected-candidate suppression, metrics, and CLI smoke behavior
- Email support is intentionally mocked/local: AIOS creates draft records only and does not fetch, create mailbox drafts, or send email automatically

AIOS now has an always-loaded dependency and lockfile authority rule:

- `config/agent-rules.md` Rule 13 requires agents to treat committed lockfiles, `packageManager`, CI config, and existing scripts as the package-manager source of truth rather than inferring capability from `node_modules`
- `AGENTS.md` mirrors the rule for repository-local execution, including the npm fallback when only `package-lock.json` exists, the ban on casual lockfile/dependency churn, and the frontend behavior coverage blocker when required tooling is missing

AIOS now has an optional mature-repo behavioral spec verification loop:

- `services.project_maturity` classifies mature-repo eligibility for `behavioral-spec-verification-loop` using route/screen count, API/server-action surface, auth/permission logic, persistent data models, test infrastructure, user-facing feature surface, background/notification jobs, source size, admin/settings/search/import/export/payment flows, and web-app/product-platform signals
- `services.task_routing` now blocks explicit behavioral-spec loop requests for small or unclear repos with a maturity eligibility report and lighter recommendations, while manual override can intentionally enable the workflow
- `config/workflows/registry.json`, `config/workflows/skills.json`, `prompts/registry.json`, `prompts/behavioral_spec_verification.md`, and `docs/workflows/behavioral-spec-verification-loop.md` register the candidate workflow, its prompt, single-writer `.xlsx` artifact contract, required phases, status schema, evidence rules, three-iteration safety cap, and Thermo simplification complexity gate reuse
- `docs/audits/behavioral-spec-verification-loop-aios-audit.md` records the implementation audit of existing AIOS workflows, gates, maturity detection, artifacts, shadow branches, subagents, and Thermo gate reuse
- `tests/test_behavioral_spec_workflow.py` covers mature eligibility, small-repo rejection, explicit opt-in, workflow schema/rules, route blocking, and the guarantee that normal lightweight implementation routing does not default to the heavy loop

AIOS Phase 12 Plan 12-01 now has its graph-native memory architecture audit:

- `docs/audits/graph-native-memory-audit.md` maps current raw storage, ingestion, indexing, search, prompt construction, packet generation, long-term memory update, provenance, conflict/staleness, graph, and prompt-caching surfaces
- the audit identifies memory-loss hotspots and flat retrieval paths across hooks, context compilation, operator search, CTS, vault search, document importers, and UI packet assembly
- ranked recommendations now give Plans 12-02 through 12-08 a concrete implementation contract for layered memory schema, memory compiler, context compiler, packet contract, quality checks, backfill planning, and KV-cache future work

AIOS Phase 12 Plan 12-02 now has the first layered-memory implementation:

- `schema.sql` defines `memory_raw_sources`, `memory_facts`, `memory_relationships`, and `memory_packet_receipts` for raw sources, normalized facts, typed relationships, and model-facing packet provenance
- `services.memory_layers` exposes independent `RawSourceMemory`, `FactMemory`, `RelationshipMemory`, and `PacketReceiptLog` classes with insert/get/query methods and `ALLOWED_PREDICATES` validation
- `bin/aios_orchestration_runtime.ensure_runtime_schema` installs the memory layer schema on runtime touch, and `tests/test_memory_layers.py` verifies idempotent schema setup plus all four layer modules

AIOS Phase 12 Plan 12-05 now has the memory packet contract:

- `docs/specs/memory-packet-contract.md` defines required and optional model-facing packet sections, section ordering, internal schema shape, Markdown rendering, provenance rules, stale/superseded and contradiction handling, confidence labels, token-budget priority, and good/bad examples
- the contract makes raw JSON in model-facing packet output a hard violation; compiler internals may use structured JSON/rows/edges, but rendered packets must be readable Markdown for LLM reasoning
- `services.memory_layers.FactMemory` and `schema.sql` now enforce the contract validity statuses: `active`, `superseded`, `contradicted`, `uncertain`, and `archived`

AIOS Phase 12 Plan 12-07 now has a memory backfill plan:

- `docs/backfills/graph-native-memory-backfill.md` inventories P0/P1/P2 memory hotspots across project truth, tracker truth, PRD-style docs, agent rules, user preferences, long-term memory, decisions, code quality rules, prompt libraries, skills, design specs, and wiki/context pages
- each hotspot maps current memory value, missing structure, recommended Layer B facts, recommended Layer C relationships, stable/dynamic prefix classification, project/global scope, and priority
- the first recommended backfill run targets the Plan 12-01 audit’s P0 memory-loss areas: project truth, state, audit recommendations, prompt-time retrieval, closeout memory, and agent rules

AIOS Phase 12 Plan 12-08 now has the KV-cache-aware local runner future note:

- `docs/future/kv-cache-aware-local-runner.md` states that KV-cache-level memory is an optional optimization layer, not the source of truth
- the note documents why closed API models should be optimized through stable prompt prefixes rather than direct client-controlled KV-cache injection
- it defines local-runner prerequisites and explains how the future stable-prefix ContextCompiler can bridge API prompt caching today with vLLM/LMCache-style cache reuse later

AIOS Phase 12 Plan 12-03 now has the Layer D memory compiler:

- `services.memory_compiler.MemoryCompiler` accepts prefetched raw source, fact, and relationship rows and compiles retrieved ids into model-facing Markdown briefing packets without hidden disk, network, or database reads
- compiled packets preserve the required section order while omitting empty sections, keep Current Truth limited to active facts, label superseded/contradicted/uncertain facts outside current truth, and cap causal/dependency traversal at three hops
- Sources / Provenance is always included, `current_truth_only` mode omits history sections, and token-budget enforcement drops lower-priority sections before higher-priority context

AIOS Phase 12 Plan 12-04 now has the cache-aware context compiler:

- `services.context_compiler.ContextCompiler` returns ordered provider-agnostic `role`/`content` prompt sections with stable project context before dynamic task context
- stable prefix sections cover system/developer instructions, AIOS operating rules, user preferences, project memory summary, and project truth packet, and remain deterministic across task changes for the same project context
- dynamic suffix sections compose task-specific memory through `MemoryCompiler`, deduplicate facts already present in project truth, filter stale facts by default, and compress lower-priority dynamic content before stable project truth and memory summary

AIOS Phase 12 Plan 12-06 now has retrieval quality checks:

- `tests/memory/test_packet_quality.py` enforces the nine memory packet quality constraints from the contract using integration-level compiler fixtures
- `tests/context/test_context_quality.py` verifies deterministic stable prefixes, dynamic-after-stable ordering, and deduplication in `ContextCompiler`
- `scripts/validate-memory-packets.py` is an executable standalone validator for generated packet Markdown files, checking section order, provenance, raw JSON leakage, validity markers, and token limits

AIOS Phase 12 is complete across Graph-Native Memory Architecture And Cache-Aware Context Compilation:

- `.planning/phases/12-graph-native-memory-architecture/12-VERIFICATION.md` verifies MEM-01 through MEM-08 with all eight plan summaries present
- the phase now has a layered SQLite memory foundation, model-facing Markdown compiler, stable-prefix context compiler, packet contract, quality gates, backfill plan, and KV-cache future note
- the planning state has advanced to Phase 13 Plan 13-01 for multi-provider session ingestion and second-brain data pipeline work

AIOS deployment workflow policy no longer narrows branch pushes to only explicitly requested push tasks:

- `AGENTS.md` still requires the normal quality ladder, commits before deployment, and watched Vercel deployment success for Vercel-affecting shipped work
- the prior Vercel gate line that said to push only when asked or when the task explicitly includes pushing has been removed so push behavior follows the broader repository Git workflow policy

AIOS planning now reflects the expanded quality-gate success criteria as landed baseline infrastructure:

- Phase 14 plans now reference the registered success-criteria gate ids as the canonical vocabulary for complexity, architecture, simplicity, testing, UI, data, API, supply-chain, and agent-claim verification work
- Phase 14 remaining scope is narrowed to agent-rule/docs/checklist/backfill surfaces instead of inventing a parallel gate taxonomy
- Phase 22 now treats the expanded criteria as AIOS-local/runtime gates by default and scopes remaining work to portability classification, promotion policy, backfill evidence, and hook integration

AIOS success criteria now include diff-scoped quality gates for pre-PR review and adoption/backfill quality ratchets:

- new gate specs cover `complexity-budget`, `supply-chain-review`, `architecture-boundary`, `thin-display`, `test-quality`, `data-integrity`, `api-contract`, `performance-budget`, `accessibility`, `resilience`, `product-alignment`, `simplicity`, and `agent-claim-verification`
- `security-review` now explicitly separates application security concerns from supply-chain review while covering auth, authz, validation, injection, unsafe file handling, SSRF, XSS, CSRF, permission boundaries, and data leakage
- success-criteria resolution now infers UI, accessibility, performance, dependency, data, migration, API contract, complexity, resilience, and product domains from objective text and changed files
- hard-blocker heuristics now cover package-manager drift, missing critical test/execution evidence, data/API changes without integrity evidence, complexity-risk changes without benchmark/fixture evidence, and session-close code claims without validation evidence
- the success-criteria index documents Pre-PR gate mode, Adoption/backfill mode, and diff-scoped routing so UI, DB, auth, algorithm, dependency, and large agent-generated changes get the right gates without turning every task into a universal checklist

AIOS now owns a global allowlisted project quality-gate runner:

- `config/quality-gates.json` registers known gate IDs and vetted argv arrays per project, with Soundscape mapped to `test_quality`, `architecture`, and `pre_cr`
- repo-local `.aios-quality-gate.json` files declare only gate IDs; they cannot provide shell commands
- `bin/user-commit-quality-gate.py` blocks registered source commits when the local gate contract is missing, malformed, unknown, or failing, after the existing Pre-CR requirement
- `python3 bin/aios.py --json gate run <gate_id> --project <project_id> --repo-root <path>` runs a single allowlisted adapter for pre-commit or full mode
- `services.commit_quality_ladder` now verifies that AIOS itself has the allowlisted quality-gate registry and local contract, making this an AIOS quality-ladder gate
- Soundscape `test_quality` now runs `pnpm test:quality:audit` before inventory and script-policy checks, so known weak-test patterns fail the gate instead of being hidden behind a narrower command
- the AIOS `test_quality` runner now carries the global non-regression policy: fixes must preserve or improve behavior coverage, and deletion is valid only for obsolete tests, duplicate stronger coverage, or pure noise

AIOS now registers the Thermo-Nuclear Simplification gate as a first-class structural quality ratchet:

- `thermo_nuclear_simplification` is allowlisted in `config/quality-gates.json`, declared in `.aios-quality-gate.json`, and required in the AIOS quality pipeline
- `thermo-nuclear-simplification` is a blocking success criterion for planning, implementation, bugfix, refactor, and review work
- `docs/quality-gates/thermo-nuclear-simplification.md` defines the strict Pre-PR/adoption/shadow-eval review contract, including severity, scorecard, output template, waiver rules, file-sprawl checks, thin-wrapper rejection, type-boundary protection, and canonical-layer reuse
- `docs/pre-pr/quality-ladder.md` places Thermo after correctness checks and before merge recommendation, while `docs/adoption/backfill-quality-ratchet.md` defines the adoption-mode ratchet for legacy debt
- `services.commit_quality_ladder` now verifies that AIOS keeps the Thermo gate registered, configured, and declared locally

AIOS default workflow routing now uses explicit relevance evidence instead of active-workflow fallback:

- `services.workflow_orchestration.rank_workflow_candidates` scores matched trigger phrases and family evidence rather than token overlap or lifecycle state alone
- code-like bugfix, UI, API, DB, CI, test, and verification phrasing routes through implementation evidence and falls back to `implementation-delivery` when no more specific route wins
- content-generation workflows require content evidence and are suppressed for code-like objectives, preventing bugfix requests from falling through to `academic_paper_v1`
- expert audit-plan/rubric-remediation objectives now have explicit routing evidence, and diagnostic mentions of workflow keys such as `academic_paper_v1` no longer count as paper-writing intent
- weak or tied workflow evidence returns no selected workflow so `start-work` blocks for clarification instead of silently choosing the first active workflow
- route story tests cover AIOS bugfix phrasing, non-AIOS login bugfix phrasing, UI user-story verification, academic-paper routing, and ambiguity blocking

AIOS now has a repeatable copied-live-DB readiness gate for default routing:

- `scripts/aios-readiness-check.py` copies `data/aios.db`, runs route selector stories through `start-work`, verifies route-decision search, checks daily-flow preview/replay, and confirms next-action returns structured output
- `services.next_action` supports both older fixture-style `success_criteria_findings.run_id` rows and the canonical schema where findings link to runs through `success_criteria_evaluations`
- `.planning/quick/260623-aios-readiness-check/readiness-report.json` and `.planning/quick/260623-aios-readiness-check/readiness-report.md` record the passing copied-live-DB gate
- `scripts/aios-adoption-gate.py` now runs the managed-runtime adoption gate on a copied live DB across AIOS internal bugfix, non-AIOS bugfix, and AIOS operator UI verification stories
- `.planning/quick/260623-aios-adoption-gate/adoption-gate-report.json` and `.planning/quick/260623-aios-adoption-gate/adoption-gate-report.md` record the passing gate, including completed lifecycle linkage, workflow/evaluation/writeback/TMCP artifacts, route-decision search, and daily-flow replay evidence
- this proves copied-live-DB managed-run adoption readiness for routing representative serious work through AIOS by default; broad default-launcher use should still keep the adoption gate in the release checklist after routing/runtime changes

AIOS now has a repeatable field-pressure gate for default-use confidence:

- `scripts/aios-field-pressure-gate.py` copies `data/aios.db`, routes 12 mixed daily-use objectives, executes 6 managed-runtime pilots, verifies closeout artifact volume, runs operator UI lint/typecheck, probes operator-search/daily-flow/next-action drilldowns, simulates context-loop and session-save learning, and exercises ambiguous-objective, invalid-project, missing-run, stale-schema, and missing-managed-run recovery
- `.planning/quick/260623-aios-field-pressure-gate/field-pressure-report.json` and `.planning/quick/260623-aios-field-pressure-gate/field-pressure-report.md` record the passing 100/100 gate
- `services.operator_search` now matches run-linked writebacks by `run_id` and canonical success-criteria findings through `success_criteria_evaluations.run_id`, so operator run-id searches expose the evidence needed to inspect closeout state
- `.gitignore` treats `logs/control-plane/` and `logs/session-effectiveness/` as runtime artifact directories, reducing dirty-tree noise from managed-run simulations and probes
- `bin/aios-managed-run.py` now returns structured preflight JSON for missing runs instead of surfacing a Python traceback
- the field-pressure report includes dirty-tree classification, separating source changes from ignored runtime artifacts so managed-run probes do not obscure implementation work

AIOS now has a Codex command-trigger route helper:

- prompts that start with `/aios` instruct Codex to route the task through AIOS before non-trivial work
- `/aios` creates a shadow lane by default and marks the AIOS route as governing context for the baseline task
- `/aios-route-only` is the explicit opt-out for rare cases where a routed record is wanted without a shadow
- `scripts/codex-aios-route.py` infers the active project from the current working directory or accepts `--project`, runs `aios start-work`, and prints the follow-up operator-search, daily-flow, and next-action commands
- `AGENTS.md` documents the command behavior so the user can start AIOS routing with a concise command instead of manually composing shell commands
- `README.md` documents examples such as `/aios Fix the route selector bug and verify the checks`

AIOS now has a Codex shadow command helper:

- all non-trivial Codex tasks run `scripts/codex-aios-shadow.py` automatically, even without `/aios`, so AIOS can collect comparison evidence while normal Codex work remains the baseline
- `/aios` runs the same helper with `--governed-route`, making the AIOS route and packet authoritative for the baseline task
- `scripts/codex-aios-shadow.py` infers the active project, records the AIOS route, creates a shadow worktree through `aios shadow create-worktree`, and prints the prompt to run in a separate Codex thread
- automatic non-`/aios` shadow routes are evidence only and do not govern baseline implementation
- `.gitignore` ignores `.aios/shadow-worktrees/` so local comparison worktrees do not pollute source status
- `AGENTS.md` states that shadow output must not be merged, copied, or promoted into the baseline workspace without explicit user review

## Implemented On 2026-06-22

AIOS now has a versioned pre-commit quality ladder for standards enforcement:

- `.githooks/pre-commit` invokes `bin/aios-quality-ladder.py`
- `services.commit_quality_ladder` checks global standards inventory, standards-health registry coverage, context compiler validation, success-criteria registry coverage, AIOS quality-pipeline gate coverage, and staged confident-code event-loop ordering
- staged JavaScript/TypeScript code that registers message response handlers before `postMessage()` is blocked unless it documents a real runtime reason with an explicit `aios-quality` waiver comment
- focused tests in `tests/test_commit_quality_ladder.py` cover the standards inventory, standards-health registry, success-criteria registry, event-loop blocker, and waiver behavior

AIOS also installs a portable user-level commit quality gate for repositories that are not yet running through AIOS:

- global Git `core.hooksPath` points to `/Users/jakyeamos/AIOS/.githooks-user`
- `.githooks-user/pre-commit` invokes `bin/user-commit-quality-gate.py` without requiring AIOS context, SQLite, or repo-local setup
- the portable gate blocks staged merge conflict markers, likely secret literals, npm/yarn package-manager drift, production TypeScript `any`, oversized source files, weak Python tests, and JavaScript/TypeScript handler-before-`postMessage()` ordering without a documented runtime-reason waiver
- source commits require `.pre-cr.json` and a `pre-cr` CLI on PATH, then run `pre-cr run --json --workspace <repo>` so the global hook bridges into Pre-CR changed-line readiness
- AIOS itself keeps local `core.hooksPath=.githooks`, so the stricter AIOS-specific standards ladder still runs for this repository

AIOS roadmap planning now makes standards-to-ladder promotion explicit:

- Phase 14 owns the portable AIOS standards ladder contract and warn-only/reporting entry point for checks that are deterministic without AIOS runtime state
- Phase 16 owns the evidence and independent-verifier prerequisites required before standards checks can block in AIOS-managed repositories
- Phase 22 owns progressive promotion into the global user-level commit quality ladder, including backfill, false-positive review, waiver policy, and fail-closed eligibility

AIOS session-start packets now inject a user-story verification loop for broad app, UI, UX, and feature verification work:

- `bin/hook-session-start.py` detects user-facing verification objectives and adds a compact loop contract to the hook packet
- the loop requires one canonical `.planning/user-story-verification.csv` spreadsheet with feature source refs, user story, expected behavior, test evidence, errors, fix refs, and retest status
- the packet instructs agents to enumerate implemented features from code, test each user story through the real UI/code path before fixing, then retest affected stories after fixes while leaving missing-evidence rows blocked or failing
- `tests/test_agent_rules_runtime.py` covers both injection for app verification objectives and non-injection for narrow backend work

AIOS now has a portable TMCP developer-process skill graph:

- `config/tmcp/portable-dev-process/manifest.json` defines a repo-vendored skill graph for practical AIOS-derived development helpers without requiring AIOS runtime state, SQLite, truth-file updates, eval archives, or continuous-learning loops
- the pack includes router, task, module, branch, and routing-case nodes for repo detection, command discovery, quality checks, debugging, diff review, test authoring, CI triage, frontend verification, git hygiene, dependency audits, docs updates, and hook guidance
- `planning_review` now routes read-only strategy comparison and promotion-path planning through command discovery, test-authoring, and quality-gate guidance so objectives like `Compare workflow promotion strategies` avoid the generic agent-workflow ambiguity path
- the default branch is read-only, while explicit mutation, network-required, and destructive-action branches preserve safe behavior when the pack is used in other projects
- `tests/test_portable_dev_process_tmcp.py` verifies graph integrity, core capability coverage, routing-case consistency, and the no-AIOS-governance portability contract

AIOS also now vendors the `make-interfaces-feel-better` UI polish skill under `skills/`, registers it as the `make_interfaces_feel_better` candidate workflow skill, and exposes it as an optional TMCP module for detail-level UI polish inside the portable dev-process `visual_polish` route.

AIOS agent completion rules now include an explicit Vercel deployment verification gate for Vercel-affecting shipping work:

- `scripts/vercel-deploy-watch.sh` runs `vercel deploy` for preview or production, captures the deployment URL, and blocks on `vercel inspect --logs --wait`
- root package scripts expose `pnpm deploy:preview:watch` and `pnpm deploy:prod:watch`
- `AGENTS.md` instructs agents not to mark Vercel-affecting shipped work complete until the watched deployment succeeds, while keeping tokens environment-only through `VERCEL_TOKEN`

AIOS success criteria now enforce git worktree cleanliness at session close:

- `git-worktree-cleanliness` is a blocking global success criterion backed by `spec/success-criteria/git-worktree-cleanliness.md`
- `bin/hook-stop.py` captures `git status --porcelain` for the active repository and passes it into success-criteria evaluation
- dirty tracked or untracked files at closeout produce a blocker-level finding so completed work left uncommitted is visible in durable evaluation artifacts

## Implemented On 2026-06-21

AIOS now has a file-backed TMCP paired-run benchmark pipeline:

- `bin/tmcp-benchmark.py` supports `discover`, `preflight`, `task import`, `conditions`, `freeze`, `run`, and `aggregate` commands over the `tmcp-benchmark/` scaffold
- `services.tmcp_benchmark` now records task families, held-out task manifests, seeded anonymous condition maps, frozen hash manifests, shortcut leakage checks, isolated git-worktree dry runs, timing/token/route/patch/evaluation artifacts, package-manager-aware command discovery, and conservative aggregate comparisons
- aggregation reports baseline, flat-skills, cold-TMCP, and validated-shortcut comparisons separately, including the required cold-vs-shortcut comparison, and refuses speed/token improvement claims unless completion and quality are non-inferior and the measured delta is positive
- the current dry-run calibration artifact set contains 8 stub runs across `Bballedu` and `Terrace`; those records validate the harness shape only and are not promotional evidence for TMCP performance
- the first real portable dev-process paired benchmark ran on `BidCamp` with `baseline` (`realpair-bidcamp-baseline-260623`) and `tmcp_cold_start` (`realpair-bidcamp-tmcp-cold-260623`); both failed the public quality command because the isolated worktree lacked runnable dependencies, and the failure is recorded in `tmcp-benchmark/reports/failure-casebook.md`
- benchmark preflight now accepts clean repositories with at least one discovered quality command (`test`, `lint`, or `typecheck`) instead of requiring a test command specifically; Node script discovery now follows the repo's declared package manager or lockfile instead of assuming `pnpm`

## Implemented On 2026-06-21

AIOS Phase 11 is complete across Testing, Benchmark Evaluation, And Shadow Workflows:

- eval-run infrastructure now records tasks, runs, scores, failures, gold-set tasks, context profiles, final status, priority, and JSON-list fields through `services.eval_run_service` and `aios eval`
- second-brain lift, retrieval metrics, gold-set recall, feature ablations, shadow branch comparisons, passive peer traces, candidate scoring, and approval-gated shadow automation now have durable services, schema support, and CLI surfaces
- `services.portable_context_packet_generator` creates privacy-filtered portable context packets in `config/context-packets/`, while `services.external_benchmark_adapter` maps eval tasks to SWE-bench and Terminal-Bench formats and normalizes external results as `external_clean_room`
- the operator UI now reads eval tables through `aios-ui/server/aios/eval-data.ts`, exposes them through tRPC, and embeds collapsible eval summary and shadow candidate queue panels on the Command Center, project detail, and run detail surfaces
- `.planning/phases/11-testing-benchmark-evaluation-and-shadow-workflows/11-VERIFICATION.md` records EVAL-01 through EVAL-08 as passed with targeted Python tests, Python lint/type checks, UI lint/typecheck, architecture lint, context validation, and live route smoke evidence

## Implemented On 2026-06-18

AIOS now has a non-mutating TMCP multi-project benchmark scaffold:

- `services.tmcp_benchmark` discovers eligible non-hidden Git repositories read-only and records project id, branch, current commit, AIOS shadow branch, lockfiles, CI config, build/test/typecheck/lint commands, skills, TMCP graph, and shortcut registry signals
- `bin/tmcp-benchmark.py init` creates the `tmcp-benchmark/` directory contract with manifests, task/run/evaluation/analysis/report folders, frozen condition names, shortcut states, run-record template defaults, and claims-discipline report stubs
- the generated scaffold under `tmcp-benchmark/` currently inventories 35 non-hidden local Git repositories from `/Users/jakyeamos` without fetching, syncing, force-pushing, executing agents, or making benchmark claims
- `tests/test_tmcp_benchmark.py` covers read-only discovery, shadow-branch detection, tooling inventory, hidden-directory exclusion, manifest generation, shortcut-state recording, and null token defaults for unavailable metrics

## Implemented On 2026-06-13

AIOS now has a safe optional NotebookLM MCP route for bounded second-brain synthesis:

- `services.notebooklm_synthesis` classifies when NotebookLM should be used, rejected, or sequenced after local retrieval, including source-of-truth memory, operational memory, code search, bounded source synthesis, connection discovery, learning detection, drift detection, and whole-vault rejection cases
- source-bundle metadata now records included and excluded sources while excluding sensitive classes, raw operational paths, and over-limit sources before any NotebookLM handoff
- the default `NotebookLMMCPAdapter` is optional, reads the experimental `jacob_bd_notebooklm_mcp_cli` backend contract from `config/notebooklm/backends.json`, checks for `nlm` and `notebooklm-mcp`, and fails safely with `skipped_unavailable` provenance instead of making AIOS boot depend on an external MCP server
- `NotebookLMCLIAdapter` now provides a guarded automated agent path through `nlm login --check`, `nlm notebook create`, `nlm source add --wait`, and `nlm notebook query`, while failing closed for missing auth, empty bundles, excluded sources, unsafe sources, or command failures
- `docs/contracts/notebooklm-mcp-cli-contract.md`, `aios/policies/notebooklm-routing.md`, `docs/architecture/notebooklm-mcp-addon.md`, and `aios/context/packets/knowledge.notebooklm-routing.md` document that the `jacob-bd/notebooklm-mcp-cli` backend is experimental, uses internal APIs/cookie auth, and must remain bounded and review-gated
- regression coverage in `tests/test_notebooklm_synthesis.py` validates the nine requested routing scenarios plus bundle filtering, backend registry loading, mode-to-tool planning, CLI command sequencing, auth failure behavior, unavailable-adapter behavior, and staging template structure

## Implemented On 2026-06-13

AIOS managed runtime now uses persisted TMCP traversal receipts for shortcut promotion:

- `services.tmcp_runtime.compile_tmcp_packet` can evaluate prior receipts for the same traversal fingerprint, source graph version, task, validation success rate, positive token ROI, and blocker-free evidence before marking a shortcut active
- promoted shortcuts become the packet entry node and prepend the selected node path so workflow reports show that the managed path entered through `@shortcut:*` while preserving the underlying task/module/branch traversal
- `bin/aios-managed-run.py` compiles TMCP packets with the runtime SQLite connection and updates each traversal receipt with workflow execution outcome and validation evidence after workflow execution
- runtime-shaped verification now covers a managed subprocess run seeded with repeated successful receipts and confirms the generated workflow report routes through the promoted shortcut

## Architecture Governance On 2026-06-05

AIOS now tracks subsystem extraction decisions in `.planning/SUBSYSTEM_EXTRACTION_PLAN.md`. The current architecture posture is to keep AIOS as a monorepo incubator and extract only after a subsystem has a stable public contract, focused tests, clear data ownership, independent reuse pressure, and lower coordination cost outside this repo.

`AGENTS.md` requires future work to update that plan whenever subsystem maturity, ownership, contracts, storage boundaries, dependency direction, or extraction posture changes.

## Implemented On 2026-06-05

AIOS now has a reusable local skills harvest workflow:

- `aios skills harvest` scans explicit project and agent roots for AGENTS/CLAUDE/GEMINI/Cursor/Codex/Claude skills, commands, workflows, prompts, and agent-facing configuration without modifying source files
- `services.skills_harvest` classifies candidates, redacts secret-like values, records provenance, detects edit-permission conflicts, and consolidates overlapping reusable skill candidates into canonical skill groups
- source tiers distinguish `project_authoritative`, `personal_agent`, `local_agent_config`, `plugin_reference`, `history_reference`, and `reference` material so project and personal behavior shape active TMCP while plugin/history material stays preserved but advisory
- the generated local repository lives at `skills-library/`, is ignored by the parent AIOS repo, and contains `skills/`, `instructions/`, `workflows/`, `skills.tmcp/`, `audit/`, `manifest.json`, and `skills.lock`
- TMCP now treats repeated successful traversal paths as shortcut candidates: receipt fingerprints with repeated validation success and positive token ROI can become top-level graph nodes that later branches build from
- the first broad local harvest scanned projects plus local Gemini/Cursor/Claude/Codex/Agents roots, found 2,834 candidate files, consolidated 1,694 reusable skill candidates into 99 canonical skills, and used 1,539 project/personal/global-config sources as active TMCP authority
- the generated repository is committed locally; GitHub push remains an operator step when network approval is available

## Implemented On 2026-06-13

AIOS Phase 11 Plan 11-01 now has durable eval-run infrastructure:

- `schema.sql` defines eval task, run, score, failure, and gold-set task tables for benchmark and shadow-workflow evidence
- `services.eval_run_service` records eval tasks/runs, scores, failures, run detail, run lists, and aggregate summaries with context-profile, final-status, priority, and JSON-list validation
- `aios eval record-run`, `aios eval list-runs`, and `aios eval summary` expose the eval-run store through the existing CLI path
- `tests/test_eval_run_service.py` and eval CLI coverage verify the service contract against real SQLite behavior, including missing-later-table tolerance for future Phase 11 plans

AIOS Phase 11 Plan 11-02 now has the second-brain eval track:

- `schema.sql` defines second-brain retrieval and gold-set context mapping tables for precision, recall, and staleness measurement
- `services.second_brain_eval` records retrievals, computes retrieval metrics, registers gold-set context requirements, evaluates missed required sources, and computes Second Brain Lift between full and repo-only runs
- `config/agent-eval/ablation-policies/` includes no-second-brain, no-personal-corpus, no-project-truth, and no-prior-task-history policy files
- `aios eval second-brain-lift`, `aios eval retrieval-metrics`, and `aios eval gold-set-run` expose the track through the JSON-first CLI
- focused service and CLI tests verify retrieval math, gold-set recall, missing-run handling, policy JSON shape, and CLI output

AIOS Phase 11 Plan 11-03 now has shadow branch testing infrastructure:

- `schema.sql` defines `shadow_branch_runs` for paired eval branch/worktree metadata, comparison deltas, and contamination status
- `services.shadow_branch_runner` creates isolated worktrees, rejects active-tree path reuse, checks branch contamination, parses diff stats, computes test deltas, computes Shadow Branch Delta from eval scores, and cleans up worktrees
- `aios shadow create-worktree`, `aios shadow compare`, and `aios shadow cleanup` expose the shadow branch path through the JSON-first CLI
- focused mocked git tests verify safety rules, diff/test parsing, delta math, branch naming, cleanup, and CLI output

AIOS Phase 11 Plan 11-05 now has peer passive trace infrastructure:

- `schema.sql` defines peer session, peer trace, and shadow candidate tables
- `config/peer-eval/peer-trace-policy.json` defaults peer trace mode to observation-only with prompt mutation, context injection, subagents, repo writes, automated shadow launch, prompt text storage, and file content storage disabled
- `services.peer_trace` starts/stops peer sessions, records redacted trace metadata, lists sessions, and returns session details
- `services.shadow_candidate_scorer` scores observed tasks with weighted criteria, hard blocker caps, recommendation tiers, reasons, and blockers
- `aios peer-trace start|stop|list`, `aios shadow score`, and `aios shadow queue` expose the passive trace and candidate queue surfaces

AIOS Phase 11 Plan 11-04 now has the feature ablation runner:

- `config/agent-eval/ablation-policies/` includes no-context-packets, no-success-criteria, no-subagents, and no-model-routing, completing the eight-policy ablation suite with the Plan 11-02 policies
- `services.ablation_runner` loads policies, creates shadow worktrees, invokes context compilation with disabled features, falls back to a worktree-local ablation override file, records EvalRuns, and compares ablation scores against a base run
- `aios ablation run` and `aios ablation compare` expose ablation execution and score comparison through the JSON-first CLI

AIOS Phase 11 Plan 11-06 now has the peer automated shadow benchmark pipeline:

- `services.shadow_automation` approves candidates, advances persisted automation states, captures start SHA, blocks contaminated runs, creates shadow worktrees, writes comparison reports, appends backlog follow-ups, and records verification scoring/failure hooks
- `aios shadow approve`, `aios shadow run-pipeline`, and `aios shadow status` expose candidate approval, pipeline execution, and state inspection through the JSON-first CLI
- mocked state-machine tests verify approval, transition persistence, contamination blocking, report creation, and backlog append behavior

## Implemented On 2026-06-01

AIOS Phase 9 continuous learning now routes divergent strategy and workflow experiment winners through governed promotion proposals:

- `services.workflow_promotion.propose_asset_promotion` emits approval-required improvement writebacks plus proposed lifecycle rows for prompt and skill promotion candidates
- divergent strategy winners now target `candidate` through the Phase 8 proposal surface instead of silently writing lifecycle promotion state
- workflow-skill experiment winners keep existing scoring and `promotion_ready` outcomes while additionally emitting reviewable skill-promotion proposals
- defensive fallback paths preserve legacy behavior with explicit stderr warnings when the Phase 8 proposal surface is unavailable
- regression coverage locks live proposal rows, fallback warnings, runtime persistence, and prompt/skill asset-kind routing
- Phase 9 is verified complete in `.planning/phases/09-continuous-learning-and-conservative-optimization/09-VERIFICATION.md` with LEARN-01 through LEARN-04 satisfied and 185 targeted tests passing

## Implemented On 2026-06-01

AIOS Phase 10 now has the first operator-surface backend for cross-entity search:

- `services.operator_search.search_entities` returns safe `OperatorSearchHit` projections across 17 entity kinds without new SQLite tables or FTS indexes
- every search hit carries a non-null `drill_down_path` for later UI and tRPC operator surfaces
- `aios operator-search` exposes the backend from the CLI with kind, project, and limit filters
- `contracts-audit` now includes an `OperatorSurface` row marked partial until the UI mirror, tRPC router, and rendered search page ship

## Implemented On 2026-06-01

AIOS Phase 10 now has a read-time next-action fusion backend:

- `services.next_action.get_next_actions` ranks actions from standards deltas, pending writebacks, open blockers, terminal-run learning gaps, backfill tasks, promotion candidates, and learning proposals
- `NextAction` rows carry priority buckets, confidence, evidence ids, optional workflow launch keys, and non-null drill-down paths
- `aios next-action` exposes the fused action list from the CLI with project and limit filters
- `contracts-audit` now includes a `NextAction` row marked partial until the UI mirror, tRPC router, and rendered panels ship

## Implemented On 2026-06-01

AIOS Phase 10 now has a Python daily-flow trace backend:

- `services.daily_flow.preview_from_objective` returns the canonical eight-step `DailyFlowTrace` from objective input without persisting orchestration run or briefing packet rows
- `services.daily_flow.replay_from_run` reconstructs the same goal, route, packet, run, evaluation, writeback, unresolved delta, and next-action sequence from existing SQLite rows
- every `DailyFlowStep` carries provenance, evidence references, freshness, metadata, and a non-null drill-down path, with missing upstream phase tables rendered as explicit `missing` steps
- `services.agentize.agentize_request(dry_run=True)` wraps packet generation in a SQLite SAVEPOINT followed by rollback so preview remains inspection-only
- `aios daily-flow` exposes mutually exclusive preview (`--objective`) and replay (`--run-id`) modes from the CLI
- `contracts-audit` now includes a `DailyFlow` row marked partial until the TypeScript mirror, tRPC router, and rendered trace components ship

## Implemented On 2026-06-01

AIOS Phase 10 now has a TypeScript operator projection layer for the UI:

- `aios-ui/lib/drill-down.ts` centralizes 18 URL builders for operator-visible entities and encodes every interpolated id/key
- `aios-ui/lib/control-plane.ts` exports shared operator-surface types for search hits, next actions, daily-flow traces, phase status, and priority buckets
- `aios-ui/server/aios/operator-search.ts` mirrors the Python operator-search backend with 17 read-only dispatchers, safe-column projection, scoring constants, and drill-down paths
- `aios-ui/server/aios/next-action.ts` mirrors the Python next-action backend with six source fetchers, bucket ranking, and drill-down paths
- `aios-ui/server/aios/standards-health.ts` and `aios-ui/server/aios/learning.ts` now attach drill-down paths to operator-visible delta, backfill, workflow recommendation, learning rollup, recurring pattern, and conservative proposal rows
- UI quality gates pass with `pnpm lint`, `pnpm exec tsc --noEmit`, and `pnpm lint:architecture`; lint still reports the existing anti-slop warning baseline only

## Implemented On 2026-06-01

AIOS Phase 10 operator projections are now callable through the UI tRPC layer:

- `operatorSearch`, `nextAction`, `dailyFlow`, and `writebacks` routers expose search, next-action, daily-flow preview/replay, and governed writeback inspection procedures
- `aios-ui/server/aios/daily-flow.ts` mirrors the Python daily-flow shape with the canonical eight steps and read-only preview behavior
- automation and project remediation trigger mutations reuse the existing control-plane path by calling `planTask` before `invokeControlPlaneRun`
- grounded query answers now classify `should_i_run_workflow` questions and return optional workflow recommendation, packet-preview, and launchable-run fields without auto-launching
- `getControlPlaneOverview` now includes next actions, a daily-flow summary, learning impact rollups, and phase status reports when backing tables are present
- governance overview rows include policy-class drill-down paths for approval review surfaces
- catalog rows now distinguish registered workflow data from seeded fallback UI catalog entries with `isSeedData`
- UI verification passes with `pnpm lint`, `pnpm exec tsc --noEmit`, and `pnpm lint:architecture`; lint still reports the existing anti-slop warning baseline only

## Implemented On 2026-06-01

AIOS Phase 10 operator projections are now rendered in the local UI:

- `/search` is in primary navigation and renders faceted mixed-entity operator search from `operatorSearch.search`
- the top bar now includes debounced global search suggestions with drill-down links and full-results navigation
- the Command Center renders phase-status and seed-data banners, top next actions, daily-flow trace summary, and learning-impact rollup
- project detail pages render project-scoped next actions, while run detail pages render daily-flow replay traces
- `/writebacks` now consumes the governed `writebacks.list` router with status, policy-class, source, and project filters
- automations and grounded-query answers expose workflow launch controls through the existing governed trigger mutations without auto-launching
- Browser verification passed for `/`, `/search?query=implementation`, `/writebacks`, `/automations`, `/projects/be2139e874c1a02e`, and `/runs/managed-invoke-manual-5a3df472-1a00-46ce-a2ba-02c271fde2b8`
- UI verification passes with `pnpm exec tsc --noEmit`, `pnpm lint`, and `pnpm lint:architecture`; lint still reports the existing anti-slop warning baseline only

## Implemented On 2026-06-01

AIOS Phase 10 now has an Agent Eval Foundation for major-task review:

- `docs/evals/benchmark-eval-architecture.md` defines the four-layer eval stack, eight rollout phases, AIOS Effectiveness Score formula, context comparison formulas, 14 conditions, 25 failure labels, completion gates, and anti-cheating rules
- `docs/evals/context-profiles.md` defines the six context profiles and the rule that second-brain wins prove local lift rather than portable benchmark superiority
- `docs/evals/templates/` contains major-task, backfill-hotspot, shadow-branch, failure-record, and portable-context-packet templates for agent-fillable eval records
- `config/agent-eval/eval-schemas.py` defines `EvalTask`, `EvalRun`, `ShadowCandidate`, `EvalScore`, and `EvalFailure` TypedDict contracts for later automation
- `AGENTS.md` now includes an Agent Eval Workflow rule after Execution-First Verification with trigger scope, a 10-step checklist, anti-cheating rules, and personalized/local portability labeling
- verification passes with `python3 -m py_compile config/agent-eval/eval-schemas.py`, `uv run ruff check config/agent-eval/eval-schemas.py`, and `git diff --check`

## Implemented On 2026-06-05

AIOS managed prompt capture now flows through the same hook path as interactive prompt submission:

- `bin/aios-managed-run.py` emits `hook-prompt-submit.py` for the governed run objective after managed session start, preserving explicit session/run/invocation/backend linkage
- managed session-effectiveness receipts now see `prompts_used` rows for synthesized managed sessions instead of blocking on `prompt_count: 0`
- regression coverage in `tests/test_orchestration_runtime.py` verifies the managed subprocess path writes the objective into `prompts_used`
- runtime verification against `data/aios.db` produced `logs/session-effectiveness/managed-invoke-managed-prompt-capture-260604202353.json` with `prompt_count: 1`, project `AIOS`, run `run-managed-prompt-capture-260604202353`, and no blockers

## Implemented On 2026-06-01

AIOS Phase 10 now has a quality eval baseline for future major-task reviews:

- `scripts/quality-eval.sh` provides a read-only hotspot scan for large Python files, assertion-free tests, `services` importing `bin`, large UI components, vulture findings, and shellcheck findings
- `package.json` exposes the scan through `pnpm quality:eval`
- `docs/backfill/agent-eval-backfill.md` records the first factual hotspot inventory for Python services, CLI scripts, tests, aios-ui, config, and eval infrastructure
- the baseline records 59 Python files over 500 lines, 0 assertion-free Python tests, 0 `services` imports from `bin`, 3 TypeScript component files over 400 lines, 0 vulture findings, and 2 shellcheck files with findings in the current workspace
- Phase 10 is complete in planning state and the active roadmap position has advanced to Phase 11 testing and benchmark evaluation

## Implemented On 2026-06-01

AIOS session-effectiveness attribution now preserves the real project and governed run linkage through the hook lifecycle:

- hook lifecycle project resolution treats agent config directories such as `.claude` and `.codex` as non-project cwd payloads when the hook process is running inside a registered project
- `hook-session-start.py` stores the resolved workspace cwd in session rows, runtime metadata, invocation metadata, startup packets, and hook logs
- `hook-stop.py` repairs open sessions before closeout if their cwd resolves away from an agent config directory, then persists resolved run/invocation linkage back onto `sessions` before writing session-effectiveness receipts
- regression coverage locks `.claude` payload resolution to the registered AIOS project and verifies effectiveness receipts see persisted governed run ids
- the runtime path was verified against `/Users/jakyeamos/AIOS/data/aios.db` with a `.claude` payload cwd, producing a receipt under project `AIOS` and run `run-session-attribution-runtime-test`
- managed governed workflow runs now pass the runtime SQLite connection through stage execution, so `workflow_execution_reports.report_json` and `success_criteria_stage_findings` are populated from the same execution path that powers `workflow-compare` and workflow promotion candidates

## Implemented On 2026-05-24

AIOS now records session effectiveness as a durable receipt and exposes live activity indicators to Claude Code:

- `services/session_effectiveness.py` computes a session effectiveness score, rating, blocker/warning lists, activity lights, and source-backed measures from captured prompts, tool events, artifacts, failures, run linkage, RTK savings, and closeout receipts
- `hook-stop.py` writes `session_effectiveness_receipts` rows and JSON files under `logs/session-effectiveness/` when sessions close
- `bin/aios-statusline.py` renders a Claude Code `statusLine` bottom-bar summary with capture, work, quality, governance, prompt, artifact, bug, token-savings, model, and context indicators
- `.claude/settings.local.json` wires the local project status line to the AIOS renderer with a short refresh interval
- `tests/test_session_effectiveness.py` locks the receipt score, persistence path, and statusline rendering contract

## Current Product Boundary

Shipped AIOS behavior today is primarily:

- session logging
- prompt logging
- artifact logging
- bug capture
- pattern extraction
- lightweight startup retrieval
- dashboard-style visibility into runs, prompts, projects, and costs
- CLI-started routed work packets for serious agent sessions

AIOS is now partially usable as a preflight and routing layer for selected work, but it is not yet the default launcher for every agent session.

## Target Architecture Direction

AIOS must separate and expose these layers explicitly:

1. Durable knowledge
2. Project memory
3. Live workflow/orchestration state
4. Briefing packet generation
5. Grounded retrieval/query logic
6. Inspectability for routing, retrieval, assumptions, and changes

## This Pass

This implementation pass establishes:

- an audit artifact documenting the gap to the target system
- first-class control-plane schema and modules inside `aios-ui`
- knowledge-oriented information architecture instead of dashboard-only navigation
- grounded query and inspectable retrieval surfaces
- orchestration run logging and briefing packet generation
- ADR support and handoff documentation for continuation
- post-run memory updates written into dedicated control-plane state
- explicit run/session handshake and invocation records
- event-driven lifecycle transitions with durable history
- approval review surfaces for gated writebacks
- structured evaluator outputs for contradiction, drift, and stale-truth detection
- a real managed invocation backend path tied to the workflow/agent registry

## Implemented On 2026-05-14

AIOS tiered context standards now make machine readability a top-level precedence rule:

- `aios/context/standards/global.maintainability.md` requires instructions, packets, errors, logs, schemas, receipts, and status surfaces to preserve parseable structure, stable identifiers, explicit states, deterministic labels, and actionable remediation fields before human-friendly presentation
- `aios/context/domains/agent-harnesses.md` narrows the rule for packets, prompts, workflows, states, IDs, and remediation steps
- human-readable text remains allowed as clarification, but must not replace, obscure, or contradict machine-readable data

## Implemented On 2026-05-16

AIOS agent rules in `config/agent-rules.md` are now part of runtime behavior:

- session start packets inject the parsed agent-rule summary before learned active rules
- context compilation treats `config/agent-rules.md` as an immutable global context source and records it in receipts
- workflow execution loads the same rules into normalized prompts and report artifacts
- installed skill sync now preserves `source_path` and `installed_name` metadata so workflow skill reports can trace synced skills back to their installed `SKILL.md`

## Implemented On 2026-05-17

AIOS now treats orchestrated sub-agent development as the default strategy for most non-trivial work:

- `config/agent-rules.md` and `AGENTS.md` define the durable rule, including direct-execution exceptions for tiny local work
- `config/execution-strategies/model-routing-policy.json` records the configurable routing table for direct execution, subagent preference signals, agent roles, model tiers, reasoning levels, telemetry fields, benchmark classes, marginal-value learning, and promotion statuses
- `services/execution_strategy.py` and `bin/validate-execution-strategies.py` validate the routing policy alongside the existing execution-strategy catalog
- `docs/workflows/orchestrated-subagent-development.md` documents the workflow, eval plan, and follow-up implementation path for persistent telemetry and approval-gated policy updates
- `docs/evals/aios-harness-eval-v0.md` now includes the model-routing eval extension for learning cheapest reliable model/reasoning defaults over time

AIOS now has a first-class service-layer route contract for serious-work intent:

- `services/project_inventory.py` can now list registered projects across sparse or full project schemas and rank candidate projects from objective text, working-directory evidence, and explicit project overrides
- `services/task_routing.py` turns a vague objective into a machine-readable route result with project outcome (`exact`, `likely`, `ambiguous`, or `unsupported`), selected workflow, nearby workflow alternatives, prompt-family recommendation, backend recommendation, and blocked-reason semantics
- `tests/test_project_inventory.py` and `tests/test_task_routing.py` now lock exact-match, ambiguity, unsupported, implementation-route, failure-recovery-route, audit-route, and prompt-fallback behavior
- this establishes the route contract for Phase 1, but `aios start-work` still needs to adopt and persist it before AIOS can claim routed serious work flows through the main entrypoint by default

AIOS `start-work` now uses and persists the Phase 1 route contract:

- `services/aios_cli.py` now routes serious-work objectives before packet creation, deriving project/workflow/agent/backend defaults from the route layer while still allowing explicit overrides
- blocked project outcomes now stop `start-work` before run or packet creation, returning an explicit `route-blocked` CLI error instead of silently guessing
- `orchestration_runs` and `briefing_packets` now persist `route_id` plus machine-readable route metadata so later packet/query/operator surfaces can inspect routing decisions without recomputing them
- `tests/test_aios_cli.py` and `tests/test_orchestration_runtime.py` now cover route-aware packet creation, persisted route metadata, and ambiguity blocking in the main control-plane entrypoint

AIOS now has a shared route-aware packet contract across the CLI and UI/runtime packet surfaces:

- `aios-ui/lib/control-plane.ts` now models `routeId`, `routeResult`, and route-aware run metadata in the shared control-plane types
- `aios-ui/server/aios/schema.ts` now keeps UI/runtime schema upkeep aligned with the route-aware `orchestration_runs` and `briefing_packets` columns already present in `schema.sql` and `services/aios_cli.py`
- `aios-ui/server/aios/control-plane.ts` now reads and writes route-aware packet/run metadata instead of assuming the older packet-only shape
- `aios-ui/server/aios/packet-assembly.ts` now emits packet objects that conform to the shared route-aware packet contract, even when routing data is not yet attached in the UI-created path
- this closes the Phase 2 storage/reader drift between CLI and UI packet surfaces, but compiler/query provenance convergence and final governed handoff composition still remain

AIOS context compilation and grounded query now share packet-compatible provenance semantics:

- `tools/context-compile.mjs` now emits `retrieval_trace` and `packet_contract` metadata in the compiler payload and durable receipt JSON so context selection can flow into packet and query surfaces without translation loss
- `tests/context-compiler.test.mjs` now locks the packet-compatible provenance contract, including deterministic selection policy, route compatibility, loaded-context counts, and populated retrieval reasons
- `aios-ui/server/aios/query.ts` now loads the latest persisted packet provenance for a project and folds it into grounded `project_state` and `agent_brief` answers instead of relying only on adjacent dossier/topic traces
- grounded-query retrieval traces can now cite the latest briefing packet with objective, top context, and route-summary evidence, making compiler output and operator answers tell one provenance story
- this closes the main Phase 2 provenance gap between compiler receipts and query answers, but the final governed handoff packet still needs explicit workflow instructions, checks, and acceptance criteria

AIOS serious-work packets now use a governed handoff contract instead of a generic context summary:

- `services/aios_cli.py` now builds `start-work` packets with explicit workflow stages, routed prompt-family guidance, required checks, escalation rules, and closeout/writeback instructions
- the CLI packet response now returns the governed section structure directly and persists packet-contract metadata alongside the routed retrieval trace
- `tests/test_aios_cli.py` now locks the new packet contract, including section presence and persisted `governed-handoff-v1` metadata
- `aios-ui/server/aios/packet-assembly.ts` now composes the same contract shape for control-plane planned packets so UI-created work packets are also execution-oriented
- `aios-ui/server/aios/control-plane.ts` now records the packet contract version in the ready-state reason metadata for planned UI runs
- this closes Phase 2 with an agent-ready packet contract that combines context, workflow, prompt, checks, and governed closeout expectations in one default serious-work handoff

AIOS run lifecycle semantics now distinguish nuanced terminal outcomes instead of overloading clean completion:

- `bin/aios_orchestration_runtime.py` now recognizes `partial` and `needs_follow_up` as first-class runtime statuses and stamps closeout time for those terminal-but-incomplete outcomes
- `services/aios_cli.py` now treats `partial` and `needs_follow_up` as canonical lifecycle states, includes them in audit attention visibility, and reports them as supported terminal outcomes instead of unsupported noise
- `tests/test_orchestration_runtime.py` now locks partial closeout transitions and persisted reason metadata
- `tests/test_aios_cli.py` now verifies lifecycle audits include the widened attention/terminal contract and still isolate truly unsupported states
- this opens Phase 3 with a stronger lifecycle vocabulary for partial completion and follow-up debt before resume snapshots and closeout summaries are added

AIOS now persists explicit resume snapshots for serious runs:

- `bin/aios_orchestration_runtime.py` now stores and loads `resume_snapshot_json` on `orchestration_runs`, giving each resumable run a durable packet id, current stage, next recommended action, pending approval count, and approval targets
- `schema.sql` and `services/aios_cli.py` now keep the resume snapshot field in the canonical schema and in the `start-work` bootstrapping path
- `aios start-work` now seeds a `packet_ready` resume snapshot so serious work is resumable immediately after handoff creation
- `services/aios_cli.py status` now exposes resumable runs directly instead of forcing manual event reconstruction
- `bin/hook-session-start.py` now upgrades linked run snapshots to `execution_active` on session launch and surfaces the resume snapshot in the startup packet for resumed serious work
- `tests/test_orchestration_runtime.py`, `tests/test_aios_cli.py`, and `tests/test_agent_rules_runtime.py` now lock runtime persistence, status visibility, start-work seeding, and session-start packet injection for the resume contract
- this closes the main Phase 3 resume gap: AIOS can now preserve packet identity, stage, next action, and approval context without replaying raw run history

AIOS now persists governed closeout evidence for serious runs:

- `bin/hook-stop.py` now compiles a governed closeout summary after runtime completion, combining changed artifacts, checks run, pending approvals, unresolved deltas, and writeback implications in one persisted payload
- `bin/aios_orchestration_runtime.py` now allows workflow execution reports to attach closeout summaries even when only a run-level linkage is available
- `services/aios_cli.py status` now exposes recent governed closeouts so operators can inspect serious-run outcomes without manually joining workflow reports, writebacks, criteria evaluations, and memory updates
- `tests/test_orchestration_runtime.py` now verifies explicit-handshake stop closes with a persisted governed closeout report
- `tests/test_aios_cli.py` now verifies recent closeout visibility through the status payload
- this closes Phase 3 with a default serious-work execution contract that covers routing, packets, lifecycle nuance, resumable state, and governed closeout evidence

AIOS now has a first reusable personalized humanizer skill:

- `skills/personalized-humanizer/SKILL.md` defines the local skill contract for voice matching, context modes, privacy boundaries, debug/audit output, and feedback-gated learning
- `config/personalized-humanizer/profile.json` stores the versioned personal voice profile with global voice rules, mode-specific profiles, anti-style rules, confidence, and provenance
- `services/personalized_humanizer.py` implements task classification, bounded corpus example selection, compact voice packet generation, conservative rewriting, quality scorecards, feedback capture, candidate profile updates, and eval execution
- `config/workflows/registry.json` and `config/workflows/skills.json` expose the `personalized-humanizer` workflow and its staged skills for AIOS workflow routing
- `schema.sql` includes durable tables for personalized humanizer runs, feedback, candidate profile updates, and eval results
- `docs/architecture/personalized-humanizer.md` documents usage, retrieval, profile versioning, feedback promotion, evals, privacy boundaries, and debug inspection
- `tests/test_personalized_humanizer.py` covers the five required writing modes, mode-boundary retrieval, privacy-preserving provenance, prompt structure preservation, feedback proposal gating, eval cases, and workflow execution

AIOS personalized humanizer now has an explicit optional pipeline-step contract:

- `services/personalized_humanizer.py` supports `pipeline_position="standalone"` for the existing conservative cleanup-plus-voice path and `pipeline_position="after_generic_humanizer"` for a voice-specific pass after the generic humanizer
- debug output and durable run metadata now record the selected pipeline position and contract so agents can inspect whether a run owned generic cleanup or only personal voice adaptation
- `skills/personalized-humanizer/SKILL.md`, `config/workflows/skills.json`, and `docs/architecture/personalized-humanizer.md` now describe the intended composition: generic humanizer first for broad AI-writing cleanup, personalized humanizer second only when the user wants the result closer to their voice
- `tests/test_personalized_humanizer.py` covers the post-generic voice pass, explicit invalid pipeline-position failures, and the existing standalone behavior

AIOS now has an `agentize` intent compiler skill:

- `services/agentize.py` defines the `AgentizedTaskPacket` schema and deterministic request transformation pipeline for task classification, execution mode selection, targeted context planning, standards attachment, success criteria attachment, verification planning, output contracts, and prompt-pattern evidence
- `skills/agentize/SKILL.md` documents the reusable skill contract and reframes prompt templates as supporting evidence instead of the primary routing abstraction
- `config/workflows/registry.json` and `config/workflows/skills.json` register the `agentize` workflow and `agentize_intent_compiler` skill for AIOS workflow routing
- `schema.sql` and `data/schema.sql` add `agentize_evaluations` so outcome quality, tests, user correction, follow-up rate, and major-repair signals can improve packet generation over time
- `docs/architecture/agentize-skill.md` records the audit, architecture decision, packet contract, evaluation loop, compatibility notes, and migration plan
- `prompts/README.md` now describes the prompt library as a pattern/evidence corpus that `agentize` can use without requiring static request-to-template mapping
- `tests/test_agentize.py` covers packet structure, classification, execution-mode selection, context planning, standards attachment, verification planning, prompt-library demotion, evaluation logging, and workflow/skill registry binding

AIOS vault-root resolution is now centralized:

- `services/path_resolution.py` owns the vault root contract for Python services, preserving explicit overrides and `AIOS_VAULT_ROOT`
- `bin/aios_paths.py` wraps that resolver for script imports and shell use
- health checks, maintenance, import, sync, and ingest scripts no longer carry independent `~/projects/Vaults/Command-Center` or legacy `~/Vaults/Command-Center` defaults
- `bin/health_check.sh` creates the dashboard directory before writing and can skip macOS notification with `AIOS_SKIP_NOTIFICATION=1` for non-interactive validation
- `tests/test_path_resolution.py` covers override behavior, canonical-vs-legacy fallback, legacy path rewriting, and the script CLI used by shell entrypoints

AIOS hook session resolution now repairs stale payload ids:

- `hook_lifecycle.resolve_hook_session_id` prefers the open `logs/current_session` pointer when a hook payload points at a different cwd or an already closed stale session
- prompt-submit, post-tool-use, and stop hooks use the shared resolver before writing prompt rows, tool events, artifacts, summaries, or closeout state
- `bin/repair-stale-open-sessions.py` provides a dry-run-first backfill that abandons old open sessions only when they have no prompts, no non-start tool events, and no runtime invocation linkage
- the live smoke session `codex-agent-rules-live-check-260516` now has a captured prompt row, closeout summary, criteria evaluation, and standards-health snapshot
- `tests/test_hook_lifecycle.py` covers stale prompt reassignment, stale stop closeout reassignment, and inactive-session backfill filtering

## Implemented On 2026-05-19

AIOS now has a governed project truth audit contract:

- `aios truth-audit --json` inspects the canonical truth file, defaults to `PROJECT.md`, and reports freshness, required operating facet coverage, review findings, recent governed closeout evidence, and resumable run evidence
- `services/aios_cli.py` defines the truth-update contract: accepted truth comes from the selected truth file, proposals come from `workflow_execution_reports.report_json` and `orchestration_runs.resume_snapshot_json`, and important updates require review
- the truth audit checks for required facets covering goals, architecture, risks, completed work, unresolved deltas, next actions, and decisions
- `tests/test_aios_cli.py` verifies the governed truth contract, proposal-source linkage, resumable evidence, closeout evidence, and missing-facet warnings
- this starts Phase 4 by making truth freshness and governed truth updates inspectable through the same JSON-first control-plane CLI used by agents

## Implemented On 2026-05-21

AIOS agent rules now include truth-first reasoning as a core operating principle:

- `config/agent-rules.md` requires agents to prioritize correctness over agreement, treat user claims and plans as unverified until checked, and state clear verdicts when evaluating claims, diagnoses, plans, code paths, or technical decisions
- the rule requires agents to reject bad or symptom-only fixes, inspect real code paths before accepting diagnoses, challenge weak planning assumptions, distinguish fact from inference or opinion, and say when evidence is unknown or unproven
- because `config/agent-rules.md` is already injected into session-start packets, context compilation receipts, and workflow execution artifacts, this principle now applies through the existing AIOS runtime rule path

AIOS knowledge surfaces now distinguish accepted truth, proposed evidence, and inferred context assets:

- `aios-ui/lib/control-plane.ts` defines a `TruthKnowledgeBoundary` contract with accepted, proposed, and inferred authority states for agent-readable knowledge linkage
- `aios-ui/server/aios/knowledge.ts` exposes accepted truth from `PROJECT.md` and accepted decision records, proposed knowledge from workflow closeout reports and resumable run snapshots, and inferred knowledge from workflows, agent/skill profiles, prompt-library context, and research-tagged wiki pages
- `aios-ui/server/routers/knowledge.ts` adds `knowledge.truthBoundary`, giving agents one typed UI/server surface for truth-vs-proposal boundaries instead of forcing them to infer authority from page names or raw tables
- runtime closeouts and resume snapshots remain proposal evidence until reviewed; prompts, skills, workflows, and research can shape packets but cannot overwrite truth directly
- this advances Phase 4 by making truth, decisions, prompts, skills, workflows, and research explicitly linkable while preserving authority boundaries

AIOS grounded query now answers truth-first operator questions:

- `aios-ui/server/aios/query.ts` loads the truth boundary before composing default operator answers
- truth/operator questions now answer from accepted truth, recent proposal evidence, recent runtime changes, and inferred prior knowledge in distinct lanes
- project-state, agent-brief, what-changed, and system-state answers now cite the truth boundary and explain whether evidence is accepted, proposed, or inferred
- unresolved proposal evidence is called out as needing review before promotion into `PROJECT.md`, standards, prompts, skills, or workflow defaults
- this closes Phase 4 by making grounded query usable as the default surface for asking what changed, what remains unresolved, and what prior knowledge matters before manual context assembly

AIOS now has a cross-asset governance audit contract:

- `aios governance-audit --json` normalizes proposal evidence from `improvement_writebacks`, `memory_writeback_proposals`, `workflow_synthesis_proposals`, and `promotion_lifecycle_items`
- the audit reports proposal counts, pending approval counts, terminal run counts, terminal runs missing governance evidence, governed closeout counts, and unresolved closeout counts
- terminal meaningful runs are now auditable against the rule that they need writeback, follow-up, closeout, or no-learning evidence before they can be trusted as complete
- governance findings flag pending approvals and blocker-level terminal runs that have no durable governance evidence
- `tests/test_aios_cli.py` verifies pending truth approval, unresolved closeout evidence, and silent terminal-run detection through the JSON-first CLI

AIOS writebacks now carry explicit approval policy classes:

- `bin/aios_orchestration_runtime.py` derives approval policy classes for truth, standards, prompt, skill, workflow, packet, workflow-default, global, project-truth, and destructive-action writebacks
- high-impact writebacks now become `pending_approval` by default unless they are scoped project-memory proposals
- writeback event metadata and proposed-change payloads include the approval policy so later audits and UI surfaces can explain why a proposal is gated
- `bin/hook-stop.py` includes a machine-readable governance summary in governed closeout reports, including writeback counts, approval-required counts, policy classes, unresolved follow-up count, and review requirement
- `tests/test_orchestration_runtime.py` verifies derived workflow-default approval gating and closeout governance policy visibility

AIOS governance state is now visible through the UI/server control-plane contract:

- `aios-ui/lib/control-plane.ts` defines `GovernanceOverview`, `GovernanceProposalSummary`, and terminal-run governance gap types for agent-readable approval visibility
- `aios-ui/server/aios/control-plane.ts` builds a governance overview with proposal counts, pending approval counts, policy-class counts, terminal-run evidence gaps, pending approval rows, recent proposal rows, and governance link rules
- `aios-ui/server/routers/control-plane.ts` exposes `controlPlane.governance`, and the existing overview now embeds the same governance summary
- the UI/server layer can now answer which proposals require review and which terminal runs are missing writeback/closeout/no-learning evidence without raw database inspection
- this closes Phase 5 by making writebacks, approval policy, pending review, unresolved follow-up, and terminal-run governance gaps visible to agents and operator surfaces

## Implemented On 2026-05-14

AIOS now has a fixture-backed harness eval v0 contract:

- `docs/evals/aios-harness-eval-v0.md` defines the same-model/same-task/same-budget harness comparison frame and the deterministic v0 fixture/run artifact contract
- `docs/aios/harness-eval/config.json` registers five initial categories: context routing, false completion, approval gates, recovery, and writebacks
- `services/harness_eval.py` scores context precision/recall, gate accuracy, success-criteria recall, trace completeness, false-completion detection, recovery evidence, and useful writeback evidence without live model calls
- `aios harness-eval run --json` exposes the suite through the normal AIOS CLI JSON envelope
- `tests/fixtures/harness-eval/` contains baseline and AIOS-shadow sample runs for each v0 category, covered by `tests/test_harness_eval.py`

## Implemented On 2026-05-13

AIOS planning now has an explicit functionality-to-tier-one mapping layer:

- `.planning/FUNCTIONALITY_MAP.md` now maps major current and planned AIOS capabilities to:
  - concrete code surfaces
  - current implementation status
  - v1 requirements
  - roadmap phases
  - tier-one gaps
- `.planning/FUNCTIONALITY_PLAN.md` now expands that summary into detailed planning guidance for every major functionality group and the workflow library, including:
  - current state
  - tier-one target
  - detailed scope
  - implementation tracks
  - dependencies
  - exit evidence
- `.planning/WORKFLOW_MATRIX.md` now gives workflows their own first-class planning artifact with one row per current or planned workflow covering:
  - trigger conditions
  - stage contract
  - prompt family
  - required skills and validations
  - approval gates
  - artifacts
  - writebacks
  - learning signals
  - roadmap ownership
  - tier-one gaps
- `.planning/ROADMAP.md` is now expanded from a short phase summary into a fuller execution contract:
  - each phase now includes detailed scope
  - current code surfaces to evolve
  - workflow ownership
  - expected outputs
  - dependencies
  - observable success criteria
  - a phase dependency chain and explicit workflow rollout strategy are also recorded
- three deeper planning control artifacts now sit underneath the roadmap so execution can be traced more concretely:
  - `.planning/PHASE_01_SUBROADMAP.md` breaks Phase 1 into detailed routing workstreams, deliverables, dependencies, risks, and exit gates
  - `.planning/REQUIREMENTS_CODE_SURFACE_MATRIX.md` maps every v1 requirement to the concrete code/config/storage surfaces that must evolve to reach tier one
  - `.planning/TIER_ONE_ACCEPTANCE_CHECKLIST.md` defines per-phase capability gates, evidence gates, and failure conditions for default-layer readiness
- the map makes prompt-library selection, grounded query, automation observability, CTS/repository intelligence, reusable asset lifecycle, and other current/planned surfaces explicit instead of leaving them implied inside broader requirements
- `.planning/REQUIREMENTS.md` and `.planning/ROADMAP.md` were tightened so prompt-library selection and prompt/handoff composition are represented in the early execution loop:
  - Phase 1 routing now includes prompt/handoff-family selection
  - Phase 2 packet compilation now includes prompt assets and prompt/handoff instructions
  - operator answers now explicitly include reusable prompt/skill relevance
- workflow contracts are now first-class planning scope instead of being spread implicitly across routing and asset lifecycle:
  - `.planning/REQUIREMENTS.md` adds `WFLO-01` through `WFLO-04`
  - Phase 8 now covers workflow-stage contracts, prompt/skill/tool bindings, stage-level evaluation, and workflow promotion/revision/deprecation
- roadmap phase names now carry more explicit product meaning for the runtime loop:
  - Phase 1 is now `Project, Workflow, And Prompt Routing`
  - Phase 2 is now `Context, Query, And Briefing Compilation`
  - Phase 4 is now `Project Truth, Knowledge, And Grounded Query`
  - Phase 8 is now `Prompt, Skill, Workflow Contracts, And Asset Lifecycle`
  - Phase 10 is now `Operator Surfaces, Query, And Daily-Flow Visibility`
- this gives the repo a clearer planning contract for “all current or planned functionality must reach tier one through requirements and roadmap coverage,” not just broad thematic phase buckets

## Implemented On 2026-05-13

AIOS now treats the requested harness durability rules as first-class context standards:

- common error surfaces should be fixed durably at their recurrence point or captured as explicit follow-up work
- agent-facing code, packets, prompts, and workflows should stay inviting under limited context, using responsibility-based splits instead of arbitrary line-count ceilings
- errors surfaced to agents should be machine-readable and include actionable remediation steps
- the rules live in `global.maintainability`, `global.observability`, and `domains.agent-harnesses` so future context compiler receipts can load them for relevant work

## Implemented On 2026-05-14

AIOS now has the first backend-neutral agent harness test ladder slice:

- `aios harness-brief --json` combines deterministic context compiler packet selection with success-criteria preview for a task before any live agent run
- `aios harness-simulate --json` replays fake-agent fixture events into the existing orchestration run/event/briefing tables and refuses to mark claimed completion complete when tests or gates fail
- `aios harness-replay --json` converts stored sessions, tool events, and artifacts into stable harness events for deterministic post-hoc evaluation
- `aios harness-shadow-evaluate --json` evaluates an existing or latest session in read-only shadow mode without blocking tools, creating writebacks, or launching an agent
- active harness enforcement remains explicitly disabled behind `aios harness-active-readiness --json` until fake lifecycle, replay, shadow, approval, and writeback evidence gates are satisfied
- the runtime lifecycle vocabulary now accepts blocked, waiting-for-user, waiting-for-tool, and failed-validation states for harness and control-plane tests
- the harness CLI import surface is lint-clean under the existing Ruff import ordering gate

AIOS now has a fixture-backed harness eval v0 contract:

- `docs/evals/aios-harness-eval-v0.md` defines the same-model/same-task/same-budget harness comparison frame and the deterministic v0 fixture/run artifact contract
- `docs/aios/harness-eval/config.json` registers five initial categories: context routing, false completion, approval gates, recovery, and writebacks
- `services/harness_eval.py` scores context precision/recall, gate accuracy, success-criteria recall, trace completeness, false-completion detection, recovery evidence, and useful writeback evidence without live model calls
- `aios harness-eval run --json` exposes the suite through the normal AIOS CLI JSON envelope
- `tests/fixtures/harness-eval/` contains baseline and AIOS-shadow sample runs for each v0 category, covered by `tests/test_harness_eval.py`

## Implemented On 2026-05-13

AIOS now has a first-class Pre-PR readiness gate backed by `pre-cr-suite-lsp`:

- repo-level `.pre-cr.json` config now defines the current AIOS `pre-cr` contract around Python changed-line coverage using an external temp LCOV artifact
- `uv run python bin/aios.py pre-pr-readiness` now starts the built `pre-cr-suite-lsp` server locally, runs `$/preCr/runPreCrCheck`, and returns a JSON-safe gate result
- the AIOS-specific wrapper fails fast when the current diff touches unsupported JS/TS or shell surfaces so the gate cannot silently overclaim repo-wide coverage
- `config/quality-pipeline.json` now exposes `pre_pr_readiness` as a required AIOS quality gate
- `README.md` now documents the operator command for this gate
- Stop-hook closeout now supports RTK metrics aggregation on the default SQLite tuple row factory used by `bin/hook-stop.py`; the May 12 post-standards-snapshot crash path now records the Stop event after RTK logging instead of failing with tuple string-index access.

## Implemented On 2026-04-28

Tier-one AIOS planning now has a dedicated execution pack under `docs/superpowers/plans/tier-one-aios/`:

- `00-index.md` defines the tier-one acceptance gate and execution order
- section plans cover runtime/invocation reliability, command-center UI, knowledge/personal memory, workflow learning, project standards health, observability/telemetry, integrations/retrieval, testing/release hardening, and rollout governance
- the pack treats UI polish as the final stage after runtime, knowledge, learning, telemetry, and contract trust are proven

## Implemented On 2026-04-29

The tier-one audit fix pass has started with capability trust gates before UI polish:

- release and regression gates now lock the current audit promises for lifecycle states, canonical contracts, Prompt Library visibility, RTK explanations, readable automation schedules, workflow learning counts, and capability missing-data reasons
- UI quality CI now runs lint, the 71-warning ESLint ratchet, architecture lint, anti-slop fixture lint, and production build; Python CI now runs `uv run pytest -q`
- project health audit output now reports explicit states/subtypes such as `healthy`, `degraded`, `missing_source`, `missing_snapshot`, `unknown`, `active_with_sessions`, and `active_no_sessions`
- automation health now treats missing durable run history as unknown/inferred instead of confirmed seeded reliability
- RTK audit output now distinguishes `token_regressive` from inactive or beneficial states
- workflow learning now persists `workflow_learning_events` from writebacks, durable inferred evidence, and explicit no-learning reasons
- the live workflow-learning audit backfilled 110 terminal runs into persisted events: 96 learning events and 14 no-learning signals
- contracts audit now reports `WorkflowLearningEvent` as implemented
- knowledge objects now enforce valid kinds, report unknown kinds as audit findings, expose source refs/backlinks/freshness/confidence plus retrieval trace counts, and search across topic text plus reference labels/excerpts/source kinds
- briefing packets now persist retrieval traces with query, matched objects, omitted context count, expansion path, citations, token budget, and ranking reason
- success-criteria findings now have lifecycle/resolution metadata matching consistency findings
- the live contracts audit now reports all seven canonical contracts as implemented with zero partial contracts
- automation reliability now has a durable `automation_run_history` schema shared by Python audits and the UI schema
- automation audit and UI states now derive success rate, status, urgency, last run, next run, failure summary, approvals, and writeback blockers from run history; empty history is surfaced as unknown/watch instead of seeded health
- RTK command execution now honors the configured short-output compression threshold for successful runs, passing small outputs through as raw telemetry instead of manufacturing token-regressive compression events
- the first critical implementation target is managed runtime closeout and explicit handshake reliability
- `EXECUTION.md` now routes agents through the plan pack by priority gates, verification commands, stop conditions, parallelization rules, and final tier-one claim checklist
- Managed runtime closeout now has direct start and closeout guards in `bin/aios-managed-run.py` so hook-side evaluator failures cannot leave authoritative runs stuck in `ready`; `tests/test_orchestration_runtime.py::test_managed_runtime_completes_via_explicit_handshake` and the full Python suite now pass.
- Managed runtime closeout now has an explicit regression for authoritative closeout repair: `tests/test_orchestration_runtime.py::test_managed_closeout_repairs_authoritative_run_state` verifies a run left in `ready` is completed with the correct session, invocation, closeout event, and closed session state.
- Workflow learning audit now recognizes inferred durable evidence from workflow reports, memory updates, standards snapshots, success evaluations, and session artifacts linked through runs; the live audit moved from 110 no-learning terminal runs to 96 inferred evidence records and 14 no-learning runs.
- Priority standards-health snapshots were regenerated for AIOS, Terrace, amos-saas, portfolio, and soundscape-app using `services.standards_health.evaluate_and_record(..., trigger_kind="tier_one_priority_audit")`; the current priority scores are AIOS 64.8, Terrace 63.2, amos-saas 63.2, portfolio 72.8, and soundscape-app 63.2.
- `aios prove-project-health --json` now records repeatable tier-one standards-health proof snapshots and reports missing inventory/source explicitly; the live proof recorded snapshots for AIOS 68.0, soundscape-app 63.2, Terrace 63.2, portfolio 72.8, and amos-saas 63.2.
- `aios prove-project-health --all-inventory --json` now processes every inventory row by project id, including duplicate project names; the live all-inventory proof recorded 27 standards-health snapshots and left only concrete missing-source findings for `Bball`, the duplicate `Terrace ` path with trailing whitespace, and `sleeper_league_pack`.
- `aios sync-automation-history --json` now imports durable daily pipeline evidence from `logs/pipeline.log` into `automation_run_history`; the live sync parsed 3 runs and the capability audit now reports no automation-history findings, with Daily ingest status confirmed from history as latest `healthy`, success rate 0.667, and urgency `watch`.
- RTK metrics now separate total telemetry from eligible compression telemetry using the configured compression threshold, so short pass-through outputs are counted as ineligible instead of token-regressive compression attempts; the live RTK state remains `token_regressive` because one eligible historical event is still net-regressive, while 2 of 3 events are now classified as pass-through/ineligible.
- Prompt Library visibility is now backed by the existing prompt sync path: `bin/sync-prompts.py` copied 5 prompt templates into the configured vault template directory and created 5 `prompt_library_links` rows, removing the `prompt_library_empty` finding from the live capability audit.
- RTK telemetry now distinguishes state from benefit: `aios rtk --json` and `aios capability-audit --json` report `benefit_state` values such as `beneficial`, `no_benefit`, `token_regressive`, and `no_eligible_data`; the current live RTK signal is `inactive` with `token_regressive` evidence because 3 events recorded 47 raw tokens and 110 compressed tokens.
- Tier-one audit regressions now lock the current control-plane promises in `tests/test_tier_one_regressions.py`: lifecycle audits reject unsupported states, contract audits expose seven canonical contracts, capability audits preserve prompt-library visibility, RTK explanations, readable automation schedules, and missing automation history.
- Capability truth now separates project health subtypes (`healthy`, `degraded`, `missing_source`, `missing_snapshot`, `unknown`) from broad inventory status, and project findings include source, freshness, confidence, and missing reason. Broad `active` status is qualified as `active_with_sessions`, `active_no_sessions`, or `missing_source`.
- Automation reliability no longer treats seeded health as confirmed: when `automation_run_history` is absent, automation status and success rate are `missing` with explicit missing-history reasons, readable schedules remain the primary trigger label, and urgency is reported as `watch`.
- RTK `token_regressive` is now a first-class runtime state in Python and UI types; the live RTK audit reports `state=token_regressive` and `benefit_state=token_regressive` rather than hiding the condition behind a generic inactive zero-savings state.
- Tier-one release gates now include Python CI for `uv run pytest -q`, UI CI production build, and an ESLint warning ratchet at the current 71-warning baseline via `aios-ui/scripts/assert-eslint-warning-baseline.mjs`; README quality-check docs now mirror the CI command set.

## Implemented On 2026-05-07

AIOS now has a repeatable corpus evaluation harness for product-level regression testing:

- `scripts/aios-corpus-eval.cjs` runs configured AIOS commands against disposable copied or synthetic workspaces and defaults evidence output to the system temp directory to avoid live project mutation.
- `docs/aios/corpus/config.json` defines the initial migrated, scratch-real, synthetic, dirty, and negative corpus tracks plus CLI, prompt-library, workflow, success-criteria, hook, repo-intelligence, state, and negative command suites.
- `npm run corpus:evaluate` is the project command, and `aios corpus run` / `aios corpus report` wrap the same harness through the Python CLI.
- The harness captures stdout, stderr, exit code, duration, parsed JSON, artifacts written, git status/diff summaries, classification, raw evidence paths, JSON reports, Markdown reports, dry-run plans, sample/full filters, suite/repo/mode filters, report-only regeneration, timeouts, and `--keep-worktrees`.
- Full-mode evaluation now includes explicit oracles for workflow start packets, hook DB/log side effects, CTS build/status behavior, dirty worktree detection, JSON shape, clean negative failures, and SQLite artifact persistence rather than relying on exit codes alone.
- Corpus harness checks now cover self-test behavior, suite filtering, and Python CLI passthrough in `tests/test_corpus_eval.py`.

## Implemented On 2026-05-13

AIOS now has a committed GSD codebase map for brownfield planning initialization:

- `.planning/codebase/` now exists with:
  - `STACK.md`
  - `INTEGRATIONS.md`
  - `ARCHITECTURE.md`
  - `STRUCTURE.md`
  - `CONVENTIONS.md`
  - `TESTING.md`
  - `CONCERNS.md`
- the codebase map captures the current stack, integrations, architecture, structure, conventions, testing posture, and known concerns for this repository at commit `c8817f21`
- this gives the repo a concrete GSD planning baseline before `/gsd-new-project` generates requirements, roadmap, and execution phases

## Implemented On 2026-05-12

AIOS now has the first file-backed Context Compiler:

- `aios/context/` defines thin tiered Markdown manifests for global standards, domains, project routers, feature routers, packets, handoffs, generated briefings, and receipts.
- `tools/context-compile.mjs` scans context Markdown, validates frontmatter, classifies tasks with deterministic signals, scores candidate context, follows `load_if_matched`, resolves immutable-global conflicts, reports missing/stale context, and writes latest briefing/receipt outputs.
- Root scripts now include `pnpm context:compile --task "..."`, `pnpm context:validate`, and `pnpm test:context`.
- `AGENTS.md` now includes the Context Compiler bootloader so agents load the smallest sufficient context packet instead of sweeping every Markdown file.
- `docs/context/context-compiler.md` records the audit, operating model, schema, conflict precedence, Obsidian evolution path, and UI integration follow-up.
- `aios-ui/app/context/page.tsx` now exposes the latest compiled context packet, loaded/skipped files, context inventory, conflicts, missing/stale context, writeback candidates, and the raw receipt from the file-backed compiler.

AIOS now has a branch-level Divergent Strategy Workflow experiment:

- `services/divergent_strategy.py` creates local deterministic divergent runs with task classification, role-based candidate generation, reusable judges, portfolio selection, entropy tracking, and approval-gated writeback proposals.
- New SQLite tables store `divergent_runs`, `divergent_candidates`, `divergent_judgments`, `memory_writeback_proposals`, `entropy_observations`, and `promotion_lifecycle_items`.
- Candidate and judge registries live in `config/divergent-strategy/`, and the workflow is registered as `divergent-strategy` in the AIOS workflow registry.
- UI read surfaces now expose `/runs/divergent`, `/runs/divergent/:id`, `/writebacks`, and `/skills/candidates`.
- Memory writebacks are separated into HOW, WHAT, FAILURE, and ENTROPY categories and remain proposals until approved.
- Prompt/skill/judge/workflow promotion now has a lightweight evidence-gated lifecycle: `draft -> candidate -> tested -> approved -> active -> deprecated`.
- The skill packet lives at `skills/divergent-strategy/`, with thin `SKILL.md` and tiered reference files.
- Architecture docs now cover divergent strategy, memory writebacks, prompt/skill promotion, and entropy tracking.
- The divergent strategy contract is now appended to preexisting test and experiment surfaces as `experimentation.divergent_strategy_standard`: standards registry, AIOS quality pipeline, corpus eval config, experiment test repos, and workflow skill experiment artifacts.

Stage 1 capability-truth baseline work has started with a first trusted-signal slice in `aios-ui`:

- added a shared UI/server `TrustedSignal` contract for capability metrics with:
  - provenance: `confirmed`, `inferred`, `missing`, `contradictory`
  - confidence
  - source label/table/field
  - freshness
  - explanation
  - missing reason
  - contradiction detail
- Projects now attach trusted signals to:
  - health score
  - health trend
  - critical delta count
  - unknown coverage
  - pipeline state
  - project status
- Projects no longer render the confusing health parenthetical as the primary display; health score and trend are separate visible signals.
- Pipeline badges now render an explicit configured/required label, and an `error` status with zero configured required checks is represented as a contradictory trusted signal instead of silently rendering as `0/5 ERROR`.
- Efficiency/RTK now exposes an explicit RTK state:
  - `active`
  - `inactive`
  - `no_eligible_data`
  with source-backed explanation for zero-savings states.
- Automations now infer readable schedule labels from persisted RRULE triggers and preserve the raw RRULE as secondary evidence instead of the primary trigger display.
- Automations now attach trusted signals to trigger, success rate, and status while acknowledging seeded automation health until durable run history exists.
- Projects and Automations tables now have dedicated grid layouts to avoid the screenshot-observed column wrapping/overlap.
- `aios capability-audit --json` now exposes the same Stage 1 trusted-signal contract from the CLI for core capability surfaces:
  - Projects
  - RTK
  - Automations
  - Prompt Library
  - Knowledge
- The capability audit emits source-backed/missing/inferred states and backend findings such as missing project health snapshots.
- Prompt Library audit now verifies whether `prompt_library_links` exists and whether body-hash-backed templates are actually visible.
- Knowledge audit now reports topic count, source-reference coverage, relationship count, and findings for topics without references.
- This gives later runtime, knowledge, workflow-learning, architecture, and UI phases a concrete Stage 1 gate instead of relying only on dashboard rendering.
- Grounded Query now recognizes capability/status audit questions and answers them from live SQLite counts for:
  - project health snapshot coverage
  - RTK telemetry events
  - seeded automation status
  - prompt library body-hash visibility
  - knowledge topic/reference coverage
- Stage 2 agent-runtime capability has started with an invocation backend contract:
  - added a shared backend registry in `services/invocation_backends.py` for Codex managed runtime, Claude managed runtime, and the deprecated manual-session legacy path
  - `aios invocation-audit --json` now exposes backend count, required invocation contract fields, handshake coverage, and legacy fallback policy
  - `aios start-work --backend ...` now persists the selected backend key and label instead of labeling every invocation as Codex
  - strict handshake fields are now an explicit CLI contract: run id, invocation id, backend key, objective, project id, workflow key, packet id, lifecycle events, artifacts, and closeout evaluation
  - `aios lifecycle-audit --json` now exposes the canonical run lifecycle contract, observed state counts, unsupported states, and attention-state events for blocked, waiting-for-user, waiting-for-tool, and failed-validation runs
- Stage 3 knowledge-memory capability has started with a Knowledge Object contract:
  - `aios knowledge-objects --json` adapts existing `knowledge_topics`, `knowledge_references`, and `knowledge_relationships` rows into stable objects with source refs, backlinks, freshness, and confidence
  - the command reports source-reference coverage and objects without sources so grouped topic summaries can be distinguished from citable memory
- Stage 4 workflow-learning capability has started with an evidence classification audit:
  - `aios workflow-learning-audit --json` classifies terminal runs as workflow evidence, prompt-template evidence, standards-health evidence, bug/quality evidence, or no-learning signal
  - the command reports proposal counts, approval-gated proposals, and completed/failed/canceled/superseded runs that produced no durable learning record
- Stage 5 architecture hardening has started with a canonical contract audit:
  - `aios contracts-audit --json` reports the current status and storage source for TrustedSignal, InvocationBackend, RunLifecycleEvent, KnowledgeObject, RetrievalTrace, WorkflowLearningEvent, and EvaluationFinding
  - the contract audit distinguishes implemented contracts from partial contracts so later UI work can avoid exposing unstable abstractions as finished product surfaces

This pass makes milestones 1 and 2 operational for selected work from the local CLI:

- `aios start-work "<objective>"` creates a routed work record before implementation:
  - `orchestration_runs`
  - `briefing_packets`
  - `orchestration_invocations`
  - `orchestration_run_events`
- when `logs/current_session` points at a hook-created session, `start-work` links that session through:
  - `sessions.run_id`
  - `sessions.invocation_id`
  - `sessions.runtime_metadata_json`
- the generated packet now includes:
  - objective and project context
  - applicable success criteria preview
  - active rules
  - recent improvement writebacks
  - matching indexed knowledge topics
  - an explicit routing/closeout contract
- this makes AIOS useful as a preflight and handshake layer for serious current-session work without pretending the managed runtime is already the full Codex work loop.

## Implemented On 2026-04-18

The current app now includes:

- `knowledge` routes for projects, decisions, workflows, agents, and system pages
- `control` route for workflow selection, agent registry, run history, and packet generation
- `query` route for grounded, inspectable internal answers
- dedicated control-plane schema:
  - `orchestration_runs`
  - `briefing_packets`
  - `memory_updates`
- ADR-backed decision logging in `docs/adr/`
- upgraded project dossiers with memory, rules, likely files, decisions, and recent changes
- `hook-stop.py` memory update writes on session close
- orchestration run lifecycle closure from `hook-stop.py`, including:
  - `session_id`
  - `memory_update_id`
  - `result_summary`
  - `completed_at`
- curated vault wiki ingestion into first-class `concept` knowledge pages
- derived wiki backlinks and relationship resolution inside the knowledge surface
- CTS-backed enrichment for:
  - control-plane packet generation
  - grounded query project-state answers
  - grounded query agent brief answers
  - inspectable retrieval traces

## Implemented On 2026-04-19

This pass adds the first persisted topic-graph and compact-packet vertical slice:

- persisted indexed knowledge layer:
  - `knowledge_topics`
  - `knowledge_relationships`
  - `knowledge_references`
  - `knowledge_markers`
  - `knowledge_graph_state`
- compact ranked packet delivery as the default orchestration policy
- explicit packet trace and omitted-context storage in `briefing_packets`
- traced targeted expansion logging in `packet_expansions`
- improvement writeback storage in `improvement_writebacks`
- Taski-led project operating surface on `/projects/[id]`
- topic-graph-backed retrieval in grounded query
- concept pages enriched with persisted references, relationships, and drift markers
- post-run improvement writeback proposals from `hook-stop.py`
- architecture note for the hardened retrieval policy:
  - `docs/architecture/2026-04-19-topic-graph-ranked-packets.md`

This pass also turns the execution layer into a real control-plane path:

- explicit durable handshake through:
  - `orchestration_runs.id`
  - `sessions.run_id`
  - `sessions.invocation_id`
  - `orchestration_invocations`
- first-class lifecycle and trace tables:
  - `orchestration_run_events`
  - `improvement_writeback_events`
- event-driven run statuses now written from runtime events:
  - `planned`
  - `ready`
  - `in_progress`
  - `completed`
  - `failed`
  - `canceled`
  - `superseded`
- structured run state on `orchestration_runs`:
  - `backend_key`
  - `active_invocation_id`
  - `started_at`
  - `failed_at`
  - `canceled_at`
  - `superseded_by_run_id`
  - `status_reason_json`
- approval decision persistence on `improvement_writebacks`
- structured evaluation storage:
  - `consistency_evaluations`
  - `consistency_findings`
- `/control` upgraded from packet planning only to:
  - managed run invocation
  - runtime status inspection
  - approval review
  - event timeline / evaluator trace
- Taski project surface upgraded to show:
  - structured findings
  - approval queue
  - event-driven run state
- managed backend runner in `bin/aios-managed-run.py`
- `hook-session-start.py` now moves explicitly linked runs to `in_progress`
- `hook-stop.py` now resolves the exact run by handshake first and only falls back to heuristic matching as a legacy escape hatch

## Implemented On 2026-04-23

Phase 0a architecture enforcement baseline is now live as an AIOS-managed profile system:

- AIOS registry for reusable architecture profiles:
  - `config/architecture-enforcement/profiles.json`
  - `config/architecture-enforcement/projects.json`
- new enforcement runner and CLI:
  - `services/architecture_enforcement.py`
  - `bin/architecture-enforcement.py`
- Python profile (`python-service-v1`) enforcing:
  - `services -> bin` import boundary denial
  - cycle detection for local Python modules
  - optional ruff adapter when local tooling exists
- Next.js profile (`ts-nextjs-v1`) enforcing:
  - Dependency Cruiser layer boundaries + cycle detection
  - existing ESLint/TypeScript lint checks
- proof-target wiring in `aios-ui`:
  - `.dependency-cruiser.cjs`
  - `npm run lint:architecture`
- architecture audit + rollout doc:
  - `docs/architecture/2026-04-23-aios-architecture-enforcement.md`

Phase 0b agent workflow CLI surfaces are now implemented after the hard checkpoint:

- audit package (checkpoint gate):
  - `docs/architecture/2026-04-23-aios-agent-workflow-audit.md`
- unified JSON-first command surface:
  - `bin/aios.py`
  - `services/aios_cli.py`
- implemented command family:
  - `aios status --json`
  - `aios health --json`
  - `aios metadata --json`
  - `aios logs --json`
  - `aios recent-failures --json`
  - `aios skills status --json`
  - `aios skills refresh --json [--apply]`
- standardized semantic exit-code envelope on unified surfaces:
  - usage, not-found, dependency/config, runtime
- instruction/skills refresh flow moved to declarative registry:
  - `config/instruction-registry.json`
- implementation handoff:
  - `docs/handoffs/2026-04-23-aios-agent-workflow-cli-handoff.md`

Phase 0c success criteria control-plane baseline is now live:

- criteria registry + skill mapping:
  - `config/success-criteria/registry.json`
  - `config/success-criteria/skill-map.json`
- canonical criteria docs and discovery index:
  - `spec/success-criteria/index.md`
  - `spec/success-criteria/_template.md`
  - normalized criteria docs for:
    - `code-simplicity`
    - `testing-trust`
    - `security-review`
    - `observability`
    - `truth-file-consistency`
    - `repo-boundary-discipline`
    - `workflow-state-integrity`
- runtime evaluator and artifact persistence:
  - `services/success_criteria.py`
  - `data/success-criteria/evaluations/*.json`
- hook integration:
  - `hook-session-start.py` now previews applicable criteria before implementation
  - `hook-stop.py` now evaluates changed patch paths and records criteria findings
- durable schema additions:
  - `success_criteria_evaluations`
  - `success_criteria_findings`
- metadata snapshot visibility:
  - `aios metadata --json` now exposes criteria catalog + latest evaluation
- phase architecture note:
  - `docs/architecture/2026-04-23-aios-success-criteria-system.md`

## Implemented On 2026-04-27

Execution-first verification is now mechanically represented in the success criteria system:

- new blocker-level criterion:
  - `execution-first-verification`
  - `spec/success-criteria/execution-first-verification.md`
- registry and discovery updates:
  - `config/success-criteria/registry.json`
  - `config/success-criteria/skill-map.json`
  - `spec/success-criteria/index.md`
- evaluator enforcement:
  - `services/success_criteria.py` infers runtime-risk triggers and blocks triggered changes with no execution evidence
  - `hook-stop.py` passes recorded Bash/RTK command evidence into success criteria evaluation
- repo agent contract:
  - `AGENTS.md` now includes the Execution-First Verification rule

The `aios-ui` root layout now suppresses hydration warnings on the root `<html>` element so browser-extension-injected root attributes do not surface as app hydration errors during local development.

The knowledge and topic-graph freshness labels now share one formatter. Routine 8-44 day-old records display as `Updated N days ago`; the stronger `Stale for N days` label is reserved for records 45+ days old.

Phase 1a prompt library baseline is now implemented:

- prompt template source-of-truth tree:
  - `prompts/README.md`
  - `prompts/research.md`
  - `prompts/summarization.md`
  - `prompts/coding_debug.md`
  - `prompts/content_writing.md`
  - `prompts/reasoning.md`
  - `prompts/evals/*/cases.md`
- prompt validation/index generation:
  - `bin/validate-prompts.py`
  - generated registry: `prompts/registry.json`
- vault + DB sync path:
  - `bin/sync-prompts.py`
  - updates `prompt_library_links` using body-hash linkage
- hook integration:
  - `hook-prompt-submit.py` now resolves best template by classification + tag overlap and injects compact hint context
- test coverage:
  - `tests/test_validate_prompts.py`
  - `tests/test_hook_prompt_submit.py`
  - fixture set: `tests/fixtures/prompts/*.md`
- phase architecture note:
  - `docs/architecture/2026-04-23-aios-prompt-library-phase1.md`

Prompt library visibility is now implemented in the UI:

- `/prompts` includes a first-class Prompt Library section backed by `prompts/registry.json`
- prompt template cards expose template name, classification, tags, required inputs, version, update date, and source file
- prompt templates must now be backed by `prompt_library_links` body-hash evidence before the UI or prompt-submit hook surfaces them; registry-only starter templates are hidden
- raw recent prompt history is intentionally hidden from the main `/prompts` surface
- mined prompt/pattern rows are intentionally hidden from `/prompts`; repetition alone is not evidence that a prompt is a reusable library asset
- raw prompt text is no longer written to `patterns`; prompt reuse belongs in the curated prompt library, not the general pattern/rule system

Experiment test repo visibility is now implemented:

- canonical registry:
  - `config/experiments/test-repos.json`
- local git repo workspaces:
  - `staging/experiment-test-repos/clean-small-app`
  - `staging/experiment-test-repos/messy-monorepo`
  - `staging/experiment-test-repos/backend-heavy-service`
  - `staging/experiment-test-repos/weak-tests-ui`
- `/compare` now shows the registered test repos, readiness, purpose, profile, setup, and path before experiment run history
- the local repo workspaces live under ignored `staging/` so they can be mutated during experiments without polluting the AIOS control-plane repository

Phase 1b anti-slop ESLint ratchet is now implemented on top of existing plugin wiring:

- anti-slop fixture lint lane:
  - `aios-ui/eslint/anti-slop-fixtures.config.mjs`
  - `aios-ui/eslint/fixtures/anti-slop/pass/**`
  - `npm --prefix aios-ui run lint:anti-slop:fixtures`
- architecture-enforcement profile metadata:
  - `config/architecture-enforcement/profiles.json` now includes `anti-slop-fixtures` adapter for `ts-nextjs-v1`
- CI quality wiring:
  - `.github/workflows/aios-ui-quality.yml`
  - runs `lint`, `lint:architecture`, and `lint:anti-slop:fixtures` for `aios-ui`
- ratchet docs + rollout guidance:
  - `docs/architecture/2026-04-23-anti-slop-eslint-ratchet.md`

Phase 1c improvement engine audit (audit-only) is complete:

- decision-quality audit memo:
  - `docs/architecture/2026-04-23-aios-improvement-engine-audit.md`
- scored seven capability areas against ideal target architecture:
  - scheduled experimentation infrastructure
  - prompt experimentation
  - rule experimentation
  - evaluation system
  - improvement loop integrity
  - operational architecture
  - cost/speed/complexity tradeoffs
- recommendation selected for downstream planning:
  - hybrid path (deterministic cron gates + selective qualitative judgment)
- explicit "Brutal Truth" section delivered per spec requirements.

Phase 2a workflow orchestration baseline is now implemented:

- typed workflow + skill registry is now first-class:
  - `config/workflows/registry.json`
  - `config/workflows/skills.json`
- deterministic workflow execution engine:
  - `services/workflow_orchestration.py`
  - explicit stage model execution with contract validation
- reference workflow vertical slice delivered:
  - `academic_paper_v1`
  - stages: parse -> normalize -> enrich -> generate -> transform -> validate -> finalize
  - explicit humanizer contract enforcement via meaning-preservation validation gate
- workflow execution reporting is now durable:
  - `workflow_execution_reports` table (runtime + canonical schema files)
  - report artifacts: `logs/control-plane/workflow-reports/<invocation-id>.json`
  - managed runtime writes `workflow-execution-report` artifacts and links them to run/invocation state
- managed runtime integration:
  - `bin/aios-managed-run.py` now executes workflow pipelines, records execution reports, and includes workflow summary linkage in invocation report metadata
- metadata observability:
  - `aios metadata --json` now includes workflow registry summary and latest execution report pointer
- phase architecture note:
  - `docs/architecture/2026-04-23-aios-workflow-orchestration-phase2a.md`

Phase 2b prompt library phase 2 (execution strategies) is now implemented as a hybrid baseline:

- canonical task-spec registry:
  - `config/execution-strategies/task-specs.json`
- surface strategy bundles:
  - `config/execution-strategies/strategies.json`
  - seeded first-slice task family: `audit_and_implement`
  - includes one validated strategy for each required surface:
    - `audit_and_implement_claude_v1`
    - `audit_and_implement_codex_v1`
- deterministic compiler/selector:
  - `services/execution_strategy.py`
  - selects strategy by `task_family + surface`, compiles constraints/contracts/rubric into execution instructions
- validation and generated selection registry:
  - `bin/validate-execution-strategies.py`
  - `config/execution-strategies/registry.json`
- runtime integration:
  - workflow normalization now attaches execution strategy bundles for implementation workflows
  - managed runtime maps backend to strategy surface (`claude_code` vs `codex`)
- metadata observability:
  - `aios metadata --json` now includes execution strategy coverage summary
- phase architecture note:
  - `docs/architecture/2026-04-23-aios-prompt-library-phase2.md`

Phase 3a AIOS UI command center MVP is now implemented:

- command-center homepage (`aios-ui/app/page.tsx`) now provides source-backed situational awareness for:
  - system health
  - active/failing/stale run signals
  - approvals/interventions inbox
  - unified change timeline (runs, approvals, changes, experiments)
- shared status/provenance model added:
  - `aios-ui/lib/status-provenance.ts`
  - explicit states: `confirmed`, `inferred`, `stale`, `missing`
- reusable provenance UI primitive added:
  - `aios-ui/components/primitives/ProvenanceBadge.tsx`
- control-plane observability upgraded with provenance badges:
  - `aios-ui/components/control/ControlPlaneStudio.tsx`
  - run history, run detail, and approval queue now expose status confidence + source metadata
- command-center IA/navigation labels updated:
  - `aios-ui/lib/constants.ts`
  - `aios-ui/components/layout/TopBar.tsx`
- command-center docs delivered per spec:
  - `docs/aios-ui-command-center-audit.md`
  - `docs/aios-ui-command-center-implementation-plan.md`
  - `docs/aios-ui-command-center-handoff.md`

Phase 3b Standards Delta / Project Health is now implemented:

- standards are now first-class AIOS registry objects:
  - `config/standards/registry.json`
  - fields include domain, weight, severity, evaluation method, remediation playbook, applicability, versioning, and waiver policy metadata
- standards-health scoring engine and persistence:
  - `services/standards_health.py`
  - explainable penalty model with explicit handling for:
    - `pass`
    - `partial`
    - `fail`
    - `unknown`
    - `regressed fail`
    - `waived`
    - `not_applicable`
- durable governance/remediation tables are now live:
  - `standards_profiles`
  - `standards_definitions`
  - `project_standards_profiles`
  - `standards_assessments`
  - `standards_delta_items`
  - `standards_backfill_tasks`
  - `standards_health_snapshots`
- runtime integration:
  - `hook-stop.py` now records standards-health snapshots after session close
  - each run writes deltas and Taski-traceable backfill tasks
- metadata observability:
  - `aios metadata --json` now includes standards registry summary + latest health snapshot
- Taski/UI health surfaces:
  - `aios-ui/server/aios/standards-health.ts`
  - `aios-ui/components/projects/TaskiProjectSurface.tsx` now renders:
    - health header
    - domain breakdown
    - delta matrix
    - prioritized backfill lane
    - standards migration view
  - `aios-ui/app/projects/page.tsx` now shows per-project health score, critical deltas, unknown coverage, and score trend
- quality pipeline surfaces:
  - `config/quality-pipeline.json` defines the portable linked-project gate model with three tiers:
    - Tier 1 Core: frozen install, lint, typecheck where applicable, tests, build where applicable, architecture boundary, CI gate
    - Production App: secret scan, env validation, dependency security, coverage, E2E smoke
    - Domain Specific: SEO/Lighthouse, telemetry utility, database restore/PITR, mobile release, full release E2E
  - `quality_pipeline_runs` records durable per-project gate results with evidence and source metadata
  - `services/quality_pipeline.py` and `aios-ui/server/aios/quality-pipeline.ts` resolve generated AIOS project IDs to stable repo slugs/names
  - `services/project_inventory.py` and `bin/sync-project-inventory.py` sync Git repositories from `~/projects` into the Taski `projects` table; Taski project inventory is the source of truth
  - unconfigured Taski projects now receive inferred Tier 1 gates from their repo path, lockfile/package metadata, package scripts, architecture script, and workflow directory
  - `soundscape-app` is the gold-profile implementation with core, production, public-web, telemetry, database, and mobile gates; other projects inherit only applicable gates instead of Soundscape-specific requirements
  - the Projects index now shows per-project pipeline coverage/status, and Taski project detail now includes a first-class Quality Pipeline panel with tier coverage
- workflow synthesis loop:
  - `bin/extract-patterns.py` now mines workflow candidates from repeated session traces (prompt classifications + post-tool event counts) instead of low-value handoff verbs
  - `bin/aios-pipeline.py` runs general pattern extraction before scoring and workflow synthesis so captured sessions can become proposal evidence
  - `services/workflow_synthesis.py` turns high-confidence prompt/workflow patterns into reviewable workflow proposals with generated workflow specs, skill specs, and validation plans
  - generated workflow executor skills now run through `learned_workflow_executor_v1` instead of being display-only registry entries
  - generated workflow best practices are not populated from static archetype text; they are gated on test-repo experiment evidence
  - workflow skill experiments are queued across the four registered test repos before promotion, with generated paper fixtures available for humanizer experiments
  - `bin/run-workflow-skill-experiments.py` runs queued workflow-skill experiments without an LLM agent, creates test-repo experiment branches, compares candidate workflows against a loose workflow baseline plus a no-skill ablation, runs repo-specific validation commands with a Python test-file fallback when pytest is unavailable, records repo/workflow fit in baseline/candidate scores, and only marks candidates promotion-ready when validation passes
  - `bin/aios-pipeline.py` now consumes queued workflow-skill experiments after synthesis as a normal automation phase
  - synthesis now also backfills reviewable proposals from the resolved Obsidian vault by clustering markdown workflow signals into archetype-level proposals; one-note vault backfill proposals are treated as too granular and are no longer generated
  - `workflow_synthesis_proposals` stores pending/approved workflow candidates with source pattern evidence
  - `bin/synthesize-workflows.py` creates pending proposals from DB patterns plus vault notes by default, supports `--no-vault`, and can explicitly approve a proposal into `config/workflows/registry.json` + `config/workflows/skills.json`
  - `/workflows` now surfaces pending workflow synthesis proposals with status, source evidence, and created timestamp alongside registered workflow metrics
  - proposal rows are review queue items only; `/workflows/[id]` routes are reserved for approved workflows from `config/workflows/registry.json`
  - `bin/aios-pipeline.py` now runs workflow synthesis as a recurring pipeline phase so repeated successful patterns are continually surfaced for approval
- phase architecture note:
  - `docs/architecture/2026-04-23-aios-standards-delta-health-phase3b.md`

RTK context compression is now integrated as an AIOS system primitive:

- unified command interface:
  - `services/rtk_integration.py`
  - `bin/rtk-run.py`
  - `rtk_run(command, mode)` with `compressed`, `raw`, and `adaptive` modes
- compression rules and context waste map:
  - `config/rtk/rules.json`
  - `docs/architecture/2026-04-27-aios-rtk-context-compression.md`
- lifecycle hook integration:
  - `hook-session-start.py` creates RTK schema and injects active compression policy
  - prompt, focus, and stop hooks now recover a missing session row from the current hook payload when `SessionStart` was not observed, so lifecycle events are captured instead of dropped as unknown sessions
  - `hook-stop.py` treats empty stdin as a recoverable lifecycle edge by falling back to `logs/current_session` before closing or skipping an already closed session
  - hook lifecycle recovery has focused regression coverage for prompt-submit recovery, stop recovery, and empty-stdin stop fallback against real hook entrypoints
  - `hook-post-tool-use.py` compresses Bash tool responses, records telemetry, and surfaces compact output
  - `hook-stop.py` logs per-session RTK savings in Stop event metadata
- workflow/runtime integration:
  - `bin/aios-pipeline.py` routes managed subprocess output through RTK adaptive mode
  - workflow execution reports include RTK policy metadata for implementation and failure-recovery workflows
- telemetry and UI:
  - `rtk_compression_events` records raw/compressed token estimates, reductions, ambiguous failures, raw tee paths, and workflow keys
  - `workflow_metrics` receives RTK token metrics for existing efficiency comparisons
  - `aios metadata --json` and `aios --json rtk` expose RTK rules and metrics
  - `/costs` now surfaces RTK tokens saved, reduction percent, ambiguous failures, and savings by workflow

The wiki/DeepWiki-style knowledge layer now has a minimum maintenance contract for agent use:

- wiki/context pages are treated as compressed maps and task-briefing inputs, not as replacements for repo files, docs, tests, validation scripts, or durable project truth
- `aios-ui/server/aios/wiki-maintenance.ts` defines maintenance metadata, page status labels, confidence labels, typed source refs, source coverage, stale-area tracking, a 0-5 maintenance score, and compact agent packet generation
- `/knowledge` pages now expose maintenance status, confidence, score, source references, known stale areas, related pages, and an agent packet checklist next to existing relationships/backlinks
- `config/wiki-maintenance/critical-pages.json` tracks source refs for the built-in system wiki pages that are otherwise assembled from code
- `pnpm wiki:check` runs `tools/wiki-check.mjs` to validate critical source refs, flag current pages without refs, warn on missing validation timestamps, and check referenced `pnpm` commands against package scripts
- `docs/wiki-maintenance.md` documents the post-task wiki/project-truth checklist agents should apply after meaningful work
- high-risk context routes now have explicit maintenance metadata and source refs: `context.index`, `context.router`, `context.schema`, `handoffs.latest`, `features.context-compiler`, `domains.knowledge-systems`, `packets.knowledge.obsidian-routing`, `packets.workflow.approval-gates`, `packets.ui.command-center`, and `projects.aios-ui`
- `pnpm wiki:check` also validates personal corpus refs against `aios.db` when present, including patterns, sessions, orchestration/divergent runs, briefing packets, memory updates, knowledge topics, vault notes, imported conversations, agent summaries, and task/writeback records
- remaining gap: lower-risk legacy context files and vault wiki pages still need explicit `wiki_status`, `source_refs`, and validation metadata before they can be scored as agent-usable or verified

## Still Missing

- more than one production-grade invocation backend beyond the new managed local runtime
- richer backend adapters for external/manual agent sessions so they emit the same handshake without fallback
- broader evaluator rule coverage and explicit finding resolution workflows
- deeper packet/result inspection at file/topic delta level
- richer Taski operator controls beyond summary, approvals, run/evaluator inspection, and standards backfill visibility
- legacy heuristic run matching still exists only as a fallback for older sessions that lack explicit handshake metadata
- linked-project profile ratchet completion (`BidCamp`, `soundscape-app`, `Terrace`, `portfolio`) so each has native profile config + CI wiring in-repo

## Spec Roadmap Corrections On 2026-04-23

The spec execution roadmap has been corrected before execution:

- The roadmap now treats AIOS as the global orchestration/control layer for all linked development projects. This repo is the implementation home and first self-check target, not the whole scope.
- Anti-Slop ESLint is now treated as an existing integration to audit and ratchet, not a greenfield build.
- Workflow orchestration must extend the existing control-plane primitives instead of recreating them.
- Phase 0 is serial by default because architecture enforcement, agent CLI surfaces, and success criteria share scripts, hooks, docs, and runtime contracts.
- Prompt Library Phase 1 uses the schema in `2026-04-08-prompt-library-design.md` as canonical.
- Agent Workflow CLI work must honor the hard checkpoint before implementation.
- Success criteria own judging rubrics; Standards Delta owns project health scoring and remediation.
- Prompt Library Phase 2 is scoped by the Improvement Engine audit rather than requiring full replay/shadow/canary infrastructure up front.
- UI Command Center now has an explicit MVP gate before the broader ten-surface target.

## Guardrails

- SQLite remains authoritative for machine-readable operational state
- Vault remains authoritative for curated human-readable knowledge
- staging remains non-canonical
- AIOS should prefer explicit inspectable pipelines over hidden prompt behavior
- default agent context policy is locked:
  - broad retrieval may happen inside AIOS
  - only compact ranked output reaches the agent by default
  - targeted expansion must be explicit and traced

## 2026-06-23 - Soundscape test-quality gate subprocess hardening

- Updated the AIOS-controlled Soundscape `test_quality` gate commands to invoke TypeScript scripts through `pnpm exec node --import tsx ...` instead of package-script `tsx` entrypoints.
- Rationale: AIOS captures gate subprocess output, and direct `tsx` CLI entrypoints attempted to open an IPC pipe that fails in the managed sandbox; the `node --import tsx` form preserves the vetted argv allowlist while avoiding that pipe.
- Verification: `python3 /Users/jakyeamos/AIOS/bin/aios.py --json gate run test_quality --project soundscape-app --repo-root /Users/jakyeamos/projects/soundscape-app` passed.

## 2026-06-23 - TMCP behavior-atom compiler controls

- Added tracked TMCP behavior-atom and golden-prompt registries under `config/tmcp/` so graph generation, packet quality tests, and future evals share the same expected behavior vocabulary.
- Extended TMCP runtime receipts with actionable feedback updates, node/behavior-atom token ROI summaries, missed-requirement repair recommendations, semantic source-skill section extraction, and packet explanation payloads.
- Added `aios tmcp explain`, `aios tmcp learning-summary`, and `aios tmcp receipt-feedback` for local inspection and learning-loop operation.
- Added `tmcp_behavior_optimized` as a benchmark condition between flat skill loading and validated shortcuts, with regression coverage for token-load comparison.
- Verification: focused TMCP runtime/harvest/benchmark tests passed, managed-runtime TMCP smoke tests passed, focused Ruff passed, context validation passed, and canonical graph verification passed against the 99-skill local graph.

## 2026-06-23 - TMCP packet adherence and claim discipline

- Added packet-adherence evaluation so TMCP can distinguish router failure from agent compliance failure when a packet required behavior atom is not observed in the final run.
- Added granular TMCP receipt events and intervention audit events for packet compilation, node selection, observed actions, ignored required behavior, validation commands, blockers, reruns, scope reductions, and related quality interventions.
- Added phase-aware and domain-aware packet compilation, negative golden prompt fixtures, TMCP packet diffing, shortcut lifecycle governance recommendations, and a benchmark claim gate that blocks TMCP improvement claims unless quality, token, shortcut-separation, and missed-requirement criteria pass.
- Verification: focused TMCP runtime/harvest/benchmark tests passed, managed-runtime TMCP smoke tests passed, focused Ruff passed, context validation passed, JSON validation passed, and canonical graph verification passed.

## 2026-06-24 - Phase 24 production web gate evidence

- Added real local production-web gate surfaces in `portfolio`, `dispatches-from-cyberspace`, `Bballedu`, and `tm`, then registered matching commands in AIOS quality-pipeline and quality-gate config.
- Recorded fresh local evidence for every attempted gate in those four repos and updated the linked-repo adoption audit with pass/fail evidence IDs.
- Current truth: all four repos remain blocked. `portfolio` still needs local CI, coverage, SEO, full e2e, and Pre-CR proof; `dispatches-from-cyberspace`, `Bballedu`, and `tm` still have failed gates plus architecture and local CI proof gaps.

## 2026-06-24 - Phase 24 targeted production app evidence

- Resolved package-manager ambiguity for `remodelvision` and `amos-saas` by making pnpm the explicit package contract and removing the competing npm lockfile in both linked repos.
- Added local validation scripts and AIOS workflow files, then registered matching AIOS quality-pipeline commands.
- Current truth: both repos remain blocked. `remodelvision` passes install and repo-truth evidence only; `amos-saas` passes install, tests, secret scan, static smoke, and repo-truth evidence, but still fails or lacks other required production-web proof.

## 2026-06-24 - Phase 24 developer-tool evidence

- Added developer-tool secret scan and dependency-security gates for `Terrace`, `pre-cr-suite-lsp`, and `eslint-plugin-anti-slop`, then registered the matching commands in AIOS quality-pipeline and quality-gate config.
- Updated the quality-pipeline standard so `secret_scan` and `dependency_security` apply to `developer_tool` projects, making package/tool security evidence visible in readiness reports.
- `video-pipeline` is deprecated and excluded from Phase 24 readiness targeting alongside `agent-router`; the failed local readiness migration attempt was reverted and no readiness claim is made for that repo.
- Current truth: all three active developer-tool repos in Plan 24-05 remain blocked on architecture, local CI proof, and repo-specific failing or missing gates.

## 2026-06-24 - Phase 24 structured repo evidence

- Registered class-specific structure, secret scan, dependency, and validation gates for `LIS`, `career-ops`, `Dsci-proj`, and `Fantasy` using AIOS-owned quality-pipeline commands.
- `Fantasy` now uses aggregate backend/frontend install, test, and validation commands instead of backend-only proof.
- `Dsci-proj` keeps npm as the dashboard subproject package manager because `apps/dashboard/package-lock.json` is the checked-in lockfile; no pnpm migration was introduced.
- Current truth: all four Plan 24-06 repos remain blocked. `LIS`, `career-ops`, `Dsci-proj`, and `Fantasy` have recorded pass/fail evidence, but failed local gates and local CI proof still prevent readiness.

## 2026-06-24 - Phase 24 floor-replacement repo evidence

- Replaced floor-style validation for `claude-improvement-lab`, `R-Project`, and `csds391-s26-6` with bounded class-specific AIOS quality-pipeline gates.
- Recorded evidence for runnable validation, structure, secret scan, dependency, repo-truth, and Pre-CR gates without changing external repo files.
- Current truth: the three active Plan 24-07 repos remain blocked. `manga-sync` is deprecated and excluded from readiness targeting.

## 2026-06-24 - Phase 24 content/container evidence

- Added `scripts/content-container-validator.py` for AIOS-owned Vaults and BBDSE validation.
- Documented the Vaults validation contract in external commit `26e38ed` and BBDSE child-project ownership in external commit `ffd3b4c`.
- `Vaults` now has evidence for content/vault validation, but remains blocked on failing validator, secret scan, Pre-CR, and local CI proof.
- `BBDSE` now has child ownership documentation and aggregate delegated validation evidence across all child repos, including LIS, but remains blocked on failing delegated child Pre-CR evidence and local CI proof.

## 2026-06-24 - Phase 24 CI exception decision

- Non-remote CI exceptions are approved for Phase 24 after the user clarified that GitHub Actions credits are constrained across the linked repository portfolio.
- `config/quality-pipeline.json` now records `non_remote_ci_exception` metadata for all 20 in-scope repos with local proof commands that write to `quality_pipeline_runs.ci`.
- Current truth: all 20 Phase 24 in-scope repos remain blocked until their local replacement `ci` gate passes, and `video-pipeline`, `manga-sync`, plus `agent-router` remain excluded.
- Production-app `env_validation` is warning-level evidence; missing local environment values no longer block readiness by themselves.

## 2026-06-24 - Phase 24 final linked-repo readiness ledger

- Closed Phase 24 with `.planning/phases/24-rectify-linked-repo-aios-readiness-blockers-except-agent-router/24-VERIFICATION.md`.
- Final Phase 24 scope is 20 in-scope repositories, with `agent-router` excluded by original scope and `video-pipeline` plus `manga-sync` excluded because the user clarified both are deprecated.
- Final verdict distribution remains 0 ready, 0 evidence-required, 20 blocked, and 3 excluded; no linked repo should be represented as adoption-ready from Phase 24 evidence.
- Local CI replacement proof is allowed for the 20 in-scope repos, but it is not a CI skip: each repo still needs a passing recorded `ci` run before readiness can clear.
- Copied and live `prove-project-health --all-inventory` both recorded 23 snapshots with 0 missing-source and 0 missing-inventory rows.
- Fixed the Phase 24 readiness-report placeholder-row regression in commit `7f9516e5`; report generation now keeps project inventory read-only except for table creation.

## 2026-06-24 - Phase 24 local CI setup and failure ledger

- Added `scripts/linked-repo-ci-local-proof.py` and updated `scripts/linked-repo-quality-runner.py` so approved non-remote `ci` gates execute local replacement proof instead of workflow YAML paths.
- Updated quality-pipeline evaluation to honor `standard.classes[*].required_gates`; class contracts now decide blocker status, while non-class global gates remain visible without creating false blockers.
- Filled missing runnable commands for required architecture/lint/Pre-CR/local-proof gates across the 20 in-scope repos.
- Corrected the remaining AIOS setup gap by adding platform `secret_scan` and `dependency_security` commands, then added a regression test proving every Phase 24 in-scope required gate has a configured command and every required `ci` gate has local proof metadata.
- Current truth: all 20 repos remain blocked, but setup is complete for execution. The report has 0 unconfigured required gates; remaining failures are recorded in `24-VERIFICATION.md` and should be cleared repo by repo.

## 2026-06-24 - Codex AIOS shadow route-blocked diagnostics

- Automatic Codex shadow setup no longer blocks baseline work when `start-work` returns `route-blocked`; it records a local JSONL diagnostic event and returns a non-blocking shadow payload instead.
- Explicit governed `/aios` routing still treats `route-blocked` as a blocker, preserving the governed workflow contract.
- Added `docs/diagnostics/route-blocked-failures.md` as the review guide for classifying route failures and deciding whether repeated failures should become workflow, prompt-route, or context-packet work.

## 2026-06-24 - TMCP design-source ingestion

- The portable dev-process TMCP visual-polish path now includes a required `saas_interaction_architecture` module distilled from the SaaS Design Bible so container choice, overlay behavior, tables, forms, loading, empty states, toasts, AI interaction structure, and primitive-layer decisions are routed before visual styling.
- The same path now has an optional `print_report_design` module distilled from the Treasurer's Report Design Bible for fixed-page reports, board packets, HTML-to-PDF rendering, financial number formatting, chart selection, and PDF fidelity checks.
- Product-specific visual identity remains opt-in: Tenure stays optional, and new BidCamp and Framework Labs branches are loaded only when the active project or user request selects those identities.

## 2026-06-24 - Workflow routing investigation vocabulary

- Added `investigate` and `investigation` as analysis-route evidence so route-blocked diagnostic objectives can select an audit workflow instead of failing with no governed workflow candidates.
- Verified the previously blocked route-blocked investigation objective now routes through the active `divergent-strategy` audit workflow.

## 2026-06-24 - Semantic workflow routing fallback

- Workflow routing now supports a semantic fallback after deterministic scoring fails to produce a viable unique workflow.
- The fallback is provider-neutral: callers may inject a semantic reasoner directly, or configure `AIOS_WORKFLOW_SEMANTIC_ROUTER_CMD` to run a local/model-backed JSON command.
- Semantic routes must name a registered workflow and meet the `0.75` confidence threshold; otherwise AIOS preserves the semantic recommendation as diagnostic evidence and keeps the governed route blocked.
- Added `docs/diagnostics/semantic-workflow-routing.md` with the command request/response schema and confidence-gate behavior.

## 2026-06-24 - Runtime-phase TMCP expansion

- Workflow execution now treats TMCP as a runtime-governed active packet, not only an invocation-start packet: stage phase changes recompile a phase-specific TMCP packet, persist a new traversal receipt, diff it against the prior packet, and record a `runtime_packet_expansion` intervention event.
- Expanded packets replace `run_state["tmcp_packet"]` for subsequent workflow stages, and workflow reports expose `tmcp_packet_expansions` plus per-stage `tmcp_expansion` evidence for operator inspection.
- Managed runtime packet artifacts now sync to the final active TMCP receipt while superseded initial receipts remain durable evidence, including cases where a promoted shortcut was used before phase-specific expansion.
- Verification: focused TMCP/workflow/orchestration suites passed (`97 passed`), focused Ruff passed, focused Basedpyright passed with 0 errors, and `pnpm context:validate` passed.

## 2026-07-01 - Automatic Codex shadow execution

- `scripts/codex-aios-shadow.py` now scores each created shadow lane and auto-launches headless `codex exec` only for good/excellent candidates, while blocked, small, dirty, unsafe, or unmeasurable tasks remain route-only evidence with a recorded skip reason.
- `services/shadow_codex_runner.py` owns the v1 execution backend: command construction, `workspace-write` sandboxing, `--ask-for-approval never`, JSONL/final-message artifact paths, detached launch metadata, status checks, and cancellation.
- `shadow_branch_runs` now records execution status, backend, pid, command, output paths, timestamps, and execution metadata; `aios shadow run/status/cancel` exposes those controls without promoting shadow output.
- Current truth: AIOS shadowing can now collect implementation evidence opportunistically during normal Codex work, but the baseline workspace remains the source of truth and shadow output must not be merged or copied back without explicit review.

## 2026-07-10 - Session-intel candidate helper adoption

- All current `pending_review` Codex session-intelligence candidates were implemented into telemetry-tracked helper-family records: 75 candidates across `artifact_probe`, `bespoke_review`, `doc_excerpt`, `git_history`, `repo_state`, and `workflow_skill`.
- Candidate implementation upserts now preserve an existing helper family's `telemetry_status` and `removal_status` instead of resetting active telemetry back to `awaiting_telemetry`.
- Current truth: the pending-review session-intel queue is empty, and all eight helper families remain `active` with `monitor` removal status.
