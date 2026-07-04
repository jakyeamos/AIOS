# Rollout Governance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Coordinate the tier-one migration without mixing unrelated work or shipping partial capability as product truth.

**Architecture:** Use milestone gates. Each subsystem must graduate from diagnostic contract to trusted capability to UI exposure. `PROJECT.md` remains the current truth file after every coherent commit.

**Tech Stack:** Git, `PROJECT.md`, docs, CLI audits, pytest, pnpm quality checks.

---

## Milestones

### Milestone 1: Runtime Trust

Required documents:

- [Runtime And Invocation Reliability](./01-runtime-and-invocation-reliability.md)
- [Testing Release And Operational Hardening](./08-testing-release-operational-hardening.md)

Exit criteria:

- [ ] Python suite green
- [ ] managed runtime closes runs deterministically
- [ ] current-period handshake coverage reported
- [ ] unsupported lifecycle states are zero
- [ ] unknown invocation backend is rejected explicitly

### Milestone 2: Memory Trust

Required documents:

- [Knowledge And Personal Memory](./03-knowledge-and-personal-memory.md)
- [Integrations Corpus And Retrieval](./07-integrations-corpus-retrieval.md)

Exit criteria:

- [ ] knowledge object contract is shared by CLI and UI
- [ ] knowledge search works
- [ ] priority knowledge objects have source refs
- [ ] corpus source audit exists
- [ ] Grounded Query answers include citations and retrieval trace

### Milestone 3: Learning Trust

Required documents:

- [Workflow Learning Loop](./04-workflow-learning-loop.md)
- [Projects Standards And Quality Health](./05-projects-standards-quality-health.md)

Exit criteria:

- [ ] terminal runs produce learning or no-learning events
- [ ] workflow proposals cite evidence
- [ ] project health metrics are trusted signals
- [ ] priority linked projects have health profiles
- [ ] standards deltas produce lifecycle-managed findings/tasks

### Milestone 4: Product Trust

Required documents:

- [Observability Efficiency And Telemetry](./06-observability-efficiency-telemetry.md)
- [Command Center Product Surface](./02-command-center-product-surface.md)

Exit criteria:

- [ ] home page is attention-first
- [ ] every metric has an inspection path
- [ ] automations show readable schedule, next run, last failure, and urgency
- [ ] efficiency separates cost, waste, and value
- [ ] UI no longer exposes raw implementation formats as primary product language

## Governance Rules

- Do not start UI polish before the backing contract is testable.
- Do not add a new abstraction unless it is consumed by at least two surfaces or removes real duplication.
- Do not silently hide missing data; represent it with source, freshness, confidence, and missing reason.
- Do not merge a feature if blocker-level success criteria fail without recorded accepted tradeoff.
- Do not update dashboards around placeholder metrics.

## Branch And Commit Policy

For each subsystem:

```bash
git switch -c codex/tier-one-<subsystem>
```

Commit pattern:

```bash
git add <code-and-tests>
git commit -m "feat(<area>): <capability>"
git add PROJECT.md
git commit -m "docs: record <capability>"
```

Doc-only planning packs may use:

```bash
git add docs/superpowers/plans/tier-one-aios
git commit -m "docs: add tier-one AIOS implementation plans"
git add PROJECT.md
git commit -m "docs: record tier-one planning pack"
```

## Review Gates

Before milestone close:

- [ ] run `uv run pytest -q`
- [ ] run `cd aios-ui && pnpm lint`
- [ ] run `uv run python bin/aios.py --json contracts-audit`
- [ ] run `uv run python bin/aios.py --json capability-audit`
- [ ] inspect `git status --short` and account for unrelated dirty files
- [ ] update `PROJECT.md`

## Tier-One Final Review

AIOS can be considered tier-one only after a final review confirms:

- [ ] execution path is deterministic
- [ ] memory path is citable
- [ ] learning path is durable
- [ ] telemetry path is interpretable
- [ ] project health is comparable
- [ ] UI surfaces are decision-oriented
- [ ] tests and CI enforce the above
