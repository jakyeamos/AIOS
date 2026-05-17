---
phase: 03-workflow-execution-and-run-state
phase_number: "03"
type: research
updated: 2026-05-17
---

# Phase 3 Research

## Existing Strengths

- Runtime persistence already has durable rows for runs, invocations, events, writebacks, workflow learning, execution reports, and consistency evaluations.
- Explicit run/invocation/session linkage is already tested through `hook-stop` and runtime transition tests.
- The CLI already exposes lifecycle and invocation audits, so new execution-state improvements can remain visible without inventing a separate observability path.

## Existing Weaknesses

- The runtime currently treats terminal nuance too coarsely. `completed`, `failed`, `canceled`, and `superseded` exist, but partial completion and follow-up-needed outcomes still do not.
- Resume semantics are recoverable from the DB but not yet modeled as a first-class runtime contract.
- Closeout metadata is spread across tables; the system does not yet emit one run-centric closeout summary with checks, approvals, changed artifacts, unresolved deltas, and next actions.

## Code Observations

- `transition_run(...)` in `bin/aios_orchestration_runtime.py` is the central place to widen status semantics safely.
- `_lifecycle_audit_payload(...)` in `services/aios_cli.py` is the authoritative place to keep the lifecycle contract inspectable.
- `hook-stop.py` is already the best place to attach final outcome nuance because it sees memory summary, changed artifacts, writebacks, criteria results, and consistency evaluation in one session-close path.
- `orchestration_run_events` already carries `reason_json` and `metadata_json`, which can support resume snapshots and closeout evidence without inventing another event table.

## Recommended Phase Split

### 03-01
Expand lifecycle vocabulary and audit visibility.

### 03-02
Add explicit resume snapshot and next-action persistence.

### 03-03
Create governed closeout summaries and approval-aware execution evidence.

## Risks

- Lifecycle changes have to stay compatible with existing runtime tests, audits, and hooks.
- Adding new statuses without updating audits will make the contract look broken even when runtime behavior is correct.
- Resume metadata can become noisy if it duplicates evidence already stored elsewhere instead of summarizing it cleanly.
