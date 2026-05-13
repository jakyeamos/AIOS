---
title: AIOS Testing Reference
mapped_on: 2026-05-13
last_mapped_commit: c8817f21
---

# AIOS Testing

## Scope

This reference captures the testing and verification posture visible at commit `c8817f21`, using `README.md`, `.github/workflows/aios-python-quality.yml`, `.github/workflows/aios-ui-quality.yml`, `package.json`, `aios-ui/package.json`, `pyproject.toml`, and the live `tests/` tree.

## Current Test Stack

- Python automated tests use `pytest`, run through `uv` as documented in `README.md` and CI.
- JavaScript context-compiler tests use the built-in Node test runner via `node --test` from the root `package.json` script `pnpm test:context`.
- The UI currently relies on quality gates rather than a first-class frontend unit/e2e suite:
  - `pnpm lint`
  - `pnpm lint:warning-baseline`
  - `pnpm lint:architecture`
  - `pnpm lint:anti-slop:fixtures`
  - `pnpm build`
- There are no repo-owned React/Vitest/Jest/Playwright spec files under `aios-ui/app`, `aios-ui/components`, `aios-ui/lib`, or `aios-ui/server` in the current tree.
- Lockfiles indicate Playwright is present in transitive dependencies inside `aios-ui/package-lock.json` and `aios-ui/pnpm-lock.yaml`, but there is no active first-party Playwright test suite wired into scripts or CI.

## Test Layout

- Python tests live in `tests/` as `test_*.py` modules. Current count: `21` Python test files.
- Root Node tests currently include `tests/context-compiler.test.mjs`.
- Fixtures are colocated under `tests/fixtures/`, including prompt fixtures in `tests/fixtures/prompts/` and sample exports such as `tests/fixtures/codex_sample.json`.
- The testing style is largely behavior- and contract-oriented rather than snapshot-heavy.

## What The Tests Cover

- CLI and runtime flows: `tests/test_aios_cli.py`, `tests/test_orchestration_runtime.py`, `tests/test_hook_post_tool_use.py`, and `tests/test_hook_prompt_submit.py`.
- Data import and transformation: `tests/test_import_ai_history.py` and `tests/test_extract_patterns.py`.
- Workflow and orchestration logic: `tests/test_workflow_orchestration.py`, `tests/test_workflow_experiments.py`, `tests/test_workflow_synthesis.py`, and `tests/test_divergent_strategy.py`.
- Quality and governance systems: `tests/test_quality_pipeline.py`, `tests/test_success_criteria.py`, `tests/test_standards_health.py`, and `tests/test_architecture_enforcement.py`.
- Regression and contract coverage: `tests/test_tier_one_regressions.py`, `tests/test_validate_prompts.py`, `tests/test_project_inventory.py`, and `tests/test_corpus_eval.py`.
- Context compiler selection and frontmatter integrity: `tests/context-compiler.test.mjs`.

## Common Testing Patterns

- Python tests frequently use in-memory SQLite via `sqlite3.connect(":memory:")`, as seen in `tests/test_divergent_strategy.py`, `tests/test_extract_patterns.py`, and `tests/test_project_inventory.py`.
- Temp directories via `tmp_path` are used heavily for repo simulation, config generation, and isolated file operations.
- Tests often seed only the minimum schema needed for the code path under test instead of booting the full application.
- Assertions typically verify structured outputs, status enums, DB side effects, and contract fields rather than broad textual snapshots.
- Node tests in `tests/context-compiler.test.mjs` validate both successful routing and failure/reporting behavior such as conflict detection and missing-context suggestions.

## Local Verification Commands

Run the main Python suite:

```bash
cd /Users/jakyeamos/AIOS
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q
```

Run the context compiler tests:

```bash
cd /Users/jakyeamos/AIOS
pnpm test:context
```

Validate context metadata without running the test suite:

```bash
cd /Users/jakyeamos/AIOS
pnpm context:validate
```

Run UI lint and typecheck:

```bash
cd /Users/jakyeamos/AIOS/aios-ui
pnpm lint
```

Run the full current UI quality gate set:

```bash
cd /Users/jakyeamos/AIOS/aios-ui
pnpm lint
pnpm lint:warning-baseline
pnpm lint:architecture
pnpm lint:anti-slop:fixtures
pnpm build
```

## CI Gates

- Python CI in `.github/workflows/aios-python-quality.yml` runs:
  - `uv sync`
  - `uv run pytest -q`
- UI CI in `.github/workflows/aios-ui-quality.yml` runs:
  - `npm ci --prefix aios-ui`
  - `npm --prefix aios-ui run lint`
  - `npm --prefix aios-ui run lint:warning-baseline`
  - `npm --prefix aios-ui run lint:architecture`
  - `npm --prefix aios-ui run lint:anti-slop:fixtures`
  - `npm --prefix aios-ui run build`
- CI is path-filtered, so Python and UI checks trigger only when relevant files change.

## Quality Gates Beyond Tests

- `pyproject.toml` configures Ruff linting and BasedPyright typing for `bin`, `services`, and `tests`.
- `aios-ui/package.json` treats `eslint . && tsc --noEmit` as the default `lint` gate.
- `aios-ui/scripts/assert-eslint-warning-baseline.mjs` enforces a warning ratchet instead of allowing warning growth.
- `aios-ui/.dependency-cruiser.cjs` provides architecture validation as a test-like gate for import boundaries and cycles.
- Anti-slop fixture verification in `aios-ui/eslint/anti-slop-fixtures.config.mjs` acts as regression coverage for custom ESLint rules.

## Current Test Posture

- Backend and control-plane logic have meaningful automated coverage, especially around SQLite-backed services, CLI flows, and orchestration contracts.
- The strongest coverage is contract/integration-style testing of Python services with narrow synthetic fixtures.
- The root JavaScript tooling has at least one direct automated suite for the context compiler.
- Frontend behavior coverage is comparatively light: there is strong static verification for the UI, but no first-party component tests, browser e2e tests, or route-level render tests in the repo-owned `aios-ui/` source tree.
- The repo treats successful lint/build/architecture gates as part of the effective testing surface for the UI.

## Practical Guidance

- If changing `bin/`, `services/`, schema-facing logic, or orchestration behavior, run `uv run pytest -q`.
- If changing context compiler logic or context manifests, run both `pnpm test:context` and `pnpm context:validate`.
- If changing anything under `aios-ui/`, run the full UI gate set, not just `pnpm lint`.
- If changing dependency boundaries, expect both architecture enforcement in `tests/test_architecture_enforcement.py` and UI dependency-cruiser checks to matter.
- If adding frontend behavior that is business-critical, current posture suggests a gap: the repo would benefit from first-party UI interaction tests because static gates are stronger than runtime UI tests today.
