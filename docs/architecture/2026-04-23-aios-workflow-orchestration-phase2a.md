# AIOS Workflow Orchestration (Phase 2a)

Date: 2026-04-23  
Status: Implemented baseline

## 1) What Was Missing

- Existing control-plane runtime primitives (`orchestration_runs`, handshake, events, managed runtime) were present, but there was no typed workflow/skill registry consumed at execution time.
- There was no deterministic stage executor for reference workflows like `academic_paper_v1`.
- There was no first-class durable execution report per workflow run.

## 2) Implemented Components

### Typed workflow + skill registries
- Added workflow registry:
  - `config/workflows/registry.json`
- Added skill registry:
  - `config/workflows/skills.json`
- Includes explicit stage model (`parse_request`, `normalize_prompt`, `enrich_context`, `generate`, `transform`, `validate`, `finalize`) and contract metadata.

### Deterministic workflow execution engine
- Added `services/workflow_orchestration.py`:
  - loads/validates workflow + skill registries
  - enforces stage-to-skill binding contracts
  - executes staged workflows with deterministic state passing
  - implements reference `academic_paper_v1` pipeline including:
    - prompt normalization
    - Obsidian corpus style-profile retrieval adapter with bounded fallback
    - draft generation
    - humanizer transform contract
    - explicit validation gates (`structure_checker`, `citation_checker`, `meaning_preservation_checker`)
  - supports default workflows (`implementation-delivery`, `failure-recovery`) with explicit scope validation

### Durable execution-report ledger
- Added runtime schema/table:
  - `workflow_execution_reports`
- Added runtime insert helper:
  - `insert_workflow_execution_report(...)` in `bin/aios_orchestration_runtime.py`
- Added schema parity in both:
  - `schema.sql`
  - `data/schema.sql`

### Managed runtime integration
- Updated `bin/aios-managed-run.py` to:
  - execute workflow stages before final hook stop
  - persist JSON execution artifacts to:
    - `logs/control-plane/workflow-reports/<invocation-id>.json`
  - write durable report rows to `workflow_execution_reports`
  - attach `workflow-execution-report` artifacts
  - include workflow summary + report linkage in invocation report metadata

### Metadata observability
- Updated `services/aios_cli.py` metadata snapshot to expose:
  - workflow registry summary (`config/workflows/registry.json`)
  - latest execution report pointer from `workflow_execution_reports`

## 3) Verification

- `ruff check services/workflow_orchestration.py services/aios_cli.py bin/aios-managed-run.py bin/aios_orchestration_runtime.py tests/test_workflow_orchestration.py tests/test_aios_cli.py tests/test_orchestration_runtime.py`
- `python3 -m pytest tests/test_workflow_orchestration.py tests/test_orchestration_runtime.py tests/test_aios_cli.py`

## 4) Remaining Ratchet Work

1. Add richer project/profile requirements in the workflow registry and enforce them at runtime selection.
2. Expand validation gates from structural heuristics to stronger evidence-aware checks per workflow family.
3. Add command-center UI panels for stage-by-stage workflow execution report diffing and replay.
