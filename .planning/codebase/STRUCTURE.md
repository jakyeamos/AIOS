---
last_mapped: 2026-05-13
last_mapped_commit: c8817f21
---

# AIOS Structure Map

## Top-Level Layout

The repository is organized as a monorepo-style workspace with a Python root control plane and a separate Next.js app under `aios-ui/`.
The most important top-level paths are:
- `bin/` for executable operator and hook entrypoints.
- `services/` for Python business logic and subsystem implementations.
- `aios-ui/` for the local inspection dashboard and server-side UI helpers.
- `aios/context/` for the file-backed context compiler source, compiled packets, and receipts.
- `config/` for registries and declarative runtime policy.
- `docs/` for ADRs, architecture notes, audits, handoffs, plans, and specs.
- `tests/` for Python and Node-based verification.
- `data/`, `logs/`, and `staging/` for operational artifacts and generated state.

## Root Files That Matter

- `AGENTS.md` defines repo-specific operating rules.
- `PROJECT.md` is the project truth file describing current system state.
- `README.md` is the operator-facing quick reference.
- `pyproject.toml` defines Python tooling and analysis configuration.
- `package.json` at the repo root is scoped to the context compiler tooling.
- `schema.sql` and `data/schema.sql` snapshot the SQLite schema authority.

## Python Control Plane

`bin/` is flat and command-oriented. Naming is descriptive rather than package-based:
- `bin/aios.py` is the main CLI bootstrap.
- `bin/hook-*.py` files handle lifecycle and prompt/session instrumentation.
- `bin/cts-*.py` files operate the CTS subsystem.
- `bin/*pattern*.py`, `bin/*workflow*.py`, and `bin/*experiment*.py` group around learning and experimentation flows.
- Shell helpers such as `bin/health_check.sh` and `bin/weekly-maintenance.sh` sit beside Python commands rather than in a separate ops folder.

`services/` is flatter than the UI and works like the main Python application package:
- Core orchestration and audits live in files such as `services/aios_cli.py`, `services/workflow_orchestration.py`, `services/execution_strategy.py`, `services/success_criteria.py`, and `services/quality_pipeline.py`.
- Project and standards concerns live in `services/project_inventory.py`, `services/project_health_proof.py`, and `services/standards_health.py`.
- Runtime-specific concerns live in `services/invocation_backends.py`, `services/rtk_integration.py`, and `services/capability_truth.py`.
- Experimental and synthesis work lives in `services/divergent_strategy.py`, `services/workflow_experiments.py`, and `services/workflow_synthesis.py`.

## CTS Subtree

`services/cts/` is the main nested subsystem and has internal layering:
- Storage and search primitives live in `services/cts/graph_store.py`, `services/cts/search.py`, and `services/cts/models.py`.
- Indexing and parsing live in `services/cts/indexer.py`, `services/cts/parser.py`, and `services/cts/tsconfig_resolver.py`.
- Backends are split under `services/cts/backends/`.
- External adapters are split under `services/cts/adapters/`.
- Evaluation helpers live under `services/cts/eval/`.
This subtree is more package-like than the rest of `services/`, which makes it the clearest isolated subsystem in the repo.

## UI Application

`aios-ui/` is a standalone Next.js app with its own `package.json`, `tsconfig.json`, `next.config.ts`, and `eslint.config.mjs`.
Major UI directories:
- `aios-ui/app/` holds route segments and page entrypoints such as `aios-ui/app/control/page.tsx`, `aios-ui/app/projects/page.tsx`, and `aios-ui/app/context/page.tsx`.
- `aios-ui/components/` groups reusable UI by area, including `command-center`, `control`, `knowledge`, `projects`, `query`, and `workflows`.
- `aios-ui/server/` holds the server-side read layer.
- `aios-ui/server/aios/` contains domain helpers for runtime, packet assembly, schema, knowledge, context compiler inspection, and control-plane access.
- `aios-ui/server/routers/` contains tRPC routers such as `projects.ts`, `control-plane.ts`, `knowledge.ts`, and `query.ts`.
- `aios-ui/lib/` holds shared TypeScript contracts used across pages and server helpers.

## Context Compiler Layout

`aios/context/` is explicitly tiered by responsibility:
- `aios/context/standards/` for global rules.
- `aios/context/domains/` for domain-specific routers.
- `aios/context/projects/` for project-specific routing notes.
- `aios/context/features/` for feature packets.
- `aios/context/packets/` for deeper reusable guidance.
- `aios/context/handoffs/` for the current handoff node.
- `aios/context/compiled/` for generated briefing output.
- `aios/context/receipts/` for generated loaded/skipped context receipts.
The naming pattern is thin routers plus deeper packets, with dotted filenames such as `global.maintainability.md` and `maintainability.architecture-boundaries.md`.

## Declarative Configuration

`config/` holds registries that drive runtime behavior:
- `config/workflows/` for workflow and skill registries.
- `config/execution-strategies/` for task strategy selection.
- `config/success-criteria/` for quality gates and skill mapping.
- `config/architecture-enforcement/` for project and profile rules.
- `config/divergent-strategy/` for candidate and judge definitions.
- `config/rtk/` for compression rules.
- `config/experiments/` and `config/standards/` for supporting inventories.
JSON is the dominant format here; behavior is intentionally data-driven instead of hard-coded in one module.

## Evidence, Docs, and Generated State

`docs/` is partitioned by document purpose rather than by runtime layer, with notable areas in `docs/architecture/`, `docs/context/`, `docs/audits/`, `docs/handoffs/`, `docs/specs/`, and `docs/superpowers/`.
`tests/` mirrors subsystem names in filenames, for example `tests/test_workflow_orchestration.py`, `tests/test_success_criteria.py`, and `tests/context-compiler.test.mjs`.
`data/` stores durable artifacts, including the primary SQLite database and success-criteria outputs.
`logs/` stores session and control-plane evidence, including `logs/control-plane/`.
`staging/` is for intermediate or candidate artifacts that are not yet promoted.
`archive/` contains legacy material and should not be treated as active architecture.

## Naming and Navigation Heuristics

If the task starts with "run", "hook", "ingest", or "sync", start in `bin/`.
If the task is about durable logic or policy evaluation, start in `services/`.
If the task is about UI pages or operator visibility, start in `aios-ui/app/` and then `aios-ui/server/`.
If the task is about "what context should load", start in `aios/context/` and `tools/context-compile.mjs`.
If the task is about changing allowed behavior, inspect `config/` before editing Python or TypeScript.
Ignore `.next/`, `node_modules/`, `.venv/`, `.pnpm-store/`, `.pytest_cache/`, and similar generated directories unless the task is explicitly about build or environment state.
