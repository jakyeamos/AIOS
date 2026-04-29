# Tier-One AIOS Execution Router

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` for single-agent execution or `superpowers:subagent-driven-development` when splitting independent tasks across agents. This document routes work through the tier-one plan pack in the correct order.

**Goal:** Route an implementation agent through the tier-one AIOS plans without skipping foundational trust work or polishing UI around weak primitives.

**Architecture:** Execute capability first, hardening second, product surface last. Every completed implementation slice must end with a code/test commit followed immediately by a `PROJECT.md` truth-file commit.

**Tech Stack:** Python 3.14, SQLite, Next.js App Router, TypeScript, tRPC, pytest, pnpm lint/typecheck, local AIOS hooks.

---

## Start Here

Before choosing work:

- [ ] Read [00-index.md](./00-index.md)
- [ ] Run:

```bash
git status --short
```

- [ ] Note unrelated dirty files and do not touch them.
- [ ] Run baseline checks:

```bash
uv run pytest -q
```

```bash
cd aios-ui
npm run lint
```

- [ ] Run capability audits:

```bash
uv run python bin/aios.py --json contracts-audit
uv run python bin/aios.py --json invocation-audit
uv run python bin/aios.py --json lifecycle-audit
uv run python bin/aios.py --json capability-audit
```

Record important failures in your first progress update.

## Priority Router

Choose the first incomplete item whose gate fails.

### Priority 1: Runtime Trust

Route to: [01-runtime-and-invocation-reliability.md](./01-runtime-and-invocation-reliability.md)

Start here if any of these are true:

- Python suite has a runtime or orchestration failure
- managed runtime does not complete runs deterministically
- `invocation-audit` reports low or missing current-period handshake coverage
- `lifecycle-audit` reports unsupported states
- unknown invocation backends silently fall back
- run/session/invocation linkage is ambiguous

Completion gate:

```bash
uv run pytest tests/test_orchestration_runtime.py tests/test_aios_cli.py -q
uv run python bin/aios.py --json invocation-audit
uv run python bin/aios.py --json lifecycle-audit
```

### Priority 2: Test And Release Trust

Route to: [08-testing-release-operational-hardening.md](./08-testing-release-operational-hardening.md)

Start here if any of these are true:

- full Python suite is not green after runtime fixes
- UI lint/typecheck has errors
- CI does not mirror local checks
- screenshot-backed confusion cases lack regression coverage
- warning baseline can grow silently

Completion gate:

```bash
uv run pytest -q
cd aios-ui
npm run lint
npm run build
```

### Priority 3: Knowledge And Memory Trust

Route to: [03-knowledge-and-personal-memory.md](./03-knowledge-and-personal-memory.md)

Start here if any of these are true:

- `knowledge-objects` reports low source-reference coverage for priority memory
- Knowledge lacks search over topics and references
- Grounded Query cannot cite source records for project/workflow questions
- personal corpus records are not represented as knowledge references
- object kinds are inconsistent or silently downgraded to concepts

Completion gate:

```bash
uv run python bin/aios.py --json knowledge-objects
uv run pytest tests/test_aios_cli.py -q
cd aios-ui
npm run lint
```

### Priority 4: Integrations And Retrieval Trust

Route to: [07-integrations-corpus-retrieval.md](./07-integrations-corpus-retrieval.md)

Start here if any of these are true:

- corpus sources are not auditable
- importers do not record provenance
- CTS/code truth is not cited in Grounded Query
- briefing packets lack retrieval traces or omitted-context records

Completion gate:

```bash
uv run python bin/aios.py --json corpus-audit
uv run python bin/aios.py --json knowledge-objects
uv run pytest -q
```

If `corpus-audit` does not exist yet, the first task is to create it.

### Priority 5: Workflow Learning Trust

Route to: [04-workflow-learning-loop.md](./04-workflow-learning-loop.md)

Start here if any of these are true:

- terminal runs do not produce learning or no-learning events
- workflow proposals lack cited run evidence
- rejected proposals do not preserve rationale
- failed or abandoned runs are counted only as waste, not diagnostic findings

Completion gate:

```bash
uv run python bin/aios.py --json workflow-learning-audit
uv run pytest tests/test_workflow_synthesis.py tests/test_aios_cli.py -q
```

### Priority 6: Project Health Trust

Route to: [05-projects-standards-quality-health.md](./05-projects-standards-quality-health.md)

Start here if any of these are true:

- priority linked projects lack comparable profiles
- project paths are missing but still look active/healthy
- health scores lack component explanations
- pipeline states can render contradictory labels
- missing health data is not first-class

Completion gate:

```bash
uv run pytest tests/test_standards_health.py tests/test_quality_pipeline.py -q
uv run python bin/aios.py --json capability-audit
cd aios-ui
npm run lint
```

### Priority 7: Telemetry Trust

Route to: [06-observability-efficiency-telemetry.md](./06-observability-efficiency-telemetry.md)

Start here if any of these are true:

- RTK zero values lack explanations
- efficiency page cannot separate cost, waste, and value
- automations show raw RRULE as the primary trigger
- automation failures lack last failure, next run, or urgency
- recent failures are fragmented across surfaces

Completion gate:

```bash
uv run pytest tests/test_rtk_integration.py tests/test_aios_cli.py -q
uv run python bin/aios.py --json rtk
uv run python bin/aios.py --json recent-failures --last 20
cd aios-ui
npm run lint
```

### Priority 8: Command Center Product Surface

Route to: [02-command-center-product-surface.md](./02-command-center-product-surface.md)

Start here only after runtime, memory, learning, project health, and telemetry contracts are trustworthy.

Start here if any of these are true:

- home page does not answer what needs attention now
- visible metrics lack inspection paths
- UI exposes raw implementation formats as product language
- pages are organized around backend tables rather than user decisions

Completion gate:

```bash
cd aios-ui
npm run lint
npm run build
```

Then manually verify:

- `/`
- `/control`
- `/projects`
- `/knowledge`
- `/workflows`
- `/costs`
- `/automations`

### Priority 9: Rollout Governance

Route to: [09-rollout-governance.md](./09-rollout-governance.md)

Use this after each milestone and at final review.

Completion gate:

```bash
uv run pytest -q
cd aios-ui
npm run lint
npm run build
```

Also run:

```bash
uv run python bin/aios.py --json contracts-audit
uv run python bin/aios.py --json capability-audit
uv run python bin/aios.py --json invocation-audit
uv run python bin/aios.py --json lifecycle-audit
uv run python bin/aios.py --json knowledge-objects
uv run python bin/aios.py --json workflow-learning-audit
```

## Per-Task Execution Protocol

For every task inside a plan:

- [ ] Read the task and file list.
- [ ] Inspect existing code before editing.
- [ ] Write or update the failing test first where practical.
- [ ] Run the focused test and confirm the expected failure.
- [ ] Implement the smallest coherent change.
- [ ] Run the focused test and confirm pass.
- [ ] Run the relevant plan completion gate if the task touches shared contracts.
- [ ] Commit the code and tests:

```bash
git add <changed-code-and-tests>
git commit -m "<type>(<area>): <specific capability>"
```

- [ ] Update `PROJECT.md` with the new durable project truth.
- [ ] Commit the truth file:

```bash
git add PROJECT.md
git commit -m "docs: record <specific capability>"
```

## Stop Conditions

Stop and report instead of continuing if:

- a required test requires network or external services unavailable locally
- a command would require destructive cleanup of user changes
- a migration could alter production-like local data without backup
- the plan contradicts current repo behavior after inspection
- an earlier priority gate is failing and later UI/product work was requested

## Parallelization Rules

Safe parallel work:

- knowledge search and corpus audit after runtime is stable
- workflow learning and project health after runtime tests are green
- telemetry and project health if they touch disjoint files
- UI product surface only after its backend contracts are stable

Unsafe parallel work:

- multiple agents editing `services/aios_cli.py`
- multiple agents editing `PROJECT.md`
- runtime transition changes while UI assumes a status vocabulary
- importer changes while knowledge schema is being migrated

## Final Tier-One Claim Checklist

Do not claim tier-one status until all are true:

- [ ] `uv run pytest -q` passes
- [ ] `cd aios-ui && npm run lint` passes
- [ ] `cd aios-ui && npm run build` passes
- [ ] `contracts-audit` reports no undocumented canonical contracts
- [ ] `invocation-audit` reports target handshake coverage or explicit accepted tradeoff
- [ ] `lifecycle-audit` reports no unsupported states
- [ ] `knowledge-objects` reports source-backed priority knowledge
- [ ] `workflow-learning-audit` reports terminal runs as learning or no-learning
- [ ] project health metrics have trusted-signal explanations
- [ ] automations and efficiency metrics are interpretable
- [ ] command center UI is attention-first
- [ ] `PROJECT.md` reflects current implementation reality
