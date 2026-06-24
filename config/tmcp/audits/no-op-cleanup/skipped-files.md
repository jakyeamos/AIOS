# Skipped Files

Date: 2026-06-24

## Explicit Exclusions

| Path pattern | Reason |
|---|---|
| `config/tmcp/audits/**` | Audit evidence and quoted candidate material; not live agent instructions. |
| `skills-library/**` | Generated/canonical harvested skill library; edit source skills or TMCP overlays instead. |
| `tmcp-benchmark/runs/**` | Benchmark run worktrees and fixtures; not the editable source of current instructions. |
| `.worktrees/**` | Local git worktrees; not the baseline source of truth. |
| `.aios/shadow-worktrees/**` | AIOS shadow worktrees; evidence only for this ordinary task. |
| `logs/**` | Runtime output. |
| `staging/**` | Staged/generated operational artifacts. |
| `node_modules/**`, `aios-ui/node_modules/**`, `.pnpm-store/**` | Vendored dependencies. |
| `.next/**`, `aios-ui/.next/**` | Generated Next.js build/dev output. |
| `__pycache__/**`, `*.pyc` | Python bytecode. |
| lockfiles and binary artifacts | Not agent-facing instruction surfaces. |

## Non-Instruction Source

Application code, tests, and ordinary architecture docs were not scanned unless
they are prompt, skill, workflow, router, hook, TMCP, or agent-facing context
surfaces. This keeps the audit focused on instructions agents may execute or
imitate.
