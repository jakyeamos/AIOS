# Dependency Map

Date: 2026-06-24

## New TMCP Nodes

| Node | Depends on | Used by |
|---|---|---|
| `@module:instruction_hygiene` | `@module:diff_review`, `@module:quality_gate` for final review and checks | `@task:instruction_hygiene` |
| `@task:instruction_hygiene` | `@module:instruction_hygiene`, `@module:diff_review`, `@module:quality_gate` | Router intents involving skill creation/revision, instruction review, prompt consolidation, prompt-size reduction, instruction-repo merging, drift investigation, and prose behavior evaluation |

## Existing TMCP Files Updated

- `config/tmcp/portable-dev-process/router.md`
- `config/tmcp/portable-dev-process/manifest.json`
- `config/tmcp/portable-dev-process/tests/routing-cases.json`

## Tooling Dependencies

- `pnpm tmcp:no-op-scan` runs `node tools/no-op-instruction-scan.mjs`.
- `pnpm test:no-op-scan` runs `node --test tests/no-op-instruction-scan.test.mjs`.
- The scanner reads tracked files through `git ls-files` and uses
  `config/tmcp/no-op-scan-allowlist.json` for justified false positives.
