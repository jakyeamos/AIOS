# AIOS Context Compiler

Date: 2026-05-12
Status: Implemented first version

## Audit Report

Current Markdown and context structure before this pass:

- `PROJECT.md` is the main project truth file.
- `AGENTS.md` defines success-criteria workflow requirements.
- `config/success-criteria/` and `spec/success-criteria/` define executable completion criteria.
- `config/standards/registry.json` defines project-health standards used by the standards delta system.
- `docs/architecture/` contains feature design history for standards health, prompt library, knowledge, CTS, and workflow control plane.
- `docs/handoffs/` contains older handoffs, but there was no tiered context routing tree.
- `aios-ui` already has run, packet, retrieval trace, knowledge, and project-health UI surfaces that can later consume compiler receipts.

Gaps found:

- No file-backed context manifest schema existed for agent routing.
- No deterministic CLI compiled a smallest sufficient Markdown briefing.
- No receipt format explained loaded, skipped, missing, stale, or conflicting context.
- Existing docs were useful but too broad for task-specific loading.
- Obsidian integration had scripts and design direction, but no graph-aware routing packet.

Recommended structure implemented:

- `aios/context/index.md`, `router.md`, and `schema.md` are thin bootloader/schema manifests.
- `aios/context/standards/` stores global standards.
- `aios/context/domains/` stores domain standards.
- `aios/context/projects/` stores project truth routers.
- `aios/context/features/` stores subsystem routers.
- `aios/context/packets/` stores deeper but still compact task packets.
- `aios/context/handoffs/latest.md` stores current routing handoff.
- `aios/context/compiled/` and `aios/context/receipts/` store generated latest outputs.

Risks:

- The first classifier is deterministic keyword/signal routing, so it is inspectable but not semantically rich.
- Candidate project files for Taski, Terrace, and Soundscape need authoritative truth sources before they should carry high authority.
- UI integration is deferred to avoid premature DB schema changes.

## How It Works

Run:

```bash
pnpm context:compile --task "Improve the AIOS UI health score drilldowns"
```

The compiler:

1. Scans `aios/context/**/*.md`, excluding generated output folders.
2. Parses frontmatter.
3. Classifies the task into deterministic signals.
4. Scores each context file by relevance, specificity, authority, recency, and token cost.
5. Loads selected files and any `load_if_matched` packets.
6. Resolves conflicts where immutable globals protect a topic.
7. Reports missing or stale context as writeback candidates.
8. Writes `aios/context/compiled/latest.md`, `aios/context/compiled/latest.json`, `aios/context/receipts/latest.md`, and `aios/context/receipts/latest.json`.

## Adding Context Files

Create a thin Markdown file in the correct tier directory with required frontmatter:

```yaml
---
id: features.example
title: Example Feature
tier: feature
scope:
  - aios
priority: normal
status: active
summary: One-sentence routing summary.
applies_when:
  - task_touches_context_compiler
tags:
  - example
last_reviewed: 2026-05-12
---
```

Then add a short summary, applicability rules, links to packets, acceptance criteria, and conflict notes. Validate with:

```bash
pnpm context:validate
```

## Priority and Conflicts

Precedence is:

`global immutable > domain > project > feature > task packet > agent inference`

More specific files may add constraints. They may not weaken global security, privacy, maintainability, testing, or observability standards. Conflict metadata uses `conflicts.protected_topics` and `conflicts.weakens`; the receipt reports the winner and loser.

## Agent Use

Agents should start from the compiled briefing and receipt, not from a full-docs sweep. Missing context and writeback candidates should be reviewed before promoting new rules or project truth changes.

## Obsidian Evolution

Future Obsidian support should follow the packet in `aios/context/packets/knowledge.obsidian-routing.md`:

1. Classify intent.
2. Find relevant note clusters.
3. Load MOC notes first, such as `MOC.AIOS.md`, `MOC.Soundscape.md`, `MOC.JobSearch.md`, and `MOC.WritingStyle.md`.
4. Traverse backlinks, tags, and frontmatter.
5. Compile the smallest sufficient packet with a receipt.

## UI Integration Follow-Up

Recommended AIOS UI surfaces:

- Run detail: context packets loaded per run and context receipt link.
- Project health / standards delta: missing context and stale context warnings.
- Control plane: conflicting rules and writeback candidates before agent invocation.
- Knowledge page: suggested new packets and MOC routing status.
- Approval dashboard: proposed rule, packet, and truth-file writebacks.

Initial implementation should persist compiler JSON into existing `briefing_packets` or a future `context_receipts` table only after the file-backed contract stabilizes.
