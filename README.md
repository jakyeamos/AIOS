# AIOS

AIOS is the local operating system for work context, agent workflows, durable project memory, and linked-project health. It runs primarily from local files and SQLite, with a Next.js dashboard in `aios-ui/`.

## Local UI

Start the dashboard:

```bash
cd /Users/jakyeamos/AIOS/aios-ui
pnpm install
pnpm dev
```

Open:

```text
http://localhost:3000
```

If port `3000` is already in use, Next.js may offer another port such as `3001`.

## Required Local Stores

AIOS expects these local stores:

```text
/Users/jakyeamos/AIOS/data/aios.db
/Users/jakyeamos/AIOS/logs/
/Users/jakyeamos/AIOS/staging/
/Users/jakyeamos/projects/Vaults/Command-Center/
```

Override the vault location when needed:

```bash
export AIOS_VAULT_ROOT=/Users/jakyeamos/projects/Vaults/Command-Center
```

The UI reads operational state from:

```text
/Users/jakyeamos/AIOS/data/aios.db
```

## Useful UI Pages

- `/` - command center overview
- `/projects` - Taski project inventory and quality pipeline status
- `/projects/[id]` - project health, standards deltas, runs, findings, and pipeline details
- `/control` - orchestration runs, invocation backends, packets, approvals, and evaluator traces
- `/runs` - run history
- `/runs/[id]` - run detail and inspection
- `/workflows` - registered workflow metrics and pending workflow synthesis proposals
- `/query` - grounded query surface
- `/knowledge` - indexed AIOS knowledge pages
- `/prompts` - prompt and rule visibility

## Workflow Proposal Backfill

Create pending workflow proposals from DB patterns and Obsidian vault notes:

```bash
cd /Users/jakyeamos/AIOS
UV_CACHE_DIR=/tmp/uv-cache uv run python bin/synthesize-workflows.py --limit 20
```

Preview without writing:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python bin/synthesize-workflows.py --dry-run --limit 20
```

View proposals in the UI:

```text
http://localhost:3000/workflows
```

Approve a proposal into the workflow and skill registries:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python bin/synthesize-workflows.py \
  --approve <proposal-id> \
  --actor operator \
  --note "Approved as reusable workflow."
```

## Quality Checks

Python test suite:

```bash
cd /Users/jakyeamos/AIOS
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q
```

UI lint and typecheck:

```bash
cd /Users/jakyeamos/AIOS/aios-ui
pnpm lint
```

UI production build:

```bash
cd /Users/jakyeamos/AIOS/aios-ui
pnpm build
```

Architecture check:

```bash
cd /Users/jakyeamos/AIOS/aios-ui
pnpm lint:architecture
```

## Pipeline

Run the AIOS maintenance pipeline:

```bash
cd /Users/jakyeamos/AIOS
UV_CACHE_DIR=/tmp/uv-cache uv run python bin/aios-pipeline.py
```

Dry-run without lab report generation:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python bin/aios-pipeline.py --dry-run --skip-lab
```

## RTK Context Compression

AIOS routes managed command output through the RTK compression layer:

```bash
cd /Users/jakyeamos/AIOS
python3 bin/rtk-run.py --mode adaptive -- pytest -q
python3 bin/rtk-run.py --metrics --json
python3 bin/aios.py --json rtk
```

Rules live in `config/rtk/rules.json`; architecture details live in
`docs/architecture/2026-04-27-aios-rtk-context-compression.md`.

## Important Files

- `PROJECT.md` - project truth and current implementation state
- `AGENTS.md` - repository agent workflow contract
- `docs/STORES.md` - storage authority contract
- `schema.sql` - SQLite schema snapshot
- `services/` - Python service modules
- `bin/` - local hooks, importers, and operators
- `aios-ui/` - Next.js dashboard
- `config/workflows/registry.json` - approved workflow registry
- `config/workflows/skills.json` - approved workflow skill registry

## Notes

- Keep `main` deployable.
- Prefer feature branches for non-trivial code changes.
- `logs/`, `staging/`, local DB files, and generated caches are operational artifacts unless explicitly promoted.
- Some UI verification currently reports existing anti-slop warnings and a Turbopack NFT trace warning; both are non-blocking unless the current change touches those areas.
