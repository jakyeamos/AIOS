# Phase 26: Expert rubric remediation core artifacts - Research

**Researched:** 2026-06-24
**Domain:** Python artifact service, deterministic review schemas, pytest contract coverage
**Confidence:** HIGH

## User Constraints

No phase CONTEXT.md exists. Planning continues without discuss-phase context because the phase boundary is already locked in `.planning/ROADMAP.md`, `docs/superpowers/specs/2026-06-24-expert-rubric-remediation-design.md`, and `docs/superpowers/plans/2026-06-24-expert-rubric-remediation.md`. [VERIFIED: repo files]

Source constraints for this phase:

- Build only the core artifact engine: service module, schemas, profile selection, validation, rendering, artifact writing, Soundscape-inspired evidence fixture, audit report builder, remediation planner, and implementation handoff builder. [VERIFIED: ROADMAP.md Phase 26]
- Do not register the workflow, wire the workflow runtime, or add the CLI in Phase 26; those are Phase 27 and Phase 28 responsibilities. [VERIFIED: ROADMAP.md Phases 27-28]
- The workflow must produce artifacts and must not execute implementation without later user approval. [VERIFIED: expert-rubric-remediation design spec]

## Summary

Phase 26 is a bounded Python service slice. It creates `services/expert_rubric_remediation.py` and `tests/test_expert_rubric_remediation.py`, then extends both with evidence fixture support and implementation-handoff construction. The approved implementation plan already provides exact public function names, schema constants, validation behavior, and the Soundscape evidence fixture, so no external library research is needed. [VERIFIED: docs/superpowers/plans/2026-06-24-expert-rubric-remediation.md]

The service should stay deterministic and file-backed: dictionaries in, dictionaries and markdown/json artifacts out. Validation functions must return explicit `validation_key`, `passed`, and `issues` fields because Phase 27 will call them from the workflow validation stage. [VERIFIED: services/workflow_orchestration.py validation patterns]

**Primary recommendation:** Implement the service under one new Python module with focused pytest coverage before adding any workflow registry/runtime wiring.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| Rubric schema constants and profile selection | `services/expert_rubric_remediation.py` | `tests/test_expert_rubric_remediation.py` | Service owns deterministic artifact shape; tests lock behavior before runtime wiring. |
| Rubric, audit, remediation, and handoff validation | `services/expert_rubric_remediation.py` | Phase 27 workflow validation skills | Validation must be callable directly in tests and later through workflow skill dispatch. |
| Markdown/json artifact writing | `services/expert_rubric_remediation.py` | target repo `.aios/reviews/{run_id}` | Service writes concrete files; workflow runtime later decides output root. |
| Soundscape visual-polish evidence fixture | `tests/fixtures/expert-rubric-remediation/` | `tests/test_expert_rubric_remediation.py` | Fixture proves evidence-backed audit and remediation without depending on the external Soundscape repo. |
| Implementation handoff payload | `services/expert_rubric_remediation.py` | Phase 28 CLI output | Handoff is a produced artifact, not an execution trigger. |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `json` | Python 3.12 stdlib | Deterministic JSON artifact serialization | Existing AIOS Python services avoid dependencies for local artifact transforms. |
| Python stdlib `pathlib.Path` | Python 3.12 stdlib | File and directory handling | Existing CLI/services use `Path` for repo-local artifact paths. |
| `pytest` | Existing repo tool | Contract and fixture tests | AIOS Python tests are pytest-based. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Ruff | Existing repo tool | Lint and format checks | Run targeted checks on the new service/test files. |
| BasedPyright | Existing repo tool | Type checking | Run targeted checks on touched Python modules where feasible. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Plain dictionaries | Pydantic/dataclasses | Extra dependency or conversion cost is unnecessary; workflow runtime already passes dictionaries. |
| Local fixture JSON | Live Soundscape checkout scan | Live scan belongs to later review usage; Phase 26 needs deterministic unit coverage. |

**Installation:** None.

## Architecture Patterns

### System Architecture Diagram

```text
TMCP-like packet fixture
  -> synthesize_rubric()
  -> validate_rubric()
  -> build_audit_report(evidence_items)
  -> validate_audit_report()
  -> build_remediation_plan()
  -> validate_remediation_plan()
  -> build_implementation_handoff()
  -> write_review_artifacts(output_dir)
```

### Existing Patterns To Follow

- Python services use `from __future__ import annotations`, explicit return types, and narrow helper functions. [VERIFIED: `.planning/codebase/CONVENTIONS.md`]
- Tests insert the repo root on `sys.path` when needed and use `tmp_path` for isolated file outputs. [VERIFIED: `tests/test_workflow_orchestration.py`, `tests/test_aios_cli.py`]
- Validation payloads should be explicit dictionaries rather than exceptions for expected artifact-quality failures. [VERIFIED: `services/workflow_orchestration.py` validation flow]

## Don't Hand-Roll

- Do not create a generic schema framework; direct schema constants and validation functions are enough for this slice.
- Do not compile TMCP packets here; Phase 26 consumes packet-shaped dictionaries only.
- Do not perform repo scans or inspect screenshots here; evidence items are explicit inputs.
- Do not execute implementation from the handoff; the handoff must say approval is required.

## Common Pitfalls

- Findings without evidence references must fail validation, not become low-confidence findings.
- Rubric dimensions must preserve `source_nodes`; otherwise Phase 27 cannot prove TMCP provenance.
- Artifact writing must create both JSON and markdown outputs with stable filenames.
- The Soundscape fixture must remain deterministic and compact; it is a contract fixture, not a broad external audit.
- Avoid relying on perfect positive sample data only; tests need failure cases for missing evidence and missing verification.

## Validation Architecture

| Layer | Command | Purpose |
|-------|---------|---------|
| Unit contracts | `uv run pytest tests/test_expert_rubric_remediation.py -q` | Proves schema constants, validation failures, fixture audit, remediation, handoff, and artifact writes. |
| Targeted lint | `uv run ruff check services/expert_rubric_remediation.py tests/test_expert_rubric_remediation.py` | Catches import/style issues in touched files. |
| Targeted format | `uv run ruff format --check services/expert_rubric_remediation.py tests/test_expert_rubric_remediation.py` | Ensures touched files are formatted. |
| Targeted type check | `uv run basedpyright services/expert_rubric_remediation.py tests/test_expert_rubric_remediation.py` | Checks the new service/test surface where feasible. |

## Security Notes

- Trust boundary: user-provided evidence JSON crosses into artifact rendering. Mitigation: coerce evidence references to strings and fail validation when evidence is missing.
- Trust boundary: `output_dir` writes files. Mitigation: use explicit caller-provided directory and stable filenames; Phase 27/28 own the repo-root selection.
- No network, database, secrets, subprocess execution, or external service calls belong in Phase 26.

## Open Questions (RESOLVED)

1. **Should Phase 26 create workflow registry entries?** RESOLVED: No. ROADMAP assigns registry/runtime work to Phase 27.
2. **Should Phase 26 scan Soundscape directly?** RESOLVED: No. Use the committed fixture from the approved plan.
3. **Should handoff execute implementation?** RESOLVED: No. It must require explicit user approval.
