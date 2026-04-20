# AIOS Control Plane Handoff

Date: 2026-04-19
Scope: execution control-plane hardening pass

## What This Pass Changed

- Replaced run completion linkage with an explicit durable handshake:
  - `orchestration_runs.id` remains the stable run identifier
  - `sessions.run_id` and `sessions.invocation_id` now persist the runtime linkage
  - `orchestration_invocations` stores backend launch metadata, PID, session, and timestamps
  - `hook-stop.py` resolves the exact run from explicit linkage first
- Moved run lifecycle tracking onto first-class runtime events:
  - `orchestration_run_events`
  - structured `status_reason_json` on `orchestration_runs`
  - runtime-set `started_at`, `completed_at`, `failed_at`, `canceled_at`
- Added a real invocation backend path:
  - registry entries now carry `defaultBackendKey`
  - `aios-managed-runtime` launches `bin/aios-managed-run.py`
  - managed runtime opens a hook-linked session, writes an invocation artifact, and closes through explicit handshake
- Added approval review support:
  - `impact_scope`, `decision_note`, `decision_actor`, `decision_at`, `updated_at` on `improvement_writebacks`
  - `improvement_writeback_events` for proposal / approval / rejection history
  - `/control` now exposes approval review buttons and historical status
- Replaced heuristic drift/contradiction markers with structured evaluator outputs:
  - `consistency_evaluations`
  - `consistency_findings`
  - topic-graph markers now derive from stored findings instead of lightweight read-time heuristics
- Updated UI surfaces:
  - `/control` now shows backend registry, run invocation actions, approval queue, structured findings, and per-run event detail
  - Taski project surface now shows structured findings and pending approvals

## Runtime Protocol

### Handshake

1. `planTask()` creates `orchestration_runs.id = run-*`
2. Packet persistence moves the run from `planned` to `ready`
3. `invokeControlPlaneRun()` creates `orchestration_invocations.id = invoke-*`
4. managed runtime launches with:
   - `AIOS_RUN_ID`
   - `AIOS_INVOCATION_ID`
   - `AIOS_BACKEND_KEY`
   - `AIOS_DB`
5. `hook-session-start.py` stores `sessions.run_id` / `sessions.invocation_id` and transitions the run to `in_progress`
6. `hook-stop.py` resolves the run from explicit linkage, writes memory + writebacks + evaluator outputs, and transitions the run to the terminal status from runtime payload

### Lifecycle Model

- `planned`
  - emitted when the run row is created
- `ready`
  - emitted once the packet is persisted and backend is selected
- `in_progress`
  - emitted by `hook-session-start.py` on a linked runtime session start
- `completed`
  - emitted by `hook-stop.py` when runtime exits normally
- `failed`
  - emitted by `hook-stop.py` when runtime provides structured failure metadata
- `canceled`
  - emitted by `hook-stop.py` after managed runtime catches a cancel signal and closes itself cleanly
- `superseded`
  - emitted when a newer planned run replaces older `planned` / `ready` runs for the same project

All lifecycle transitions land in `orchestration_run_events`.

## Structured Evaluator

Current evaluator version is `v1`.

It compares:

- project truth from `PROJECT.md`
- recent indexed topics when available
- latest memory update for the run
- recent runs in the same project
- packet policy / token budget / packet sections
- workflow and agent policy context

Current finding kinds:

- `likely_stale`
- `direct_contradiction`
- `soft_tension`

Current rules are intentionally small and explicit:

- project truth still says a capability is missing while a completed run claims it landed
- recent related runs disagree on terminal outcomes
- runtime packet behavior diverges from compact-ranked default policy

## Approval Flow

1. writeback is created with `status = proposed` or `pending_approval`
2. review UI shows:
   - proposal summary
   - evidence
   - approval reason
   - impact scope / layer
3. operator chooses `Approve` or `Reject`
4. decision updates the writeback row and appends `improvement_writeback_events`
5. rejected proposals remain visible as historical decisions

## Key Files

- [bin/aios_orchestration_runtime.py](/Users/jakyeamos/AIOS/bin/aios_orchestration_runtime.py)
- [bin/aios-managed-run.py](/Users/jakyeamos/AIOS/bin/aios-managed-run.py)
- [bin/hook-session-start.py](/Users/jakyeamos/AIOS/bin/hook-session-start.py)
- [bin/hook-stop.py](/Users/jakyeamos/AIOS/bin/hook-stop.py)
- [tests/test_orchestration_runtime.py](/Users/jakyeamos/AIOS/tests/test_orchestration_runtime.py)
- [aios-ui/server/aios/control-plane.ts](/Users/jakyeamos/AIOS/aios-ui/server/aios/control-plane.ts)
- [aios-ui/server/aios/runtime.ts](/Users/jakyeamos/AIOS/aios-ui/server/aios/runtime.ts)
- [aios-ui/server/aios/schema.ts](/Users/jakyeamos/AIOS/aios-ui/server/aios/schema.ts)
- [aios-ui/components/control/ControlPlaneStudio.tsx](/Users/jakyeamos/AIOS/aios-ui/components/control/ControlPlaneStudio.tsx)
- [aios-ui/components/projects/TaskiProjectSurface.tsx](/Users/jakyeamos/AIOS/aios-ui/components/projects/TaskiProjectSurface.tsx)

## Legacy Fallback That Still Remains

- `bin/hook-stop.py` still has the old objective/token-overlap matcher as a clearly marked legacy fallback
- it is only used when a session closes without `run_id` or `sessions.run_id`
- when used, it logs that legacy linkage occurred and records that fact in the terminal run reason metadata

## Recommended Next Steps

1. Add more backend adapters that emit the same handshake contract as `aios-managed-runtime`
2. Add finding resolution / acknowledgement workflow so structured evaluator outputs can be closed intentionally
3. Add deeper per-run delta inspection for packet sections, topic changes, writeback applications, and file-level outputs
