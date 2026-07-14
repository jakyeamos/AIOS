---
title: Govern the Start Work Verify Slice
type: task
status: resolved
claim: /root (2026-07-14)
resolved: 2026-07-14
blocked_by:
  - 009-ship-read-only-v2-operator-shell
blocks:
  - 011-gated-review-and-closeout
---

# Govern the Start Work Verify Slice

## Question

Can a real task move through the canonical route, packet, run, invocation,
verification, and resume contracts with foreign-key-safe ordering and no
untracked side effects?

## Scope

- Make `start-work` safe against the canonical foreign-key schema.
- Preserve route ambiguity/unsupported blocking before durable creation.
- Prove packet, run, invocation, event, evidence, verifier, and resume linkage.
- Exercise verification through the registered project contract.
- Keep UI mutations disabled; the Python owner remains the only write path.

## Completion Evidence

- Clear, ambiguous, and unsupported route fixtures remain explicit; risk-bearing tasks retain the packet escalation contract.
- A foreign-key-enforced start-work fixture creates one coherent run envelope.
- Verification records source-backed evidence and truthful completion/failure.
- Blocked/partial state retains a resume snapshot and next action.
- Focused Python tests, static checks, and an executable integration proof pass.

## Resolution

M4 is complete at the Python-owned broker boundary. `start-work` now persists
the run and packet before creating the invocation, then links
`orchestration_runs.active_invocation_id` only after its foreign-key target
exists. Current-session linkage is rejected when the session belongs to a
different routed project, preserving provenance.

Evidence:

- `tests/test_m4_start_work.py` builds the full `schema.sql` with
  `PRAGMA foreign_keys=ON`, starts a routed task with an open session, asserts
  run/packet/invocation/event linkage and zero `PRAGMA foreign_key_check`
  findings, preserves partial-state resume snapshots, blocks cross-project
  sessions, and completes `verify_run` with evidence and a verifier artifact.
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_aios_cli.py tests/test_run_verification.py tests/test_orchestration_runtime.py tests/test_daily_flow.py tests/test_task_routing.py` — 155 passed.
- Focused Ruff and BasedPyright checks for the touched Python/tests — passed.
- Ambiguous and unsupported route tests continue to prove no durable rows are
  created before routing is safe.

M5 is next: approval, capability, loopback, egress, writeback, and closeout
enforcement. The v2 UI remains read-only until that gate is executable.
