# Phase 11: Testing, Benchmark Evaluation, and Shadow Workflows — Research

**Gathered:** 2026-05-23
**Status:** Ready for planning

<source_spec>
## Source Architecture

Phase 11 is fully specified in the AIOS Testing & Benchmark Evaluation Design Spec (ingested 2026-05-23). The spec defines the complete evaluation system across eight rollout phases. Phase 10 Plans 07–08 delivered Phase 1 (Agent Eval Foundation). Phase 11 delivers Phases 2–8 of the rollout.

The design spec is the authoritative source for requirements, data models, evaluation logic, and completion gates. This research document extracts the implementation-ready findings needed to plan Phase 11 without re-deriving them from the spec.
</source_spec>

<domain>
## Phase Boundary

Phase 11 is the evaluation automation layer. It converts the docs, templates, and schemas from Phase 10 Plan 07–08 into running instrumentation. The deliverables are:

1. **Second Brain Eval Track** — gold-set context tests, retrieval logs, staleness detection, ablation variants
2. **Shadow Branch Testing** — start SHA capture, worktree creation, condition runner, diff + test comparison, scorecard output
3. **Feature Ablations** — disable-feature variants: no context packets, no second brain, no success criteria, no subagents, no model routing, no personal corpus, no project truth
4. **Peer Passive Trace** — observation-only trace mode with privacy-safe capture and shadow candidate detection
5. **Peer Automated Shadow Benchmark** — fully automated post-approval benchmark execution pipeline
6. **Portable Context Packets** — repo summary generator, task context packet generator, privacy filter
7. **External Harness Benchmarks** — SWE-bench-style and Terminal-Bench-style adapters, result normalization

Phase 11 does not build new domain features. It builds the measurement infrastructure that proves Phase 1–10 features create lift.
</domain>

<key_questions>
## Key Questions Resolved from Design Spec

### Q1: Where do eval run records live in the database?
Two new tables: `eval_tasks` and `eval_runs`. `eval_tasks` maps to the EvalTask TypedDict from config/agent-eval/eval-schemas.py. `eval_runs` maps to EvalRun. Schema column names use snake_case matching existing AIOS conventions.

### Q2: Where do shadow branches live?
Shadow branches follow the naming convention: `aios/eval/{task_id}/{condition}` (e.g., `aios/eval/soundscape-2026-05-21-feature-flag-audit/full-second-brain`). Worktrees are preferred over branches when the host repo supports them. Git SHA capture uses `git rev-parse HEAD` at task approval time.

### Q3: How does the peer trace capture work without modifying active workflow?
Peer trace mode is observation-only: it hooks into the existing AIOS stop hook (`bin/hook-session-stop.py`) and prompt-submit hook (`bin/hook-prompt-submit.py`) to capture metadata into the `peer_sessions` and `peer_traces` tables. It never writes to the active branch, never modifies files, and never injects prompts. The trace capture is controlled by `peerMode: "trace"` in a new `config/peer-eval/peer-trace-policy.json`.

### Q4: How does shadow candidate scoring work?
The `services/shadow_candidate_scorer.py` module reads from completed `peer_traces` rows, scores each detected task using the weighted formula (complexity 25% + measurability 20% + reproducibility 15% + AIOS relevance 15% + learning value 10% + safety 10% + benchmark coverage need 5%), and writes a `shadow_candidates` row with the score, recommendation tier, reasons, and blockers. Hard blockers (dirty repo, secrets risk, no start SHA, private external systems) set `automation_state = 'BLOCKED'` immediately.

### Q5: How does the peer approval → automation state machine work?
The state machine lives in `services/shadow_automation.py`. After in-person approval (human sets `automation_state = 'APPROVED_IN_PERSON'` via CLI command `aios shadow approve <candidate_id>`), the state machine advances through: SNAPSHOT_CREATED → SHADOW_BRANCH_CREATED → TASK_PACKET_GENERATED → AIOS_RUN_STARTED → VERIFICATION_STARTED → SCORING_STARTED → COMPARISON_REPORT_CREATED → BACKLOG_ITEMS_CREATED. Each transition is persisted to the `shadow_candidates` table before proceeding. Failures write `automation_state = 'BLOCKED'` with a reason.

### Q6: What does a portable context packet contain?
A portable context packet is a JSON file at `config/context-packets/{packet_id}.json` with fields matching the `portable-context-packet.md` template: packet_id, scope, task_summary, included_files (explicit list of repo-relative paths), detected_conventions (list of strings), test_commands (list), success_criteria_refs (list of paths), known_constraints (list), excluded_content_categories (explicit list), privacy_review_status, staleness_notes. A `services/portable_context_packet_generator.py` generates them from a task description + git history + detected conventions.

### Q7: How does the external benchmark adapter work?
The adapter is a thin shim in `services/external_benchmark_adapter.py` that translates AIOS eval tasks into the SWE-bench task format (repo, instance_id, problem_statement, base_commit) and Terminal-Bench task format (task_id, command, expected_exit_code). Results from external runs are normalized into `EvalRun` rows with `mode = 'external'` and `context_profile = 'external_clean_room'`.

### Q8: How do second brain ablations work?
Each ablation variant is a `config/agent-eval/ablation-policies/` JSON file that specifies which context sources to disable. The ablation runner in `services/ablation_runner.py` reads the policy, runs the task with context filtered accordingly, and writes an `EvalRun` with the ablation condition as the `condition` field. Baseline run and ablation runs share the same `task_id` so scorecard comparison is trivial.

### Q9: What are the new SQLite tables?
New tables (all in schema.sql):
- `eval_tasks` — matches EvalTask schema
- `eval_runs` — matches EvalRun schema
- `shadow_candidates` — matches ShadowCandidate schema with full 14-state + BLOCKED automaton_state enum
- `eval_scores` — matches EvalScore schema
- `eval_failures` — matches EvalFailure schema
- `peer_sessions` — anonymous peer session records
- `peer_traces` — per-task observations from peer passive trace mode
- `portable_context_packets` — metadata for generated packets (contents on disk in config/context-packets/)
- `eval_second_brain_retrievals` — per-task second-brain retrieval log for precision/recall/staleness metrics
- `eval_gold_set_tasks` — gold-set task definitions with known-required-context for second brain recall testing
</key_questions>

<decisions>
## Implementation Decisions

### Plan Sequencing
The seven rollout phases from the design spec map to seven Phase 11 plans in dependency order:

- **11-01** (wave 1): Database schema + base eval services (eval_tasks, eval_runs, eval_scores, eval_failures tables; EvalTaskService, EvalRunService, EvalScoreService)
- **11-02** (wave 2): Second Brain Eval Track (gold-set tasks, retrieval logs, staleness detection, ablation policies, second brain ablation runner)
- **11-03** (wave 2): Shadow Branch Testing (start SHA capture, worktree creation, condition runner, diff/test comparison, shadow branch scorecard)
- **11-04** (wave 3): Feature Ablations (ablation policy files for all seven ablation variants; ablation runner; ablation scorecard comparison)
- **11-05** (wave 3): Peer Passive Trace (peer trace config, anonymous session IDs, privacy-safe capture via existing hooks, shadow candidate detector, peer session CLI)
- **11-06** (wave 4): Peer Automated Shadow Benchmark (shadow automation state machine, candidate queue, approval CLI, automated worktree + run + verification + report + backlog)
- **11-07** (wave 5): Portable Context Packets + External Harness Benchmarks (packet generator, privacy filter, SWE-bench adapter, Terminal-Bench adapter, result normalization, UI surfaces for eval data on existing dashboard pages)

Plans 11-02 and 11-03 can run in parallel (wave 2). Plans 11-04 and 11-05 can run in parallel (wave 3).

### Database Migration Strategy
All new tables are additive. They follow the existing AIOS pattern: new CREATE TABLE blocks added to schema.sql with `IF NOT EXISTS`, applied by `bin/db-migrate.py` (or the existing migration pattern — verify during Plan 11-01 implementation). No existing tables are modified.

### Context Profile Enforcement
All eval services validate that `context_profile` is one of the six defined profiles before accepting an EvalTask or EvalRun. Second-brain context usage in a run labeled `peer_repo_only` or `external_clean_room` raises a `ContextProfileViolation` exception and logs the violation — it does not silently proceed.

### Peer Privacy Defaults
Peer trace captures only: session metadata, task category, workflow metrics, shadow candidate scores. Default `store_prompt_text: false`, `store_file_contents: false`, `store_full_diff: false`. Secret redaction is always on. Repo name is hashed by default. These defaults are in `config/peer-eval/peer-trace-policy.json` and cannot be overridden without explicit config edit.

### Shadow Branch Contamination Prevention
Shadow branches always use isolated worktrees (`git worktree add`). The automation state machine checks `git status --porcelain` in the peer's active working tree before proceeding; if the tree is dirty, it sets `automation_state = 'BLOCKED_DIRTY_REPO'` and does not proceed. Peer active branch is never written to.

### UI Integration
Phase 11 does not build new UI pages. Plan 11-07 adds eval data to the existing Phase 10 operator surfaces (Command Center, projects detail, runs detail) as optional panels — visible only when eval data exists for the run/project. This matches the Phase 10 degradation pattern.

### Claude's Discretion
- Exact SQL migration file naming and versioning — follow the existing migration pattern in bin/
- Internal caching strategy for second-brain retrieval logs — use the same approach as existing services
- Whether the ablation runner calls services directly or shells out to `aios` CLI — prefer direct service calls to avoid subprocess overhead
- Exact shadow branch comparison diff format — prefer standard `git diff --stat` output normalized to a simple changed-files count + test result delta
</decisions>

<requirements>
## Phase 11 Requirements

### EVAL-01: Eval Run Record Infrastructure
Every AIOS eval run must be recorded in a durable, queryable eval_runs table with context profile, condition, model, harness, result, cost, and failure labels. Eval tasks must be replayable from the recorded start SHA and accepted criteria.

### EVAL-02: Second Brain Evaluation Track
AIOS must be able to run the same task in full-second-brain mode and repo-only mode and compute Second Brain Lift (full minus repo-only score). AIOS must detect stale context retrievals and propose writebacks when second-brain content is outdated. Gold-set tasks must have known-required-context so recall can be measured deterministically.

### EVAL-03: Shadow Branch Testing
AIOS must be able to run a task from the same starting SHA on an isolated branch/worktree under a specified AIOS condition, then compare the result against a baseline using shared acceptance criteria, tests, lint, and typecheck. The baseline branch must never be contaminated.

### EVAL-04: Feature Ablation Runner
AIOS must be able to disable individual features (context packets, second brain, success criteria, subagents, model routing, personal corpus, project truth) and produce an EvalRun for each variant from the same starting SHA. Ablation scorecard comparison must identify which features contribute measurable lift.

### EVAL-05: Peer Passive Trace
AIOS must observe peer workflow sessions without modifying prompts, injecting context, spawning subagents, or changing model selection. Trace captures must be privacy-safe by default. Shadow candidate detection must automatically score each observed task.

### EVAL-06: Peer Automated Shadow Benchmark
After a shadow candidate is approved in person, AIOS must automatically execute the full benchmark pipeline: snapshot, isolated worktree, task packet generation, AIOS run, verification, scoring, comparison report, and backlog item creation for every failure. Peer active branch must remain untouched throughout.

### EVAL-07: Portable Context Packets
AIOS must be able to generate a portable context packet from a task description + repo structure that allows peer/core runs to access relevant context without requiring the personal second brain. Packets must explicitly exclude personal notes, private history, and secrets. Generated packets must be privacy-reviewed before use.

### EVAL-08: External Harness Benchmark Adapter
AIOS must be able to translate eval tasks into SWE-bench and Terminal-Bench compatible formats, run them against the external harness, and normalize results into EvalRun rows with context_profile = external_clean_room. This enables apples-to-apples comparison against public benchmarks.
</requirements>

<code_context>
## Existing Infrastructure to Extend

### Hooks (bin/)
- `bin/hook-session-stop.py` — captures session end metadata into aios.db; peer trace extends this with peer_session_id and context_profile fields
- `bin/hook-prompt-submit.py` — captures prompt metadata; peer trace adds passive observation fields

### Services
- `services/harness_eval.py` — deterministic fixture-backed eval (Phase 1 / harness layer); Phase 11 eval services are a sibling layer, not a replacement
- `services/standards_health.py` — evidence-backed health scoring; Phase 11 EvalScore consumes health domain scores as one input
- `services/workflow_learning.py` (Phase 9) — learning pattern detection; Phase 11 ablation runner can disable this source
- `services/capability_truth.py` — truth-backed capability queries; portable context packet generator reads capability truth to populate packets

### CLI (bin/aios.py / services/aios_cli.py)
- Existing subcommand pattern: `aios <noun> <verb>` with `--json` output flag
- Phase 11 adds: `aios eval record`, `aios eval score`, `aios shadow detect`, `aios shadow approve`, `aios shadow run`, `aios trace start`, `aios trace stop`, `aios packet generate`, `aios benchmark run`

### Database (schema.sql / data/aios.db)
- Existing migration pattern: additive CREATE TABLE IF NOT EXISTS blocks
- Phase 11 adds 9 new tables (see key_questions Q9)
- All new tables use snake_case column names, ISO timestamp strings, and nullable foreign keys following existing conventions

### Config
- `config/agent-eval/eval-schemas.py` — TypedDicts from Plan 10-07; Phase 11 services import these
- `config/agent-eval/ablation-policies/` — new directory for ablation policy JSON files
- `config/peer-eval/peer-trace-policy.json` — new peer trace configuration
- `config/context-packets/` — new directory for generated portable context packets

### aios-ui
- Phase 11 adds eval panels to existing pages (Command Center, project detail, run detail) as optional collapsible sections following the Phase 10 degradation pattern
- No new top-level pages required; eval data is surfaced inline where runs and projects are already displayed
</code_context>
