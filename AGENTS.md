# AIOS Agent Workflow Contract

This repository uses AIOS-managed success criteria as a first-class completion gate.

## AIOS Context Compiler Bootloader

Before non-trivial execution, compile or follow the smallest sufficient context packet:

1. Classify the task.
2. Load `PROJECT.md` and the relevant context compiler receipt.
3. Load relevant global standards from `aios/context/standards/`.
4. Load relevant domain standards from `aios/context/domains/`.
5. Load selected feature/task packets from `aios/context/features/` and `aios/context/packets/`.
6. Produce or inspect a context receipt listing loaded and skipped context with reasons.
7. Execute against that compiled packet.
8. Update truth files or propose writebacks when state changes, rules are missing, context is stale, or a reusable pattern appears.

Never load every Markdown file by default. Never weaken global security, privacy, maintainability, testing, or observability standards with narrower project convenience. Never treat broad semantic search as equivalent to authoritative context selection.

Useful commands:

- `pnpm context:compile --task "Describe the concrete task"`
- `pnpm context:validate`

## Required Execution Flow

1. Resolve applicable criteria before implementation.
2. Keep criteria visible during execution (blockers vs warnings).
3. Evaluate final changed files against applicable criteria before completion.
4. Record blockers, warnings, passes, and accepted tradeoffs in durable artifacts.

## Rule: Orchestrated Sub-Agent Development

Prefer sub-agent-driven development for most non-trivial tasks. Use the orchestrator for task decomposition, routing, context control, supervision, quality gates, and final synthesis. Delegate execution to specialized subagents with the lowest-cost model tier and reasoning level likely to complete the task reliably.

Direct orchestrator execution is allowed when the task is simple and likely under 5-10 minutes, requires no repo-wide context, affects one small file or doc, is a pure explanation, small rewrite, or isolated command, or subagent setup would cost more than it saves.

Prefer sub-agent execution when the task requires repo inspection, multiple phases, architecture, tests, security, migrations, data models, multi-file changes, parallel research, isolated review, protection from context bloat, or would waste premium-model tokens if handled monolithically.

Routing defaults, role definitions, telemetry fields, benchmark classes, and promotion statuses live in `config/execution-strategies/model-routing-policy.json`.

## Rule: Execution-First Verification

Trigger this rule for:

- non-trivial side effects or state
- cross-system interactions
- core/shared logic modification
- debugging inconsistent behavior
- low trust in tests
- complex domain models

When triggered:

1. Run the exact code path being modified.
2. Call all relevant functions directly.
3. Reproduce real inputs, using mocks only when necessary.
4. Observe outputs, side effects, and state changes.
5. Only then propose or implement changes.

Do not rely solely on static reasoning in these cases.

## Rule: Subsystem Extraction Governance

AIOS is a monorepo incubator for local-first agent operating-system functionality. Do not split subsystems into packages or repos just because a feature area is large, and do not preserve overlapping subsystems just because they already exist. First prove whether the work should be consolidated, kept product-integrated, packaged, or repo-extracted based on stable contracts, clear data ownership, focused tests, independent reuse pressure, and coordination cost.

Use `.planning/SUBSYSTEM_EXTRACTION_PLAN.md` as the living boundary, consolidation, and extraction roadmap. Update it whenever work changes subsystem maturity, public contracts, storage ownership, overlap/consolidation posture, extraction posture, dependency direction, or the decision to keep a subsystem inside AIOS. Record the date, evidence, changed subsystem, and next decision point.

Every new roadmap phase must include a `Subsystem consolidation goal` entry and a `Subsystem extraction posture goal` entry. These entries must name the affected subsystem or state `none`, declare the target posture, identify any consolidation candidates, and explain what evidence would justify consolidating, keeping, packaging, or repo-extracting that subsystem after the phase.

## Agent Eval Workflow

Run this eval workflow after large tasks: PRD implementation, major refactors, test-suite generation, architecture changes, cross-file feature work, quality audits, shadow-branch comparisons, and peer-run benchmark candidates. Apply proportionality: small edits, typo fixes, narrow doc updates, and isolated one-file changes do not require a full eval record unless they affect success criteria, governance, security, privacy, or project truth.

Minimum eval checklist:

1. Re-read the original task, PRD, plan, or acceptance criteria before judging completion.
2. Identify the context profile: `jakye_second_brain_full`, `jakye_second_brain_limited`, `jakye_repo_only`, `peer_repo_only`, `peer_portable_context_packet`, or `external_clean_room`.
3. Check every acceptance criterion against current evidence.
4. Run the automated checks that match the changed surface, such as lint, typecheck, tests, build, architecture lint, or rendered/runtime verification.
5. Run maintainability checks for architecture boundaries, duplication, complexity, naming, typing, security, privacy, observability, and test adequacy.
6. Produce or update a backfill note when a hotspot, missing standard, failure record, or reusable lesson remains.
7. Separate completed work, failed checks, residual risks, and follow-ups instead of mixing them into one success claim.
8. Do not claim success if key checks failed unless the blocker is explicitly accepted and recorded.
9. Label failures using the AIOS failure taxonomy in `docs/evals/benchmark-eval-architecture.md`.
10. Label personalized local runs as non-portable when they use `jakye_second_brain_full` or `jakye_second_brain_limited`.

Anti-cheating rules:

1. Do not edit tests, fixtures, or acceptance criteria merely to make an implementation pass.
2. Do not skip verification and claim success from static reasoning alone.
3. Do not suppress command errors, logs, warnings, failed checks, or browser/runtime failures.
4. Do not claim completion when blocker-level criteria still fail.
5. Do not use private second-brain context in `peer_repo_only` or `external_clean_room` runs.
6. Do not contaminate peer or baseline branches with AIOS-only fixes before comparison.
7. Do not silently change the task scope after implementation.
8. Do not use a narrow check as proof of broad behavior.
9. Do not hide unresolved follow-ups that affect acceptance or quality.
10. Do not label personalized local wins as portable/core benchmark wins.

Portability label rule: any run using `jakye_second_brain_full` or `jakye_second_brain_limited` context must be labeled personalized/local, not portable/core. Use `docs/evals/benchmark-eval-architecture.md`, `docs/evals/context-profiles.md`, and `docs/evals/templates/major-task-eval.md` for the full eval vocabulary and record format.

## Runtime Sources of Truth

- Criteria registry: `config/success-criteria/registry.json`
- Skill mapping: `config/success-criteria/skill-map.json`
- Criteria docs index: `spec/success-criteria/index.md`
- Evaluator: `services/success_criteria.py`

## Hook Integration

- Session start (`bin/hook-session-start.py`) surfaces applicable criteria in startup packet.
- Session close (`bin/hook-stop.py`) evaluates criteria and persists findings.

## Storage Contract

- SQLite tables:
  - `success_criteria_evaluations`
  - `success_criteria_findings`
- JSON artifacts:
  - `data/success-criteria/evaluations/<evaluation-id>.json`

## Completion Requirement

Do not mark implementation complete when blocker-level criteria fail unless accepted tradeoffs are explicitly recorded in evaluation metadata.

## Deployment Completion Gate

When a task includes committing, pushing, shipping, or release preparation for changes that affect the Vercel app:

1. Run the normal quality ladder first.
2. Commit the changes before deployment.
3. Push the branch only when asked or when the task explicitly includes pushing.
4. After pushing or deploying, run one of:
   - `pnpm deploy:preview:watch`
   - `pnpm deploy:prod:watch`
5. Do not report the task as complete until Vercel returns a successful deployment.
6. If Vercel deployment fails, inspect the logs, fix the issue, rerun applicable checks, redeploy, and only then report completion.

Use `VERCEL_TOKEN` from the environment when non-interactive authentication is needed. Do not add static deployment tokens to repo files.

<!-- GSD:project-start source:PROJECT.md -->
## Project

**AIOS**

AIOS is a local-first, knowledge-aware agent operating system for AI-driven work. It acts as a second brain, orchestration layer, workflow harness, and quality-control system that turns vague goals into governed, context-rich, testable workflows, then learns from every run to improve future work.

The primary user is your agents. Over time, the project should become strong enough to open source, but its immediate purpose is to become the default operating layer you and your agents work through instead of manually assembling context, rules, workflows, and writebacks by hand.

**Core Value:** AIOS should compile messy human intent into the right context, standards, workflow, agent instructions, evaluation, artifacts, and memory updates with less manual babysitting than direct model use.

### Constraints

- **Local-first**: The system should run from local files, local stores, and local operator tooling — this is part of the product identity
- **Primary user**: The main user is your agents — workflows, packets, and handoffs must optimize for machine execution as much as human inspection
- **Governance**: Important changes to truth, standards, prompts, skills, and workflows should remain reviewable instead of silently becoming default behavior
- **Brownfield continuity**: Existing runtime, UI, context, and audit subsystems must be extended and unified rather than replaced with a disconnected rewrite
- **Explainability**: Health, drift, routing, and workflow decisions must remain drill-downable to explicit sources, reasoning, and remediation paths
- **Compounding memory**: Meaningful runs should leave the system more accurate and more reusable through reliable writebacks and lifecycle-managed learning
- **Open-source trajectory**: The project should eventually be legible and portable enough for external contributors, even though immediate use is personal and agent-centered
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Scope
## Repository Shape
- Root app and automation code is primarily Python in `bin/` and `services/`.
- The operator UI is a separate Next.js app in `aios-ui/`.
- Context compiler and policy content live as Markdown and JSON under `aios/context/` and `config/`.
- Persistent schema authority is checked into `schema.sql`.
- Tests are split between Python tests in `tests/*.py` and Node tests in `tests/context-compiler.test.mjs`.
## Languages
- Python is the main control-plane language across `bin/*.py` and `services/*.py`.
- TypeScript is the main UI and server language in `aios-ui/app/`, `aios-ui/server/`, and `aios-ui/lib/`.
- JavaScript exists in a limited supporting role:
- Shell is used for operator automation in files like `bin/init-db.sh`, `bin/health_check.sh`, and `bin/takeout-ingest.sh`.
- SQL is first-class via the checked-in schema in `schema.sql`.
## Python Runtime
- Root Python package metadata is in `pyproject.toml`.
- Required version is `>=3.12` from `pyproject.toml`.
- Ruff targets Python `3.12` in `pyproject.toml`.
- BasedPyright is configured for Python `3.12` over `bin`, `tests`, and `services`.
- The repo uses `uv` operationally, confirmed by `uv.lock` and commands in `README.md`.
## Python Dependency Posture
- The Python project is intentionally light at the metadata layer: `pyproject.toml` declares tooling but not an expanded dependency list.
- Locked Python dependencies are tracked in `uv.lock`.
- Several Python features rely on optional/import-at-runtime packages rather than hardcoded imports in `pyproject.toml`.
- Confirmed optional/runtime dependencies from source:
- Many root scripts intentionally stay on the Python standard library plus `sqlite3`, `subprocess`, and filesystem APIs.
## Node and Package Management
- Root JS package metadata is minimal in `package.json`.
- The root package defines four scripts:
- The UI package is isolated in `aios-ui/package.json`.
- The repo standard is `pnpm`, and the UI lockfile is `aios-ui/pnpm-lock.yaml`.
- There is no top-level monorepo orchestrator file such as `pnpm-workspace.yaml` or `turbo.json` in the repo root.
## UI Runtime
- UI framework is Next.js `^16.0.0` in `aios-ui/package.json`.
- React runtime is `^19.0.0` with `react-dom` `^19.0.0`.
- TypeScript is `^5.7.3`.
- `aios-ui/next.config.ts` enables `reactStrictMode: true`.
- `aios-ui/tsconfig.json` uses:
- `aios-ui/app/api/trpc/[trpc]/route.ts` exposes a tRPC route inside the Next app.
## UI Server/Data Frameworks
- tRPC v11 is used for the server boundary:
- React Query is provided by `@tanstack/react-query`.
- `superjson` is used as the tRPC transformer in `aios-ui/server/trpc.ts`.
- Runtime validation uses `zod`.
- `better-sqlite3` is the direct UI database adapter in `aios-ui/server/db.ts`.
- Charts use `recharts`.
- Graph/flow rendering uses `@xyflow/react`.
## UI Architecture Conventions
- App Router structure is used under `aios-ui/app/`.
- Server-side data access is colocated under `aios-ui/server/`.
- DB schema bootstrapping for UI-owned tables exists in `aios-ui/server/aios/schema.ts`.
- Router composition happens in `aios-ui/server/routers/_app.ts`.
- Domain-oriented server modules include:
## Linting, Type Checking, and Code Quality
- Root Python linting is Ruff via `pyproject.toml`.
- Root Python type checking is BasedPyright via `pyproject.toml`.
- Dead-code scanning is configured through Vulture in `pyproject.toml`.
- UI linting uses ESLint `^9.19.0` and `eslint-config-next` `^16.0.0`.
- Architecture constraints are enforced with `dependency-cruiser` in `aios-ui/package.json`.
- Custom UI copy/client-component rules come from local package `eslint-plugin-anti-slop` referenced as `file:../../projects/eslint-plugin-anti-slop`.
- `aios-ui/eslint.config.mjs` enables anti-slop rules such as:
## Testing
- Python tests live in `tests/` and are run with `uv run pytest -q` per `README.md`.
- Node’s built-in test runner is used for `tests/context-compiler.test.mjs`.
- The UI lint script also runs `tsc --noEmit`, making typecheck part of the default UI quality gate.
- The documented local verification path in `README.md` is:
## Config and Registry Files
- Runtime and policy configuration is file-backed, not centralized in one application config service.
- Important config surfaces include:
- Context compiler source material is stored under:
## Persistence Technologies
- The main operational datastore is SQLite, modeled in `schema.sql`.
- The UI connects to SQLite directly through `better-sqlite3` in `aios-ui/server/db.ts`.
- Python services connect through the stdlib `sqlite3` module across `bin/` and `services/`.
- CTS maintains separate per-repo SQLite graph stores under `~/AIOS/data/cts/`, described in `docs/STORES.md` and implemented in `services/cts/graph_store.py`.
## Runtime Entry Points
- CLI bootstrap is `bin/aios.py`, which forwards into `services/aios_cli.py`.
- Managed runtime orchestration entrypoints include:
- Hook entrypoints include:
## Practical Takeaways
- AIOS is not a single-framework application; it is a local platform composed of Python automation plus a separate Next.js operator UI.
- SQLite is the shared runtime spine between Python services and the UI.
- Most stack decisions are encoded in repo files rather than environment-provisioned services.
- When changing behavior, check both root Python config and `aios-ui/` config because the system is intentionally split across two runtimes.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Scope
## Repository Shape
- The repo is intentionally split across a Python operations/backend layer in `bin/` and `services/`, a Next.js UI in `aios-ui/`, and file-backed context/config/docs under `aios/`, `config/`, and `docs/`.
- Runtime state is primarily local-first and file-backed: SQLite in `data/aios.db`, logs in `logs/`, staged artifacts in `staging/`, and compiled context artifacts under `aios/context/`.
- Keep implementation aligned with the current truth file in `PROJECT.md`; it is treated as the durable narrative of what is actually shipped.
## Language And Typing Rules
- Python targets 3.12+ per `pyproject.toml`, while CI installs Python 3.14 in `.github/workflows/aios-python-quality.yml`.
- Python modules commonly enable postponed annotations with `from __future__ import annotations`.
- Python favors explicit return types on public helpers, e.g. `services/quality_pipeline.py`, `services/success_criteria.py`, and `services/rtk_integration.py`.
- TypeScript runs in strict mode in `aios-ui/tsconfig.json`.
- The UI uses the `@/*` import alias from `aios-ui/tsconfig.json` for internal imports such as `@/server/db` and `@/components/layout/PageShell`.
- Shared contracts are modeled explicitly with TypeScript types and Python `TypedDict` / `dataclass` structures rather than untyped dictionaries where stable shapes matter.
## Naming Patterns
- Python file and symbol names are snake_case, e.g. `services/workflow_experiments.py`, `ensure_quality_pipeline_schema`, and `load_skill_map`.
- TypeScript and TSX file names are mixed by role:
- React component exports are typically PascalCase functions, e.g. `PageShell`, `StatusBadge`, `GroundedQueryStudio`, and `TaskiProjectSurface`.
- Database helpers prefer imperative verb names like `getDb`, `tableExists`, `ensure_*_schema`, `evaluate_and_record`, and `run_*`.
## Architecture Rules
- The UI is App Router based in `aios-ui/app/` and defaults to server-rendered pages that call data through server helpers like `@/server/caller`.
- Client components are deliberately limited. Current `"use client"` usage is concentrated in interactive surfaces such as `aios-ui/app/providers.tsx`, `aios-ui/components/query/GroundedQueryStudio.tsx`, and chart/workflow components.
- `aios-ui/eslint.config.mjs` enforces `anti-slop/no-unjustified-use-client`, so adding client components requires a concrete reason.
- Import boundaries are machine-enforced in `aios-ui/.dependency-cruiser.cjs`:
- The backend side follows a similar layer mindset. `tests/test_architecture_enforcement.py` verifies Python import-boundary rules such as forbidding `services/` from importing `bin/`.
- SQLite is the dominant persistence mechanism. Python uses `sqlite3`; the UI server uses a singleton `better-sqlite3` connection in `aios-ui/server/db.ts`.
## Dependency Management
- Root JavaScript usage is minimal and uses `pnpm` scripts from `package.json` for context tooling such as `pnpm context:compile`, `pnpm context:validate`, and `pnpm test:context`.
- The UI package in `aios-ui/` is also operated locally with `pnpm`, per `README.md` and repo-wide defaults in `AGENTS.md`.
- Current repo state keeps both `aios-ui/pnpm-lock.yaml` and `aios-ui/package-lock.json`.
- CI for `aios-ui` still installs with `npm ci --prefix aios-ui` in `.github/workflows/aios-ui-quality.yml`, so local and CI package-manager behavior are not fully unified yet.
- Python dependencies are managed with `uv`, reflected by `uv sync` and `uv run pytest -q`.
## Workflow Conventions
- The repo expects a context-compilation boot sequence before non-trivial work. The contract is documented in `AGENTS.md` and implemented by `tools/context-compile.mjs`.
- Non-trivial work should load `PROJECT.md`, selected standards in `aios/context/standards/`, relevant domain/feature packets in `aios/context/domains/`, `aios/context/features/`, and `aios/context/packets/`, then validate or inspect the resulting receipt.
- Keep `main` deployable and prefer feature branches for non-trivial code changes, per `AGENTS.md` and `README.md`.
- Each logical implementation slice is expected to end in a coherent code commit followed by an immediate `PROJECT.md` truth-file update commit; this rule is repeated in `AGENTS.md` and `docs/superpowers/plans/tier-one-aios/EXECUTION.md`.
- Generated or operational artifacts under `logs/`, `staging/`, and local DB stores are not treated as source unless explicitly promoted.
## Style Conventions
- Python formatting is driven by Ruff settings in `pyproject.toml`; the configured line length is `100`.
- Ruff lint selection emphasizes correctness and simplification: `E`, `W`, `F`, `I`, `B`, `UP`, and `SIM`.
- Tests are allowed slightly looser Python linting via `pyproject.toml` per-file ignores for `tests/**`.
- TypeScript style is governed more by framework defaults and lint rules than by a standalone formatter config in the repo root.
- UI copy and interaction patterns are actively constrained by anti-slop rules in `aios-ui/eslint.config.mjs`, including bans on placeholder copy and demo-data-primary-path usage.
## Error Handling Patterns
- Python code tends to raise concrete built-ins for invalid inputs and missing resources, e.g. `ValueError`, `FileNotFoundError`, and `RuntimeError` in `bin/import_ai_history.py` and `services/workflow_experiments.py`.
- When malformed data is expected as an operational possibility, helpers often degrade safely instead of failing hard, e.g. `_json_list` in `services/quality_pipeline.py` and JSON parsing guards in `services/success_criteria.py`.
- SQLite and file-system edges are wrapped in narrow `try`/`except` blocks around the actual failure surface rather than blanket exception handling around whole modules.
- UI server code generally prefers typed returns and explicit nullability instead of exception-driven control flow, e.g. `tableExists` in `aios-ui/server/db.ts` and nullable lookup helpers across `aios-ui/server/aios/`.
- Operational hooks in `bin/hook-session-start.py` and `bin/hook-stop.py` tolerate partial failure and continue producing best-effort packets or evaluation records because they sit on critical session boundaries.
## Practical Do And Don’t
- Do preserve the Python/UI layering between `bin/`, `services/`, `aios-ui/server/`, `aios-ui/lib/`, `aios-ui/components/`, and `aios-ui/app/`.
- Do prefer explicit schemas and typed transport objects when data crosses process, DB, or UI boundaries.
- Do keep new UI code server-first and add `"use client"` only for real interaction needs.
- Do use `pnpm` locally for JavaScript work and `uv` for Python work.
- Don’t bypass the truth-file workflow around `PROJECT.md` for substantive implementation.
- Don’t add convenience imports that violate the architecture boundaries enforced by `aios-ui/.dependency-cruiser.cjs` or the Python architecture enforcement tests.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## System Pattern
- Python commands and hooks write durable state.
- JSON registries in `config/` define policies, workflows, experiments, criteria, and architecture rules.
- The UI in `aios-ui/` reads and explains that state rather than owning business logic.
## Major Layers
## Primary Entry Points
- CLI bootstrap starts at `bin/aios.py`, which imports `services/aios_cli.py`.
- Session lifecycle hooks enter through files such as `bin/hook-session-start.py`, `bin/hook-stop.py`, `bin/hook-prompt-submit.py`, and `bin/hook-post-tool-use.py`.
- Managed runtime flows enter through `bin/aios-managed-run.py` and `bin/aios_orchestration_runtime.py`.
- Context compilation enters through `tools/context-compile.mjs` and root scripts in `package.json`.
- UI requests enter via route files in `aios-ui/app/**/page.tsx`, then move into `aios-ui/server/routers/*.ts` and `aios-ui/server/aios/*.ts`.
## Data Flow
## Control-Plane Boundaries
## Key Abstractions
- Invocation backend contract: `services/invocation_backends.py` defines backend identities and the strict handshake fields expected of managed and legacy runtimes.
- Workflow and skill registries: `services/workflow_orchestration.py` loads `config/workflows/registry.json` and `config/workflows/skills.json` into typed workflow/stage/skill abstractions.
- Success criteria engine: `services/success_criteria.py` evaluates file and task outcomes against registry-defined criteria in `config/success-criteria/`.
- Trusted capability state: `services/capability_truth.py` and related UI contracts model confirmed, inferred, missing, and contradictory signals.
- Context packet model: `aios/context/` plus `tools/context-compile.mjs` implement deterministic selection, receipts, and writeback candidates.
- CTS repository registry: `services/cts/registry.py` maps AIOS projects to per-repo graph stores and isolates index storage from the main DB.
## Architectural Centers of Gravity
## Practical Reading Order
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
