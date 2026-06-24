# Phase 28: Expert rubric remediation CLI and verification - Research

**Researched:** 2026-06-24
**Domain:** AIOS TMCP CLI, focused quality gates, project truth closeout, smoke verification
**Confidence:** HIGH

## User Constraints

No phase CONTEXT.md exists. Planning follows `.planning/ROADMAP.md`, the approved `expert_rubric_remediation_v1` design, the approved implementation plan, and the Phase 26-27 planning contracts. [VERIFIED: repo files]

Source constraints for this phase:

- Add a read-only `aios tmcp review-plan` CLI that compiles a TMCP packet, runs the expert review workflow, and writes review artifacts to a caller-selected output directory. [VERIFIED: implementation plan Task 6]
- Keep implementation work out of the CLI command; it creates rubric/audit/remediation/handoff artifacts only. [VERIFIED: design spec]
- Run focused quality gates after the runtime and CLI are complete, update `.tracker/PROJECT_TRUTH.md`, and preserve existing repo-level failure honesty. [VERIFIED: AGENTS.md and implementation plan Task 7]
- Record a smoke run and final handoff evidence for the expert workflow before closeout. [VERIFIED: implementation plan Task 8]

## Summary

Phase 28 finishes first-class exposure and verification for `expert_rubric_remediation_v1`. The implementation work belongs in Phases 26 and 27; this phase should bind the workflow into the existing TMCP CLI surface, run focused checks, update project truth, and leave a durable handoff artifact proving the full review-plan path works. [VERIFIED: ROADMAP.md]

The CLI surface already has a `tmcp` command group in `services/aios_cli.py` with JSON-oriented subcommands such as `explain`, `learning-summary`, `adherence`, `record-event`, `record-intervention`, `packet-diff`, and `shortcut-governance`. The new command should follow that parser and `run_cli` branch style rather than create a separate entrypoint. [VERIFIED: services/aios_cli.py]

**Primary recommendation:** Add the command and tests first, then run focused gates and record a smoke artifact that links the objective, evidence input, output directory, generated artifact paths, and remaining repo-level quality caveats.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| `aios tmcp review-plan` parser | `services/aios_cli.py` | `tests/test_aios_cli.py` | Existing AIOS CLI owns TMCP subcommands and JSON output behavior. |
| TMCP packet compilation | `services.tmcp_runtime.compile_tmcp_packet` | `WorkflowExecutionContext.tmcp_packet` | Review-plan starts from the same compiled expertise packet as existing TMCP explain behavior. |
| Workflow execution | `services.workflow_orchestration.execute_workflow` | `config/workflows/registry.json` | The CLI should invoke the registered workflow runtime from Phase 27. |
| Artifact output | Phase 26 artifact writer through runtime report | caller `--output-dir` | Artifact paths must be visible in JSON output and smoke evidence. |
| Quality/truth closeout | `.tracker/PROJECT_TRUTH.md` and phase verification artifact | command output logs | The final state snapshot must reflect actual checks and known repo-level failures. |

## Standard Stack

| Tool | Existing Surface | Purpose |
|------|------------------|---------|
| argparse | `services/aios_cli.py` | Add `tmcp review-plan` parser and options. |
| pytest | `tests/test_aios_cli.py`, `tests/test_workflow_orchestration.py` | Cover CLI JSON behavior and runtime integration. |
| Ruff | `pyproject.toml` | Focused lint/format checks for touched Python files. |
| BasedPyright | `pyproject.toml` | Focused type check for touched Python files. |
| Vulture | existing quality ladder command | Dead-code check/report for closeout. |

**Installation:** None.

## Existing Patterns To Follow

- `run_cli` returns `EXIT_OK` and prints JSON when `--json` is present. [VERIFIED: services/aios_cli.py]
- TMCP subcommands accept JSON strings for structured payloads where needed. [VERIFIED: `packet-diff`, `adherence`, and event commands]
- CLI tests seed a local SQLite fixture and call `run_cli([...])` directly. [VERIFIED: tests/test_aios_cli.py]
- Project truth updates must keep failing repo-level quality baselines visible instead of overwriting them with focused pass results. [VERIFIED: `.tracker/PROJECT_TRUTH.md`]

## Don't Hand-Roll

- Do not add a second CLI entrypoint for review-plan.
- Do not bypass `compile_tmcp_packet`; the command should use the existing TMCP compiler to produce expertise input.
- Do not bypass `execute_workflow`; artifact production should use the registered workflow contract from Phase 27.
- Do not claim repo-level quality is green when only focused checks pass.
- Do not run implementation edits from the review-plan CLI.

## Common Pitfalls

- `--evidence-json` needs deterministic parsing and validation errors; malformed JSON should return usage/runtime failure consistently with nearby CLI branches.
- `--output-dir` must be honored by the workflow context or copied into the artifact writer path in a deterministic way; tests need to assert real files exist.
- CLI JSON output should include workflow key, run id, artifact paths, validation status, and remediation slice count so downstream operators can trust the result.
- Focused checks can pass while full repo checks remain failing; truth and verification docs must preserve that distinction.
- The smoke command should use a small evidence payload rather than scanning a target repo, keeping Phase 28 read-only and reproducible.

## Validation Architecture

| Layer | Command | Purpose |
|-------|---------|---------|
| CLI command test | `uv run pytest tests/test_aios_cli.py::test_tmcp_review_plan_writes_expert_review_artifacts -q` | Proves the CLI creates review-plan artifacts and emits JSON metadata. |
| Runtime regression | `uv run pytest tests/test_workflow_orchestration.py::test_expert_review_workflow_executes_with_artifacts tests/test_workflow_orchestration.py::test_expert_review_workflow_registry_contract -q` | Proves Phase 27 runtime/registry still work. |
| Focused lint/format | `uv run ruff check services/aios_cli.py tests/test_aios_cli.py services/workflow_orchestration.py tests/test_workflow_orchestration.py services/expert_rubric_remediation.py tests/test_expert_rubric_remediation.py` and `uv run ruff format --check ...` | Checks touched Phase 26-28 Python files. |
| Focused type | `uv run basedpyright services/aios_cli.py services/workflow_orchestration.py services/expert_rubric_remediation.py tests/test_aios_cli.py tests/test_workflow_orchestration.py tests/test_expert_rubric_remediation.py` | Checks the touched typed surfaces. |
| Dead code | `uv run vulture . --min-confidence 70` | Reports dead-code baseline for closeout. |
| Smoke | `uv run python bin/aios.py --json tmcp review-plan ...` | Proves the operator-facing command path works end to end. |

## Security Notes

- Trust boundary: operator-provided `--evidence-json` becomes local review artifacts. Mitigation: Phase 26 evidence validators reject unsupported finding shape.
- Trust boundary: caller-provided `--output-dir` controls local artifact destination. Mitigation: CLI should expand the path, create only directories/files under that destination, and report paths.
- Privacy posture: command is local/read-only against target project input; no network calls or external repo scan are required.

## Runtime State Inventory

This phase does not rename or migrate persisted identifiers. Runtime state checks:

| Category | Finding |
|----------|---------|
| Stored data | None; command does not require DB schema changes. |
| Live service config | None; registry entries are file-backed and covered in Phase 27. |
| OS-registered state | None. |
| Secrets/env vars | None. |
| Build artifacts | None. |

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python | CLI and tests | yes | project runtime | none |
| uv | focused quality/test commands | yes | project tool | use documented local environment only |
| pytest | tests | yes | project dependency | none |
| Ruff | lint/format | yes | project dependency | none |
| BasedPyright | type checks | yes | project dependency | document failure if baseline blocks |
| Vulture | dead-code check | yes | project dependency | document failure if unavailable |

## Sources

- `.planning/ROADMAP.md` - Phase 28 scope and dependency.
- `docs/superpowers/specs/2026-06-24-expert-rubric-remediation-design.md` - workflow contract.
- `docs/superpowers/plans/2026-06-24-expert-rubric-remediation.md` - original Tasks 6-8.
- `services/aios_cli.py` - existing TMCP CLI parser and command branch pattern.
- `tests/test_aios_cli.py` - CLI test fixture and `run_cli` invocation pattern.
- `.tracker/PROJECT_TRUTH.md` - current quality baseline and truth update expectations.

## Open Questions

None. Phase 28 can be planned against current repo surfaces and the Phase 26-27 contracts.
