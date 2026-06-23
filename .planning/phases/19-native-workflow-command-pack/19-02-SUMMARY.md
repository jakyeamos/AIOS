# Phase 19 Plan 19-02 Summary: Command Contracts And Safety Classes

## Completed Scope

- Added `docs/specs/native-workflow-command-contracts.md`.
- Added `config/commands/native-workflow-commands.json`.
- Defined contracts for:
  - `aios zoom-out`
  - `aios handoff`
  - `aios review squad`
  - `aios audit security`
  - `aios cleanup de-slopify`
  - `aios prototype`
- Defined safety classes: `read_only`, `artifact_write`, `guarded_modify`, `sandbox_write`, and `shadow_branch_only`.
- Defined input schemas, output schemas, write behavior, second-brain usage, sub-agent/reviewer lane representation, validation gates, logging metadata, rollback expectations, and implementation order.
- Explicitly marked `codebase-sweep` as deferred and not default.

## TMCP / Agent-Rule Placement Decision

No always-loaded agent files were edited. The full command contract belongs in `docs/specs/` plus machine-readable registry metadata. Future always-loaded rules should only point to the registry when native command execution is relevant.

## Requirement Evidence

- `CMDP-02`: Complete. The spec and registry define names, schemas, safety classes, behavior, context usage, lanes, gates, logging metadata, rollback, and MVP order.

## Verification

- `python3 -m json.tool config/commands/native-workflow-commands.json` -> parsed.
- Python registry assertion checked six MVP command IDs, safety classes, required input/output schema fields, logging metadata, and `codebase_sweep` default deferral.
- `rg` coverage checked all six MVP invocations plus `codebase-sweep` in the contract doc.
- `pnpm context:validate` -> passed.

## Next Plan

Proceed to Phase 19 Plan 19-03: read-only MVP commands.
