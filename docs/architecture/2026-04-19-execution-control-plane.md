# Execution Control Plane Runtime

Date: 2026-04-19

## Run / Session Handshake Protocol

AIOS now treats the run identifier as a durable execution key rather than a read-time guess.

Protocol:

1. planning issues `orchestration_runs.id = run-*`
2. invocation issues `orchestration_invocations.id = invoke-*`
3. runtime startup persists:
   - `sessions.run_id`
   - `sessions.invocation_id`
   - `sessions.runtime_metadata_json`
4. hook stop resolves the run in this order:
   - payload `run_id`
   - `sessions.run_id`
   - payload `invocation_id`
   - legacy heuristic matcher only if none of the above exist

This materially reduces `hook-stop.py` heuristic glue. The fuzzy matcher still exists only for older/manual sessions without explicit runtime metadata.

## Lifecycle Event Model

Authoritative current state stays on `orchestration_runs.status`.
Authoritative history lives in `orchestration_run_events`.

Transitions:

- `planned` when the run record is created
- `ready` when the packet is persisted and backend is selected
- `in_progress` when `hook-session-start.py` sees the linked runtime session
- `completed` / `failed` / `canceled` when `hook-stop.py` receives terminal runtime payload
- `superseded` when a newer run replaces an older pending run

Structured terminal reasons are stored on:

- `orchestration_runs.status_reason_json`
- `orchestration_run_events.reason_json`

Timestamps are explicit:

- `started_at`
- `completed_at`
- `failed_at`
- `canceled_at`

## Invocation Backend Integration

Workflow and agent registry entries now expose `defaultBackendKey`.

Current real backend:

- `aios-managed-runtime`
  - transport: `managed_session`
  - launcher: `bin/aios-managed-run.py`
  - capabilities:
    - durable run/invocation handshake
    - managed session start/stop
    - invocation artifact write
    - cancel via PID / signal

Design intent:

- keep AIOS as the control plane
- let backends be replaceable execution adapters
- keep invocation metadata durable and inspectable in SQLite

## Approval Flow

Approval-gated writebacks now have both state and history.

State lives on `improvement_writebacks`:

- `status`
- `impact_scope`
- `decision_note`
- `decision_actor`
- `decision_at`
- `updated_at`

History lives on `improvement_writeback_events`.

UI requirements now satisfied on `/control`:

- inspect proposal
- inspect evidence and approval reason
- inspect scope/layer impact
- approve or reject
- keep rejected items inspectable

## Structured Evaluator Design

Evaluator storage:

- `consistency_evaluations`
- `consistency_findings`

Finding taxonomy:

- `likely_stale`
- `direct_contradiction`
- `soft_tension`

Current evaluator inputs:

- project truth from `PROJECT.md`
- topic graph topics when available
- latest memory update
- recent runs
- packet policy / packet sections
- workflow + agent policy context

The design is intentionally extensible:

- rule identity is explicit via `rule_key`
- provenance is stored per finding
- finding kind and severity are normalized
- UI can grow without changing the runtime contract

This is a structured first pass, not a general-purpose research engine.

## Legacy Heuristics That Remain

Only one meaningful heuristic remains in the core completion path:

- `bin/hook-stop.py` objective/token-overlap matching

Why it remains:

- historical/manual sessions may close without `run_id`
- removing fallback immediately would orphan those legacy runs

Current stance:

- explicit linkage is primary
- fallback is legacy
- usage is logged and tagged in reason metadata
