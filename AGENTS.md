# AIOS Agent Router

AIOS is a local-first agent operating system for work context, workflows, and durable project memory. Keep this file as the always-loaded router; detailed governance lives in `.agents/context/`.

## Before Non-Trivial Work

1. Read `.agents/context/README.md`.
2. Read `.agents/context/governance.md` for AIOS shadow routing, success criteria, eval workflow, deployment, or subsystem governance.
3. Run or inspect `pnpm context:compile --task "<objective>"` when context compiler routing is relevant.
4. Use `.agents/context/commands.md` for exact quality commands.
5. Load stack, architecture, UI, Python, or context-compiler files only when routed by `.agents/context/README.md`.

## Hard Stops

- Never load every Markdown file by default.
- Never weaken global security, privacy, maintainability, testing, or observability standards with project convenience.
- Do not bypass governed `/aios` routing failures unless the user explicitly says to bypass AIOS.
- Do not merge, copy, or promote AIOS shadow output into the baseline workspace without explicit user review.
- Do not mark implementation complete when blocker-level criteria fail unless accepted tradeoffs are recorded.
- Do not add static deployment tokens to repo files.

## Core Routes

| Task evidence | Read |
| --- | --- |
| `/aios`, shadow routing, success criteria, eval workflow, deployment, subsystem extraction | `.agents/context/governance.md` |
| Context compiler, packets, receipts, colocated context | `.agents/context/context-compiler.md` and `aios/context/.context/README.md` |
| UI work under `aios-ui/` | `aios-ui/AGENTS.md` and `.agents/context/ui.md` |
| Python control-plane work under `services/` or `bin/` | `services/AGENTS.md` and `.agents/context/python.md` |

## Source Material

- `PROJECT.md` is a durable project overview when it is useful.
- `.agents/context/` is stable repo reference.
- `aios/context/` is compiler-managed context.
- Do not re-inline generated GSD sections into `AGENTS.md`.
