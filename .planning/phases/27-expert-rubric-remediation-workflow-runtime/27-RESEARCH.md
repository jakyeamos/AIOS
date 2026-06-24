# Phase 27: Expert rubric remediation workflow runtime - Research

**Researched:** 2026-06-24
**Domain:** AIOS workflow runtime, skill registry contracts, route candidate scoring
**Confidence:** HIGH

## User Constraints

No phase CONTEXT.md exists. Planning continues from `.planning/ROADMAP.md`, the approved expert-rubric workflow design spec, the approved implementation plan, and current runtime source files. [VERIFIED: repo files]

Source constraints for this phase:

- Wire Phase 26 artifact builders into `services/workflow_orchestration.py` through deterministic skill dispatch. [VERIFIED: ROADMAP.md Phase 27]
- Register `expert_rubric_remediation_v1` and its skills in `config/workflows/registry.json` and `config/workflows/skills.json`. [VERIFIED: implementation plan Tasks 3-4]
- Complete routing support for expert-review/remediation objectives without reclassifying diagnostic workflow-key mentions as content-writing intent. [VERIFIED: implementation plan Task 5]
- Do not add the `aios tmcp review-plan` CLI; that is Phase 28. [VERIFIED: ROADMAP.md Phase 28]

## Summary

Phase 27 turns the Phase 26 service into a first-class governed workflow runtime path. The core runtime already has typed workflow/skill specs, stage validation, TMCP packet expansion, and route candidate scoring in `services/workflow_orchestration.py`. The plan should extend those existing seams rather than create a parallel executor. [VERIFIED: services/workflow_orchestration.py]

Current branch state already contains some expert routing coverage: `WORKFLOW_TASK_FAMILIES` includes `expert_rubric_remediation_v1`, route scoring includes expert-review terms, and `tests/test_workflow_orchestration.py` has a route test for expert audit-plan objectives. Execution and registry wiring are still absent and remain Phase 27's primary work. [VERIFIED: services/workflow_orchestration.py and tests/test_workflow_orchestration.py]

**Primary recommendation:** Implement runtime dispatch first, then registry contracts, then reconcile route scoring against the final registered workflow.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| WorkflowExecutionContext review inputs | `services/workflow_orchestration.py` | `tests/test_workflow_orchestration.py` | Runtime context carries evidence items and selected slice into skill dispatch. |
| Expert skill dispatch | `_execute_skill` in `services/workflow_orchestration.py` | `services/expert_rubric_remediation.py` | Runtime invokes Phase 26 service functions and records stage validations. |
| Workflow and skill registry entries | `config/workflows/registry.json`, `config/workflows/skills.json` | `validate_workflow_bindings` tests | Registry declares the workflow contract and active skills. |
| Route candidate scoring | `rank_workflow_candidates` and `recommend_route_primitives` | route tests | Routing must select expert remediation for audit-and-plan objectives and avoid content-generation false positives. |
| Execution report artifacts | `execute_workflow` report `artifacts` | Phase 28 CLI | Runtime exposes generated expert artifacts for CLI and downstream operator surfaces. |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib dataclasses | Python 3.12 stdlib | Extend `WorkflowExecutionContext` | Existing runtime uses frozen dataclasses for specs and contexts. |
| Python stdlib pathlib | Python 3.12 stdlib | Review artifact root construction | Existing runtime already uses `Path`. |
| JSON registry files | Existing repo convention | Workflow/skill declarations | AIOS workflow behavior is registry-backed. |
| pytest | Existing repo tool | Runtime, registry, and route tests | Existing workflow tests live in `tests/test_workflow_orchestration.py`. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Ruff | Existing repo tool | Targeted lint/format checks | Run on touched runtime/test files. |
| BasedPyright | Existing repo tool | Targeted type checks | Run on `services/workflow_orchestration.py` after dataclass and dispatch changes. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Existing `_execute_skill` dispatch | A separate expert workflow executor | Parallel executor would duplicate stage validation, skill reporting, and artifact report shape. |
| Existing registry JSON | Hardcoded workflow in runtime | Hardcoding would bypass lifecycle/governance checks and `validate_workflow_bindings`. |
| Existing route scoring | CLI-only invocation | First-class workflow requires route selection as well as explicit CLI use. |

**Installation:** None.

## Architecture Patterns

### System Architecture Diagram

```text
WorkflowExecutionContext(
  objective,
  workflow_key="expert_rubric_remediation_v1",
  tmcp_packet,
  evidence_items,
  selected_slice_id
)
  -> execute_workflow()
  -> registry stages:
       expertise_compile -> rubric_synthesize -> evidence_audit
       -> remediation_plan -> implementation_handoff -> artifact_validate
  -> _execute_skill()
  -> services.expert_rubric_remediation functions
  -> report["artifacts"] with expert artifacts and artifact paths
```

### Existing Patterns To Follow

- `WorkflowExecutionContext` is a frozen dataclass with optional runtime inputs. [VERIFIED: services/workflow_orchestration.py]
- `_execute_skill` returns `(output, validation)` and stores cross-stage state in `run_state`. [VERIFIED: services/workflow_orchestration.py]
- Workflow validation failures are represented as dictionaries with `validation_key`, `passed`, and `issues`. [VERIFIED: services/workflow_orchestration.py]
- Registry validation checks required skills against allowed stage kinds. [VERIFIED: `validate_workflow_bindings`]
- Route scoring adds evidence-specific boosts and suppresses false positives through explicit term families. [VERIFIED: `rank_workflow_candidates`]

## Don't Hand-Roll

- Do not create another workflow execution loop.
- Do not bypass `config/workflows/registry.json` or `config/workflows/skills.json`.
- Do not add CLI parsing in Phase 27.
- Do not write artifact files outside `context.repo_path/.aios/reviews/{run_id}` when runtime dispatch writes review artifacts.

## Common Pitfalls

- Registry `allowed_stages` must match stage `kind`; otherwise `validate_workflow_bindings` fails.
- Required validations listed on the workflow must actually run during the validate stage.
- `evidence_items` must be part of `WorkflowExecutionContext`; hidden globals would make CLI and tests unreliable.
- Route support must not make implementation-delivery or academic-paper routing less precise.
- Existing expert route support should be reconciled, not duplicated into another scoring branch.

## Validation Architecture

| Layer | Command | Purpose |
|-------|---------|---------|
| Dispatch test | `uv run pytest tests/test_workflow_orchestration.py::test_expert_review_workflow_executes_with_artifacts -q` | Proves runtime skill dispatch creates expert artifacts and files. |
| Registry test | `uv run pytest tests/test_workflow_orchestration.py::test_expert_review_workflow_registry_contract -q` | Proves workflow and skill registry contracts load and validate. |
| Routing tests | `uv run pytest tests/test_workflow_orchestration.py::test_rank_workflow_candidates_ignores_diagnostic_workflow_key_mentions tests/test_workflow_orchestration.py::test_expert_review_objective_routes_to_rubric_remediation_workflow -q` | Proves route scoring selects expert workflow and suppresses diagnostic content false positives. |
| Focused runtime suite | `uv run pytest tests/test_workflow_orchestration.py -q` | Catches regressions in existing workflow runtime contracts. |
| Targeted lint/type | `uv run ruff check services/workflow_orchestration.py tests/test_workflow_orchestration.py` and `uv run basedpyright services/workflow_orchestration.py tests/test_workflow_orchestration.py` | Checks touched Python runtime/test files. |

## Security Notes

- Trust boundary: workflow context evidence becomes report artifacts. Mitigation: Phase 26 validators reject unsupported findings.
- Trust boundary: route objective text influences workflow selection. Mitigation: scoring uses explicit evidence terms and blocks diagnostic workflow-key mentions from content intent.
- Trust boundary: artifact writes happen inside a target repo. Mitigation: root is derived from `context.repo_path` and `run_id`; Phase 28 CLI owns user-facing path controls.

## Open Questions (RESOLVED)

1. **Should current routing support be removed because it predates Phase 27 planning?** RESOLVED: No. Treat it as existing state and plan reconciliation/completion.
2. **Should expert workflow implementation be marked implementation-bearing?** RESOLVED: No. The workflow audits and plans, then stops before code execution.
3. **Should registry validation use existing criteria IDs?** RESOLVED: Yes. Use existing `agent-claim-verification` where the approved plan specifies validate-stage binding.
