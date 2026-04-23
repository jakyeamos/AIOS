# AIOS Architecture Enforcement (Phase 0a)

Date: 2026-04-23  
Status: Implemented baseline

## 1) Audit Findings

### AIOS control-plane repository
- `bin/` is an entrypoint layer with operational scripts and hooks.
- `services/` is a reusable logic layer (currently strongest in `services/cts/`).
- The intended direction already exists informally: `bin/*` imports `services/*`, while `services/*` generally avoids `bin/*`.
- Before this pass there was no machine-enforced global profile model for architecture boundaries across linked projects.

### AIOS UI bootstrap target (`aios-ui/`)
- The app already has practical separation into `app/`, `components/`, `lib/`, and `server/`.
- Existing ESLint checks (including anti-slop) did not enforce cross-layer dependency directionality.
- There was no cycle gate and no dedicated architecture-check command.

### Linked-project readiness
- Linked repos are known (`amos-saas`, `soundscape-app`, `GitNexus`, `Terrace`, `portfolio`), but architecture checks were not represented in a central AIOS registry.
- Enforceable rollout requires a reusable profile abstraction with project-specific bindings.

## 2) Rule Model

AIOS now uses a profile + binding registry:
- `config/architecture-enforcement/profiles.json`
- `config/architecture-enforcement/projects.json`

Profiles define reusable stack adapters:
- `python-service-v1`
  - import-layer rule: `services -> bin` is forbidden
  - cycle detection for local Python modules
  - ruff baseline command
- `ts-nextjs-v1`
  - Dependency Cruiser boundary checks
  - ESLint + TypeScript lint checks

Projects bind profiles with concrete working directories.

## 3) Implemented Enforcement

### Runner and machine-readable output
- Added `services/architecture_enforcement.py`:
  - registry loading
  - profile binding execution
  - command adapters
  - Python import-layer + cycle analyzer
- Added CLI entrypoint: `bin/architecture-enforcement.py`
  - default: runs `aios`
  - `--all-projects` for fleet scan
  - `--json` for agent-consumable output

### Proof target wiring
- Added `aios-ui/.dependency-cruiser.cjs` with enforced rules:
  - no cycles
  - `components/` cannot import `server/`
  - `server/` cannot import `app/` or `components/`
  - `lib/` cannot import `app/` or `components/`
- Added `aios-ui` script:
  - `npm run lint:architecture`
- Installed `dependency-cruiser` in `aios-ui` dev dependencies.

## 4) Usage

Run AIOS proof target:

```bash
python3 bin/architecture-enforcement.py --project aios --json
```

Run all configured linked projects:

```bash
python3 bin/architecture-enforcement.py --all-projects --json
```

Interpretation:
- `passed`: checks executed and passed
- `failed`: enforceable violation
- `missing`: project path not present locally
- `skipped`: adapter intentionally skipped (e.g., required files absent)

## 5) Allowed vs Disallowed Patterns

Python profile:
- Allowed: `bin/hook-stop.py -> services.cts.*`
- Disallowed: `services/* -> bin/*`

Next.js profile:
- Allowed: `app/* -> server/caller`
- Disallowed: `components/* -> server/*`
- Disallowed: `server/* -> app/*` or `server/* -> components/*`

## 6) Backlog / Ratchet Steps

1. Add per-repo `ts-nextjs-v1` config files for linked TypeScript projects that currently lack `.dependency-cruiser.cjs`.
2. Add a Python package-level layering policy for non-CTS service folders if/when they become stable bounded contexts.
3. Add CI invocation in each linked repo so architecture checks block merge by default.
4. Expose the latest enforcement status in command-center UI surfaces once Phase 3 starts.
