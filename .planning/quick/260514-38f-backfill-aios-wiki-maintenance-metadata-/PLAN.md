# Quick Task: Backfill AIOS wiki maintenance metadata

## Scope

Backfill maintenance metadata for the highest-risk AIOS context packets that agents use for routing, source verification, and post-task writebacks.

## Target Files

- `aios/context/index.md`
- `aios/context/router.md`
- `aios/context/schema.md`
- `aios/context/handoffs/latest.md`
- `aios/context/features/context-compiler.md`
- `aios/context/domains/knowledge-systems.md`
- `aios/context/packets/knowledge.obsidian-routing.md`
- `aios/context/packets/workflow.approval-gates.md`
- `aios/context/packets/ui.command-center.md`
- `aios/context/projects/aios-ui.md`

## Verification

- `pnpm context:validate`
- `pnpm wiki:check`
- `pnpm test:wiki`
