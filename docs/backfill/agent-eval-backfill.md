# Agent Eval Backfill Inventory

Date: 2026-06-02
Source checks: `scripts/quality-eval.sh`
Template reference: `docs/evals/templates/backfill-hotspot.md`

## Scope

This is the first factual hotspot inventory for the Agent Eval Foundation. It is based on current filesystem inspection, not speculative review. The large-Python-file scan follows the plan's repo-wide command and therefore includes files under `.worktrees/` when present in the working tree.

Observed checks:

- Python files over 500 lines: present.
- Test files with no assertions by the configured regex: none.
- `services/` files importing `bin.`: none.
- TypeScript component files over 400 lines: present.
- Vulture findings at min confidence 80: none observed.
- Shellcheck findings in `bin/*.sh`: present.

## Python Services (`services/`)

### Current Status

The services layer contains the largest Python control-plane modules. The largest service files observed were:

- `services/aios_cli.py`: 4779 lines.
- `services/standards_health.py`: 2334 lines.
- `services/workflow_orchestration.py`: 1611 lines.
- `services/success_criteria.py`: 1341 lines.
- `services/divergent_strategy.py`: 973 lines.
- `services/operator_search.py`: 960 lines.
- `services/workflow_synthesis.py`: 917 lines.
- `services/workflow_experiments.py`: 893 lines.
- `services/learning_analysis.py`: 837 lines.
- `services/cts/graph_store.py`: 808 lines.

### Quality Risks

- Hotspot: `services/aios_cli.py`.
- Evidence: 4779-line CLI module from the large-file scan.
- Risk: command parsing, dispatch, formatting, and behavior can become hard to evaluate proportionally after major work.
- Suggested Fix: split future changes by command family or add eval records for major edits touching this file.
- Priority: P1.
- Owner/Agent: implementation agent.
- Blocking Status: non-blocking.
- Related Failure Taxonomy Label: `maintainability_regression`.
- Whether It Blocks AIOS-Quality Completion: no, but it should trigger deeper audit before broad CLI refactors.

### Complexity Hotspots

- `services/standards_health.py` and `services/workflow_orchestration.py` both exceed 1500 lines.
- `services/success_criteria.py` exceeds 1300 lines and is a runtime source of truth for completion gates.
- Multiple learning, workflow, and CTS modules exceed 500 lines.

### Test Gaps

- The assertion-free-test regex found no Python test files without assertion-like checks.
- This does not prove behavior coverage; it only proves the configured assertion regex found assertions.

### Documentation Gaps

- Large services have partial narrative coverage through project docs, planning summaries, and truth files, but no per-hotspot eval records yet.

### Architecture Concerns

- The `services/` to `bin/` import check found no violations.

### Eval Instrumentation Gaps

- Phase 11 automation should track file-size hotspots and map major edits in these modules to `major-task-eval.md` records.

### Priority

P1.

## CLI / Bin Scripts (`bin/`)

### Current Status

The large-file scan found several bin scripts over 500 lines, including:

- `bin/aios_orchestration_runtime.py`: 1578 lines.
- `bin/hook-stop.py`: 1173 lines.
- `bin/review_app.py`: 987 lines.
- `bin/generate-rule-bundle.py`: 895 lines.
- `bin/import_ai_history.py`: 810 lines.
- `bin/discover-github-skills.py`: 593 lines.
- `bin/hook-prompt-submit.py`: 591 lines.
- `bin/trigger-lab-experiment.py`: 531 lines.
- `bin/hook-session-start.py`: 522 lines.

### Quality Risks

- Hotspot: lifecycle hook and runtime scripts.
- Evidence: `bin/aios_orchestration_runtime.py`, `bin/hook-stop.py`, `bin/hook-prompt-submit.py`, and `bin/hook-session-start.py` exceed 500 lines.
- Risk: hook/runtime behavior can be difficult to verify without direct execution-path tests.
- Suggested Fix: require runtime-path eval records for major hook or orchestration changes.
- Priority: P1.
- Owner/Agent: implementation agent.
- Blocking Status: non-blocking.
- Related Failure Taxonomy Label: `runtime_path_not_exercised`.
- Whether It Blocks AIOS-Quality Completion: no for this snapshot; yes for future unverified hook/runtime changes.

### Complexity Hotspots

- `bin/aios_orchestration_runtime.py` is the largest CLI/runtime script found by the configured scan.
- `bin/hook-stop.py` is a lifecycle boundary and exceeds 1000 lines.

### Test Gaps

- This inventory did not run tests; it records hotspot evidence only.

### Documentation Gaps

- Hook behavior is described across planning summaries and `PROJECT.md`, but there is no dedicated eval backfill record per hook script.

### Architecture Concerns

- Shellcheck found:
  - `bin/takeout-ingest.sh`: SC1071 because the script uses `zsh`, which shellcheck does not support.
  - `bin/weekly-maintenance.sh`: SC2155 for declaring and assigning `AIOS_VAULT_ROOT` in one export statement.

### Eval Instrumentation Gaps

- Phase 11 should distinguish shellcheck unsupported-shell findings from actionable bash/sh warnings.

### Priority

P1.

## Tests

### Current Status

The assertion-free-test scan found no matching Python test files without `assert`, `assertEqual`, `assertIn`, or `pytest.raises`.

Large test files observed in the repo-wide large-Python scan included:

- `tests/test_aios_cli.py`: 3359 lines.
- `tests/test_orchestration_runtime.py`: 1291 lines.
- `tests/test_workflow_orchestration.py`: 883 lines.
- `tests/test_standards_health.py`: 874 lines.
- `tests/test_import_ai_history.py`: 729 lines.
- `tests/test_learning_analysis.py`: 685 lines.
- `tests/test_learning_impact.py`: 595 lines.
- `tests/test_operator_search.py`: 527 lines.

### Quality Risks

- Hotspot: very large test modules.
- Evidence: `tests/test_aios_cli.py` is 3359 lines and multiple test files exceed 500 lines.
- Risk: broad test modules can hide coverage gaps and make eval failure attribution harder.
- Suggested Fix: future eval automation should link failures to test module scope and acceptance criteria.
- Priority: P2.
- Owner/Agent: evaluation agent.
- Blocking Status: non-blocking.
- Related Failure Taxonomy Label: `verification_too_narrow`.
- Whether It Blocks AIOS-Quality Completion: no.

### Complexity Hotspots

- `tests/test_aios_cli.py` is the primary test-size hotspot from the current scan.

### Test Gaps

- No assertion-free files were found by the configured regex.
- Happy-path-only coverage was not assessed by this mechanical scan and needs deeper audit.

### Documentation Gaps

- Test modules are not mapped to eval dimensions or failure labels yet.

### Architecture Concerns

- None found by the configured `services/` import-boundary check.

### Eval Instrumentation Gaps

- Phase 11 should record which tests were run, which acceptance criteria they cover, and whether they exercise runtime paths.

### Priority

P2.

## aios-ui (Next.js)

### Current Status

The TypeScript component scan found three component files over 400 lines:

- `aios-ui/components/control/ControlPlaneStudio.tsx`: 686 lines.
- `aios-ui/components/projects/TaskiProjectSurface.tsx`: 540 lines.
- `aios-ui/components/workflows/WorkflowSandbox.tsx`: 403 lines.

### Quality Risks

- Hotspot: `ControlPlaneStudio.tsx`.
- Evidence: 686-line interactive component from the TS component scan.
- Risk: large client-side surfaces can accumulate UI state, mutation, and rendering complexity that is hard to verify only through static checks.
- Suggested Fix: major UI changes in these components should include rendered Browser checks and a major-task eval record.
- Priority: P1.
- Owner/Agent: frontend agent.
- Blocking Status: non-blocking.
- Related Failure Taxonomy Label: `verification_too_narrow`.
- Whether It Blocks AIOS-Quality Completion: no for this snapshot; yes for future UI work that skips rendered verification.

### Complexity Hotspots

- `ControlPlaneStudio.tsx` and `TaskiProjectSurface.tsx` are the main size hotspots.

### Test Gaps

- This scan did not run UI tests; it only records size hotspots.

### Documentation Gaps

- Large UI components are not mapped to eval templates or acceptance-criteria coverage yet.

### Architecture Concerns

- No architecture-lint result is recorded in this backfill snapshot.

### Eval Instrumentation Gaps

- Phase 11 should connect UI eval records to route-level Browser verification and mutation side-effect policy.

### Priority

P1.

## Config / Standards / Success Criteria

### Current Status

The `services/` import-boundary check found no `from bin.` imports. Vulture at min confidence 80 produced no findings in the current run.

### Quality Risks

- Hotspot: schema and standards authority are distributed across config, docs, services, and UI projections.
- Evidence: no mechanical violation from this plan's checks; risk is based only on artifact distribution observed while adding eval docs and schemas.
- Suggested Fix: Phase 11 should add automation that maps eval records to success criteria files and registry ids.
- Priority: P2.
- Owner/Agent: evaluation agent.
- Blocking Status: non-blocking.
- Related Failure Taxonomy Label: `context_missing_required_source`.
- Whether It Blocks AIOS-Quality Completion: no.

### Complexity Hotspots

- No config-size hotspot was measured by this plan's script.

### Test Gaps

- Not assessed by the quality script.

### Documentation Gaps

- Eval schema docs exist after Plan 10-07, but automation linkage is not implemented.

### Architecture Concerns

- No `services/` to `bin/` import violations were found.

### Eval Instrumentation Gaps

- Later automation needs durable storage or generated records for eval tasks, eval runs, scores, and failures.

### Priority

P2.

## Documentation / Eval Infrastructure

### Current Status

Plan 10-07 added the eval architecture, context profiles, five templates, and schema definitions. This plan adds the first hotspot script and inventory.

### Quality Risks

- Hotspot: eval process is still manual.
- Evidence: `scripts/quality-eval.sh` is a read-only reporter and no automation tables or runtime hooks are introduced in Phase 10.
- Risk: agents may inconsistently apply templates until Phase 11 instrumentation exists.
- Suggested Fix: Phase 11 should add task/run records, scoring persistence, and workflow integration.
- Priority: P1.
- Owner/Agent: evaluation automation agent.
- Blocking Status: non-blocking.
- Related Failure Taxonomy Label: `verification_skipped`.
- Whether It Blocks AIOS-Quality Completion: no for the foundation; yes for claims that automation is already implemented.

### Complexity Hotspots

- No documentation size hotspot was measured by the script.

### Test Gaps

- This plan does not include doc rendering or template parsing tests.

### Documentation Gaps

- Template usage examples and automation persistence docs are deferred to Phase 11.

### Architecture Concerns

- The eval foundation intentionally remains docs, templates, schema stubs, and a read-only scan script.

### Eval Instrumentation Gaps

- Missing durable eval run storage.
- Missing score calculation automation.
- Missing task-to-context-profile enforcement.
- Missing shadow-branch candidate automation.

### Priority

P1.

## Needs Deeper Audit

- `services/aios_cli.py`: largest Python module in the scan; needs command-family breakdown before broad CLI changes.
- `services/standards_health.py`: standards-health logic is large enough to need targeted eval coverage mapping.
- `services/workflow_orchestration.py`: workflow state and routing behavior need runtime-path eval records.
- `services/success_criteria.py`: success-criteria authority should be mapped to eval score and completion-gate evidence.
- `bin/aios_orchestration_runtime.py` and lifecycle hooks: future edits should run exact hook/runtime paths, not only static checks.
- `tests/test_aios_cli.py`: very large test file; needs acceptance-criteria and failure-label mapping.
- `aios-ui/components/control/ControlPlaneStudio.tsx`: large interactive surface; future changes should include rendered Browser verification.

## Summary

This inventory gives Phase 11 a concrete baseline: size hotspots in Python services, bin scripts, tests, and UI components; no assertion-free Python test files by the configured regex; no `services/` importing `bin.` violations; no vulture findings at the configured threshold; and shellcheck findings for one unsupported zsh script and one export-assignment warning.
