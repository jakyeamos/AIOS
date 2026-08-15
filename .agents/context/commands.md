# AIOS commands

Last reviewed: 2026-08-15

Run commands from the repository root unless a UI command explicitly changes directory.

## Install and generated contracts

```bash
pnpm install --frozen-lockfile
pnpm context:validate
pnpm test:context
pnpm test:no-op-scan
pnpm test:pre-cr-coverage
pnpm --dir aios-ui install --frozen-lockfile
pnpm --dir aios-ui prompts:check
pnpm --dir aios-ui workflows:check
pnpm --dir aios-ui runtime-pages:check
pnpm --dir aios-ui test:runtime-pages
```

## Python and CLI

```bash
uv sync --frozen
PYTHONPATH=.:bin uv run pytest -q
uv run ruff check .
uv run basedpyright
uv run python bin/aios.py --json doctor
uv run python bin/aios.py --json pre-pr-readiness
```

The Pre-CR hook merges Python LCOV with c8 coverage for the Node context compiler.
Only the self-hosting merge adapter and non-executable/generated contract artifacts are excluded;
the adapter has a deterministic unit test and is exercised by the hook itself.

## UI

```bash
pnpm --dir aios-ui lint
pnpm --dir aios-ui lint:warning-baseline
pnpm --dir aios-ui lint:architecture
pnpm --dir aios-ui lint:anti-slop:fixtures
pnpm --dir aios-ui build
pnpm --dir aios-ui test:browser
```

Use focused tests while iterating, then run every applicable full gate before promotion.
