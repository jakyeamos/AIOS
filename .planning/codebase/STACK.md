---
last_mapped: 2026-05-13
last_mapped_commit: c8817f21
---

# AIOS Stack Map

## Scope

This document maps the implemented technology stack in `/Users/jakyeamos/AIOS` as of `2026-05-13`.
It focuses on concrete code and config in `package.json`, `pyproject.toml`, `uv.lock`, `schema.sql`, and `aios-ui/`.
Use this as a quick reference before changing runtime behavior, adding dependencies, or interpreting tooling assumptions.

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
  - root scripts in `package.json`
  - `tools/context-compile.mjs`
  - `scripts/aios-corpus-eval.cjs`
  - ESLint/config files such as `aios-ui/eslint.config.mjs`
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
  - `fastmcp` for the CTS MCP server in `services/cts/mcp_server.py`
  - `pypdf` in `bin/takeout-process.py`
  - `openpyxl` in `bin/takeout-process.py`
  - `python-pptx` via `from pptx import Presentation` in `bin/takeout-process.py`
  - `icalendar` in `bin/takeout-process.py`
  - `python-docx` in `bin/index-docx.py`
- Many root scripts intentionally stay on the Python standard library plus `sqlite3`, `subprocess`, and filesystem APIs.

## Node and Package Management

- Root JS package metadata is minimal in `package.json`.
- The root package defines four scripts:
  - `context:compile`
  - `context:validate`
  - `test:context`
  - `corpus:evaluate`
- The UI package is isolated in `aios-ui/package.json`.
- The repo standard is `pnpm`, and the UI lockfile is `aios-ui/pnpm-lock.yaml`.
- There is no top-level monorepo orchestrator file such as `pnpm-workspace.yaml` or `turbo.json` in the repo root.

## UI Runtime

- UI framework is Next.js `^16.0.0` in `aios-ui/package.json`.
- React runtime is `^19.0.0` with `react-dom` `^19.0.0`.
- TypeScript is `^5.7.3`.
- `aios-ui/next.config.ts` enables `reactStrictMode: true`.
- `aios-ui/tsconfig.json` uses:
  - `strict: true`
  - `target: ES2022`
  - `moduleResolution: bundler`
  - `jsx: react-jsx`
  - path alias `@/* -> ./*`
- `aios-ui/app/api/trpc/[trpc]/route.ts` exposes a tRPC route inside the Next app.

## UI Server/Data Frameworks

- tRPC v11 is used for the server boundary:
  - `@trpc/server`
  - `@trpc/client`
  - `@trpc/react-query`
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
  - `aios-ui/server/aios/runtime.ts`
  - `aios-ui/server/aios/control-plane.ts`
  - `aios-ui/server/aios/knowledge.ts`
  - `aios-ui/server/aios/topic-graph.ts`
  - `aios-ui/server/aios/context-compiler.ts`
  - `aios-ui/server/aios/quality-pipeline.ts`

## Linting, Type Checking, and Code Quality

- Root Python linting is Ruff via `pyproject.toml`.
- Root Python type checking is BasedPyright via `pyproject.toml`.
- Dead-code scanning is configured through Vulture in `pyproject.toml`.
- UI linting uses ESLint `^9.19.0` and `eslint-config-next` `^16.0.0`.
- Architecture constraints are enforced with `dependency-cruiser` in `aios-ui/package.json`.
- Custom UI copy/client-component rules come from local package `eslint-plugin-anti-slop` referenced as `file:../../projects/eslint-plugin-anti-slop`.
- `aios-ui/eslint.config.mjs` enables anti-slop rules such as:
  - `no-unjustified-use-client`
  - `no-placeholder-copy`
  - `no-demo-data-primary-path`

## Testing

- Python tests live in `tests/` and are run with `uv run pytest -q` per `README.md`.
- Node’s built-in test runner is used for `tests/context-compiler.test.mjs`.
- The UI lint script also runs `tsc --noEmit`, making typecheck part of the default UI quality gate.
- The documented local verification path in `README.md` is:
  - `uv run pytest -q`
  - `pnpm lint`
  - `pnpm lint:warning-baseline`
  - `pnpm lint:architecture`
  - `pnpm lint:anti-slop:fixtures`
  - `pnpm build`

## Config and Registry Files

- Runtime and policy configuration is file-backed, not centralized in one application config service.
- Important config surfaces include:
  - `config/rtk/rules.json`
  - `config/workflows/registry.json`
  - `config/workflows/skills.json`
  - `config/success-criteria/registry.json`
  - `config/success-criteria/skill-map.json`
  - `config/execution-strategies/*.json`
  - `config/architecture-enforcement/*.json`
  - `config/divergent-strategy/*.json`
- Context compiler source material is stored under:
  - `aios/context/standards/`
  - `aios/context/domains/`
  - `aios/context/features/`
  - `aios/context/packets/`

## Persistence Technologies

- The main operational datastore is SQLite, modeled in `schema.sql`.
- The UI connects to SQLite directly through `better-sqlite3` in `aios-ui/server/db.ts`.
- Python services connect through the stdlib `sqlite3` module across `bin/` and `services/`.
- CTS maintains separate per-repo SQLite graph stores under `~/AIOS/data/cts/`, described in `docs/STORES.md` and implemented in `services/cts/graph_store.py`.

## Runtime Entry Points

- CLI bootstrap is `bin/aios.py`, which forwards into `services/aios_cli.py`.
- Managed runtime orchestration entrypoints include:
  - `bin/aios-managed-run.py`
  - `bin/aios_orchestration_runtime.py`
  - `services/invocation_backends.py`
- Hook entrypoints include:
  - `bin/hook-session-start.py`
  - `bin/hook-prompt-submit.py`
  - `bin/hook-post-tool-use.py`
  - `bin/hook-stop.py`
  - `bin/hook-update-focus.py`

## Practical Takeaways

- AIOS is not a single-framework application; it is a local platform composed of Python automation plus a separate Next.js operator UI.
- SQLite is the shared runtime spine between Python services and the UI.
- Most stack decisions are encoded in repo files rather than environment-provisioned services.
- When changing behavior, check both root Python config and `aios-ui/` config because the system is intentionally split across two runtimes.
