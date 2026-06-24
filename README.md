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

All Python entrypoints and bundled shell scripts resolve the vault through
`services/path_resolution.py` via `bin/aios_paths.py`, so `AIOS_VAULT_ROOT`
overrides remain honored without hardcoded script defaults drifting.

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

## Routed Agent Work

In Codex, AIOS shadowing is automatic for non-trivial tasks. Ordinary prompts keep the current workspace as the baseline and use the AIOS lane as evidence only:

```bash
python3 /Users/jakyeamos/AIOS/scripts/codex-aios-shadow.py "<objective>"
```

Governed AIOS routing is command-triggered. Use `/aios` at the start of the prompt when the AIOS route and packet should govern the baseline work:

```text
/aios Fix the route selector bug and verify the checks
```

Codex should run:

```bash
python3 /Users/jakyeamos/AIOS/scripts/codex-aios-shadow.py "<objective>" --governed-route
```

The helper infers the project from the current working directory, creates the routed run/packet, creates an isolated shadow worktree, and prints the follow-up inspection commands. For ordinary prompts, that route is comparison evidence only. For `/aios` prompts, that route is governing context. If the prompt is for another project while Codex is currently in the AIOS repo, include the project name:

```text
/aios for amos-saas: Fix the login redirect bug and verify the checks
```

The current workspace remains the baseline source of truth. The shadow lane is comparison evidence for assessing AIOS usefulness and must not be merged or copied back without explicit review.

If automatic shadow routing exits `0` with `ok: true`, `governed_route: false`, `aios_route.status: "route_failed"`, and `aios_route.blocking: false`, continue the baseline task normally. That payload means AIOS recorded a diagnostic route miss and did not create a shadow worktree; it does not require approval to continue. Explicit approval is only needed when automatic shadow setup exits nonzero or cannot record diagnostic evidence. Governed `/aios` routing failures still block unless the user explicitly bypasses AIOS.

### Durable Agent Work

Use a durable workspace for recurring or long-running streams of work such as release threads, quality gate threads, TMCP skill audits, repo adoption, documentation review, and external monitoring. Durable workspace state should preserve decisions, blockers, owners, dates, useful links, verification status, known pitfalls, and next actions without copying the chat transcript.

Every durable goal needs a verifier and stopping condition. Prefer finish lines such as typecheck passes, lint passes, tests pass, build passes, validation matrix passes, repro is fixed, benchmark improves, deployment succeeds, or artifact audit is complete.

Use steering when the current execution direction needs immediate correction:

```text
/steer Keep the existing workflow registry shape; add a candidate route instead of changing active routing.
```

Use queueing when the instruction should wait until the current checkpoint completes:

```text
/queue After the current verification checkpoint, add a follow-up to audit PR comment monitoring.
```

Steering preserves the active goal unless the operator explicitly changes it. Queued work must not interrupt in-flight verification and should be visible in the run log or durable workspace state.

For substantial work, the chat transcript is not the source of truth. Use a reviewable artifact such as a validation matrix, implementation checklist, audit log, canonical spreadsheet, generated behavioral spec, PR review summary, decision ledger, failing-gate report, static HTML dashboard, or deployment verification report.

Route-only mode is an explicit opt-out for rare cases:

```text
/aios-route-only Fix the route selector bug and verify the checks
```

Route-only mode runs:

```bash
python3 /Users/jakyeamos/AIOS/scripts/codex-aios-route.py "<objective>"
```

Create a compact AIOS packet and strict run/session/invocation handshake before serious agent work:

```bash
cd /Users/jakyeamos/AIOS
python3 bin/aios.py --json start-work "Implement the scoped objective" --project <project-id>
```

When `logs/current_session` points at an open hook-created session, the command links that session to the new run and invocation. If no open session is available, it still creates a ready run and packet for manual handoff.

Approve a proposal into the workflow and skill registries:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python bin/synthesize-workflows.py \
  --approve <proposal-id> \
  --actor operator \
  --note "Approved as reusable workflow."
```

## Quality Checks

Pre-PR readiness gate for AIOS:

```bash
cd /Users/jakyeamos/AIOS
UV_CACHE_DIR=/tmp/uv-cache uv run python bin/aios.py --json pre-pr-readiness
```

This gate shells into the built `pre-cr-suite-lsp` server at `/Users/jakyeamos/projects/pre-cr-suite-lsp`, runs the repo-level `.pre-cr.json`, and fails if the current diff touches unsupported JS/TS or shell surfaces that AIOS does not yet cover with `pre-cr`.

Allowlisted project quality gate runner:

```bash
cd /Users/jakyeamos/AIOS
python3 bin/aios.py --json gate run test_quality --project soundscape-app --repo-root /Users/jakyeamos/projects/soundscape-app
```

Linked projects declare only gate IDs in `.aios-quality-gate.json`. Executable argv arrays live in AIOS-owned `config/quality-gates.json`; the global user commit hook rejects missing, malformed, or unknown gate declarations for registered source commits and never executes shell from repo-local config.

AIOS, Pre-CR, and allowlisted project gate findings emit append-only audit events under `.aios/audit/` in the gated repo. Findings block on `main`, `master`, `dev`, `develop`, `development`, or when `AIOS_DEV_ENVIRONMENT`, `AIOS_DEV_ENV`, `QUALITY_GATE_DEV_ENV`, or `GATE_CONNECTED_DEV_ENV` is set; findings on detected unprotected feature branches are warnings. Unknown branches remain conservative and block. The generated `gate-events.jsonl`, `gate-summary.md`, and `learning-lessons.md` files are runtime artifacts and are ignored by git.

Global non-regression rule for `test_quality`: make the suite more meaningful,
not merely green. Fixes must preserve or improve behavior coverage. Delete tests
only when they are proven obsolete, redundant with stronger coverage, or pure
noise.

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

UI warning baseline ratchet:

```bash
cd /Users/jakyeamos/AIOS/aios-ui
pnpm lint:warning-baseline
```

Architecture check:

```bash
cd /Users/jakyeamos/AIOS/aios-ui
pnpm lint:architecture
```

CI mirrors these local gates:

```bash
cd /Users/jakyeamos/AIOS
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q
cd /Users/jakyeamos/AIOS/aios-ui
pnpm lint
pnpm lint:warning-baseline
pnpm lint:architecture
pnpm lint:anti-slop:fixtures
pnpm build
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
