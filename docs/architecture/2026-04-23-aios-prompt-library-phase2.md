# AIOS Prompt Library Phase 2 (Execution Strategies)

Date: 2026-04-23  
Status: Implemented hybrid baseline

## 1) Scope Decision (from Phase 1c Audit)

Phase 1c recommended a **hybrid path**: deterministic schema/gate infrastructure plus selective human/LLM judgment for semantic promotion decisions. This pass intentionally implements:

- explicit execution-strategy schemas and validation
- canonical task-family spec + surface-specific bundles
- deterministic compiler/selection logic
- metadata visibility and runtime integration

It intentionally does **not** implement full replay/shadow/canary automation in this first pass.

## 2) Implemented Components

### Canonical task spec registry
- Added:
  - `config/execution-strategies/task-specs.json`
- Seeded task family (first slice):
  - `audit_and_implement`
- Task spec includes:
  - intent
  - required/optional inputs
  - output contract
  - hard constraints
  - quality rubric profile
  - default context requirements

### Surface-specific strategy bundles
- Added:
  - `config/execution-strategies/strategies.json`
- Includes one validated strategy bundle per required surface for the seeded family:
  - `audit_and_implement_claude_v1`
  - `audit_and_implement_codex_v1`
- Bundles include explicit versions for:
  - command adapter
  - skill bundle
  - context profile
  - validation profile
  - model/effort profile
  - rollout policy and lineage fields

### Strategy compiler + selector
- Added:
  - `services/execution_strategy.py`
- Implements:
  - typed loaders for task specs and strategy catalog
  - contract validation across references and surfaces
  - status-aware strategy selection by `task_family + surface`
  - compiled instruction payload generation including constraints/output contract/rubric

### Validation tooling + generated registry
- Added validator:
  - `bin/validate-execution-strategies.py`
- Generated artifact:
  - `config/execution-strategies/registry.json`
- Validator enforces:
  - required fields
  - surface compatibility
  - reference integrity
  - at least one active `claude_code` and one active `codex` strategy per seeded task family

### Runtime and observability integration
- `services/workflow_orchestration.py` normalization stage now attaches execution strategy bundles for mapped workflows (`implementation-delivery`, `failure-recovery` -> `audit_and_implement`).
- `bin/aios-managed-run.py` now sets workflow execution `surface` from backend key (`claude_code` vs `codex`).
- `services/aios_cli.py` metadata snapshot now exposes execution-strategy coverage from generated registry.

## 3) Verification

- `python3 bin/validate-execution-strategies.py --config-root /Users/jakyeamos/AIOS/config/execution-strategies`
- `ruff check` on updated services/bin/tests
- `python3 -m pytest tests/test_execution_strategy.py tests/test_workflow_orchestration.py tests/test_orchestration_runtime.py tests/test_aios_cli.py`

## 4) Remaining Ratchet Work

1. Add additional seeded task families (`bug_investigation`, `research_summary`, etc.) with the same two-surface baseline.
2. Add deterministic pre-promotion gate bundles tied to run evidence quality thresholds.
3. Add manual/semi-automated qualitative review capture linked to strategy lifecycle transitions.
4. Introduce shadow/canary automation only after enough per-run rubric signal is accumulated.
