---
title: AIOS Codebase Conventions
mapped_on: 2026-05-13
last_mapped_commit: c8817f21
---

# AIOS Conventions

## Scope

This reference summarizes the conventions visible in the current repository state at `c8817f21`. It is grounded in live files such as `AGENTS.md`, `PROJECT.md`, `README.md`, `pyproject.toml`, `package.json`, `aios-ui/package.json`, `aios-ui/tsconfig.json`, `aios-ui/eslint.config.mjs`, and `aios-ui/.dependency-cruiser.cjs`.

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
  - route/page modules stay lowercase in `aios-ui/app/.../page.tsx`
  - reusable React components are PascalCase in `aios-ui/components/...`
  - utility and server helper modules are kebab-free lowercase in `aios-ui/lib/*.ts` and `aios-ui/server/**/*.ts`
- React component exports are typically PascalCase functions, e.g. `PageShell`, `StatusBadge`, `GroundedQueryStudio`, and `TaskiProjectSurface`.
- Database helpers prefer imperative verb names like `getDb`, `tableExists`, `ensure_*_schema`, `evaluate_and_record`, and `run_*`.

## Architecture Rules

- The UI is App Router based in `aios-ui/app/` and defaults to server-rendered pages that call data through server helpers like `@/server/caller`.
- Client components are deliberately limited. Current `"use client"` usage is concentrated in interactive surfaces such as `aios-ui/app/providers.tsx`, `aios-ui/components/query/GroundedQueryStudio.tsx`, and chart/workflow components.
- `aios-ui/eslint.config.mjs` enforces `anti-slop/no-unjustified-use-client`, so adding client components requires a concrete reason.
- Import boundaries are machine-enforced in `aios-ui/.dependency-cruiser.cjs`:
  - `components/` must not import `server/`
  - `server/` must not import `app/` or `components/`
  - `lib/` must not import `app/` or `components/`
  - circular dependencies are forbidden
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
