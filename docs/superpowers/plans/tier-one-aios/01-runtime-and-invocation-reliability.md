# Runtime And Invocation Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make AIOS a deterministic execution layer for agent work, with reliable run/session/invocation handshakes and inspectable lifecycle states.

**Architecture:** Treat `orchestration_runs`, `orchestration_invocations`, `sessions`, and `orchestration_run_events` as the runtime spine. All launch paths must emit the same handshake contract and lifecycle events. Legacy heuristic matching remains read-only for historical sessions.

**Tech Stack:** Python, SQLite, pytest, `bin/aios-managed-run.py`, `bin/aios_orchestration_runtime.py`, `services/aios_cli.py`, Next.js runtime inspection.

---

## Files

- Modify: `bin/aios-managed-run.py`
- Modify: `bin/aios_orchestration_runtime.py`
- Modify: `bin/hook-session-start.py`
- Modify: `bin/hook-stop.py`
- Modify: `services/aios_cli.py`
- Modify: `services/invocation_backends.py`
- Modify: `tests/test_orchestration_runtime.py`
- Modify: `tests/test_aios_cli.py`
- Modify: `aios-ui/server/aios/runtime.ts`
- Modify: `aios-ui/server/routers/control-plane.ts`
- Modify: `aios-ui/components/control/ControlPlaneStudio.tsx`
- Modify after each code commit: `PROJECT.md`

## Current Failure To Resolve First

The full test suite currently has a managed runtime failure:

```text
test_managed_runtime_completes_via_explicit_handshake
expected orchestration_runs.status == "completed"
actual: "ready"
```

This is a tier-one blocker because the system cannot be trusted as an execution layer if a managed run can finish without transitioning the authoritative run record.

### Task 1: Repair Managed Runtime Completion

**Files:**
- Modify: `bin/aios-managed-run.py`
- Modify: `bin/aios_orchestration_runtime.py`
- Test: `tests/test_orchestration_runtime.py`

- [ ] **Step 1: Run the failing test**

```bash
uv run pytest tests/test_orchestration_runtime.py::test_managed_runtime_completes_via_explicit_handshake -q
```

Expected: fail with run status staying `ready`.

- [ ] **Step 2: Trace runtime closeout**

Inspect where `bin/aios-managed-run.py` calls runtime transition helpers:

```bash
rg -n "transition_run|completed|update_invocation|link_session_runtime" bin/aios-managed-run.py bin/aios_orchestration_runtime.py
```

Expected: identify the missing or non-persisting transition path.

- [ ] **Step 3: Add regression assertion if missing**

Ensure `tests/test_orchestration_runtime.py::test_managed_runtime_completes_via_explicit_handshake` asserts:

```python
assert run[0] == "completed"
assert run[1] is not None
assert run[2] == invocation_id
assert run[3] is not None
```

- [ ] **Step 4: Implement deterministic closeout**

Make `aios-managed-run.py` call a single runtime helper that:

- transitions run to `in_progress` when the session starts
- links `sessions.run_id` and `sessions.invocation_id`
- updates invocation status to `running`
- records a completion report artifact
- transitions run to `completed`
- updates invocation status to `completed`

The transition must go through `bin/aios_orchestration_runtime.py::transition_run`, not direct ad hoc SQL.

- [ ] **Step 5: Verify focused test**

```bash
uv run pytest tests/test_orchestration_runtime.py::test_managed_runtime_completes_via_explicit_handshake -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add bin/aios-managed-run.py bin/aios_orchestration_runtime.py tests/test_orchestration_runtime.py
git commit -m "fix(runtime): complete managed runs through explicit handshake"
```

- [ ] **Step 7: Update truth file**

Add a dated note to `PROJECT.md` explaining that managed runtime closeout now transitions the authoritative run and invocation records.

```bash
git add PROJECT.md
git commit -m "docs: record managed runtime closeout fix"
```

### Task 2: Enforce Invocation Contract At Start-Work

**Files:**
- Modify: `services/invocation_backends.py`
- Modify: `services/aios_cli.py`
- Test: `tests/test_aios_cli.py`

- [ ] **Step 1: Add failing CLI test**

Add a test that starts work with each non-deprecated backend and asserts the returned payload includes:

```python
required = {
    "run_id",
    "invocation_id",
    "backend_key",
    "objective",
    "project_id",
    "workflow_key",
    "packet_id",
}
```

Expected behavior:

- valid backend returns `EXIT_OK`
- unknown backend returns usage error or an explicit fallback field, not silent defaulting
- deprecated backend is allowed only if marked deprecated in output

- [ ] **Step 2: Reject unknown backends**

Change `get_invocation_backend()` so unknown backend keys do not silently fall back to Codex. Use an explicit exception or return object that lets CLI emit a clear error.

- [ ] **Step 3: Verify**

```bash
uv run pytest tests/test_aios_cli.py::test_invocation_audit_and_backend_label_contract -q
```

- [ ] **Step 4: Commit and truth update**

```bash
git add services/invocation_backends.py services/aios_cli.py tests/test_aios_cli.py
git commit -m "fix(cli): reject unknown invocation backends"
git add PROJECT.md
git commit -m "docs: record strict backend validation"
```

### Task 3: Raise Handshake Coverage

**Files:**
- Modify: `bin/hook-session-start.py`
- Modify: `bin/hook-stop.py`
- Modify: `services/aios_cli.py`
- Test: `tests/test_orchestration_runtime.py`
- Test: `tests/test_aios_cli.py`

- [ ] **Step 1: Define current-period coverage**

Add coverage fields to `invocation-audit`:

```json
{
  "current_period_sessions": 0,
  "current_period_linked_sessions": 0,
  "current_period_coverage": 0.0
}
```

Use a 30-day default period and preserve all-time coverage.

- [ ] **Step 2: Start every serious session through a run**

Update session-start logic so sessions with a non-empty objective can either:

- link to an existing ready run by explicit `AIOS_RUN_ID`
- create a minimal run/invocation packet
- mark itself as `unrouted` with an explicit missing reason

Do not re-enable heuristic matching for new sessions.

- [ ] **Step 3: Stop hook refuses ambiguous closeout**

Update `hook-stop.py` so new sessions without `run_id` are recorded as `unrouted` runtime findings rather than silently ignored.

- [ ] **Step 4: Verify**

```bash
uv run pytest tests/test_orchestration_runtime.py tests/test_aios_cli.py -q
```

- [ ] **Step 5: Commit and truth update**

```bash
git add bin/hook-session-start.py bin/hook-stop.py services/aios_cli.py tests/test_orchestration_runtime.py tests/test_aios_cli.py
git commit -m "feat(runtime): report and improve explicit handshake coverage"
git add PROJECT.md
git commit -m "docs: record handshake coverage policy"
```

### Task 4: Lifecycle State Mutation API

**Files:**
- Modify: `bin/aios_orchestration_runtime.py`
- Modify: `services/aios_cli.py`
- Modify: `aios-ui/server/aios/runtime.ts`
- Test: `tests/test_orchestration_runtime.py`
- Test: `tests/test_aios_cli.py`

- [ ] **Step 1: Add state transition tests**

Cover transitions:

- `in_progress -> waiting_for_user`
- `in_progress -> waiting_for_tool`
- `in_progress -> blocked`
- `in_progress -> failed_validation`
- `ready -> superseded`

Each transition must insert `orchestration_run_events` and update `status_reason_json`.

- [ ] **Step 2: Implement shared Python transition validation**

Define valid transitions in one place in `bin/aios_orchestration_runtime.py`.

- [ ] **Step 3: Mirror status vocabulary in CLI audit**

Ensure `lifecycle-audit` uses the same canonical list.

- [ ] **Step 4: Mirror status vocabulary in TypeScript**

Use the same vocabulary in `aios-ui/server/aios/runtime.ts` and avoid UI-only states that do not exist in the backend.

- [ ] **Step 5: Verify**

```bash
uv run pytest tests/test_orchestration_runtime.py tests/test_aios_cli.py -q
cd aios-ui && pnpm lint
```

### Tier-One Runtime Acceptance

- [ ] full Python suite green
- [ ] managed runtime completion test green
- [ ] unknown invocation backends are rejected explicitly
- [ ] new sessions either link to a run or record an unrouted finding
- [ ] `invocation-audit` shows current-period coverage and missing reasons
- [ ] `lifecycle-audit` reports no unsupported states
- [ ] UI and CLI show the same lifecycle vocabulary
