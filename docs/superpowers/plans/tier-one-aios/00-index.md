# Tier-One AIOS Implementation Plan Index

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` for parallel subsystem execution or `superpowers:executing-plans` for inline execution. Each section plan is independently executable and uses checkbox syntax for tracking.

**Goal:** Move AIOS from a serious local alpha into a tier-one multi-function command center and AI operating system.

**Architecture:** The program is staged around capability truth first, then runtime trust, memory depth, learning loops, and finally UI product polish. Each plan turns a partial subsystem into a contract-backed, testable capability before exposing it as a polished surface.

**Tech Stack:** Python 3.14, SQLite, Next.js App Router, TypeScript, tRPC, better-sqlite3, pytest, pnpm lint/typecheck, local hooks, Obsidian vault files.

---

## Current Baseline

AIOS already has meaningful primitives:

- Next.js command center surfaces in `aios-ui/app/`
- local SQLite operational store in `data/aios.db`
- Python CLI in `bin/aios.py` and `services/aios_cli.py`
- run, invocation, packet, writeback, standards, knowledge, and evaluator tables
- hook integration through `bin/hook-session-start.py`, `bin/hook-stop.py`, and prompt/tool hooks
- workflow registries in `config/workflows/`
- standards and success criteria registries in `config/standards/` and `config/success-criteria/`
- CTS/code truth modules under `services/cts/`
- audit commands for capability truth, invocation backends, lifecycle, knowledge objects, workflow learning, and canonical contracts

Current blockers to tier-one status:

- explicit run/session/invocation handshake coverage is not high enough
- managed runtime test reliability is not green
- knowledge is indexed but not yet a deep, searchable personal memory substrate
- telemetry exists before enough interpretation and actionability
- UI surfaces expose partial concepts before the backend can fully justify them
- subsystem contracts exist but are not all canonical, enforced, and shared across CLI/UI/hooks

## Tier-One Definition

AIOS reaches tier-one when a user can rely on it as the default operating layer for serious work:

- **Attention:** it says what needs attention now and why.
- **Execution:** it can start, track, evaluate, and close agent work deterministically.
- **Memory:** it retrieves durable personal/project knowledge with citations and freshness.
- **Learning:** it turns repeated work into reviewable workflow, prompt, standard, or bug/quality improvements.
- **Explainability:** every visible metric can be inspected back to source, freshness, confidence, and missing-data reason.
- **Reliability:** core tests are green, lifecycle states are deterministic, and partial data is explicitly represented.

## Plan Documents

1. [Runtime And Invocation Reliability](./01-runtime-and-invocation-reliability.md)
2. [Command Center Product Surface](./02-command-center-product-surface.md)
3. [Knowledge And Personal Memory](./03-knowledge-and-personal-memory.md)
4. [Workflow Learning Loop](./04-workflow-learning-loop.md)
5. [Projects Standards And Quality Health](./05-projects-standards-quality-health.md)
6. [Observability Efficiency And Telemetry](./06-observability-efficiency-telemetry.md)
7. [Integrations Corpus And Retrieval](./07-integrations-corpus-retrieval.md)
8. [Testing Release And Operational Hardening](./08-testing-release-operational-hardening.md)
9. [Rollout Governance And Milestones](./09-rollout-governance.md)

## Execution Order

Execute in this order unless an urgent production bug overrides it:

1. Runtime and Invocation Reliability
2. Testing Release and Operational Hardening
3. Knowledge and Personal Memory
4. Workflow Learning Loop
5. Projects Standards and Quality Health
6. Observability Efficiency and Telemetry
7. Integrations Corpus and Retrieval
8. Command Center Product Surface
9. Rollout Governance

Reason: UI work is intentionally late. The tier-one product should not polish weak or partial primitives.

## Global Commit Discipline

For every task:

- write the failing test first where practical
- implement the smallest coherent slice
- run focused tests
- run broader verification if shared contracts changed
- commit code
- immediately update `PROJECT.md`
- commit the truth-file update

Doc-only changes may be committed directly as one coherent planning unit, followed by `PROJECT.md`.

## Global Verification Commands

Run these before claiming a subsystem complete:

```bash
uv run pytest -q
```

```bash
cd aios-ui
npm run lint
```

```bash
uv run python bin/aios.py --json contracts-audit
uv run python bin/aios.py --json capability-audit
uv run python bin/aios.py --json invocation-audit
uv run python bin/aios.py --json lifecycle-audit
```

## Tier-One Acceptance Gate

AIOS is not tier-one until all of these are true:

- full Python suite is green
- UI lint/typecheck has no errors and warnings are either ratcheted or accepted
- `invocation-audit` reports at least 90% explicit handshake coverage for current-period sessions
- `lifecycle-audit` reports no unsupported states
- `contracts-audit` reports all canonical contracts implemented or explicitly internal-only
- `knowledge-objects` reports high source-reference coverage for priority project memory
- `workflow-learning-audit` shows terminal runs classified into learning or no-learning signal
- command center UI can explain every visible metric without relying on tooltip-only definitions
