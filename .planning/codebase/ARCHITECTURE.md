---
last_mapped: 2026-05-13
last_mapped_commit: c8817f21
---

# AIOS Architecture Map

## System Pattern

AIOS is a local-first operator control plane built around two persistent substrates: the SQLite store at `data/aios.db` and file-backed knowledge/context under `aios/context/`, `docs/`, `logs/`, and `staging/`.
The repository is not a single deployable app. It is a composed system with a Python control plane, a TypeScript/Next.js inspection UI, and task-specific registries/configuration in `config/`.
The dominant pattern is "registries + durable state + read surfaces":
- Python commands and hooks write durable state.
- JSON registries in `config/` define policies, workflows, experiments, criteria, and architecture rules.
- The UI in `aios-ui/` reads and explains that state rather than owning business logic.

## Major Layers

1. Operator entrypoints: `bin/*.py`, `bin/*.sh`, and `bin/aios.py` provide the command surface used by humans, hooks, and automations.
2. Python service layer: `services/*.py` contains durable logic for orchestration, audits, capability truth, workflow synthesis, RTK, standards health, success criteria, and inventory.
3. CTS subsystem: `services/cts/` is a nested subsystem for repository indexing, graph storage, search, adapters, and evaluation.
4. File-backed context layer: `aios/context/` holds standards, routers, packets, handoffs, compiled briefings, and receipts for deterministic context selection.
5. Configuration layer: `config/` provides registries and policy data consumed by the Python and UI layers.
6. UI read layer: `aios-ui/app/`, `aios-ui/server/`, and `aios-ui/components/` expose dashboards, inspections, and operator pages over the control-plane data.
7. Evidence and design layer: `docs/`, `schema.sql`, `tests/`, and `data/` capture architecture intent, schema snapshots, executable checks, and stored evaluations.

## Primary Entry Points

- CLI bootstrap starts at `bin/aios.py`, which imports `services/aios_cli.py`.
- Session lifecycle hooks enter through files such as `bin/hook-session-start.py`, `bin/hook-stop.py`, `bin/hook-prompt-submit.py`, and `bin/hook-post-tool-use.py`.
- Managed runtime flows enter through `bin/aios-managed-run.py` and `bin/aios_orchestration_runtime.py`.
- Context compilation enters through `tools/context-compile.mjs` and root scripts in `package.json`.
- UI requests enter via route files in `aios-ui/app/**/page.tsx`, then move into `aios-ui/server/routers/*.ts` and `aios-ui/server/aios/*.ts`.

## Data Flow

The common write path is: operator action or hook -> `bin/*` entrypoint -> `services/*` logic -> SQLite/filesystem write to `data/`, `logs/`, `staging/`, or `aios/context/`.
The common read path is: UI page in `aios-ui/app/` -> server helper or tRPC router in `aios-ui/server/` -> `better-sqlite3` access in `aios-ui/server/db.ts` -> SQLite data from `data/aios.db`.
The context compiler is intentionally separate from the database path: `tools/context-compile.mjs` reads Markdown in `aios/context/` and emits compiled artifacts to `aios/context/compiled/` and `aios/context/receipts/`.
The CTS path is a sidecar indexing flow: project inventory from the main SQLite database -> `services/cts/registry.py` -> per-repo graph stores under `data/cts/`.

## Control-Plane Boundaries

The Python control plane is authoritative for writes, lifecycle state, audits, and registry-driven decisions.
The Next.js UI is primarily an inspection and operator surface; it mirrors control-plane concepts but does not appear to be the primary source of truth for them.
The file-backed context compiler is a separate authority from SQLite-backed orchestration state. That split is deliberate and called out in `aios/context/packets/maintainability.architecture-boundaries.md`.
CTS is another bounded subsystem: it depends on project inventory in SQLite but stores its own per-repository graph data under `data/cts/`.
Experimental flows are isolated behind dedicated registries and services, especially `services/divergent_strategy.py` with configuration in `config/divergent-strategy/`.

## Key Abstractions

- Invocation backend contract: `services/invocation_backends.py` defines backend identities and the strict handshake fields expected of managed and legacy runtimes.
- Workflow and skill registries: `services/workflow_orchestration.py` loads `config/workflows/registry.json` and `config/workflows/skills.json` into typed workflow/stage/skill abstractions.
- Success criteria engine: `services/success_criteria.py` evaluates file and task outcomes against registry-defined criteria in `config/success-criteria/`.
- Trusted capability state: `services/capability_truth.py` and related UI contracts model confirmed, inferred, missing, and contradictory signals.
- Context packet model: `aios/context/` plus `tools/context-compile.mjs` implement deterministic selection, receipts, and writeback candidates.
- CTS repository registry: `services/cts/registry.py` maps AIOS projects to per-repo graph stores and isolates index storage from the main DB.

## Architectural Centers of Gravity

`services/aios_cli.py` is the broadest Python façade and acts as the operator shell over many subsystems.
`services/workflow_orchestration.py`, `services/execution_strategy.py`, and `services/invocation_backends.py` define how work is routed and validated.
`aios-ui/server/aios/control-plane.ts`, `aios-ui/server/aios/runtime.ts`, and `aios-ui/server/aios/schema.ts` are the UI-side mirrors of control-plane concepts.
`config/` is structurally important because behavior is partly declarative: workflows, strategies, criteria, architecture rules, RTK rules, and experiment candidates all live there.

## Practical Reading Order

1. Read `PROJECT.md` for the product boundary and recent architecture moves.
2. Read `README.md` for operator entrypoints and storage expectations.
3. Read `services/aios_cli.py` and `bin/aios.py` for the main control path.
4. Read `services/workflow_orchestration.py`, `services/invocation_backends.py`, and `services/success_criteria.py` for control-plane contracts.
5. Read `tools/context-compile.mjs` and `aios/context/router.md` for the file-backed context system.
6. Read `aios-ui/server/aios/control-plane.ts` and `aios-ui/server/db.ts` for the UI/server boundary.
7. Read `services/cts/` only when the task involves repo indexing, graph search, or CTS evaluation.
